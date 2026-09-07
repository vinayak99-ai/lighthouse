import pytest
from fastapi.testclient import TestClient

from ..main import app


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def test_health_offline_demo_mode_when_no_llm_configured(client, monkeypatch):
    monkeypatch.delenv("LIGHTHOUSE_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("BEDROCK_MODEL_ID", raising=False)
    monkeypatch.delenv("AWS_REGION", raising=False)
    monkeypatch.delenv("LIGHTHOUSE_CORPORATE_LLM_MODEL", raising=False)
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body == {"ok": True, "mode": "offline-demo", "provider": None, "model": None}


def test_health_reports_configured_bedrock_provider_without_needing_boto3(client, monkeypatch):
    monkeypatch.setenv("LIGHTHOUSE_LLM_PROVIDER", "bedrock")
    monkeypatch.setenv("BEDROCK_MODEL_ID", "fake-model")
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"ok": True, "mode": "live", "provider": "bedrock", "model": "fake-model"}


def test_starters_returns_ten_domains(client):
    r = client.get("/api/starters")
    assert r.status_code == 200
    assert len(r.json()["domains"]) == 10


def test_chat_offline_demo_mode_end_to_end(client, monkeypatch):
    monkeypatch.delenv("LIGHTHOUSE_LLM_PROVIDER", raising=False)
    monkeypatch.delenv("BEDROCK_MODEL_ID", raising=False)
    monkeypatch.delenv("AWS_REGION", raising=False)
    monkeypatch.delenv("LIGHTHOUSE_CORPORATE_LLM_MODEL", raising=False)
    r = client.post(
        "/api/chat",
        json={"messages": [{"role": "user", "content": "Chart USDT vs USDC supply over the last 90 days"}]},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "offline-demo"
    assert body["chart"]["chart_type"] in ("line", "small_multiples", "stacked_bar", "stat")
    assert set(body["chart"]["series"]) == {"USDT", "USDC"}


def test_chat_rejects_empty_messages_array(client):
    r = client.post("/api/chat", json={"messages": []})
    assert r.status_code == 400
    assert "messages" in r.json()["error"]


def test_chat_rejects_missing_messages_key(client):
    r = client.post("/api/chat", json={})
    assert r.status_code == 400
