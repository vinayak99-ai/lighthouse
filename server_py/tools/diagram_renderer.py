"""Deterministic SVG renderer for render_diagram (Phase 1: flowchart only).

Mirrors the house-style rules from the bybit-exchange/svg-diagram skill
(layout arithmetic, escaping discipline, curved connectors, no elbows) but
adapted to this app's own architecture: the model NEVER supplies raw SVG
coordinates -- it supplies structured {title, nodes, edges} (see
diagram_validator.py for the shape contract), and this module does 100% of
the layout math. LLMs are unreliable at coordinate arithmetic; deterministic
code isn't. This also means most of the source skill's *rendered-geometry*
linter checks (overlap, clipping) are unnecessary here -- they're satisfied
by construction, since we compute every coordinate ourselves rather than
trusting model-placed ones. diagram_validator.py instead validates the
*input spec* (do the edges reference real nodes, is it small enough to lay
out legibly), the same boundary chart_validator.py checks for render_chart.

Colors are the app's own themed CSS custom properties (var(--text-primary)
etc.) rather than hardcoded hex -- unlike the source skill (built to be
pasted into GitHub READMEs with no surrounding stylesheet), this SVG is
always rendered inside DiagramCard.jsx's own themed card, so it inherits
light/dark mode for free instead of needing its own white-canvas-rect
workaround.
"""

from __future__ import annotations

FONT_LABEL = 12
FONT_ANNOTATION = 10

# Box height formula from the house style: one line = font-size * 3.
BOX_HEIGHT = FONT_LABEL * 3
BASELINE_OFFSET = BOX_HEIGHT / 2 + FONT_LABEL * 0.35

CHAR_WIDTH_FACTOR = 0.62  # rough average glyph width for a sans-serif, relative to font-size
BOX_PAD_X = 16
MIN_BOX_WIDTH = 90
MAX_BOX_WIDTH = 220

MARGIN = 24
ROW_GAP = 56
COL_GAP = 32
CORNER_RADIUS = 6

ARROW_START_CLEARANCE = 4
ARROW_END_CLEARANCE = 10


def _escape(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&apos;")
    )


def _box_width(label: str) -> float:
    raw = len(label) * FONT_LABEL * CHAR_WIDTH_FACTOR + 2 * BOX_PAD_X
    return max(MIN_BOX_WIDTH, min(MAX_BOX_WIDTH, raw))


def _layer_nodes(node_ids: list[str], edges: list[tuple[str, str]]) -> list[list[str]]:
    """Assigns each node a row (depth) via longest-path-from-source
    layering: a node with no incoming edges starts at depth 0; every other
    node sits one row below its deepest predecessor. Falls back to
    appending any node a cycle prevents from resolving normally, rather
    than looping forever -- Phase 1 diagrams are small flowcharts, not
    general graphs, so a defensive fallback is enough."""
    incoming: dict[str, list[str]] = {n: [] for n in node_ids}
    outgoing: dict[str, list[str]] = {n: [] for n in node_ids}
    for src, dst in edges:
        if src in outgoing and dst in incoming:
            outgoing[src].append(dst)
            incoming[dst].append(src)

    depth: dict[str, int] = {}
    queue = [n for n in node_ids if not incoming[n]]
    for n in queue:
        depth[n] = 0

    visited = set(queue)
    while queue:
        current = queue.pop(0)
        for nxt in outgoing[current]:
            candidate = depth[current] + 1
            if depth.get(nxt, -1) < candidate:
                depth[nxt] = candidate
            if nxt not in visited:
                visited.add(nxt)
                queue.append(nxt)

    # Defensive fallback for any node a cycle left unresolved (isolated or
    # part of a loop with no clear source) -- place it one row past
    # whatever's already been laid out instead of dropping it.
    next_depth = (max(depth.values()) + 1) if depth else 0
    for n in node_ids:
        if n not in depth:
            depth[n] = next_depth

    rows: dict[int, list[str]] = {}
    for n in node_ids:
        rows.setdefault(depth[n], []).append(n)
    return [rows[d] for d in sorted(rows)]


def render_diagram_svg(spec: dict) -> str:
    """`spec` must already have passed diagram_validator.check_diagram_spec.
    Returns a complete, self-contained SVG string. The title is NOT drawn
    inside the SVG -- DiagramCard.jsx renders it as a real HTML heading
    above the graphic, the same treatment ChartCard.jsx gives every other
    chart type's title, rather than baking it into the vector art."""
    nodes = spec["nodes"]
    edges = spec.get("edges") or []

    node_ids = [n["id"] for n in nodes]
    labels = {n["id"]: n["label"] for n in nodes}
    edge_pairs = [(e["from"], e["to"]) for e in edges]
    rows = _layer_nodes(node_ids, edge_pairs)

    # Geometry pass: width per node from its own label, rows centered
    # independently so a short row doesn't stretch to match a long one.
    geometry: dict[str, dict] = {}
    row_widths = []
    for row in rows:
        widths = [_box_width(labels[n]) for n in row]
        row_widths.append(sum(widths) + COL_GAP * (len(row) - 1))
    canvas_width = max(row_widths, default=MIN_BOX_WIDTH) + 2 * MARGIN

    for row_index, row in enumerate(rows):
        widths = [_box_width(labels[n]) for n in row]
        total_width = sum(widths) + COL_GAP * (len(row) - 1)
        x = (canvas_width - total_width) / 2
        y = MARGIN + row_index * (BOX_HEIGHT + ROW_GAP)
        for node_id, width in zip(row, widths):
            geometry[node_id] = {"x": x, "y": y, "width": width, "height": BOX_HEIGHT}
            x += width + COL_GAP

    canvas_height = MARGIN + len(rows) * BOX_HEIGHT + max(0, len(rows) - 1) * ROW_GAP + MARGIN

    parts = [
        f'<svg width="{canvas_width:.0f}" height="{canvas_height:.0f}" viewBox="0 0 {canvas_width:.0f} {canvas_height:.0f}" '
        f'xmlns="http://www.w3.org/2000/svg" font-family="system-ui, -apple-system, sans-serif">',
        "<defs>",
        '<marker id="lh-diagram-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" '
        'orient="auto-start-reverse">',
        '<path d="M 0 0 L 10 5 L 0 10 z" fill="var(--text-muted)" />',
        "</marker>",
        "</defs>",
    ]

    # Edges first so connector lines sit beneath node boxes, not on top of them.
    for edge in edges:
        # diagram_validator.py rejects a dangling edge before this normally
        # runs -- but orchestrator.py's retry budget can exhaust and render
        # the model's last (still-invalid) attempt anyway, the same
        # "user gets something rather than a hard failure" contract
        # render_chart has. Drop what can't be drawn instead of crashing.
        if edge["from"] not in geometry or edge["to"] not in geometry:
            continue
        src = geometry[edge["from"]]
        dst = geometry[edge["to"]]
        src_cx = src["x"] + src["width"] / 2
        dst_cx = dst["x"] + dst["width"] / 2
        y1 = src["y"] + src["height"] + ARROW_START_CLEARANCE
        y2 = dst["y"] - ARROW_END_CLEARANCE
        if abs(src_cx - dst_cx) < 1:
            path = f"M {src_cx:.1f} {y1:.1f} L {dst_cx:.1f} {y2:.1f}"
        else:
            mid_y = (y1 + y2) / 2
            path = f"M {src_cx:.1f} {y1:.1f} C {src_cx:.1f} {mid_y:.1f}, {dst_cx:.1f} {mid_y:.1f}, {dst_cx:.1f} {y2:.1f}"
        parts.append(
            f'<path d="{path}" fill="none" stroke="var(--text-muted)" stroke-width="1.5" '
            f'marker-end="url(#lh-diagram-arrow)" />'
        )
        if edge.get("label"):
            mid_x = (src_cx + dst_cx) / 2
            mid_y = (y1 + y2) / 2
            label = _escape(edge["label"])
            label_width = len(edge["label"]) * FONT_ANNOTATION * CHAR_WIDTH_FACTOR + 8
            parts.append(
                f'<rect x="{mid_x - label_width / 2:.1f}" y="{mid_y - FONT_ANNOTATION:.1f}" '
                f'width="{label_width:.1f}" height="{FONT_ANNOTATION + 6}" fill="var(--surface-1)" />'
            )
            parts.append(
                f'<text x="{mid_x:.1f}" y="{mid_y + FONT_ANNOTATION / 2:.1f}" text-anchor="middle" '
                f'font-size="{FONT_ANNOTATION}" fill="var(--text-muted)">{label}</text>'
            )

    for node_id in node_ids:
        g = geometry[node_id]
        parts.append(
            f'<rect x="{g["x"]:.1f}" y="{g["y"]:.1f}" width="{g["width"]:.1f}" height="{g["height"]:.1f}" '
            f'rx="{CORNER_RADIUS}" fill="var(--surface-1)" stroke="var(--border)" stroke-width="1.5" />'
        )
        text_x = g["x"] + g["width"] / 2
        text_y = g["y"] + BASELINE_OFFSET
        parts.append(
            f'<text x="{text_x:.1f}" y="{text_y:.1f}" text-anchor="middle" font-size="{FONT_LABEL}" '
            f'fill="var(--text-primary)">{_escape(labels[node_id])}</text>'
        )

    parts.append("</svg>")
    return "".join(parts)
