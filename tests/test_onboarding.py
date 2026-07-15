import json

import pytest

from status_watch.onboarding import (
    OnboardingError,
    VALID_CATEGORIES,
    first_run_message,
    register_agent,
)


class _FakePoster:
    def __init__(self, response=None, raise_error=None):
        self.response = response or {}
        self.raise_error = raise_error
        self.calls = []

    def __call__(self, url, body, headers):
        self.calls.append((url, body, headers))
        if self.raise_error:
            raise self.raise_error
        return self.response


def test_register_agent_rejects_invalid_category():
    with pytest.raises(ValueError, match="category"):
        register_agent(
            name="x", category="not-a-real-category", operator_email="a@example.com"
        )


def test_register_agent_sends_required_fields():
    poster = _FakePoster(response={"agent": {"slug": "x"}, "api_key": {"key_id": "ak_1", "secret": "s"}})
    result = register_agent(
        name="My Agent",
        category="observability",
        operator_email="me@example.com",
        poster=poster,
    )
    assert result["api_key"]["key_id"] == "ak_1"
    url, body, headers = poster.calls[0]
    assert url.endswith("/api/v1/skill-onboarding/register")
    payload = json.loads(body)
    assert payload["name"] == "My Agent"
    assert payload["category"] == "observability"
    assert payload["operator_email"] == "me@example.com"


def test_register_agent_propagates_onboarding_error():
    poster = _FakePoster(raise_error=OnboardingError(422, "bad request"))
    with pytest.raises(OnboardingError):
        register_agent(
            name="x", category="observability", operator_email="a@example.com", poster=poster
        )


def test_valid_categories_matches_platform_schema():
    # Cross-checked against both skill.md's own code block and
    # openapi.json's components.schemas.AgentCategory enum in Step 0.
    assert VALID_CATEGORIES == (
        "incident-response",
        "alert-triage",
        "remediation",
        "observability",
        "other",
    )


def test_first_run_message_mentions_env_prefix():
    message = first_run_message("STATUS_WATCH")
    assert "STATUS_WATCH_AGENT_KEY_ID" in message
    assert "STATUS_WATCH_AGENT_SECRET" in message
