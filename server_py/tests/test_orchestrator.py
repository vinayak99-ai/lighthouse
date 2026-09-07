from ..chat.llm_client import LLMResponse, ToolCall
from ..chat.orchestrator import MAX_CHART_CORRECTIONS, run_conversation


class _ScriptedClient:
    """Fake LLMClient (see chat/llm_client.py) that returns a scripted
    sequence of LLMResponses -- the Python equivalent of the injectable
    `client` param the JS provider tests use instead of a real API."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = 0

    def create(self, *, system, messages, tools):
        self.calls += 1
        return self._responses[self.calls - 1]


def test_data_tool_call_then_valid_chart():
    client = _ScriptedClient(
        [
            LLMResponse(
                text="Checking.",
                tool_calls=[ToolCall(id="t1", name="query_stablecoin_supply", input={"group_by": "total"})],
            ),
            LLMResponse(
                text="Here it is.",
                tool_calls=[
                    ToolCall(
                        id="t2",
                        name="render_chart",
                        input={"chart_type": "line", "title": "x", "series": ["Total supply"], "data": [{"x": "1", "Total supply": 1}]},
                    )
                ],
            ),
        ]
    )
    result = run_conversation([{"role": "user", "content": "q"}], client=client)
    assert result["reply"] == "Here it is."
    assert result["chart"]["chart_type"] == "line"
    assert client.calls == 2


def test_invalid_chart_self_corrects_within_the_same_turn():
    client = _ScriptedClient(
        [
            LLMResponse(
                text="",
                tool_calls=[
                    ToolCall(
                        id="bad",
                        name="render_chart",
                        input={"chart_type": "area", "title": "x", "series": ["A", "B"], "data": [{"x": "1", "A": 1, "B": 2}]},
                    )
                ],
            ),
            LLMResponse(
                text="Fixed.",
                tool_calls=[
                    ToolCall(
                        id="good",
                        name="render_chart",
                        input={"chart_type": "line", "title": "x", "series": ["A", "B"], "data": [{"x": "1", "A": 1, "B": 2}]},
                    )
                ],
            ),
        ]
    )
    result = run_conversation([{"role": "user", "content": "q"}], client=client)
    assert result["chart"]["chart_type"] == "line"
    assert result["reply"] == "Fixed."


def test_gives_up_after_max_chart_corrections_and_accepts_last_attempt():
    bad_chart = {"chart_type": "area", "title": "x", "series": ["A", "B"], "data": [{"x": "1", "A": 1, "B": 2}]}
    responses = [
        LLMResponse(text="", tool_calls=[ToolCall(id=f"c{i}", name="render_chart", input=bad_chart)])
        for i in range(MAX_CHART_CORRECTIONS + 1)
    ]
    client = _ScriptedClient(responses)
    result = run_conversation([{"role": "user", "content": "q"}], client=client)
    # The user never sees a failure -- a still-invalid chart past the retry
    # budget is accepted rather than surfaced as an error.
    assert result["chart"] == bad_chart


def test_unknown_tool_name_surfaces_as_error_result_not_a_crash():
    client = _ScriptedClient(
        [
            LLMResponse(text="", tool_calls=[ToolCall(id="t1", name="not_a_real_tool", input={})]),
            LLMResponse(text="Sorry, I can't do that.", tool_calls=[]),
        ]
    )
    result = run_conversation([{"role": "user", "content": "q"}], client=client)
    assert result["reply"] == "Sorry, I can't do that."
    assert result["chart"] is None


def test_no_tool_calls_returns_plain_reply():
    client = _ScriptedClient([LLMResponse(text="Just an answer, no chart needed.", tool_calls=[])])
    result = run_conversation([{"role": "user", "content": "q"}], client=client)
    assert result == {"reply": "Just an answer, no chart needed.", "chart": None}
