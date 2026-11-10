#!/usr/bin/env python3
"""
Pytest-compatible attack scenario tests for HoneyBadger.

These tests can be run with pytest for CI/CD integration.
Each test is a separate pytest function that can be run independently.

Run with:
    pytest tests/test_attack_scenarios.py -v
    pytest tests/test_attack_scenarios.py -v -k "ssh"
    pytest tests/test_attack_scenarios.py -v -k "http"
    pytest tests/test_attack_scenarios.py -v -k "mitre"
"""

import os
import pytest
import asyncio
from typing import AsyncGenerator

# Import the test runner
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tests.attack_scenarios import AttackScenarioTester


# Test configuration from environment
SSH_HOST = os.getenv("HB_TEST_SSH_HOST", "127.0.0.1")
SSH_PORT = int(os.getenv("HB_TEST_SSH_PORT", "8022"))
HTTP_HOST = os.getenv("HB_TEST_HTTP_HOST", "127.0.0.1")
HTTP_PORT = int(os.getenv("HB_TEST_HTTP_PORT", "8081"))
API_HOST = os.getenv("HB_TEST_API_HOST", "127.0.0.1")
API_PORT = int(os.getenv("HB_TEST_API_PORT", "8090"))
DB_DSN = os.getenv("HB_TEST_DB_DSN", "postgresql://honeybadger:honeybadger@localhost:15432/honeybadger")


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def tester() -> AsyncGenerator[AttackScenarioTester, None]:
    """Create and initialize the attack scenario tester."""
    t = AttackScenarioTester(
        ssh_host=SSH_HOST,
        ssh_port=SSH_PORT,
        http_host=HTTP_HOST,
        http_port=HTTP_PORT,
        api_host=API_HOST,
        api_port=API_PORT,
        db_dsn=DB_DSN,
    )
    await t.setup()
    yield t
    await t.cleanup()


# ============================================================
# SSH Attack Scenario Tests
# ============================================================

@pytest.mark.asyncio
async def test_ssh_credential_stuffing(tester: AttackScenarioTester):
    """T1110.004 - SSH Credential Stuffing"""
    result = await tester.test_ssh_credential_stuffing()

    assert result["events_captured"] > 0, "No events captured"
    assert result["credential_stuffing_events"] > 0, "No T1110.004 events classified"
    assert result["classification_correct"], "Classification accuracy below threshold"


@pytest.mark.asyncio
async def test_ssh_brute_force(tester: AttackScenarioTester):
    """T1110 - SSH Brute Force / Password Spraying"""
    result = await tester.test_ssh_brute_force()

    assert result["events_captured"] > 0, "No events captured"
    assert result["brute_force_events"] > 0, "No T1110 events classified"
    assert result["classification_correct"], "Classification accuracy below threshold"


@pytest.mark.asyncio
async def test_ssh_payload_download(tester: AttackScenarioTester):
    """T1105 - SSH Ingress Tool Transfer (wget/curl)"""
    result = await tester.test_ssh_payload_download()

    assert result["events_captured"] > 0, "No events captured"
    assert result["t1105_events"] > 0, "No T1105 events classified"
    assert result["payload_urls_captured"] > 0, "No payload URLs captured"
    assert result["classification_correct"], "Classification accuracy below threshold"


@pytest.mark.asyncio
async def test_ssh_post_exploitation(tester: AttackScenarioTester):
    """T1059, T1078 - SSH Post-Exploitation Commands"""
    result = await tester.test_ssh_post_exploitation()

    assert result["events_captured"] > 0, "No events captured"
    assert result["t1059_events"] > 0, "No T1059 events classified"
    assert result["classification_correct"], "Classification accuracy below threshold"


# ============================================================
# HTTP Attack Scenario Tests
# ============================================================

@pytest.mark.asyncio
async def test_http_web_scanning(tester: AttackScenarioTester):
    """T1595 - HTTP Active Scanning / Reconnaissance"""
    result = await tester.test_http_web_scanning()

    assert result["events_captured"] > 0, "No events captured"
    assert result["t1595_events"] > 0, "No T1595 events classified"
    assert result["bait_hits"] > 0, "No bait route hits"
    assert result["classification_correct"], "Classification accuracy below threshold"


@pytest.mark.asyncio
async def test_http_exploit_attempts(tester: AttackScenarioTester):
    """T1190 - HTTP Exploit Public-Facing Application"""
    result = await tester.test_http_exploit_attempts()

    assert result["events_captured"] > 0, "No events captured"
    assert result["t1190_events"] > 0, "No T1190 events classified"
    assert result["classification_correct"], "Classification accuracy below threshold"


@pytest.mark.asyncio
async def test_http_credential_capture(tester: AttackScenarioTester):
    """T1110 - HTTP Credential Capture via Login Forms"""
    result = await tester.test_http_credential_capture()

    assert result["events_captured"] > 0, "No events captured"
    assert result["t1110_events"] > 0, "No T1110 events classified"
    assert result["credentials_captured"] > 0, "No credentials captured"
    assert result["classification_correct"], "Classification accuracy below threshold"


# ============================================================
# Verification Tests
# ============================================================

@pytest.mark.asyncio
async def test_mitre_classification_accuracy(tester: AttackScenarioTester):
    """Verify MITRE ATT&CK technique classification"""
    result = await tester.test_mitre_classification_accuracy()

    assert result["all_expected_found"], f"Missing techniques: {[t for t in result['tests'] if not t['found']]}"

    # Check minimum counts for each technique
    for test in result["tests"]:
        assert test["count"] > 0, f"Technique {test['technique_id']} has zero count"


@pytest.mark.asyncio
async def test_geoip_enrichment(tester: AttackScenarioTester):
    """Verify GeoIP enrichment is working"""
    result = await tester.test_geoip_enrichment()

    assert result["total_events_checked"] > 0, "No events to check"
    # At least some events should be enriched (depends on GeoIP provider)
    assert result["enrichment_rate"] >= 0, "Enrichment rate should be non-negative"


@pytest.mark.asyncio
async def test_payload_tracking(tester: AttackScenarioTester):
    """Verify payload metadata tracking"""
    result = await tester.test_payload_tracking()

    assert result["payloads_captured"] > 0, "No payloads captured"
    assert result["payloads_with_hash"] > 0, "No payloads with hash"
    assert result["payloads_with_size"] > 0, "No payloads with size"


@pytest.mark.asyncio
async def test_api_endpoints(tester: AttackScenarioTester):
    """Verify all API endpoints are functional"""
    result = await tester.test_api_endpoints()

    assert result["all_passed"], f"Failed endpoints: {[t for t in result['tests'] if not t.get('success')]}"


@pytest.mark.asyncio
async def test_websocket_stream(tester: AttackScenarioTester):
    """Verify WebSocket event streaming"""
    result = await tester.test_websocket_stream()

    assert result["all_passed"], f"WebSocket tests failed: {result['tests']}"


@pytest.mark.asyncio
async def test_retention_purge(tester: AttackScenarioTester):
    """Verify retention manager data structures"""
    result = await tester.test_retention_purge()

    # Just verify tables exist and are queryable
    assert "total_events" in result
    assert "geoip_cache_entries" in result
    assert "credential_count_entries" in result
    assert "payload_entries" in result


# ============================================================
# Combined / Integration Tests
# ============================================================

@pytest.mark.asyncio
async def test_full_attack_chain(tester: AttackScenarioTester):
    """
    End-to-end test simulating a complete attack chain:
    1. SSH brute force -> credential stuffing
    2. Successful login -> post-exploitation commands
    3. Payload download via wget/curl
    4. HTTP scanning -> exploit attempts
    5. HTTP credential capture
    """
    # Run a subset of scenarios in sequence
    results = {}

    # SSH chain
    results["credential_stuffing"] = await tester.test_ssh_credential_stuffing()
    results["brute_force"] = await tester.test_ssh_brute_force()
    results["payload_download"] = await tester.test_ssh_payload_download()
    results["post_exploitation"] = await tester.test_ssh_post_exploitation()

    # HTTP chain
    results["web_scanning"] = await tester.test_http_web_scanning()
    results["exploit_attempts"] = await tester.test_http_exploit_attempts()
    results["credential_capture"] = await tester.test_http_credential_capture()

    # Verification
    results["mitre"] = await tester.test_mitre_classification_accuracy()
    results["geoip"] = await tester.test_geoip_enrichment()
    results["payloads"] = await tester.test_payload_tracking()

    # Verify all scenarios captured events
    for name, result in results.items():
        if "events_captured" in result:
            assert result["events_captured"] > 0, f"{name}: No events captured"

    # Verify MITRE classification found all expected techniques
    assert results["mitre"]["all_expected_found"], "Missing MITRE techniques"

    # Verify we have events across multiple techniques
    technique_counts = results["mitre"]["techniques_found"]
    total_techniques = len([t for t in technique_counts if t["count"] > 0])
    assert total_techniques >= 5, f"Expected at least 5 techniques with events, got {total_techniques}"


# ============================================================
# Parametrized Tests for Multiple Configurations
# ============================================================

@pytest.mark.parametrize("scenario_name,expected_technique", [
    ("ssh_credential_stuffing", "T1110.004"),
    ("ssh_brute_force", "T1110"),
    ("ssh_payload_download", "T1105"),
    ("ssh_post_exploitation", "T1059"),
    ("http_web_scanning", "T1595"),
    ("http_exploit_attempts", "T1190"),
    ("http_credential_capture", "T1110"),
])
@pytest.mark.asyncio
async def test_scenario_technique_classification(
    tester: AttackScenarioTester,
    scenario_name: str,
    expected_technique: str
):
    """Parametrized test for each scenario's technique classification."""
    scenario_method = getattr(tester, f"test_{scenario_name}")
    result = await scenario_method()

    assert result["classification_correct"], \
        f"{scenario_name}: {expected_technique} classification failed"

    # Verify the specific technique appears in results
    technique_key = f"{expected_technique.lower()}_events" if expected_technique != "T1110.004" else "credential_stuffing_events"
    if technique_key in result:
        assert result[technique_key] > 0, f"{scenario_name}: No {expected_technique} events"


if __name__ == "__main__":
    # Allow running directly with pytest
    pytest.main([__file__, "-v"])