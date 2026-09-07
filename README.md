# Lighthouse Analyst

A conversational data analyst, in the shape of Artemis's "Analyst" chat: ask a
question in plain English, the backend picks one of ten typed data tools,
builds the query itself, runs it against a stubbed blockchain dataset, and
renders the answer as a chart.

```
User → React chat UI → POST /api/chat → Claude or GPT (tool-calling loop)
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

## Choosing a model provider

`server/src/chat/orchestrator.js` is a thin dispatcher over two interchangeable
tool-calling loops that both speak the same tool/`render_chart` contract
(`server/src/tools/tools.js`):

- `server/src/chat/providers/anthropic.js` — Claude, via `@anthropic-ai/sdk`.
  Tool results go back as `tool_result` content blocks.
- `server/src/chat/providers/openai.js` — GPT, via the `openai` package's Chat
  Completions API. The same `TOOL_DEFINITIONS` get reshaped into OpenAI's
  `{ type: "function", function: {...} }` tool format in that file; tool
  results go back as one `{ role: "tool", tool_call_id, content }` message
  per call instead of a single content block.

Selection is by environment variable — set **one** of these in `server/.env`
(copy `server/.env.example`):

```bash
ANTHROPIC_API_KEY=sk-ant-...   # picked first if both are set
OPENAI_API_KEY=sk-...
```

If both are set, Anthropic wins by default; force a specific one with
`LLM_PROVIDER=openai` or `LLM_PROVIDER=anthropic`. Override the model per
provider with `ANTHROPIC_MODEL` / `OPENAI_MODEL` (defaults: `claude-sonnet-5`,
`gpt-4o`). `GET /api/health` reports which provider and model are active.

Adding a third provider means writing one more file under
`server/src/chat/providers/` with a `runConversation(history, apiKey)` export
and wiring it into `resolveProvider()` — nothing in the tools, the system
prompt, or the frontend needs to change.

## Why it works without any API key

If neither key is set, `/api/chat` falls back to a deterministic keyword
router (`server/src/chat/fallbackRouter.js`) that picks the same tools a model
would, from the same keyword/entity cues, and renders the same chart
contract. The frontend doesn't know or care which of the three answered.

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

## Self-correcting chart choices

`server/src/tools/chartValidator.js` codifies the same rules the system
prompt asks the model to follow (area fill only for a single series,
stacked bars capped before they read as a barcode, too many overlapping
lines should be `small_multiples` instead) as an enforced check rather than
prose the model might not perfectly follow. Both LLM providers run it the
instant `render_chart` is called: a failure never reaches the chat -- it
goes back to the model as a corrective tool result, and the model retries
within the same turn (capped at 2 corrections, so a stubborn model still
gets an answer instead of nothing). The user only ever sees the corrected
result. This keeps the "generate, self-check, correct" loop other agentic
charting tools use, without turning Lighthouse into a multi-step wizard --
one question still gets one answer, just a more reliably well-formed one.
The offline router's own heuristics are asserted against the same validator
as a regression guard (`fallbackRouter.test.js`).

## Running it

```bash
npm install --workspaces
npm run seed           # populate server/src/data/lighthouse.sqlite
npm run dev:server      # http://localhost:8787
npm run dev:client      # http://localhost:5173 (proxies /api to the server)
```

Copy `server/.env.example` to `server/.env` and set `ANTHROPIC_API_KEY` or
`OPENAI_API_KEY` to run on live tool-calling instead of the offline router
(see "Choosing a model provider" above).

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
