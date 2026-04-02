from src.core.openai import payment
from src.database.models import Account


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


def test_generate_plus_link_sends_english_checkout_headers(monkeypatch):
    calls = []

    def fake_post(url, **kwargs):
        calls.append({"url": url, "kwargs": kwargs})
        return FakeResponse({"checkout_session_id": "session-plus"})

    monkeypatch.setattr(payment.cffi_requests, "post", fake_post)

    account = Account(
        email="tester@example.com",
        email_service="tempmail",
        access_token="access-token",
        cookies="foo=bar; oai-did=device-123",
    )

    result = payment.generate_plus_link(account, proxy="http://proxy.test:8080", country="US")

    assert result == payment.TEAM_CHECKOUT_BASE_URL + "session-plus"
    assert calls[0]["url"] == payment.PAYMENT_CHECKOUT_URL
    assert calls[0]["kwargs"]["headers"]["oai-language"] == "en-US"
    assert calls[0]["kwargs"]["headers"]["oai-device-id"] == "device-123"
    assert calls[0]["kwargs"]["headers"]["cookie"] == "foo=bar; oai-did=device-123"
    assert calls[0]["kwargs"]["json"]["billing_details"] == {"country": "US", "currency": "USD"}
    assert calls[0]["kwargs"]["proxies"] == {
        "http": "http://proxy.test:8080",
        "https": "http://proxy.test:8080",
    }


def test_generate_team_link_sends_english_checkout_headers(monkeypatch):
    calls = []

    def fake_post(url, **kwargs):
        calls.append({"url": url, "kwargs": kwargs})
        return FakeResponse({"checkout_session_id": "session-team"})

    monkeypatch.setattr(payment.cffi_requests, "post", fake_post)

    account = Account(
        email="tester@example.com",
        email_service="tempmail",
        access_token="access-token",
    )

    result = payment.generate_team_link(
        account,
        workspace_name="AlphaTeam",
        price_interval="year",
        seat_quantity=10,
        country="CA",
    )

    assert result == payment.TEAM_CHECKOUT_BASE_URL + "session-team"
    assert calls[0]["kwargs"]["headers"]["oai-language"] == "en-US"
    assert calls[0]["kwargs"]["json"]["team_plan_data"] == {
        "workspace_name": "AlphaTeam",
        "price_interval": "year",
        "seat_quantity": 10,
    }
    assert calls[0]["kwargs"]["json"]["billing_details"] == {"country": "CA", "currency": "CAD"}
