// queryEngine.js builds SQL with named placeholders (@name) because that's
// what better-sqlite3 accepts natively. Snowflake's driver instead wants
// positional "?" placeholders with an ordered binds array. This is the pure,
// independently-testable bridge between the two -- it never touches a
// network connection, so it's covered by unit tests without any real
// Snowflake credentials.
export function toPositionalBinds(sql, params) {
  const binds = [];
  const converted = sql.replace(/@(\w+)/g, (match, name) => {
    if (!(name in params)) {
      throw new Error(`Missing bind parameter "${name}" for placeholder ${match}`);
    }
    binds.push(params[name]);
    return "?";
  });
  return { sql: converted, binds };
}
