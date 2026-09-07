import { sqliteAdapter } from "./adapters/sqliteAdapter.js";
import { snowflakeAdapter } from "./adapters/snowflakeAdapter.js";

// Same selection pattern as chat/orchestrator.js's LLM provider picker:
// an explicit override wins, otherwise presence of Snowflake credentials
// decides, defaulting to the SQLite stub data so the app runs with zero
// external dependencies out of the box.
export function getDataSource() {
  const forced = process.env.LIGHTHOUSE_DATA_SOURCE?.toLowerCase();
  if (forced === "snowflake") return snowflakeAdapter;
  if (forced === "sqlite") return sqliteAdapter;
  return process.env.SNOWFLAKE_ACCOUNT ? snowflakeAdapter : sqliteAdapter;
}
