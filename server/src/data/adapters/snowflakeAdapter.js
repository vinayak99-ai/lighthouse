import snowflake from "snowflake-sdk";
import { toPositionalBinds } from "../sqlBinding.js";

// Snowflake's own hard stop -- the warehouse itself aborts a query past this,
// independent of anything in this process. This is the real guarantee; it
// works even if our own app-level timeout below never runs (a crashed
// process, a killed container).
const STATEMENT_TIMEOUT_SECONDS = Number(process.env.SNOWFLAKE_STATEMENT_TIMEOUT_SECONDS || 60);
// A few seconds of slack past Snowflake's own timeout, so in the normal case
// Snowflake's server-side abort fires first and this is just a backstop for
// the case it somehow doesn't (a network partition, a stuck session).
const APP_LEVEL_TIMEOUT_MS = (STATEMENT_TIMEOUT_SECONDS + 5) * 1000;
// Separate from the above: how long to wait for the connection itself to be
// established (including the initial ALTER SESSION call). Found by actually
// testing against an unreachable account -- the driver's own default retry
// policy is ~300s, which would otherwise leave a chat request hanging for
// up to five minutes before the query-level timeout above ever gets a
// chance to run.
const CONNECT_TIMEOUT_MS = Number(process.env.SNOWFLAKE_CONNECT_TIMEOUT_SECONDS || 20) * 1000;

const WRITE_OR_DDL_KEYWORDS =
  /\b(INSERT|UPDATE|DELETE|MERGE|CREATE|DROP|ALTER|TRUNCATE|GRANT|REVOKE|COPY\s+INTO|CALL|EXECUTE\s+IMMEDIATE)\b/i;

export class UnsafeQueryError extends Error {}

/**
 * Defense-in-depth, not the real guarantee. The actual safety boundary is
 * the Snowflake role this app connects as: it should be a dedicated,
 * read-only role with SELECT-only grants (see snowflakeSetup.sql) -- that
 * holds even if this check has a bug. This just fails fast and loudly for
 * anything that obviously shouldn't be running here.
 */
export function assertSelectOnly(sql) {
  const statement = sql.trim().replace(/;+\s*$/, "");
  if (statement.includes(";")) {
    throw new UnsafeQueryError("Refusing to run multiple SQL statements in one call.");
  }
  if (!/^(WITH|SELECT)\b/i.test(statement)) {
    throw new UnsafeQueryError("Refusing to run a statement that isn't a SELECT (or a WITH...SELECT).");
  }
  if (WRITE_OR_DDL_KEYWORDS.test(statement)) {
    throw new UnsafeQueryError("Refusing to run a statement containing a write/DDL keyword.");
  }
}

let _connectionPromise = null;

function connect() {
  return new Promise((resolve, reject) => {
    let settled = false;
    const timer = setTimeout(() => {
      if (settled) return;
      settled = true;
      reject(new Error(`Could not establish a Snowflake connection within ${CONNECT_TIMEOUT_MS / 1000}s.`));
    }, CONNECT_TIMEOUT_MS);

    const connection = snowflake.createConnection({
      account: process.env.SNOWFLAKE_ACCOUNT,
      username: process.env.SNOWFLAKE_USER,
      password: process.env.SNOWFLAKE_PASSWORD,
      role: process.env.SNOWFLAKE_ROLE,
      warehouse: process.env.SNOWFLAKE_WAREHOUSE,
      database: process.env.SNOWFLAKE_DATABASE,
      schema: process.env.SNOWFLAKE_SCHEMA,
    });

    connection.connect((err, conn) => {
      if (settled) return; // the connect timeout above already fired
      if (err) {
        settled = true;
        clearTimeout(timer);
        return reject(err);
      }
      // Session-level enforcement of the statement cap -- applies to every
      // query this connection runs from here on, not just the next one.
      conn.execute({
        sqlText: `ALTER SESSION SET STATEMENT_TIMEOUT_IN_SECONDS = ${STATEMENT_TIMEOUT_SECONDS}`,
        complete: (timeoutErr) => {
          if (settled) return;
          settled = true;
          clearTimeout(timer);
          if (timeoutErr) return reject(timeoutErr);
          resolve(conn);
        },
      });
    });
  });
}

// connectFn is injectable so tests can exercise the cache/retry behavior
// without a real snowflake-sdk connection.
export function getConnection(connectFn = connect) {
  if (!_connectionPromise) {
    _connectionPromise = connectFn().catch((err) => {
      // Don't cache a permanent failure -- a transient network issue
      // shouldn't poison every query for the rest of the process's life.
      // The next call gets a fresh attempt.
      _connectionPromise = null;
      throw err;
    });
  }
  return _connectionPromise;
}

// timeoutMs is a parameter (not read from the module constant directly) so
// tests can exercise the cancel-on-timeout path in milliseconds instead of
// waiting out a real 60+ second production timeout.
function executeWithTimeout(connection, sql, binds, timeoutMs = APP_LEVEL_TIMEOUT_MS) {
  return new Promise((resolve, reject) => {
    let settled = false;

    const statement = connection.execute({
      sqlText: sql,
      binds,
      complete: (err, _stmt, rows) => {
        if (settled) return; // the app-level timeout below already fired and cancelled this
        settled = true;
        clearTimeout(timer);
        if (err) return reject(err);
        resolve(rows);
      },
    });

    const timer = setTimeout(() => {
      if (settled) return;
      settled = true;
      statement.cancel(() => {}); // best-effort: stop it burning warehouse credits after we've given up
      reject(new Error(`Query exceeded the ${timeoutMs / 1000}s application-level timeout and was cancelled.`));
    }, timeoutMs);
  });
}

export const snowflakeAdapter = {
  dialect: "snowflake",

  bucketExpr(granularity) {
    if (granularity === "week") return "DATE_TRUNC('WEEK', date)";
    if (granularity === "month") return "DATE_TRUNC('MONTH', date)";
    return "date";
  },

  async runQuery(sqlWithNamedParams, params) {
    assertSelectOnly(sqlWithNamedParams);
    const { sql, binds } = toPositionalBinds(sqlWithNamedParams, params);
    const connection = await getConnection();
    return executeWithTimeout(connection, sql, binds);
  },
};

// Exposed for tests -- lets a test exercise executeWithTimeout's cancel path
// and getConnection's retry-after-failure behavior without a real
// snowflake-sdk connection.
export const __testables = {
  executeWithTimeout,
  getConnection,
  resetConnectionCache: () => {
    _connectionPromise = null;
  },
};
