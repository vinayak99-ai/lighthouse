-- One-time Snowflake setup for Lighthouse Analyst.
-- Run this ONCE in your Snowflake account as a role with enough privilege to
-- create warehouses, roles, resource monitors, and grants (typically
-- SECURITYADMIN + SYSADMIN, or ACCOUNTADMIN). Replace <PLACEHOLDERS> with
-- your own values before running.
--
-- What this buys you (see README.md's "Connecting to real Snowflake"):
--   1. Compute isolation  -- a dedicated warehouse so a slow/heavy query from
--      this app can never starve any other workload's compute.
--   2. A hard runtime cap -- STATEMENT_TIMEOUT_IN_SECONDS aborts any query
--      server-side, independent of whether this app's own process is even
--      still running.
--   3. A cost ceiling      -- a resource monitor auto-suspends the warehouse
--      once it crosses a credit budget.
--   4. Read-only by construction -- the role this app connects as can only
--      SELECT. Even a bug in the application code, or a compromised query,
--      cannot write, alter, or drop anything -- the database enforces this,
--      not application logic.

-- 1. A small, dedicated warehouse. XSMALL auto-suspends fast (60s) so it
--    doesn't burn credits sitting idle between chat questions.
CREATE WAREHOUSE IF NOT EXISTS LIGHTHOUSE_WH
  WAREHOUSE_SIZE = 'XSMALL'
  AUTO_SUSPEND = 60
  AUTO_RESUME = TRUE
  INITIALLY_SUSPENDED = TRUE
  STATEMENT_TIMEOUT_IN_SECONDS = 60 -- belt-and-suspenders: also set at the role level below
  COMMENT = 'Dedicated compute for Lighthouse Analyst -- isolated from every other workload.';

-- 2. A resource monitor capping this warehouse's monthly spend. Adjust
--    CREDIT_QUOTA to whatever budget makes sense; the SUSPEND action stops
--    the warehouse from accepting new queries once the quota is hit (queries
--    already running are allowed to finish; add a second SUSPEND_IMMEDIATE
--    trigger at a higher threshold if you want a harder cutoff).
CREATE RESOURCE MONITOR IF NOT EXISTS LIGHTHOUSE_MONITOR
  WITH CREDIT_QUOTA = 50
  FREQUENCY = MONTHLY
  START_TIMESTAMP = IMMEDIATELY
  TRIGGERS
    ON 80 PERCENT DO NOTIFY
    ON 100 PERCENT DO SUSPEND
    ON 110 PERCENT DO SUSPEND_IMMEDIATE;

ALTER WAREHOUSE LIGHTHOUSE_WH SET RESOURCE_MONITOR = LIGHTHOUSE_MONITOR;

-- 3. A read-only role. This is the actual safety guarantee -- the
--    application-level SELECT-only guard in snowflakeAdapter.js is defense
--    in depth on top of this, not a substitute for it.
CREATE ROLE IF NOT EXISTS LIGHTHOUSE_READONLY
  COMMENT = 'Read-only role for Lighthouse Analyst. SELECT only -- never grant write/DDL privileges to this role.';

GRANT USAGE ON WAREHOUSE LIGHTHOUSE_WH TO ROLE LIGHTHOUSE_READONLY;
GRANT USAGE ON DATABASE <YOUR_DATABASE> TO ROLE LIGHTHOUSE_READONLY;
GRANT USAGE ON SCHEMA <YOUR_DATABASE>.<YOUR_SCHEMA> TO ROLE LIGHTHOUSE_READONLY;
GRANT SELECT ON ALL TABLES IN SCHEMA <YOUR_DATABASE>.<YOUR_SCHEMA> TO ROLE LIGHTHOUSE_READONLY;
-- Keep future tables read-only too, without re-running this grant by hand:
GRANT SELECT ON FUTURE TABLES IN SCHEMA <YOUR_DATABASE>.<YOUR_SCHEMA> TO ROLE LIGHTHOUSE_READONLY;

-- 4. A dedicated service user for the app, with the read-only role as its
--    ONLY role and its default. Use key-pair auth in production instead of a
--    password (see Snowflake's docs on key-pair authentication) -- swap the
--    PASSWORD line below for RSA_PUBLIC_KEY if you do.
CREATE USER IF NOT EXISTS LIGHTHOUSE_APP
  PASSWORD = '<STRONG_PASSWORD_OR_USE_KEY_PAIR_AUTH>'
  DEFAULT_ROLE = LIGHTHOUSE_READONLY
  DEFAULT_WAREHOUSE = LIGHTHOUSE_WH
  MUST_CHANGE_PASSWORD = FALSE
  COMMENT = 'Service account for Lighthouse Analyst. Only ever grant it LIGHTHOUSE_READONLY.';

GRANT ROLE LIGHTHOUSE_READONLY TO USER LIGHTHOUSE_APP;

-- Verify: this should show SELECT as the only privilege on your tables.
-- SHOW GRANTS TO ROLE LIGHTHOUSE_READONLY;

-- Note on schema: Lighthouse's 10 data tools (server/src/tools/tools.js)
-- expect specific table/column shapes (see server/src/data/db.js's SCHEMA
-- for the exact stub-data shape they were built against, e.g.
-- stablecoin_supply(date, issuer, chain, supply_usd)). Point <YOUR_SCHEMA>
-- at tables shaped the same way, or adjust the `table`/`entityCol`/
-- `valueCol` arguments each tool passes into queryEngine.js's
-- runGroupedTimeSeries() to match your actual warehouse schema.
