# Lighthouse Analyst

A conversational data analyst, in the shape of Artemis's "Analyst" chat: ask a
question in plain English, the backend picks one of ten typed data tools,
builds the query itself, runs it against a stubbed blockchain dataset, and
renders the answer as a chart.

```
User → React chat UI → POST /api/chat → Claude (tool-calling loop)
                                            │
                                            ├─ query_stablecoin_supply
                                            ├─ query_defi_tvl
                                            ├─ query_perpetuals
                                            ├─ query_prediction_markets      each: typed args →
                                            ├─ query_rwa                     parameterized SQL →
                                            ├─ query_protocol_revenue        SQLite
                                            ├─ query_chain_activity
                                            ├─ query_staking
                                            ├─ query_nft_volume
                                            ├─ query_x402_agentic_payments
                                            │
                                            └─ render_chart(chart_type, series, data, insight)
                                                   │
                                                   ▼
                                          chart JSON → React → Recharts
```

The model never writes raw SQL. Every data tool takes structured arguments
(entities, metric, date range, granularity, group-by) and the backend itself
builds and runs the parameterized query — the same shape of contract a real
analyst product would want between an LLM and a production database.

## Why it works without an API key

If `ANTHROPIC_API_KEY` isn't set, `/api/chat` falls back to a deterministic
keyword router (`server/src/chat/fallbackRouter.js`) that picks the same
tools a model would, from the same keyword/entity cues, and renders the same
chart contract. Point the client at a live Anthropic key and the tool-calling
orchestrator (`server/src/chat/orchestrator.js`) takes over transparently —
the frontend doesn't know or care which one answered.

## The data

`server/src/data/seed.js` generates ~230 days (2026-01-01 to 2026-08-22) of
daily stub data across 10 domains — stablecoin supply, DeFi TVL, perpetuals
open interest/volume, prediction market volume, tokenized RWA value, protocol
revenue, chain activity, staking, NFT volume, and x402 agentic payment
volume — as a random walk with drift, weekly seasonality, and per-entity
seeds, loaded into SQLite (`better-sqlite3`). It is not real chain data; it's
shaped to look plausible so charts have something realistic to show.

One correctness rule worth calling out: **stock metrics (supply, TVL,
tokenized value, open interest, staked ETH, active addresses) are averaged
when bucketed into a week/month, never summed** — summing a point-in-time
level across days inflates it by the bucket size. Flow metrics (volume,
fees, revenue, transaction/sales counts) are summed, correctly. See
`server/src/tools/tools.js` and the regression tests in `tools.test.js`.

## Chart quality

Chart components (`client/src/charts/`) follow a validated design-system
palette: 8 categorical hues in fixed slot order (never reassigned by rank),
run through `validate_palette.js`'s colorblind-safety + contrast checks for
both light and dark surfaces before being wired in as CSS custom properties
(`client/src/theme.css`). Mark specs — 2px lines, ≥8px hover markers, 4px
rounded bar caps, hairline gridlines, a 2px surface gap between stacked
segments — are fixed across every chart type. Every chart ships a legend
(2+ series), a hover tooltip with a crosshair on line/area, and a table-view
toggle as the accessibility fallback. Stacked bars re-bucket to week/month
past ~2 weeks of daily data so they don't collapse into an unreadable
barcode of hairline bars.

## Running it

```bash
npm install --workspaces
npm run seed           # populate server/src/data/lighthouse.sqlite
npm run dev:server      # http://localhost:8787
npm run dev:client      # http://localhost:5173 (proxies /api to the server)
```

Copy `server/.env.example` to `server/.env` and set `ANTHROPIC_API_KEY` to
run on live Claude tool-calling instead of the offline router.

Run the backend tests (10 data tools + the stock/flow aggregation
regression) with:

```bash
npm run test:server
```

## Known simplifications

- Follow-up turns send the prior plain-text conversation, not the model's
  internal tool-call trace — so "make that a stacked bar instead" works
  because the model re-derives the query, not because it remembers the
  exact prior rows.
- The offline router is intentionally simple (keyword + entity substring
  matching); it's there so the app is fully demoable with zero external
  dependencies, not as a replacement for the model-driven path.
