"""Validates render_diagram's input spec before diagram_renderer.py lays it
out -- the same role chart_validator.py plays for render_chart: a failure
here never reaches the user, it goes back to the model as corrective
feedback within the same turn (see chat/orchestrator.py).

Unlike chart_validator.py, this doesn't need to check rendered geometry
(overlap, clipping) -- diagram_renderer.py computes every coordinate
itself from a validated spec, so those failure modes can't occur by
construction. What CAN go wrong here is the *input*: a dangling edge, too
many nodes to lay out legibly, or a label too long to fit in a box.
"""

from __future__ import annotations

SUPPORTED_DIAGRAM_TYPES = ["flowchart"]
MAX_NODES = 12
MAX_LABEL_LENGTH = 30


def validate_diagram(spec: dict | None) -> dict:
    issues: list[str] = []

    if not isinstance(spec, dict):
        return {"valid": False, "issues": ["render_diagram received no diagram object."]}

    diagram_type = spec.get("diagram_type")
    nodes = spec.get("nodes")
    edges = spec.get("edges") or []

    if diagram_type not in SUPPORTED_DIAGRAM_TYPES:
        issues.append(
            f"diagram_type '{diagram_type}' isn't supported yet -- only {', '.join(SUPPORTED_DIAGRAM_TYPES)} "
            "is available right now."
        )
        return {"valid": False, "issues": issues}

    if not spec.get("title"):
        issues.append("`title` is required.")

    if not isinstance(nodes, list) or len(nodes) == 0:
        issues.append("`nodes` is empty -- there's nothing to draw. Include at least one node.")
        return {"valid": False, "issues": issues}

    if len(nodes) > MAX_NODES:
        issues.append(
            f"`nodes` has {len(nodes)} entries, over the {MAX_NODES}-node readability cap. "
            "Simplify the diagram or split it into more than one."
        )

    seen_ids: set = set()
    duplicate_ids: set = set()
    long_labels: list[str] = []
    for node in nodes:
        if not isinstance(node, dict) or not node.get("id") or not node.get("label"):
            issues.append("Every node needs a non-empty `id` and `label`.")
            continue
        if node["id"] in seen_ids:
            duplicate_ids.add(node["id"])
        seen_ids.add(node["id"])
        if len(node["label"]) > MAX_LABEL_LENGTH:
            long_labels.append(node["label"])

    if duplicate_ids:
        issues.append(f"Duplicate node ids: {', '.join(sorted(duplicate_ids))}. Every node id must be unique.")

    if long_labels:
        issues.append(
            f"These node labels are over the {MAX_LABEL_LENGTH}-character limit and won't fit in a box: "
            f"{', '.join(long_labels)}. Shorten them."
        )

    unknown_refs: set = set()
    for edge in edges:
        if not isinstance(edge, dict) or not edge.get("from") or not edge.get("to"):
            issues.append("Every edge needs a non-empty `from` and `to`.")
            continue
        if edge["from"] not in seen_ids:
            unknown_refs.add(edge["from"])
        if edge["to"] not in seen_ids:
            unknown_refs.add(edge["to"])

    if unknown_refs:
        issues.append(f"These edges reference node ids that don't exist: {', '.join(sorted(unknown_refs))}.")

    return {"valid": len(issues) == 0, "issues": issues}
