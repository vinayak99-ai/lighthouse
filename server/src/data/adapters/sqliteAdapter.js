import { getDb } from "../db.js";

// better-sqlite3 is synchronous, but the adapter interface is async so
// queryEngine.js can treat every data source (this one, or Snowflake)
// identically -- the caller always awaits runQuery().
export const sqliteAdapter = {
  dialect: "sqlite",

  bucketExpr(granularity) {
    if (granularity === "week") return "date(date, '-' || ((strftime('%w', date) + 6) % 7) || ' days')";
    if (granularity === "month") return "strftime('%Y-%m-01', date)";
    return "date";
  },

  async runQuery(sql, params) {
    return getDb().prepare(sql).all(params);
  },
};
