import json

from status_watch.providers import Provider, fetch_incidents

STATUSPAGE_SAMPLE = json.dumps(
    {
        "page": {"id": "abc"},
        "incidents": [
            {
                "id": "inc1",
                "name": "Elevated error rates",
                "status": "resolved",
                "shortlink": "https://stspg.io/x",
            },
            {"id": "inc2", "name": "Investigating latency", "status": "investigating"},
        ],
    }
)

RSS_SAMPLE = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0">
  <channel>
    <title>Azure Status</title>
    <item>
      <title>Service degradation in East US</title>
      <link>https://status.azure.com/incident/1</link>
      <guid>azure-inc-1</guid>
      <pubDate>Mon, 14 Jul 2026 10:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""


def test_parses_statuspage_json_incidents():
    provider = Provider(name="github", kind="statuspage_json", url="https://example.test")
    incidents = fetch_incidents(provider, fetcher=lambda url, timeout: STATUSPAGE_SAMPLE)
    assert len(incidents) == 2
    assert incidents[0].incident_id == "inc1"
    assert incidents[0].title == "Elevated error rates"
    assert incidents[0].status == "resolved"
    assert incidents[1].incident_id == "inc2"


def test_parses_rss_incidents():
    provider = Provider(name="azure", kind="rss", url="https://example.test")
    incidents = fetch_incidents(provider, fetcher=lambda url, timeout: RSS_SAMPLE)
    assert len(incidents) == 1
    assert incidents[0].incident_id == "azure-inc-1"
    assert incidents[0].title == "Service degradation in East US"
    assert incidents[0].provider == "azure"


def test_empty_rss_feed_returns_no_incidents():
    empty = '<?xml version="1.0"?><rss version="2.0"><channel><title>x</title></channel></rss>'
    provider = Provider(name="azure", kind="rss", url="https://example.test")
    incidents = fetch_incidents(provider, fetcher=lambda url, timeout: empty)
    assert incidents == []


def test_unknown_provider_kind_raises():
    provider = Provider(name="mystery", kind="carrier_pigeon", url="https://example.test")
    try:
        fetch_incidents(provider, fetcher=lambda url, timeout: "")
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_fetcher_receives_url_and_timeout():
    seen = {}

    def fetcher(url, timeout):
        seen["args"] = (url, timeout)
        return STATUSPAGE_SAMPLE

    provider = Provider(name="github", kind="statuspage_json", url="https://example.test/x")
    fetch_incidents(provider, timeout=7.0, fetcher=fetcher)
    assert seen["args"] == ("https://example.test/x", 7.0)
