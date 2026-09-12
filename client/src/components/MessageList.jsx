import ChartCard from "./ChartCard.jsx";
import DiagramCard from "./DiagramCard.jsx";

export default function MessageList({ messages, pending }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20, maxWidth: 760, margin: "0 auto", width: "100%", padding: "24px 0" }}>
      {messages.map((m, i) => (
        <div key={i} style={{ display: "flex", flexDirection: "column", alignItems: m.role === "user" ? "flex-end" : "flex-start" }}>
          <div
            style={{
              background: m.role === "user" ? "var(--series-1)" : "var(--surface-1)",
              color: m.role === "user" ? "#ffffff" : "var(--text-primary)",
              border: m.role === "user" ? "none" : "1px solid var(--border)",
              borderRadius: "var(--radius-md)",
              padding: "10px 16px",
              maxWidth: 560,
              fontSize: 14,
              lineHeight: 1.5,
            }}
          >
            {m.text}
          </div>
          {m.chart && <ChartCard chart={m.chart} />}
          {m.diagram && <DiagramCard diagram={m.diagram} />}
          {m.error && <div style={{ color: "var(--series-8)", fontSize: 13, marginTop: 6 }}>{m.error}</div>}
        </div>
      ))}
      {pending && (
        <div style={{ display: "flex", justifyContent: "flex-start" }}>
          <div style={{ color: "var(--text-muted)", fontSize: 13, padding: "10px 16px" }}>Analyzing…</div>
        </div>
      )}
    </div>
  );
}
