export default function StarterGrid({ domains, onPick }) {
  return (
    <div style={{ maxWidth: 720, margin: "0 auto", width: "100%" }}>
      <h1 style={{ fontSize: 28, fontWeight: 700, textAlign: "center", margin: "0 0 8px" }}>Explore what Analyst can research</h1>
      <p style={{ textAlign: "center", color: "var(--text-secondary)", margin: "0 0 28px" }}>
        Pick a data source for an example question, or ask your own below.
      </p>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        {domains.map((d) => (
          <button
            key={d.key}
            onClick={() => onPick(d.example)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 12,
              textAlign: "left",
              padding: "16px 18px",
              borderRadius: "var(--radius-md)",
              border: "1px solid var(--border)",
              background: "var(--surface-1)",
              cursor: "pointer",
              color: "var(--text-primary)",
              fontSize: 15,
              fontWeight: 600,
            }}
          >
            <span style={{ fontSize: 20 }}>{d.icon}</span>
            <span>
              {d.label}
              {d.hot && (
                <span
                  style={{
                    marginLeft: 8,
                    fontSize: 10,
                    fontWeight: 700,
                    padding: "2px 6px",
                    borderRadius: 999,
                    background: "var(--text-primary)",
                    color: "var(--surface-1)",
                    verticalAlign: "middle",
                  }}
                >
                  HOT
                </span>
              )}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
