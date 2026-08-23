import { useEffect, useState } from "react";
import StarterGrid from "./components/StarterGrid.jsx";
import MessageList from "./components/MessageList.jsx";
import ChatInput from "./components/ChatInput.jsx";
import { fetchHealth, fetchStarters, sendChat } from "./lib/api.js";

export default function App() {
  const [domains, setDomains] = useState([]);
  const [health, setHealth] = useState(null);
  const [turns, setTurns] = useState([]);
  const [pending, setPending] = useState(false);
  const [draft, setDraft] = useState("");

  useEffect(() => {
    fetchStarters().then(setDomains).catch(() => {});
    fetchHealth().then(setHealth).catch(() => {});
  }, []);

  async function handleSend(text) {
    const nextTurns = [...turns, { role: "user", text }];
    setTurns(nextTurns);
    setPending(true);
    try {
      const history = nextTurns.map((t) => ({ role: t.role, content: t.text }));
      const result = await sendChat(history);
      setTurns((cur) => [...cur, { role: "assistant", text: result.reply, chart: result.chart }]);
    } catch (err) {
      setTurns((cur) => [...cur, { role: "assistant", text: "", error: err.message }]);
    } finally {
      setPending(false);
    }
  }

  const started = turns.length > 0;

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <header
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "14px 24px",
          borderBottom: "1px solid var(--border)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ fontSize: 20 }}>🔦</span>
          <strong>Lighthouse Analyst</strong>
        </div>
        {health && (
          <span
            title={
              health.mode === "live"
                ? `Live via ${health.provider} (${health.model})`
                : "No ANTHROPIC_API_KEY or OPENAI_API_KEY set — using the offline demo router"
            }
            style={{
              fontSize: 12,
              color: "var(--text-muted)",
              border: "1px solid var(--border)",
              borderRadius: 999,
              padding: "3px 10px",
            }}
          >
            {health.mode === "live" ? `● live · ${health.provider} (${health.model})` : "● offline demo"}
          </span>
        )}
      </header>

      <main style={{ flex: 1, overflow: "auto", padding: "0 24px" }}>
        {started ? <MessageList messages={turns} pending={pending} /> : (
          <div style={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <StarterGrid domains={domains} onPick={(example) => setDraft(example)} />
          </div>
        )}
      </main>

      <footer style={{ padding: "16px 24px 24px" }}>
        <ChatInput onSend={handleSend} disabled={pending} value={draft} onValueChange={setDraft} />
      </footer>
    </div>
  );
}
