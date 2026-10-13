"""
Incident Webhook & Alert Router for FuzeAgent Orchestrator.
Receives Prometheus / Alertmanager webhooks and direct incident triggers,
invoking the 3-channel remediation dispatcher and Loki coordination mechanism.
"""

import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from pydantic import BaseModel, Field

from .incident_remediation_dispatcher import (
    IncidentAlert,
    IncidentDispatchReport,
    IncidentRemediationDispatcher,
)
from .loki_incident_coordinator import LokiIncidentCoordinator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/orchestrator/alerts", tags=["Incident Alerts & Remediation"])

dispatcher = IncidentRemediationDispatcher()
coordinator = LokiIncidentCoordinator()


class DirectIncidentTriggerRequest(BaseModel):
    alert_name: str = Field(..., example="PostgresVolumeCorrupted")
    component: str = Field(..., example="fuzeinfra-postgres")
    severity: str = Field(default="critical", example="critical")
    summary: str = Field(..., example="ext4 filesystem I/O error on /var/lib/postgresql/data/pgdata")
    diagnostics: str = Field(..., example="could not open configuration file /var/lib/postgresql/data/pgdata/postgresql.conf: Input/output error")
    incident_id: Optional[str] = None
    target_repo: Optional[str] = "izzywdev/FuzeAgent"


class AlertmanagerWebhookPayload(BaseModel):
    receiver: Optional[str] = None
    status: Optional[str] = "firing"
    alerts: List[Dict[str, Any]] = Field(default_factory=list)
    commonLabels: Dict[str, Any] = Field(default_factory=dict)
    commonAnnotations: Dict[str, Any] = Field(default_factory=dict)
    externalURL: Optional[str] = None


@router.post(
    "/trigger",
    response_model=Dict[str, Any],
    summary="Trigger an incident remediation dispatch across all 3 channels",
)
async def trigger_incident(req: DirectIncidentTriggerRequest):
    """
    Manually or programmatically triggers the 3-channel incident remediation:
    1. Anthropic Managed Agents cloud session
    2. GitHub Issue with @fuze mention
    3. FuzeAgent DevOps template pod
    Arbitrated via Loki distributed ledger.
    """
    alert = IncidentAlert(
        alert_name=req.alert_name,
        component=req.component,
        severity=req.severity,
        summary=req.summary,
        diagnostics=req.diagnostics,
        incident_id=req.incident_id,
        target_repo=req.target_repo,
    )

    report: IncidentDispatchReport = await dispatcher.dispatch_incident(alert)

    return {
        "status": "success",
        "incident_id": report.incident_id,
        "alert_name": report.alert_name,
        "component": report.component,
        "winning_channel": report.winning_channel,
        "winning_agent_id": report.winning_agent_id,
        "active_remediation_link": report.active_remediation_link,
        "sessions": [
            {
                "channel": s.channel,
                "agent_id": s.agent_id,
                "won_election": s.won_election,
                "status": s.status,
                "message": s.message,
                "details": s.details,
            }
            for s in report.sessions
        ],
        "created_at": report.created_at,
    }


@router.post(
    "/incident-webhook",
    summary="Prometheus Alertmanager Webhook Receiver",
)
async def alertmanager_webhook(payload: AlertmanagerWebhookPayload):
    """
    Receives alerts from Prometheus Alertmanager or Loki alerting rules,
    translates firing alerts into incident dispatches.
    """
    logger.info(f"📥 Received Alertmanager webhook with {len(payload.alerts)} alerts")
    reports = []

    for alert_data in payload.alerts:
        labels = alert_data.get("labels", {})
        annotations = alert_data.get("annotations", {})
        status_val = alert_data.get("status", payload.status)

        if status_val != "firing":
            continue

        alert_name = labels.get("alertname", "InfrastructureIncident")
        component = labels.get("container") or labels.get("pod") or labels.get("app") or "infrastructure"
        severity = labels.get("severity", "critical")
        summary = annotations.get("summary") or annotations.get("message") or f"{alert_name} on {component}"
        diagnostics = annotations.get("description") or str(alert_data)

        alert = IncidentAlert(
            alert_name=alert_name,
            component=component,
            severity=severity,
            summary=summary,
            diagnostics=diagnostics,
        )

        rep = await dispatcher.dispatch_incident(alert)
        reports.append(rep)

    return {
        "status": "processed",
        "alerts_processed": len(reports),
        "dispatches": [
            {
                "incident_id": r.incident_id,
                "winner": r.winning_channel,
                "link": r.active_remediation_link,
            }
            for r in reports
        ],
    }


@router.get(
    "/claims/{incident_id}",
    summary="Query active claims in Loki for an incident",
)
async def get_incident_claims(incident_id: str):
    """Inspect active claims and audit trail in Loki for a given incident."""
    claims = await coordinator.query_incident_claims(incident_id)
    return {
        "incident_id": incident_id,
        "claims_count": len(claims),
        "active_claim": claims[0] if claims else None,
        "all_claims": claims,
    }
