import { useState } from "react";

export default function ChatInput({ onSend, disabled, value, onValueChange }) {
  const [local, setLocal] = useState("");
  const text = value !== undefined ? value : local;
  const setText = onValueChange || setLocal;

  function submit(e) {
    e.preventDefault();
    if (!text.trim() || disabled) return;
    onSend(text.trim());
    setText("");
  }

  return (
    <form onSubmit={submit} style={{ maxWidth: 760, margin: "0 auto", width: "100%" }}>
      <div
        style={{
          display: "flex",
          gap: 8,
          alignItems: "center",
          border: "1px solid var(--border)",
          borderRadius: "var(--radius-md)",
          background: "var(--surface-1)",
          padding: "10px 12px",
        }}
      >
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Ask Lighthouse Analyst about stablecoins, DeFi, perpetuals, RWA, x402…"
          style={{
            flex: 1,
            border: "none",
            outline: "none",
            background: "transparent",
            color: "var(--text-primary)",
            fontSize: 14,
            fontFamily: "var(--font-sans)",
          }}
        />
        <button
          type="submit"
          disabled={disabled || !text.trim()}
          style={{
            background: disabled || !text.trim() ? "var(--baseline)" : "var(--series-1)",
            border: "none",
            color: "#fff",
            width: 32,
            height: 32,
            borderRadius: "50%",
            cursor: disabled || !text.trim() ? "default" : "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 16,
          }}
          aria-label="Send"
        >
          ↑
        </button>
      </div>
    </form>
  );
}
