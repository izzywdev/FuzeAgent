"""
Unit & Integration Tests for Incident Remediation & Loki Coordination System.
Tests:
1. Distributed leader election and deduplication in LokiIncidentCoordinator.
2. Verified stand-down message: "Issue <link> is already being handled by <owner>".
3. 3-channel dispatch (Anthropic Cloud, GitHub @fuze Issue, FuzeAgent DevOps Pod).
4. Alertmanager Webhook receiver and manual trigger API.
"""

import asyncio
import json
import os
import sys
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.abspath("."))
sys.path.insert(0, os.path.abspath("services/orchestrator"))

from services.orchestrator.loki_incident_coordinator import (
    ClaimResult,
    IncidentClaim,
    LokiIncidentCoordinator,
)
from services.orchestrator.incident_remediation_dispatcher import (
    IncidentAlert,
    IncidentDispatchReport,
    IncidentRemediationDispatcher,
    SessionOutcome,
)
from services.orchestrator.incident_webhook_router import (
    DirectIncidentTriggerRequest,
    router,
)
from fastapi import FastAPI
from fastapi.testclient import TestClient


class MockLokiCoordinator(LokiIncidentCoordinator):
    """In-memory mock for Loki to test multi-agent concurrency and consensus."""

    def __init__(self):
        super().__init__(loki_url="http://mock-loki:3100")
        self.claims_store: list[IncidentClaim] = []

    async def query_incident_claims(self, incident_id: str):
        return [c for c in self.claims_store if c.incident_id == incident_id]

    async def push_claim_to_loki(self, claim: IncidentClaim):
        self.claims_store.append(claim)
        return True


@pytest.mark.asyncio
async def test_loki_leader_election_single_winner_and_stand_downs():
    """
    Simulates 3 agents (Anthropic Cloud Session, GitHub Action, FuzeAgent Pod)
    jumping on the same incident at once.
    Verifies exactly 1 winner is elected and the other 2 stand down with:
    'Issue <link> is already being handled by <owner>'
    """
    coordinator = MockLokiCoordinator()
    incident_id = "inc-postgresvolume-test123"
    canonical_link = "https://github.com/izzywdev/FuzeAgent/issues/42"

    agent1_id = "anthropic-session-cloud-01"
    agent2_id = "github-action-fuze-02"
    agent3_id = "fuzeagent-devops-pod-03"

    # Agent 1 claims first
    res1 = await coordinator.claim_incident(
        incident_id=incident_id,
        owner=agent1_id,
        channel="anthropic_cloud",
        link=canonical_link,
        consensus_jitter_ms=10,
    )

    assert res1.won is True
    assert res1.owner == agent1_id
    assert res1.link == canonical_link

    # Agent 2 attempts to claim
    res2 = await coordinator.claim_incident(
        incident_id=incident_id,
        owner=agent2_id,
        channel="github_action",
        link=canonical_link,
        consensus_jitter_ms=10,
    )

    assert res2.won is False
    assert res2.owner == agent1_id
    expected_msg = f"Issue {canonical_link} is already being handled by {agent1_id}"
    assert res2.message == expected_msg

    # Agent 3 attempts to claim
    res3 = await coordinator.claim_incident(
        incident_id=incident_id,
        owner=agent3_id,
        channel="fuzeagent_devops_pod",
        link=canonical_link,
        consensus_jitter_ms=10,
    )

    assert res3.won is False
    assert res3.owner == agent1_id
    assert res3.message == expected_msg


@pytest.mark.asyncio
async def test_incident_remediation_dispatcher_three_mechanisms():
    """
    Verifies that the dispatcher launches all 3 channels upon receiving an alert,
    and returns a cohesive dispatch report.
    """
    mock_coord = MockLokiCoordinator()
    dispatcher = IncidentRemediationDispatcher(
        coordinator=mock_coord,
        github_token="fake-token-test",
        anthropic_api_key="fake-key-test",
    )

    alert = IncidentAlert(
        alert_name="PostgresVolumeCorrupted",
        component="fuzeinfra-postgres-0",
        severity="critical",
        summary="ext4 I/O error on /var/lib/postgresql/data/pgdata",
        diagnostics="could not open configuration file postgresql.conf: Input/output error",
        target_repo="izzywdev/FuzeAgent",
    )

    with patch.object(
        dispatcher, "_create_github_issue", new_callable=AsyncMock
    ) as mock_issue:
        mock_issue.return_value = "https://github.com/izzywdev/FuzeAgent/issues/999"

        report: IncidentDispatchReport = await dispatcher.dispatch_incident(alert)

        assert report.alert_name == "PostgresVolumeCorrupted"
        assert report.component == "fuzeinfra-postgres-0"
        assert len(report.sessions) == 3

        # One winner and two stand downs
        winners = [s for s in report.sessions if s.won_election]
        stand_downs = [s for s in report.sessions if not s.won_election]

        assert len(winners) == 1
        assert len(stand_downs) == 2

        # Stand downs must verify the required message format
        for s in stand_downs:
            assert "is already being handled by" in s.message
            assert s.details.get("link") == "https://github.com/izzywdev/FuzeAgent/issues/999"


def test_incident_webhook_router_endpoints():
    """
    Tests the FastAPI router endpoints for manual triggering and Alertmanager webhooks.
    """
    app = FastAPI()
    app.include_router(router)
    client = TestClient(app)

    # 1. Test direct trigger endpoint
    payload = {
        "alert_name": "FuzefrontApplicationsDown",
        "component": "fuzefront-applications",
        "severity": "critical",
        "summary": "Pod 0/1 crashing due to database connection timeout",
        "diagnostics": "Knex error: connect ECONNREFUSED 10.43.0.1:5432",
    }

    with patch(
        "services.orchestrator.incident_webhook_router.dispatcher.dispatch_incident"
    ) as mock_dispatch:
        mock_dispatch.return_value = IncidentDispatchReport(
            incident_id="inc-fuzefront-001",
            alert_name="FuzefrontApplicationsDown",
            component="fuzefront-applications",
            winning_channel="anthropic_managed_agents_cloud",
            winning_agent_id="anthropic-session-123",
            active_remediation_link="https://github.com/izzywdev/FuzeAgent/issues/100",
            sessions=[
                SessionOutcome(
                    channel="anthropic_managed_agents_cloud",
                    agent_id="anthropic-session-123",
                    won_election=True,
                    status="active_remediating",
                    message="Remediating",
                ),
                SessionOutcome(
                    channel="github_actions_workflow",
                    agent_id="gh-123",
                    won_election=False,
                    status="stood_down",
                    message="Issue https://github.com/izzywdev/FuzeAgent/issues/100 is already being handled by anthropic-session-123",
                ),
                SessionOutcome(
                    channel="fuzeagent_devops_pod",
                    agent_id="pod-123",
                    won_election=False,
                    status="stood_down",
                    message="Issue https://github.com/izzywdev/FuzeAgent/issues/100 is already being handled by anthropic-session-123",
                ),
            ],
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        resp = client.post("/api/orchestrator/alerts/trigger", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["incident_id"] == "inc-fuzefront-001"
        assert data["winning_channel"] == "anthropic_managed_agents_cloud"
        assert len(data["sessions"]) == 3

    # 2. Test Alertmanager webhook endpoint
    am_payload = {
        "status": "firing",
        "alerts": [
            {
                "status": "firing",
                "labels": {
                    "alertname": "PostgresVolumeCorrupted",
                    "pod": "fuzeinfra-postgres-0",
                    "severity": "critical",
                },
                "annotations": {
                    "summary": "ext4 I/O error",
                    "description": "could not open configuration file postgresql.conf: Input/output error",
                },
            }
        ],
    }

    with patch(
        "services.orchestrator.incident_webhook_router.dispatcher.dispatch_incident"
    ) as mock_dispatch:
        mock_dispatch.return_value = IncidentDispatchReport(
            incident_id="inc-postgres-am",
            alert_name="PostgresVolumeCorrupted",
            component="fuzeinfra-postgres-0",
            winning_channel="fuzeagent_devops_pod",
            winning_agent_id="pod-winner",
            active_remediation_link="https://github.com/izzywdev/FuzeAgent/issues/101",
            sessions=[],
            created_at=datetime.now(timezone.utc).isoformat(),
        )

        resp2 = client.post(
            "/api/orchestrator/alerts/incident-webhook", json=am_payload
        )
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert data2["status"] == "processed"
        assert data2["alerts_processed"] == 1


if __name__ == "__main__":
    print("Running test_loki_leader_election_single_winner_and_stand_downs...")
    asyncio.run(test_loki_leader_election_single_winner_and_stand_downs())
    print("Running test_incident_remediation_dispatcher_three_mechanisms...")
    asyncio.run(test_incident_remediation_dispatcher_three_mechanisms())
    print("Running test_incident_webhook_router_endpoints...")
    test_incident_webhook_router_endpoints()
    print("✅ All incident remediation & Loki coordination tests passed successfully!")
