"""Provider adapters for public status pages/APIs.

Two wire formats are supported out of the box:
  - "statuspage_json": the Atlassian Statuspage.io `incidents.json` API
    (used by GitHub, Cloudflare, and many others) -- a flat JSON object
    with an `incidents` array.
  - "rss": a generic RSS 2.0 feed (used by Azure's status feed) -- parsed
    with the standard library's `xml.etree.ElementTree`, no third-party
    feed parser needed.

Each adapter reduces its provider's native format to a small, uniform
`Incident` tuple so the rest of the package (state diffing, reporting)
never needs to know which wire format a given provider uses.
"""

from __future__ import annotations

import json
import urllib.request
import xml.etree.ElementTree as ET
from collections.abc import Callable
from dataclasses import dataclass

Fetcher = Callable[[str, float], str]


@dataclass(frozen=True)
class Provider:
    name: str
    kind: str  # "statuspage_json" | "rss"
    url: str


@dataclass(frozen=True)
class Incident:
    provider: str
    incident_id: str
    title: str
    status: str | None
    url: str | None


DEFAULT_PROVIDERS: tuple[Provider, ...] = (
    Provider(name="github", kind="statuspage_json", url="https://www.githubstatus.com/api/v2/incidents.json"),
    Provider(name="cloudflare", kind="statuspage_json", url="https://www.cloudflarestatus.com/api/v2/incidents.json"),
    Provider(name="azure", kind="rss", url="https://status.azure.com/en-us/status/feed/"),
)


def fetch_text(url: str, timeout: float = 15.0) -> str:
    """Real HTTP GET, returning the raw response body as text. The
    default `fetcher` for `fetch_incidents` -- swapped out entirely in
    tests, so no live network call happens in the test suite."""
    request = urllib.request.Request(url, headers={"User-Agent": "status-watch/0.1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8")


def fetch_incidents(
    provider: Provider, timeout: float = 15.0, fetcher: Fetcher = fetch_text
) -> list[Incident]:
    raw = fetcher(provider.url, timeout)
    if provider.kind == "statuspage_json":
        return _parse_statuspage_json(provider.name, raw)
    if provider.kind == "rss":
        return _parse_rss(provider.name, raw)
    raise ValueError(f"unknown provider kind: {provider.kind!r}")


def _parse_statuspage_json(provider_name: str, raw: str) -> list[Incident]:
    data = json.loads(raw)
    incidents = []
    for item in data.get("incidents", []):
        incidents.append(
            Incident(
                provider=provider_name,
                incident_id=str(item["id"]),
                title=item.get("name", "(untitled incident)"),
                status=item.get("status"),
                url=item.get("shortlink"),
            )
        )
    return incidents


_RSS_NAMESPACES = {"atom": "http://www.w3.org/2005/Atom"}


def _parse_rss(provider_name: str, raw: str) -> list[Incident]:
    root = ET.fromstring(raw)
    incidents = []
    for item in root.iter("item"):
        guid_el = item.find("guid")
        link_el = item.find("link")
        title_el = item.find("title")
        incident_id = (guid_el.text if guid_el is not None else None) or (
            link_el.text if link_el is not None else None
        )
        if not incident_id:
            continue
        incidents.append(
            Incident(
                provider=provider_name,
                incident_id=incident_id.strip(),
                title=(title_el.text.strip() if title_el is not None and title_el.text else "(untitled incident)"),
                status=None,
                url=(link_el.text.strip() if link_el is not None and link_el.text else None),
            )
        )
    return incidents
