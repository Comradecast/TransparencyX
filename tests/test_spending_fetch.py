import json
import socket
import urllib.error

from transparencyx.spending.fetch import fetch_award_exposure
from transparencyx.spending.linker import build_exposure_link


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def test_fetch_award_exposure_posts_payload_and_summarizes(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        captured["payload"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse({
            "results": [
                {
                    "Recipient Name": "REOF XXV LLC",
                    "Award ID": "A1",
                    "Awarding Agency": "B Agency",
                    "Award Amount": "10.5",
                    "Start Date": "2023-01-01",
                    "Contract Award Type": "Definitive Contract",
                },
                {
                    "Recipient Name": "REOF XXV LLC",
                    "Award ID": "A2",
                    "Awarding Agency": "A Agency",
                    "Award Amount": "2.5",
                    "Start Date": "2022-01-01",
                    "Contract Award Type": "Definitive Contract",
                },
            ],
        })

    monkeypatch.setattr("transparencyx.spending.fetch.urllib.request.urlopen", fake_urlopen)

    link = build_exposure_link("REOF XXV, LLC [AB] SP")
    summary = fetch_award_exposure(link)

    assert captured["url"] == "https://api.usaspending.gov/api/v2/search/spending_by_award/"
    assert captured["timeout"] == 5
    assert captured["payload"] == link["payload"]
    assert summary == {
        "query_recipient_name": "REOF XXV, LLC [AB] SP",
        "award_count": 2,
        "total_award_amount": 13.0,
        "agencies": ["A Agency", "B Agency"],
        "date_min": "2022-01-01",
        "date_max": "2023-01-01",
        "signal": "federal_award_exposure",
    }


def test_fetch_award_exposure_handles_url_error(monkeypatch):
    def fake_urlopen(request, timeout):
        raise urllib.error.URLError("offline")

    monkeypatch.setattr("transparencyx.spending.fetch.urllib.request.urlopen", fake_urlopen)

    summary = fetch_award_exposure(build_exposure_link("REOF XXV, LLC [AB] SP"))

    assert summary == {
        "query_recipient_name": "REOF XXV, LLC [AB] SP",
        "award_count": 0,
        "total_award_amount": 0.0,
        "agencies": [],
        "date_min": None,
        "date_max": None,
        "signal": "federal_award_exposure",
    }


def test_fetch_award_exposure_handles_timeout(monkeypatch):
    def fake_urlopen(request, timeout):
        raise TimeoutError("timed out")

    monkeypatch.setattr("transparencyx.spending.fetch.urllib.request.urlopen", fake_urlopen)

    summary = fetch_award_exposure(build_exposure_link("REOF XXV, LLC [AB] SP"))

    assert summary["award_count"] == 0
    assert summary["total_award_amount"] == 0.0
    assert summary["signal"] == "federal_award_exposure"


def test_fetch_award_exposure_handles_socket_timeout(monkeypatch):
    def fake_urlopen(request, timeout):
        raise socket.timeout("timed out")

    monkeypatch.setattr("transparencyx.spending.fetch.urllib.request.urlopen", fake_urlopen)

    summary = fetch_award_exposure(build_exposure_link("REOF XXV, LLC [AB] SP"))

    assert summary["award_count"] == 0
    assert summary["signal"] == "federal_award_exposure"


def test_fetch_award_exposure_handles_bad_json(monkeypatch):
    class BadJsonResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def read(self):
            return b"{bad json"

    monkeypatch.setattr(
        "transparencyx.spending.fetch.urllib.request.urlopen",
        lambda request, timeout: BadJsonResponse(),
    )

    summary = fetch_award_exposure(build_exposure_link("REOF XXV, LLC [AB] SP"))

    assert summary["award_count"] == 0


def test_fetch_award_exposure_handles_missing_payload_without_network(monkeypatch):
    def fake_urlopen(request, timeout):
        raise AssertionError("network should not be called")

    monkeypatch.setattr("transparencyx.spending.fetch.urllib.request.urlopen", fake_urlopen)

    summary = fetch_award_exposure({"query_recipient_name": "REOF XXV, LLC [AB] SP"})

    assert summary["award_count"] == 0
    assert summary["query_recipient_name"] == "REOF XXV, LLC [AB] SP"
