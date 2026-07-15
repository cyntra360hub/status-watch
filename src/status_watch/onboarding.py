"""Reusable self-onboarding helper, implementing the exact flow
documented in https://aiopsenabler.com/skill.md section 1 -- reused
verbatim by any fork of status-watch that doesn't yet have its own
AiOps Enabler API key pair.

This is the "first-run config module" pattern: rather than requiring a
fork's maintainer to hand-craft a signed `curl` call, `register_agent()`
does the one *unsigned* POST that bootstraps a new agent identity, and
`first_run_message()` gives a fork a copy-pasteable next step when it
runs with reporting configured but no key pair yet.

Registration itself needs no HMAC signature (it's how you *get* the key
pair that signing later depends on) -- see skill.md section 1: only a
plain `POST .../skill-onboarding/register` with a JSON body.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable
from typing import Any

DEFAULT_BASE_URL = "https://api.aiopsenabler.com"
REGISTER_PATH = "/api/v1/skill-onboarding/register"

# The 5 values both skill.md's own code block and the platform's OpenAPI
# schema (components.schemas.AgentCategory) agree on -- skill.md's prose
# says "six string values" just above this list, which appears to be a
# documentation copy-paste slip rather than a real 6th value: the code
# block and the machine-readable schema, the two authoritative sources,
# match each other exactly.
VALID_CATEGORIES = (
    "incident-response",
    "alert-triage",
    "remediation",
    "observability",
    "other",
)

Poster = Callable[[str, bytes, dict[str, str]], dict[str, Any]]


class OnboardingError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"AiOps Enabler registration error {status_code}: {detail}")


def _post_json(url: str, body: bytes) -> dict[str, Any]:
    request = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=15.0) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as exc:
        raise OnboardingError(exc.code, exc.read().decode("utf-8", "replace")) from exc


def register_agent(
    *,
    name: str,
    category: str,
    operator_email: str,
    description: str = "",
    capabilities_tags: list[str] | None = None,
    framework_model: str = "",
    repo_url: str = "",
    docs_url: str = "",
    website_url: str = "",
    base_url: str = DEFAULT_BASE_URL,
    poster: Poster | None = None,
) -> dict[str, Any]:
    """Register a brand-new agent per skill.md section 1. Returns the raw
    response body: `{"agent": {...}, "api_key": {"key_id": ..., "secret": ...}}`.
    The secret is shown exactly once here and can never be retrieved
    again -- callers must persist it immediately (env var, secrets
    manager, etc.), which this function deliberately leaves to the
    caller rather than writing files itself."""
    if category not in VALID_CATEGORIES:
        raise ValueError(f"category must be one of {VALID_CATEGORIES}, got {category!r}")

    payload = {
        "name": name,
        "category": category,
        "operator_email": operator_email,
        "description": description,
        "capabilities_tags": capabilities_tags or [],
        "framework_model": framework_model,
        "repo_url": repo_url,
        "docs_url": docs_url,
        "website_url": website_url,
    }
    body = json.dumps(payload).encode("utf-8")
    url = f"{base_url.rstrip('/')}{REGISTER_PATH}"

    if poster is not None:
        return poster(url, body, {"Content-Type": "application/json"})
    return _post_json(url, body)


def first_run_message(env_prefix: str) -> str:
    """A friendly, copy-pasteable explanation shown when reporting env
    vars are unset -- points a fork's maintainer at the self-onboarding
    flow instead of a dead end."""
    return (
        "AiOps Enabler reporting is not configured (no "
        f"{env_prefix}_AGENT_KEY_ID / {env_prefix}_AGENT_SECRET set) -- running "
        "without it. To report this agent's runs to https://aiopsenabler.com:\n"
        "  1. Register your own agent identity (one-time, per skill.md):\n"
        "       python -m status_watch.onboarding register \\\n"
        "         --name 'My status-watch fork' --category observability \\\n"
        "         --operator-email you@example.com\n"
        "  2. Save the printed key_id/secret as "
        f"{env_prefix}_AGENT_KEY_ID / {env_prefix}_AGENT_SECRET "
        "(env var locally, or a GitHub Actions secret in CI).\n"
        "  3. Check your operator email for the claim link to publish your profile."
    )


def _cli_register(args: list[str]) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="python -m status_watch.onboarding register",
        description="Register a new AiOps Enabler agent identity (skill.md section 1).",
    )
    parser.add_argument("--name", required=True)
    parser.add_argument("--category", required=True, choices=VALID_CATEGORIES)
    parser.add_argument("--operator-email", required=True)
    parser.add_argument("--description", default="")
    parser.add_argument("--repo-url", default="")
    parsed = parser.parse_args(args)

    try:
        result = register_agent(
            name=parsed.name,
            category=parsed.category,
            operator_email=parsed.operator_email,
            description=parsed.description,
            repo_url=parsed.repo_url,
        )
    except OnboardingError as exc:
        print(f"Registration failed: {exc}")
        return 1

    api_key = result.get("api_key", {})
    print("Registered! Save these now -- the secret is shown exactly once:")
    print(f"  key_id = {api_key.get('key_id')}")
    print(f"  secret = {api_key.get('secret')}")
    print("Check your operator email for the claim link to publish your profile.")
    return 0


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "register":
        raise SystemExit(_cli_register(sys.argv[2:]))
    print("Usage: python -m status_watch.onboarding register --name ... "
          "--category ... --operator-email ...")
    raise SystemExit(1)
