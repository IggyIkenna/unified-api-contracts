"""Mock replay utilities for E2E testing with UAC cassettes.

Provides helpers that load VCR cassettes from the UAC canonical location
and replay them using the ``responses`` library for HTTP mocking.
Services use these to run E2E pipeline tests without any live network calls.

Usage::

    from unified_api_contracts.testing.mock_replay import (
        replay_cassette,
        replay_cassettes_for_venue,
    )

    @responses.activate
    def test_pipeline_with_deribit_replay():
        replay_cassette("deribit", "get_instruments_multi.yaml")
        # ... run service pipeline that calls Deribit API ...

    @responses.activate
    def test_pipeline_with_all_deribit_cassettes():
        replay_cassettes_for_venue("deribit")
        # ... all Deribit endpoints are mocked ...
"""

from __future__ import annotations

import json

import responses as responses_lib
import yaml

from unified_api_contracts.testing.cassette_loader import (
    get_cassette_path,
    list_cassettes_for_venue,
)


def replay_cassette(
    venue: str,
    cassette_name: str,
    rsps: responses_lib.RequestsMock | None = None,
) -> list[responses_lib.BaseResponse]:
    """Register all interactions from a VCR cassette as response mocks.

    Each interaction in the cassette becomes a registered mock response.
    Supports both GET and POST methods with the correct URL and status.

    Args:
        venue: External source name (e.g. "deribit", "hyperliquid").
        cassette_name: YAML filename (e.g. "get_instruments_multi.yaml").
        rsps: Optional RequestsMock instance. If None, registers on the
              global responses mock (requires @responses.activate).

    Returns:
        List of registered response objects.
    """
    cassette_path = get_cassette_path(venue, cassette_name)
    content = cassette_path.read_text(encoding="utf-8")
    parsed = yaml.safe_load(content)

    if not isinstance(parsed, dict) or "interactions" not in parsed:
        raise ValueError(
            f"Cassette {cassette_name} is not a valid VCR cassette"
        )

    interactions = parsed["interactions"]
    if not isinstance(interactions, list) or len(interactions) == 0:
        raise ValueError(
            f"Cassette {cassette_name} has no interactions to replay"
        )

    registered: list[responses_lib.BaseResponse] = []

    for interaction in interactions:
        if not isinstance(interaction, dict):
            continue

        request = interaction.get("request")
        response = interaction.get("response")

        if not isinstance(request, dict) or not isinstance(response, dict):
            continue

        uri = request.get("uri", "")
        method_str = request.get("method", "GET").upper()

        body = response.get("body", {})
        body_string = ""
        if isinstance(body, dict):
            body_string = body.get("string", "")

        status_info = response.get("status", {})
        status_code = 200
        if isinstance(status_info, dict):
            status_code = status_info.get("code", 200)

        # Determine content type from response headers
        resp_headers = response.get("headers", {})
        content_type = "application/json"
        if isinstance(resp_headers, dict):
            ct_values = resp_headers.get("Content-Type", resp_headers.get("content-type"))
            if isinstance(ct_values, list) and ct_values:
                content_type = ct_values[0]
            elif isinstance(ct_values, str):
                content_type = ct_values

        method_map: dict[str, int] = {
            "GET": responses_lib.GET,
            "POST": responses_lib.POST,
            "PUT": responses_lib.PUT,
            "DELETE": responses_lib.DELETE,
            "PATCH": responses_lib.PATCH,
            "HEAD": responses_lib.HEAD,
        }
        method_int = method_map.get(method_str, responses_lib.GET)

        target = rsps if rsps is not None else responses_lib

        resp = target.add(
            method_int,
            uri,
            body=body_string if isinstance(body_string, str) else "",
            status=status_code,
            content_type=content_type,
        )
        registered.append(resp)

    return registered


def replay_cassettes_for_venue(
    venue: str,
    rsps: responses_lib.RequestsMock | None = None,
) -> list[responses_lib.BaseResponse]:
    """Register all cassettes for a venue as response mocks.

    Convenience function that replays every cassette in a venue's mocks/ dir.
    """
    all_registered: list[responses_lib.BaseResponse] = []
    for cassette_path in list_cassettes_for_venue(venue):
        registered = replay_cassette(venue, cassette_path.name, rsps=rsps)
        all_registered.extend(registered)
    return all_registered


def cassette_to_dict(venue: str, cassette_name: str) -> dict[str, object]:
    """Load a cassette and return all response bodies as a dict.

    Keys are the request URIs, values are the parsed JSON response bodies.
    Useful for feeding mock data into service pipelines.
    """
    cassette_path = get_cassette_path(venue, cassette_name)
    content = cassette_path.read_text(encoding="utf-8")
    parsed = yaml.safe_load(content)

    result: dict[str, object] = {}

    if not isinstance(parsed, dict) or "interactions" not in parsed:
        return result

    interactions = parsed["interactions"]
    if not isinstance(interactions, list):
        return result

    for interaction in interactions:
        if not isinstance(interaction, dict):
            continue
        request = interaction.get("request")
        response = interaction.get("response")
        if not isinstance(request, dict) or not isinstance(response, dict):
            continue

        uri = request.get("uri", "unknown")
        body = response.get("body", {})
        if isinstance(body, dict):
            body_string = body.get("string", "")
            if isinstance(body_string, str) and body_string.strip():
                result[uri] = json.loads(body_string)

    return result
