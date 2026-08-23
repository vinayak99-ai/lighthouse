import "dotenv/config";
import express from "express";
import cors from "cors";
import { ensureSchema, getDb } from "./data/db.js";
import { seedAll } from "./data/seed.js";
import { runConversation, hasApiKey, CHAT_MODEL } from "./chat/orchestrator.js";
import { routeOffline } from "./chat/fallbackRouter.js";
import { STARTER_DOMAINS } from "./starters.js";

const app = express();
app.use(cors());
app.use(express.json({ limit: "1mb" }));

const PORT = process.env.PORT || 8787;

// Seed on boot if the DB is empty, so a fresh checkout works with zero setup.
const db = ensureSchema(getDb());
const row = db.prepare("SELECT COUNT(*) c FROM stablecoin_supply").get();
if (row.c === 0) {
  console.log("Empty database detected — seeding stub blockchain dataset...");
  seedAll();
}

app.get("/api/health", (req, res) => {
  res.json({ ok: true, mode: hasApiKey() ? "live" : "offline-demo", model: hasApiKey() ? CHAT_MODEL : null });
});

app.get("/api/starters", (req, res) => {
  res.json({ domains: STARTER_DOMAINS });
});

app.post("/api/chat", async (req, res) => {
  const { messages } = req.body || {};
  if (!Array.isArray(messages) || messages.length === 0) {
    return res.status(400).json({ error: "Body must include a non-empty `messages` array." });
  }

  try {
    if (hasApiKey()) {
      const result = await runConversation(messages);
      return res.json({ ...result, mode: "live" });
    }
    const lastUser = [...messages].reverse().find((m) => m.role === "user");
    const text = Array.isArray(lastUser?.content)
      ? lastUser.content.map((b) => b.text || "").join(" ")
      : lastUser?.content || "";
    const result = routeOffline(text);
    return res.json({ ...result, mode: "offline-demo" });
  } catch (err) {
    console.error(err);
    return res.status(500).json({ error: err.message || "Something went wrong." });
  }
});

app.listen(PORT, () => {
  console.log(`Lighthouse Analyst server listening on http://localhost:${PORT} (mode: ${hasApiKey() ? "live" : "offline-demo"})`);
});
