import pytest

from ..tools.diagram_renderer import render_diagram_svg
from ..tools.diagram_validator import MAX_LABEL_LENGTH, MAX_NODES, validate_diagram


def _spec(**overrides):
    base = {
        "diagram_type": "flowchart",
        "title": "Test diagram",
        "nodes": [{"id": "a", "label": "A"}, {"id": "b", "label": "B"}],
        "edges": [{"from": "a", "to": "b"}],
    }
    base.update(overrides)
    return base


# --- validator ---------------------------------------------------------


def test_valid_flowchart_passes():
    result = validate_diagram(_spec())
    assert result == {"valid": True, "issues": []}


def test_no_diagram_object_is_invalid():
    result = validate_diagram(None)
    assert result["valid"] is False


def test_unsupported_diagram_type_is_invalid():
    result = validate_diagram(_spec(diagram_type="sequence"))
    assert result["valid"] is False
    assert any("sequence" in issue for issue in result["issues"])


def test_missing_title_is_invalid():
    result = validate_diagram(_spec(title=""))
    assert result["valid"] is False


def test_empty_nodes_is_invalid():
    result = validate_diagram(_spec(nodes=[]))
    assert result["valid"] is False


def test_too_many_nodes_is_invalid():
    nodes = [{"id": f"n{i}", "label": f"N{i}"} for i in range(MAX_NODES + 1)]
    result = validate_diagram(_spec(nodes=nodes, edges=[]))
    assert result["valid"] is False
    assert any(f"{MAX_NODES}-node" in issue for issue in result["issues"])


def test_node_missing_id_or_label_is_invalid():
    result = validate_diagram(_spec(nodes=[{"id": "a", "label": "A"}, {"id": "", "label": "B"}]))
    assert result["valid"] is False


def test_duplicate_node_ids_is_invalid():
    result = validate_diagram(_spec(nodes=[{"id": "a", "label": "A"}, {"id": "a", "label": "A2"}], edges=[]))
    assert result["valid"] is False
    assert any("Duplicate" in issue for issue in result["issues"])


def test_label_over_length_cap_is_invalid():
    long_label = "x" * (MAX_LABEL_LENGTH + 1)
    result = validate_diagram(_spec(nodes=[{"id": "a", "label": long_label}], edges=[]))
    assert result["valid"] is False
    assert any("character limit" in issue for issue in result["issues"])


def test_edge_referencing_unknown_node_is_invalid():
    result = validate_diagram(_spec(edges=[{"from": "a", "to": "ghost"}]))
    assert result["valid"] is False
    assert any("ghost" in issue for issue in result["issues"])


def test_edge_missing_from_or_to_is_invalid():
    result = validate_diagram(_spec(edges=[{"from": "a"}]))
    assert result["valid"] is False


def test_diagram_with_no_edges_is_still_valid():
    result = validate_diagram(_spec(edges=[]))
    assert result["valid"] is True


# --- renderer ------------------------------------------------------------


def test_render_produces_well_formed_svg():
    svg = render_diagram_svg(_spec())
    assert svg.startswith("<svg")
    assert svg.endswith("</svg>")
    assert svg.count("<svg") == 1


def test_render_escapes_labels_and_title():
    spec = _spec(nodes=[{"id": "a", "label": "<script>x</script>"[:30]}], edges=[])
    svg = render_diagram_svg(spec)
    assert "<script>" not in svg
    assert "&lt;script&gt;" in svg


def test_render_escapes_ampersand_in_edge_label():
    spec = _spec(edges=[{"from": "a", "to": "b", "label": "A & B"}])
    svg = render_diagram_svg(spec)
    assert "A & B" not in svg
    assert "A &amp; B" in svg


def test_render_places_every_node_and_edge():
    svg = render_diagram_svg(_spec())
    assert svg.count("<rect") == 2  # one box per node
    assert svg.count('marker-end="url(#lh-diagram-arrow)"') == 1  # one connector


def test_render_handles_diamond_shaped_dependency_graph():
    """a -> b, a -> c, b -> d, c -> d: b and c should land in the same row
    (both depend only on a), d one row below both."""
    spec = _spec(
        nodes=[{"id": "a", "label": "A"}, {"id": "b", "label": "B"}, {"id": "c", "label": "C"}, {"id": "d", "label": "D"}],
        edges=[{"from": "a", "to": "b"}, {"from": "a", "to": "c"}, {"from": "b", "to": "d"}, {"from": "c", "to": "d"}],
    )
    result = validate_diagram(spec)
    assert result["valid"] is True
    svg = render_diagram_svg(spec)
    assert svg.count("<rect") == 4
    assert svg.count('marker-end="url(#lh-diagram-arrow)"') == 4


def test_render_handles_a_cycle_without_hanging():
    """Defensive fallback: a cycle shouldn't infinite-loop the layering pass."""
    spec = _spec(nodes=[{"id": "a", "label": "A"}, {"id": "b", "label": "B"}], edges=[{"from": "a", "to": "b"}, {"from": "b", "to": "a"}])
    svg = render_diagram_svg(spec)
    assert svg.startswith("<svg")


def test_render_single_node_no_edges():
    spec = _spec(nodes=[{"id": "a", "label": "Solo"}], edges=[])
    svg = render_diagram_svg(spec)
    assert svg.count("<rect") == 1
    assert "marker-end" not in svg


def test_render_does_not_crash_on_a_dangling_edge():
    """Regression guard: diagram_validator.py normally rejects this before
    it reaches the renderer, but orchestrator.py's retry-budget-exhausted
    path renders the model's last attempt regardless of validity (same
    contract as render_chart) -- the renderer must degrade, not crash."""
    spec = _spec(nodes=[{"id": "a", "label": "A"}], edges=[{"from": "a", "to": "ghost"}])
    svg = render_diagram_svg(spec)
    assert svg.startswith("<svg")
    assert "ghost" not in svg
    assert "marker-end" not in svg
