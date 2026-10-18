"""Tests for the FuzeFront "build your application" API (services/orchestrator/app_builds).

Self-contained: a fake FuzeFront (httpx.MockTransport) + in-memory store; no DB, no network.
Run:  cd services/orchestrator && python -m pytest tests/test_app_builds.py -m "unit or api"
"""

import asyncio
import json
import os
from typing import Any, Dict, List, Optional

import httpx
import pytest
from fastapi import FastAPI

from app_builds import flags
from app_builds.config import Settings
from app_builds.deployer import (
    AppDeployer,
    DeployContext,
    DeployError,
    DeployResult,
    NotConfiguredDeployer,
)
from app_builds.fuzefront import FuzeFrontClient, resolve_callback_url
from app_builds.ids import AGENT_SESSION_REF_RE, mint_agent_session_ref
from app_builds.models import BuildRecord, IllegalTransition, can_transition
from app_builds.router import router, set_runtime
from app_builds.runtime import BuildRuntime, classify_callback
from app_builds.slug import (
    SLUG_RE,
    candidate_slugs,
    derive_base_slug,
    validate_integration,
)
from app_builds.store import InMemoryBuildStore

SUFFIX = "01h455vb4pex5vsknk084sn02q"
BID = f"front_abs_{SUFFIX}"
ORG = f"org_{SUFFIX}"
USR = f"usr_{SUFFIX}"
TOKEN = "inbound-secret-token"  # nosec B105 -- test-only fixture, not a real credential
REG_TOKEN = (
    "registration-token"  # nosec B105 -- test-only fixture, not a real credential
)
API = "http://fuzefront-applications.fuzefront.svc:3003"
PUBLIC = "https://app.fuzefront.com"
CB_PATH = f"/api/v1/app-registry/build-sessions/{BID}/status"

INTEGRATION = {
    "type": "module-federation",
    "remoteEntry": "/apps/my-app/remoteEntry.js",
    "scope": "myApp",
    "module": "./App",
}


def settings(**kw: Any) -> Settings:
    base = dict(
        inbound_token=TOKEN,
        fuzefront_api_url=API,
        fuzefront_public_base_url=PUBLIC,
        fuzefront_token=REG_TOKEN,
        callback_base_delay_s=5.0,
        callback_max_delay_s=300.0,
        callback_max_attempts=5,
        registry_attempts=3,
    )
    base.update(kw)
    return Settings(**base)


def body(**kw: Any) -> Dict[str, Any]:
    b = {
        "buildSessionId": BID,
        "organizationId": ORG,
        "requestedByUserId": USR,
        "context": "organization",
        "name": "My Cool App",
        "brief": "Build a todo list app",
        "callbackUrl": f"{PUBLIC}{CB_PATH}",
    }
    b.update(kw)
    return b


class FakeFuzeFront:
    """Records every call in order; scriptable callback responses."""

    def __init__(self) -> None:
        self.calls: List[Dict[str, Any]] = []
        self.taken: set = set()
        self.post_conflicts: set = set()  # slugs that 409 on POST
        self.callback_script: List[Any] = (
            []
        )  # (status, json) | Exception, consumed in order
        self.register_status = 201

    def handler(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        entry = {
            "method": request.method,
            "path": path,
            "auth": request.headers.get("authorization"),
            "json": json.loads(request.content) if request.content else None,
        }
        self.calls.append(entry)
        if path.endswith("/status") and request.method == "POST":
            if self.callback_script:
                item = self.callback_script.pop(0)
                if isinstance(item, Exception):
                    raise item
                return httpx.Response(item[0], json=item[1])
            return httpx.Response(200, json={"status": "ok"})
        if path.startswith("/api/v1/app-registry/apps/") and request.method == "GET":
            slug = path.rsplit("/", 1)[1]
            return httpx.Response(200 if slug in self.taken else 404, json={})
        if path == "/api/v1/app-registry/apps" and request.method == "POST":
            slug = entry["json"]["manifest"]["slug"]
            if slug in self.post_conflicts or slug in self.taken:
                return httpx.Response(409, json={"error": "conflict"})
            if self.register_status >= 300:
                return httpx.Response(self.register_status, json={"error": "x"})
            self.taken.add(slug)
            return httpx.Response(201, json={})
        return httpx.Response(500)

    def callbacks(self) -> List[Dict[str, Any]]:
        return [c["json"] for c in self.calls if c["path"].endswith("/status")]

    def registrations(self) -> List[Dict[str, Any]]:
        return [
            c
            for c in self.calls
            if c["method"] == "POST" and c["path"] == "/api/v1/app-registry/apps"
        ]


class FakeDeployer(AppDeployer):
    def __init__(
        self, fail: Optional[DeployError] = None, gate: Optional[asyncio.Event] = None
    ) -> None:
        self.builds = 0
        self.deploys = 0
        self.cancels = 0
        self.fail = fail
        self.gate = gate

    async def build(self, ctx: DeployContext) -> Dict[str, Any]:
        self.builds += 1
        if self.gate:
            await self.gate.wait()
        if self.fail:
            raise self.fail
        return {"image": "ghcr.io/x/app:1"}

    async def deploy(
        self, ctx: DeployContext, artifact: Dict[str, Any]
    ) -> DeployResult:
        self.deploys += 1
        return DeployResult(integration=INTEGRATION)

    async def cancel(self, ctx: DeployContext) -> None:
        self.cancels += 1


class Clock:
    def __init__(self) -> None:
        self.t = 1_000_000.0
        self.sleeps: List[float] = []

    def __call__(self) -> float:
        return self.t

    async def sleep(self, s: float) -> None:
        self.sleeps.append(s)


def make_runtime(
    ff: FakeFuzeFront,
    deployer: Optional[AppDeployer] = None,
    store=None,
    clock=None,
    **skw,
):
    s = settings(**skw)
    clock = clock or Clock()
    client = FuzeFrontClient(
        s, httpx.AsyncClient(transport=httpx.MockTransport(ff.handler))
    )
    rt = BuildRuntime(
        store or InMemoryBuildStore(),
        deployer or FakeDeployer(),
        client,
        s,
        clock=clock,
        sleep=clock.sleep,
    )
    return rt, clock


def req(**kw: Any):
    from app_builds.models import LaunchRequest

    return LaunchRequest.model_validate(body(**kw))


@pytest.fixture(autouse=True)
def _flag_on():
    flags.set_provider(lambda key, default, ctx: True)
    yield
    flags.set_provider(None)
    set_runtime(None)


def app_for(runtime: Optional[BuildRuntime]) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    set_runtime(runtime)
    return app


def http_client(app: FastAPI) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://orch"
    )


AUTH = {"Authorization": f"Bearer {TOKEN}"}


# ═══ units ═══════════════════════════════════════════════════════════════════
@pytest.mark.unit
def test_mint_agent_session_ref_is_typeid_and_unique():
    refs = {mint_agent_session_ref() for _ in range(200)}
    assert len(refs) == 200
    assert all(AGENT_SESSION_REF_RE.match(r) for r in refs)


@pytest.mark.unit
@pytest.mark.parametrize(
    "cur,tgt,ok",
    [
        ("accepted", "building", True),
        ("building", "deploying", True),
        ("deploying", "deployed", True),
        ("accepted", "deploying", True),  # forward skips are allowed, backward are not
        ("deploying", "building", False),
        ("building", "building", False),
        ("deployed", "failed", False),
        ("failed", "building", False),
        ("cancelled", "deployed", False),
        ("building", "failed", True),
        ("deploying", "cancelled", True),
    ],
)
def test_state_machine_forward_only(cur, tgt, ok):
    assert can_transition(cur, tgt) is ok


@pytest.mark.unit
def test_deployed_requires_registration():
    r = BuildRecord(
        BID,
        "agent_abs_x",
        ORG,
        USR,
        "organization",
        "n",
        "b",
        "u",
        "h",
        status="deploying",
    )
    with pytest.raises(IllegalTransition):
        r.advance("deployed")
    r.registered, r.app_slug = True, "my-app"
    r.advance("deployed")
    assert r.status == "deployed"
    with pytest.raises(IllegalTransition):
        r.advance("building")


@pytest.mark.unit
def test_slug_derivation_valid_and_deterministic():
    assert derive_base_slug("My Cool App!", BID) == "my-cool-app"
    assert derive_base_slug("Café Ünïcode", BID) == "cafe-unicode"
    fallback = derive_base_slug("!!", BID)
    assert fallback.startswith("app-")
    cands = list(candidate_slugs("My Cool App", BID))
    assert cands == list(candidate_slugs("My Cool App", BID))
    assert len(set(cands)) == len(cands)
    assert all(SLUG_RE.match(c) for c in cands)
    assert all(SLUG_RE.match(c) for c in candidate_slugs("x" * 300, BID))


@pytest.mark.unit
def test_validate_integration():
    assert validate_integration(INTEGRATION) == []
    assert validate_integration({"type": "module-federation", "remoteEntry": "/a.js"})
    assert validate_integration({"type": "iframe", "url": "javascript:alert(1)"})
    assert validate_integration({"type": "iframe", "url": "//evil.example/x"})
    assert validate_integration("nope")


@pytest.mark.unit
def test_resolve_callback_url():
    s = settings()
    assert (
        resolve_callback_url(CB_PATH, BID, s) == PUBLIC + CB_PATH
    )  # relative -> public base
    assert resolve_callback_url(PUBLIC + CB_PATH, BID, s)
    assert resolve_callback_url(API + CB_PATH, BID, s)
    for bad in [
        "https://evil.example" + CB_PATH,  # token exfiltration
        PUBLIC + "/other",
        PUBLIC + CB_PATH + "?x=1",
        "https://user:pw@app.fuzefront.com" + CB_PATH,
        "ftp://app.fuzefront.com" + CB_PATH,
        "//evil.example" + CB_PATH,
    ]:
        with pytest.raises(ValueError):
            resolve_callback_url(bad, BID, s)
    with pytest.raises(ValueError):
        resolve_callback_url(
            CB_PATH, BID, settings(fuzefront_api_url="", fuzefront_public_base_url="")
        )
    # relative falls back to the API url when no public base is set
    assert (
        resolve_callback_url(CB_PATH, BID, settings(fuzefront_public_base_url=""))
        == API + CB_PATH
    )


@pytest.mark.unit
def test_classify_callback():
    assert classify_callback(200, {}) == "delivered"
    assert classify_callback(503, {}) == "retry"
    assert classify_callback(429, {}) == "retry"
    assert classify_callback(409, {"code": "ORG_MISMATCH"}) == "halt"
    assert (
        classify_callback(409, {"message": "Build session is already deployed"})
        == "halt"
    )
    assert (
        classify_callback(
            409,
            {"message": 'Cannot move a build session from "building" to "building"'},
        )
        == "moot"
    )
    assert classify_callback(403, {}) == "dead"


@pytest.mark.unit
def test_flag_provider_env_and_failsafe(monkeypatch):
    flags.set_provider(None)
    monkeypatch.delenv("FEATURE_FLAG_FUZEAGENT_APP_BUILDS_ENABLED", raising=False)
    assert flags.app_builds_enabled() is False  # release flag defaults OFF
    monkeypatch.setenv("FEATURE_FLAG_FUZEAGENT_APP_BUILDS_ENABLED", "true")
    assert flags.app_builds_enabled() is True
    monkeypatch.setenv("FEATURE_FLAG_FUZEAGENT_APP_BUILDS_ENABLED", "nope")
    assert flags.app_builds_enabled() is False

    def boom(*a):
        raise RuntimeError("unleash down")

    flags.set_provider(boom)
    assert flags.app_builds_enabled() is False  # provider error -> OFF


@pytest.mark.unit
def test_settings_fail_closed_listing():
    assert Settings().missing_for_launch() == (
        "APP_BUILD_API_TOKEN",
        "FUZEFRONT_API_URL",
        "FUZEFRONT_REGISTRATION_TOKEN",
    )
    assert settings().missing_for_launch() == ()
    s = Settings.from_env(
        {
            "APP_BUILD_API_TOKEN": " t ",  # nosec B105 -- test-only fixture, not a real credential
            "FUZEFRONT_API_URL": "http://x/",
            "APP_BUILD_CALLBACK_MAX_ATTEMPTS": "abc",
        }
    )
    assert (
        s.inbound_token == "t"  # nosec B105 -- test-only fixture, not a real credential
        and s.fuzefront_api_url == "http://x"
        and s.callback_max_attempts == 5
    )


# ═══ HTTP: auth / flag / validation / idempotency ════════════════════════════
@pytest.mark.api
@pytest.mark.asyncio
async def test_auth_missing_bad_and_valid_token():
    ff = FakeFuzeFront()
    rt, _ = make_runtime(ff)
    async with http_client(app_for(rt)) as c:
        assert (await c.post("/api/v1/app-builds", json=body())).status_code == 401
        assert (
            await c.post(
                "/api/v1/app-builds",
                json=body(),
                headers={"Authorization": "Bearer wrong"},
            )
        ).status_code == 401
        assert (
            await c.post(
                "/api/v1/app-builds",
                json=body(),
                headers={"Authorization": "Basic " + TOKEN},
            )
        ).status_code == 401
        assert (
            await c.post(
                "/api/v1/app-builds", json=body(), headers={"Authorization": "Bearer "}
            )
        ).status_code == 401
        assert (await c.get(f"/api/v1/app-builds/{BID}")).status_code == 401
        assert (await c.post(f"/api/v1/app-builds/{BID}/cancel")).status_code == 401
        ok = await c.post("/api/v1/app-builds", json=body(), headers=AUTH)
        assert ok.status_code == 201
        assert ok.json()["agentSessionRef"].startswith("agent_abs_")
    await rt.wait_idle()


@pytest.mark.api
@pytest.mark.asyncio
async def test_unset_inbound_token_fails_closed():
    ff = FakeFuzeFront()
    rt, _ = make_runtime(
        ff, inbound_token=""
    )  # nosec B106 -- test-only fixture, not a real credential
    async with http_client(app_for(rt)) as c:
        for hdr in (
            {},
            AUTH,
            {"Authorization": "Bearer "},
            {"Authorization": "Bearer "},
        ):
            r = await c.post("/api/v1/app-builds", json=body(), headers=hdr)
            assert r.status_code == 503 and r.json()["error"] == "builder_unavailable"
    assert ff.calls == []


@pytest.mark.api
@pytest.mark.asyncio
async def test_no_runtime_and_missing_registry_config_fail_closed():
    async with http_client(app_for(None)) as c:
        assert (
            await c.post("/api/v1/app-builds", json=body(), headers=AUTH)
        ).status_code == 503
    rt, _ = make_runtime(
        FakeFuzeFront(), fuzefront_token=""
    )  # nosec B106 -- test-only fixture, not a real credential
    async with http_client(app_for(rt)) as c:
        r = await c.post("/api/v1/app-builds", json=body(), headers=AUTH)
        assert r.status_code == 503 and r.json()["error"] == "builder_unavailable"


@pytest.mark.api
@pytest.mark.asyncio
async def test_flag_off_and_on():
    ff = FakeFuzeFront()
    rt, _ = make_runtime(ff)
    app = app_for(rt)
    flags.set_provider(lambda k, d, c: False)
    async with http_client(app) as c:
        off = await c.post("/api/v1/app-builds", json=body(), headers=AUTH)
        assert off.status_code == 503 and off.json()["error"] == "feature_disabled"
        assert (
            await c.get(f"/api/v1/app-builds/{BID}", headers=AUTH)
        ).status_code == 503
        assert (
            await c.post(f"/api/v1/app-builds/{BID}/cancel", headers=AUTH)
        ).status_code == 503
        # bad token is still 401 with the flag off: the flag never turns auth into a no-op
        assert (await c.post("/api/v1/app-builds", json=body())).status_code == 401
        assert await rt.store.get(BID) is None  # nothing persisted while OFF
        flags.set_provider(lambda k, d, c_: True)
        assert (
            await c.post("/api/v1/app-builds", json=body(), headers=AUTH)
        ).status_code == 201
    await rt.wait_idle()


@pytest.mark.api
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "patch",
    [
        {"id": "front_abs_" + SUFFIX},  # unknown key (client-supplied id)
        {"extra": 1},
        {"brief": "x" * 4001},
        {"brief": ""},
        {"brief": 123},
        {"name": "  "},
        {"name": "n" * 121},
        {"context": "team"},
        {"organizationId": "usr_" + SUFFIX},
        {"organizationId": "org_short"},
        {"requestedByUserId": "bogus"},
        {"buildSessionId": "nope"},
        {"callbackUrl": "https://evil.example" + CB_PATH},
        {"callbackUrl": PUBLIC + "/api/v1/other"},
    ],
)
async def test_validation_rejects(patch):
    ff = FakeFuzeFront()
    rt, _ = make_runtime(ff)
    async with http_client(app_for(rt)) as c:
        r = await c.post("/api/v1/app-builds", json=body(**patch), headers=AUTH)
        assert r.status_code == 400, r.text
        assert r.json()["error"] == "validation_error"
    assert await rt.store.list_active() == []


@pytest.mark.api
@pytest.mark.asyncio
async def test_validation_malformed_json_and_oversize():
    rt, _ = make_runtime(FakeFuzeFront())
    async with http_client(app_for(rt)) as c:
        r = await c.post(
            "/api/v1/app-builds",
            content=b"{not json",
            headers={**AUTH, "content-type": "application/json"},
        )
        assert r.status_code == 400
        r = await c.post(
            "/api/v1/app-builds",
            content=b" " * (40 * 1024),
            headers={**AUTH, "content-type": "application/json"},
        )
        assert r.status_code == 413


@pytest.mark.api
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "bad,expected",
    [
        ("https://evil.example" + CB_PATH, "origin is not an allowed FuzeFront origin"),
        (PUBLIC + "/api/v1/other", "path must be this session's status endpoint"),
        ("ftp://app.fuzefront.com" + CB_PATH, "http(s) URL without credentials"),
    ],
)
async def test_callback_rejection_message_is_fixed_and_leaks_nothing(bad, expected):
    """The 400 carries a fixed message chosen by reason code, never exception text (CodeQL
    py/stack-trace-exposure) and never server configuration detail."""
    ff = FakeFuzeFront()
    rt, _ = make_runtime(ff)
    async with http_client(app_for(rt)) as c:
        r = await c.post("/api/v1/app-builds", json=body(callbackUrl=bad), headers=AUTH)
    assert r.status_code == 400
    msg = r.json()["fields"][0]["message"]
    assert expected in msg
    assert "FUZEFRONT_" not in r.text and "Traceback" not in r.text


@pytest.mark.api
@pytest.mark.asyncio
async def test_relative_callback_url_accepted_and_resolved():
    ff = FakeFuzeFront()
    rt, _ = make_runtime(ff)
    async with http_client(app_for(rt)) as c:
        r = await c.post(
            "/api/v1/app-builds", json=body(callbackUrl=CB_PATH), headers=AUTH
        )
        assert r.status_code == 201
    await rt.wait_idle()
    assert (await rt.store.get(BID)).callback_url == PUBLIC + CB_PATH


@pytest.mark.api
@pytest.mark.asyncio
async def test_idempotent_retry_returns_same_session_and_runs_once():
    ff = FakeFuzeFront()
    dep = FakeDeployer()
    rt, _ = make_runtime(ff, dep)
    async with http_client(app_for(rt)) as c:
        first = await c.post("/api/v1/app-builds", json=body(), headers=AUTH)
        second = await c.post("/api/v1/app-builds", json=body(), headers=AUTH)
        await rt.wait_idle()
        third = await c.post("/api/v1/app-builds", json=body(), headers=AUTH)
        assert (first.status_code, second.status_code, third.status_code) == (
            201,
            200,
            200,
        )
        assert (
            first.json()["agentSessionRef"]
            == second.json()["agentSessionRef"]
            == third.json()["agentSessionRef"]
        )
        conflict = await c.post(
            "/api/v1/app-builds", json=body(brief="different"), headers=AUTH
        )
        assert (
            conflict.status_code == 409
            and conflict.json()["error"] == "idempotency_conflict"
        )
    assert dep.builds == 1 and len(ff.registrations()) == 1


@pytest.mark.api
@pytest.mark.asyncio
async def test_session_url_only_when_template_configured():
    rt, _ = make_runtime(
        FakeFuzeFront(),
        session_url_template="https://app.fuzefront.com/app/fuzeagent/builds/{agentSessionRef}",
    )
    async with http_client(app_for(rt)) as c:
        r = await c.post("/api/v1/app-builds", json=body(), headers=AUTH)
        assert r.json()["agentSessionUrl"].endswith(r.json()["agentSessionRef"])
    await rt.wait_idle()
    rt2, _ = make_runtime(FakeFuzeFront())
    async with http_client(app_for(rt2)) as c:
        r = await c.post("/api/v1/app-builds", json=body(), headers=AUTH)
        assert "agentSessionUrl" not in r.json()
    await rt2.wait_idle()


@pytest.mark.api
@pytest.mark.asyncio
async def test_get_and_cancel_endpoints():
    gate = asyncio.Event()
    ff = FakeFuzeFront()
    dep = FakeDeployer(gate=gate)
    rt, _ = make_runtime(ff, dep)
    async with http_client(app_for(rt)) as c:
        assert (await c.get("/api/v1/app-builds/nope", headers=AUTH)).status_code == 404
        assert (
            await c.get(f"/api/v1/app-builds/{BID}", headers=AUTH)
        ).status_code == 404
        assert (
            await c.post(f"/api/v1/app-builds/{BID}/cancel", headers=AUTH)
        ).status_code == 404
        await c.post("/api/v1/app-builds", json=body(), headers=AUTH)
        await asyncio.sleep(0.05)
        assert (await c.get(f"/api/v1/app-builds/{BID}", headers=AUTH)).json()[
            "status"
        ] == "building"
        cancelled = await c.post(f"/api/v1/app-builds/{BID}/cancel", headers=AUTH)
        assert cancelled.status_code == 200
        assert (
            cancelled.json()["status"] == "cancelled"
            and cancelled.json()["cancelled"] is True
        )
        again = await c.post(
            f"/api/v1/app-builds/{BID}/cancel", headers=AUTH
        )  # no-op on terminal
        assert again.status_code == 200 and again.json()["cancelled"] is False
    gate.set()
    await rt.wait_idle()
    assert (
        ff.registrations() == []
    )  # cancelled before registration, and stays cancelled
    assert dep.cancels == 1
    assert (await rt.store.get(BID)).status == "cancelled"


# ═══ runtime: build + register + callbacks ═══════════════════════════════════
async def run_to_completion(rt: BuildRuntime, **kw: Any) -> BuildRecord:
    await rt.accept(req(**kw))
    await rt.wait_idle()
    return await rt.store.get(BID)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_default_deployer_fails_closed_with_deployer_unavailable():
    ff = FakeFuzeFront()
    rt, _ = make_runtime(ff, NotConfiguredDeployer())
    rec = await run_to_completion(rt)
    assert rec.status == "failed" and rec.error_code == "deployer_unavailable"
    assert ff.registrations() == []  # never fake a deploy
    await rt.deliver_due()
    cbs = ff.callbacks()
    assert [c["status"] for c in cbs] == ["building", "failed"]
    assert cbs[-1]["errorCode"] == "deployer_unavailable"
    assert "appSlug" not in cbs[-1]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_happy_path_registers_in_session_org_then_reports_deployed():
    ff = FakeFuzeFront()
    dep = FakeDeployer()
    rt, _ = make_runtime(ff, dep)
    rec = await run_to_completion(rt)
    assert rec.status == "deployed" and rec.app_slug == "my-cool-app"
    reg = ff.registrations()
    assert len(reg) == 1
    assert reg[0]["json"]["organizationId"] == ORG  # the SESSION's org, nothing else
    assert reg[0]["auth"] == f"Bearer {REG_TOKEN}"
    m = reg[0]["json"]["manifest"]
    assert (
        m["slug"] == "my-cool-app"
        and m["manifestVersion"] == "1"
        and m["integration"] == INTEGRATION
    )
    assert m["visibility"] == "organization"
    # Nothing is sent before the outbox is drained, and `deployed` is after the registration.
    await rt.deliver_due()
    cbs = ff.callbacks()
    assert [c["status"] for c in cbs] == ["building", "deploying", "deployed"]
    assert cbs[-1] == {"status": "deployed", "appSlug": "my-cool-app"}
    order = [
        ("reg" if c in reg else "cb:" + c["json"]["status"])
        for c in ff.calls
        if c in reg or c["path"].endswith("/status")
    ]
    assert order.index("reg") < order.index("cb:deployed")
    assert all(c["auth"] == f"Bearer {REG_TOKEN}" for c in ff.calls)
    assert all(
        c["method"] in ("GET", "POST") for c in ff.calls
    )  # never PUT: no editing existing apps


@pytest.mark.integration
@pytest.mark.asyncio
async def test_personal_context_registers_private_into_session_org():
    ff = FakeFuzeFront()
    rt, _ = make_runtime(ff)
    await run_to_completion(rt, context="personal")
    assert ff.registrations()[0]["json"]["manifest"]["visibility"] == "private"
    assert ff.registrations()[0]["json"]["organizationId"] == ORG


@pytest.mark.integration
@pytest.mark.asyncio
async def test_slug_conflict_picks_suffixed_alternative_before_registering():
    ff = FakeFuzeFront()
    ff.taken.add("my-cool-app")  # someone else's app: must never be edited
    rt, _ = make_runtime(ff)
    rec = await run_to_completion(rt)
    assert rec.status == "deployed"
    assert rec.app_slug != "my-cool-app" and rec.app_slug.startswith("my-cool-app-")
    assert [r["json"]["manifest"]["slug"] for r in ff.registrations()] == [rec.app_slug]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_post_409_race_moves_to_next_candidate():
    ff = FakeFuzeFront()
    ff.post_conflicts.add("my-cool-app")  # free on GET, but lost the race on POST
    rt, _ = make_runtime(ff)
    rec = await run_to_completion(rt)
    assert rec.status == "deployed" and rec.app_slug.startswith("my-cool-app-")
    assert len(ff.registrations()) == 2


@pytest.mark.integration
@pytest.mark.asyncio
async def test_registry_down_fails_with_registry_unavailable_and_no_deployed():
    ff = FakeFuzeFront()
    ff.register_status = 503
    rt, clock = make_runtime(ff)
    rec = await run_to_completion(rt)
    assert rec.status == "failed" and rec.error_code == "registry_unavailable"
    assert clock.sleeps  # backed off between registry attempts
    await rt.deliver_due()
    assert "deployed" not in [c["status"] for c in ff.callbacks()]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_registry_auth_failure_reported():
    ff = FakeFuzeFront()
    ff.register_status = 403
    rt, _ = make_runtime(ff)
    rec = await run_to_completion(rt)
    assert rec.status == "failed" and rec.error_code == "registry_auth_failed"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_deployer_error_and_invalid_integration_fail_cleanly():
    rt, _ = make_runtime(
        FakeFuzeFront(), FakeDeployer(fail=DeployError("build_failed", "compile error"))
    )
    rec = await run_to_completion(rt)
    assert rec.status == "failed" and rec.error_code == "build_failed"

    class BadIntegration(FakeDeployer):
        async def deploy(self, ctx, artifact):
            return DeployResult(
                integration={"type": "iframe", "url": "javascript:alert(1)"}
            )

    ff = FakeFuzeFront()
    rt, _ = make_runtime(ff, BadIntegration())
    rec = await run_to_completion(rt)
    assert rec.status == "failed" and rec.error_code == "manifest_invalid"
    assert ff.registrations() == []


@pytest.mark.integration
@pytest.mark.asyncio
async def test_unexpected_exception_becomes_internal_error_without_leaking_detail():
    class Boom(FakeDeployer):
        async def build(self, ctx):
            raise RuntimeError("secret internal detail")

    rt, _ = make_runtime(FakeFuzeFront(), Boom())
    rec = await run_to_completion(rt)
    assert rec.status == "failed" and rec.error_code == "internal_error"
    assert "secret" not in (rec.error_message or "")


# ═══ callback delivery: retry / backoff / 409 / resume ═══════════════════════
@pytest.mark.integration
@pytest.mark.asyncio
async def test_callback_retries_with_backoff_on_5xx_and_network_errors():
    ff = FakeFuzeFront()
    ff.callback_script = [(503, {}), httpx.ConnectError("down"), (200, {})]
    rt, clock = make_runtime(ff, NotConfiguredDeployer())
    await run_to_completion(rt)

    async def entry():
        return (await rt.store.get(BID)).outbox[0]

    await rt.deliver_due()  # attempt 1 -> 503
    e = await entry()
    assert (
        e["state"] == "pending"
        and e["attempts"] == 1
        and e["nextAttemptAt"] == clock.t + 5
    )
    await rt.deliver_due()  # not due yet: no call
    assert len(ff.callbacks()) == 1
    clock.t += 5
    await rt.deliver_due()  # attempt 2 -> network error
    e = await entry()
    assert (
        e["attempts"] == 2
        and e["nextAttemptAt"] == clock.t + 10
        and "ConnectError" in e["lastError"]
    )
    clock.t += 10
    await rt.deliver_due()  # attempt 3 -> 200, then the next entry (failed) goes out too
    assert (await entry())["state"] == "delivered"
    assert [c["status"] for c in ff.callbacks()][-1] == "failed"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_callback_gives_up_after_bounded_attempts_and_records_dead():
    ff = FakeFuzeFront()
    ff.callback_script = [(500, {})] * 20
    rt, clock = make_runtime(ff, NotConfiguredDeployer(), callback_max_attempts=3)
    await run_to_completion(rt)
    for _ in range(10):
        clock.t += 1000
        await rt.deliver_due()
    rec = await rt.store.get(BID)
    assert rec.outbox[0]["state"] == "dead" and rec.outbox[0]["attempts"] == 3
    assert sum(1 for c in ff.callbacks() if c["status"] == "building") == 3  # bounded


@pytest.mark.integration
@pytest.mark.asyncio
async def test_callback_409_org_mismatch_is_terminal_and_not_retried():
    ff = FakeFuzeFront()
    ff.callback_script = [
        (409, {"code": "ORG_MISMATCH", "message": "different organization"})
    ]
    rt, clock = make_runtime(ff)
    await run_to_completion(rt)
    await rt.deliver_due()
    clock.t += 10_000
    await rt.deliver_due()
    rec = await rt.store.get(BID)
    assert len(ff.callbacks()) == 1  # nothing after the 409, no retry
    assert rec.callbacks_halted == "ORG_MISMATCH"
    assert [e["state"] for e in rec.outbox] == ["rejected", "superseded", "superseded"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_callback_409_stale_transition_is_skipped_and_delivery_continues():
    ff = FakeFuzeFront()
    # FuzeFront already moved launching->building itself, so our `building` is a no-op 409.
    ff.callback_script = [
        (409, {"message": 'Cannot move a build session from "building" to "building"'})
    ]
    rt, _ = make_runtime(ff)
    await run_to_completion(rt)
    await rt.deliver_due()
    rec = await rt.store.get(BID)
    assert [e["state"] for e in rec.outbox] == ["rejected", "delivered", "delivered"]
    assert [c["status"] for c in ff.callbacks()] == [
        "building",
        "deploying",
        "deployed",
    ]
    assert rec.callbacks_halted is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_pending_callbacks_survive_restart_via_store():
    ff = FakeFuzeFront()
    store = InMemoryBuildStore()
    rt1, clock = make_runtime(ff, store=store)
    await run_to_completion(rt1)  # outbox written, nothing delivered (loop not started)
    assert ff.callbacks() == []
    # "pod restart": brand-new runtime over the same durable store
    rt2, _ = make_runtime(ff, store=store, clock=clock)
    await rt2.deliver_due()
    assert [c["status"] for c in ff.callbacks()] == [
        "building",
        "deploying",
        "deployed",
    ]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_restart_resumes_unfinished_session_without_redoing_finished_steps():
    ff = FakeFuzeFront()
    dep = FakeDeployer()
    store = InMemoryBuildStore()
    rt0, clock = make_runtime(ff, dep, store=store)
    rec, _ = await rt0.accept(req())
    await rt0.wait_idle()  # complete one pass to get a realistic record

    # rewind to "crashed after the deployer finished but before registration"
    def rewind(r: BuildRecord):
        r.status, r.registered, r.app_slug, r.slug, r.register_attempted = (
            "deploying",
            False,
            None,
            None,
            False,
        )
        r.outbox, r.slugs_tried = [], []

    await store.update(BID, rewind)
    ff.taken.clear()
    ff.calls.clear()
    builds_before, deploys_before = dep.builds, dep.deploys

    rt1, _ = make_runtime(ff, dep, store=store, clock=clock)
    await rt1.start()
    await rt1.wait_idle()
    await rt1.stop()
    assert (dep.builds, dep.deploys) == (
        builds_before,
        deploys_before,
    )  # steps not repeated
    assert (await store.get(BID)).status == "deployed"
    assert len(ff.registrations()) == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_restart_after_register_post_landed_does_not_duplicate_or_resuffix():
    ff = FakeFuzeFront()
    dep = FakeDeployer()
    store = InMemoryBuildStore()
    rt0, clock = make_runtime(ff, dep, store=store)
    await rt0.accept(req())
    await rt0.wait_idle()

    # crashed after POST /apps succeeded (app exists) but before `registered` was persisted
    def rewind(r: BuildRecord):
        r.status, r.registered, r.app_slug = "deploying", False, None
        r.register_attempted = True
        r.outbox = []

    await store.update(BID, rewind)
    ff.calls.clear()
    rt1, _ = make_runtime(ff, dep, store=store, clock=clock)
    await rt1.start()
    await rt1.wait_idle()
    await rt1.stop()
    rec = await store.get(BID)
    assert (
        rec.status == "deployed" and rec.app_slug == "my-cool-app"
    )  # same slug, no "-xxxxxx" duplicate


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cancel_is_noop_on_terminal_and_supersedes_pending_callbacks():
    ff = FakeFuzeFront()
    rt, _ = make_runtime(ff)
    await run_to_completion(rt)
    rec, changed = await rt.cancel(BID)
    assert changed is False and rec.status == "deployed"

    gate = asyncio.Event()
    ff2 = FakeFuzeFront()
    rt2, _ = make_runtime(ff2, FakeDeployer(gate=gate))
    await rt2.accept(req())
    await asyncio.sleep(0.05)
    rec, changed = await rt2.cancel(BID)
    assert changed is True and rec.status == "cancelled"
    assert all(e["state"] != "pending" for e in rec.outbox)
    await rt2.deliver_due()
    assert ff2.callbacks() == []  # a cancelled session reports nothing further
    assert (await rt2.cancel("front_abs_" + "0" * 26)) is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_background_loop_delivers_callbacks():
    ff = FakeFuzeFront()
    rt, _ = make_runtime(ff, poll_interval_s=0.01)
    await rt.start()
    await rt.accept(req())
    for _ in range(100):
        if len(ff.callbacks()) == 3:
            break
        await asyncio.sleep(0.02)
    await rt.stop()
    assert [c["status"] for c in ff.callbacks()] == [
        "building",
        "deploying",
        "deployed",
    ]


# ═══ logging hygiene ═════════════════════════════════════════════════════════
@pytest.mark.api
@pytest.mark.asyncio
async def test_token_and_brief_never_logged(caplog):
    caplog.set_level("DEBUG")
    ff = FakeFuzeFront()
    rt, _ = make_runtime(ff)
    secret_brief = "SUPER-SECRET-BRIEF-CONTENT"  # nosec B105 -- test-only fixture, not a real credential
    async with http_client(app_for(rt)) as c:
        await c.post("/api/v1/app-builds", json=body(brief=secret_brief), headers=AUTH)
        await c.post(
            "/api/v1/app-builds",
            json=body(),
            headers={"Authorization": "Bearer wrong-token-value"},
        )
    await rt.wait_idle()
    await rt.deliver_due()
    text = "\n".join(r.getMessage() for r in caplog.records)
    assert text  # something was logged
    for forbidden in (TOKEN, REG_TOKEN, secret_brief, "wrong-token-value"):
        assert forbidden not in text


# ═══ Postgres store (opt-in) ═════════════════════════════════════════════════
DB_URL = os.environ.get("APP_BUILDS_TEST_DATABASE_URL")


@pytest.mark.database
@pytest.mark.asyncio
@pytest.mark.skipif(
    not DB_URL,
    reason="set APP_BUILDS_TEST_DATABASE_URL to run the Postgres store tests",
)
async def test_postgres_store_roundtrip_and_atomic_update():
    import importlib.util
    from contextlib import asynccontextmanager

    import asyncpg

    from app_builds.store import PostgresBuildStore

    mig = importlib.util.spec_from_file_location(
        "m",
        os.path.join(
            os.path.dirname(__file__),
            "..",
            "migrations",
            "20261004_120001_add_app_build_sessions.py",
        ),
    )
    module = importlib.util.module_from_spec(mig)
    mig.loader.exec_module(module)

    @asynccontextmanager
    async def connect():
        conn = await asyncpg.connect(DB_URL)
        for t in ("json", "jsonb"):
            await conn.set_type_codec(
                t, encoder=json.dumps, decoder=json.loads, schema="pg_catalog"
            )
        try:
            yield conn
        finally:
            await conn.close()

    async with connect() as conn:
        await module.downgrade(conn)
        await module.upgrade(conn)
        await module.upgrade(conn)  # idempotent

    store = PostgresBuildStore(connect)
    rec = BuildRecord(
        BID, mint_agent_session_ref(), ORG, USR, "organization", "n", "b", "u", "h"
    )
    stored, created = await store.create_if_absent(rec)
    assert created
    again, created2 = await store.create_if_absent(
        BuildRecord(
            BID, mint_agent_session_ref(), ORG, USR, "organization", "n", "b", "u", "h"
        )
    )
    assert created2 is False and again.agent_session_ref == rec.agent_session_ref

    def mut(r: BuildRecord):
        r.advance("building")
        r.enqueue_callback({"status": "building"}, 1.0)

    await store.update(BID, mut)
    got = await store.get(BID)
    assert got.status == "building" and got.outbox[0]["state"] == "pending"
    assert [r.build_session_id for r in await store.list_pending_outbox()] == [BID]
    assert [r.build_session_id for r in await store.list_active()] == [BID]

    # concurrent updates serialise (row lock): 20 increments of a counter in the outbox
    async def bump():
        await store.update(
            BID, lambda r: r.enqueue_callback({"status": "building"}, 1.0)
        )

    await asyncio.gather(*[bump() for _ in range(20)])
    assert len((await store.get(BID)).outbox) == 21
    await store.update(BID, lambda r: r.supersede_pending())
    assert await store.list_pending_outbox() == []
    assert await store.update("front_abs_" + "0" * 26, lambda r: None) is None
