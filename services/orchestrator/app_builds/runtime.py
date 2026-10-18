"""Build runtime: accepts sessions, drives the state machine, delivers status callbacks.

Durability model (survives a pod restart — nothing lives only in an in-memory timer):

* Every state change and the status callback it implies are written in ONE atomic store
  update (the transactional-outbox pattern). A callback is only ever *enqueued* by the same
  update that advanced the state, so ``deployed`` cannot be enqueued before the app is
  registered (``BuildRecord.advance`` refuses it).
* Step results (artifact, chosen slug, registration) are persisted as they complete; on
  restart :meth:`BuildRuntime.start` re-runs every non-terminal session, skipping finished steps.
* A background loop delivers due outbox entries in order with bounded exponential backoff.

Single-replica assumption: the orchestrator Deployment runs ``replicas: 1``. Two replicas would
both resume a session; registration is protected by the persisted slug and FuzeFront's
forward-only/409 handling, but the deployer would be invoked twice.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Awaitable, Callable, Dict, Optional, Tuple, TypeVar

from . import slug as slugmod
from .config import Settings
from .deployer import (
    AppDeployer,
    DeployContext,
    DeployError,
    NotConfiguredDeployer,
)
from .fuzefront import (
    FuzeFrontClient,
    RegistryAuthFailed,
    RegistryRejected,
    RegistryTransient,
    SlugConflict,
    resolve_callback_url,
)
from .ids import mint_agent_session_ref
from .models import (
    BUILDING,
    CANCELLED,
    DEPLOYED,
    DEPLOYING,
    FAILED,
    BuildRecord,
    LaunchRequest,
    request_fingerprint,
)
from .store import BuildStore

logger = logging.getLogger(__name__)
T = TypeVar("T")


class _Stop(Exception):
    """The session reached a terminal state elsewhere (cancel); stop quietly."""


class _Fail(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class IdempotencyConflict(Exception):
    pass


def classify_callback(status: int, body: Dict[str, Any]) -> str:
    """-> delivered | retry | halt | moot | dead (see module docs)."""
    if 200 <= status < 300:
        return "delivered"
    if status == 409:
        msg = str(body.get("message") or "")
        if body.get("code") == "ORG_MISMATCH" or msg.startswith(
            "Build session is already"
        ):
            return "halt"  # terminal on FuzeFront's side: stop reporting this session
        return "moot"  # e.g. "cannot move building -> building": this entry is stale, go on
    if status == 429 or status >= 500:
        return "retry"
    return "dead"


class BuildRuntime:
    def __init__(
        self,
        store: BuildStore,
        deployer: Optional[AppDeployer] = None,
        fuzefront: Optional[FuzeFrontClient] = None,
        settings: Optional[Settings] = None,
        *,
        clock: Callable[[], float] = time.time,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self.settings = settings or Settings.from_env()
        self.store = store
        self.deployer: AppDeployer = deployer or NotConfiguredDeployer()
        self.fuzefront = fuzefront or FuzeFrontClient(self.settings)
        self._clock = clock
        self._sleep = sleep
        self._tasks: Dict[str, asyncio.Task] = {}
        self._loop_task: Optional[asyncio.Task] = None
        self._wake = asyncio.Event()

    # ── lifecycle ────────────────────────────────────────────────────────────
    async def start(self) -> None:
        """Resume unfinished sessions and start the callback-delivery loop."""
        try:
            for rec in await self.store.list_active():
                logger.info(
                    "app_build resume build_session_id=%s status=%s",
                    rec.build_session_id,
                    rec.status,
                )
                self.enqueue(rec.build_session_id)
        except Exception as exc:
            logger.error("app_build resume failed err=%s", type(exc).__name__)
        self._loop_task = asyncio.create_task(self._delivery_loop())

    async def stop(self) -> None:
        for t in [self._loop_task, *self._tasks.values()]:
            if t is not None:
                t.cancel()
        await asyncio.gather(
            *[t for t in [self._loop_task, *self._tasks.values()] if t],
            return_exceptions=True,
        )
        self._tasks.clear()
        await self.fuzefront.aclose()

    # ── accept / cancel ──────────────────────────────────────────────────────
    async def accept(self, req: LaunchRequest) -> Tuple[BuildRecord, bool]:
        """Create (or idempotently return) the session and enqueue the work. Fast: no build here."""
        callback_url = resolve_callback_url(
            req.callbackUrl, req.buildSessionId, self.settings
        )
        now = self._clock()
        rec = BuildRecord(
            build_session_id=req.buildSessionId,
            agent_session_ref=mint_agent_session_ref(),
            organization_id=req.organizationId,
            requested_by_user_id=req.requestedByUserId,
            context=req.context,
            name=req.name,
            brief=req.brief,
            callback_url=callback_url,
            request_hash=request_fingerprint(req),
            created_at=now,
            updated_at=now,
        )
        stored, created = await self.store.create_if_absent(rec)
        if not created and stored.request_hash != rec.request_hash:
            raise IdempotencyConflict(req.buildSessionId)
        if created:
            self.enqueue(stored.build_session_id)
        return stored, created

    async def cancel(self, build_session_id: str) -> Optional[Tuple[BuildRecord, bool]]:
        """Stop a non-terminal session. Returns (record, changed); None if unknown."""

        def mut(r: BuildRecord) -> bool:
            if r.terminal:
                return False
            r.advance(CANCELLED)
            r.supersede_pending()
            r.updated_at = self._clock()
            return True

        changed = await self.store.update(build_session_id, mut)
        if changed is None:
            return None
        rec = await self.store.get(build_session_id)
        assert rec is not None
        if changed:
            task = self._tasks.get(build_session_id)
            if task and task is not asyncio.current_task():
                task.cancel()
            try:
                await self.deployer.cancel(self._ctx(rec))
            except Exception as exc:  # best effort
                logger.warning(
                    "app_build deployer.cancel failed build_session_id=%s err=%s",
                    build_session_id,
                    type(exc).__name__,
                )
            logger.info("app_build cancelled build_session_id=%s", build_session_id)
        return rec, changed

    def enqueue(self, build_session_id: str) -> None:
        existing = self._tasks.get(build_session_id)
        if existing and not existing.done():
            return
        task = asyncio.create_task(self.run(build_session_id))
        self._tasks[build_session_id] = task
        task.add_done_callback(
            lambda t, b=build_session_id: (
                self._tasks.pop(b, None) if self._tasks.get(b) is t else None
            )
        )

    async def wait_idle(self) -> None:
        """Test helper: wait for in-flight runner tasks."""
        while self._tasks:
            await asyncio.gather(*list(self._tasks.values()), return_exceptions=True)

    # ── state machine driver ─────────────────────────────────────────────────
    def _ctx(self, r: BuildRecord) -> DeployContext:
        return DeployContext(
            build_session_id=r.build_session_id,
            agent_session_ref=r.agent_session_ref,
            organization_id=r.organization_id,
            requested_by_user_id=r.requested_by_user_id,
            context=r.context,
            name=r.name,
            brief=r.brief,
        )

    async def _persist(
        self, bid: str, fn: Callable[[BuildRecord], None]
    ) -> BuildRecord:
        """Apply ``fn`` unless the session is already terminal (then raise _Stop)."""

        def mut(r: BuildRecord) -> bool:
            if r.terminal:
                return False
            fn(r)
            r.updated_at = self._clock()
            return True

        ok = await self.store.update(bid, mut)
        if not ok:
            raise _Stop()
        rec = await self.store.get(bid)
        assert rec is not None
        return rec

    def _advance_with_callback(
        self, r: BuildRecord, target: str, payload: Dict[str, Any]
    ) -> None:
        r.advance(target)
        r.enqueue_callback(payload, self._clock())

    async def _fail(self, bid: str, code: str, message: str) -> None:
        def mut(r: BuildRecord) -> bool:
            if r.terminal:
                return False
            r.error_code = code
            r.error_message = message[:500]
            self._advance_with_callback(
                r,
                FAILED,
                {"status": FAILED, "errorCode": code, "errorMessage": message[:500]},
            )
            r.updated_at = self._clock()
            return True

        if await self.store.update(bid, mut):
            logger.warning(
                "app_build failed build_session_id=%s error_code=%s", bid, code
            )
            self._wake.set()

    async def run(self, bid: str) -> None:
        start = time.monotonic()
        logger.info("app_build run start build_session_id=%s", bid)
        try:
            await self._steps(bid)
        except _Stop:
            logger.info("app_build run stopped (terminal) build_session_id=%s", bid)
        except _Fail as f:
            await self._fail(bid, f.code, f.message)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception(
                "app_build run crashed build_session_id=%s err=%s",
                bid,
                type(exc).__name__,
            )
            await self._fail(
                bid, "internal_error", "Internal error while building the application"
            )
        finally:
            self._wake.set()
            logger.info(
                "app_build run end build_session_id=%s elapsed_ms=%d",
                bid,
                int((time.monotonic() - start) * 1000),
            )

    async def _steps(self, bid: str) -> None:
        rec = await self.store.get(bid)
        if rec is None or rec.terminal:
            return

        if rec.status == "accepted":
            rec = await self._persist(
                bid,
                lambda r: self._advance_with_callback(
                    r, BUILDING, {"status": BUILDING}
                ),
            )
            self._wake.set()

        ctx = self._ctx(rec)

        if rec.artifact is None:
            artifact = await self._deployer_call(bid, "build", self.deployer.build(ctx))
            rec = await self._persist(bid, lambda r: setattr(r, "artifact", artifact))

        if rec.status == BUILDING:
            rec = await self._persist(
                bid,
                lambda r: self._advance_with_callback(
                    r, DEPLOYING, {"status": DEPLOYING}
                ),
            )
            self._wake.set()

        if rec.deploy_result is None:
            res = await self._deployer_call(
                bid, "deploy", self.deployer.deploy(ctx, rec.artifact or {})
            )
            problems = slugmod.validate_integration(res.integration)
            if problems:
                raise _Fail(
                    "manifest_invalid",
                    "Deployer returned an invalid integration: "
                    + "; ".join(problems)[:300],
                )
            data = {"integration": res.integration, "description": res.description}
            rec = await self._persist(bid, lambda r: setattr(r, "deploy_result", data))

        app_slug = await self._register(bid)

        def finish(r: BuildRecord) -> None:
            self._advance_with_callback(
                r, DEPLOYED, {"status": DEPLOYED, "appSlug": app_slug}
            )

        await self._persist(bid, finish)
        logger.info("app_build deployed build_session_id=%s", bid)

    async def _deployer_call(self, bid: str, op: str, coro: Awaitable[T]) -> T:
        start = time.monotonic()
        logger.debug("app_build deployer.%s start build_session_id=%s", op, bid)
        try:
            return await coro
        except DeployError as e:
            raise _Fail(
                e.code if e.code.replace("_", "").isalnum() else "deploy_failed",
                e.message,
            ) from e
        finally:
            logger.info(
                "app_build deployer.%s end build_session_id=%s elapsed_ms=%d",
                op,
                bid,
                int((time.monotonic() - start) * 1000),
            )

    # ── registration ─────────────────────────────────────────────────────────
    async def _registry(self, fn: Callable[[], Awaitable[T]]) -> T:
        n = self.settings.registry_attempts
        for i in range(n):
            try:
                return await fn()
            except RegistryTransient:
                if i == n - 1:
                    raise _Fail(
                        "registry_unavailable", "FuzeFront app registry is unavailable"
                    ) from None
                await self._sleep(min(2**i, 10))
            except RegistryAuthFailed:
                raise _Fail(
                    "registry_auth_failed",
                    "FuzeAgent's registry credential was rejected",
                ) from None
            except RegistryRejected as e:
                raise _Fail("manifest_rejected", str(e)[:300]) from None
        raise AssertionError("unreachable")

    async def _register(self, bid: str) -> str:
        """Register the app under the SESSION's organizationId; returns the registered slug."""
        while True:
            rec = await self.store.get(bid)
            assert rec is not None
            if rec.terminal:
                raise _Stop()
            if rec.registered and rec.app_slug:
                return rec.app_slug

            slug = rec.slug
            if slug is None:
                slug = await self._pick_free_slug(rec)
                rec = await self._persist(
                    bid,
                    lambda r, s=slug: (
                        setattr(r, "slug", s),
                        setattr(r, "register_attempted", False),
                    ),
                )
            resumed = rec.register_attempted

            dr = rec.deploy_result or {}
            manifest = slugmod.build_manifest(
                slug=slug,
                name=rec.name,
                brief=rec.brief,
                context=rec.context,
                integration=dr.get("integration") or {},
                description=dr.get("description"),
            )
            await self._persist(bid, lambda r: setattr(r, "register_attempted", True))
            try:
                # organizationId is ALWAYS the session's (never any other org).
                await self._registry(
                    lambda: self.fuzefront.register(manifest, rec.organization_id, bid)
                )
            except SlugConflict:
                if resumed:
                    pass  # our own earlier POST landed before the restart
                else:
                    logger.info(
                        "app_build slug conflict build_session_id=%s; picking another",
                        bid,
                    )
                    await self._persist(
                        bid,
                        lambda r, s=slug: (
                            r.slugs_tried.append(s),
                            setattr(r, "slug", None),
                        ),
                    )
                    continue
            await self._persist(
                bid,
                lambda r, s=slug: (
                    setattr(r, "registered", True),
                    setattr(r, "app_slug", s),
                ),
            )
            logger.info("app_build registered build_session_id=%s", bid)
            return slug

    async def _pick_free_slug(self, rec: BuildRecord) -> str:
        for cand in slugmod.candidate_slugs(rec.name, rec.build_session_id):
            if cand in rec.slugs_tried or not slugmod.SLUG_RE.match(cand):
                continue
            if await self._registry(
                lambda c=cand: self.fuzefront.slug_exists(c, rec.build_session_id)
            ):
                await self._persist(
                    rec.build_session_id, lambda r, c=cand: r.slugs_tried.append(c)
                )
                continue
            return cand
        raise _Fail("slug_unavailable", "Could not find a free application slug")

    # ── callback delivery ────────────────────────────────────────────────────
    async def _delivery_loop(self) -> None:
        while True:
            try:
                await self.deliver_due()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error(
                    "app_build delivery pass failed err=%s", type(exc).__name__
                )
            # asyncio.wait (not wait_for): never swallows a cancellation racing the timeout.
            waiter = asyncio.ensure_future(self._wake.wait())
            try:
                await asyncio.wait({waiter}, timeout=self.settings.poll_interval_s)
            finally:
                waiter.cancel()
            self._wake.clear()

    async def deliver_due(self) -> int:
        """One pass: deliver every due pending callback (in order, per session)."""
        n = 0
        for rec in await self.store.list_pending_outbox():
            n += await self._deliver_session(rec.build_session_id)
        return n

    async def _deliver_session(self, bid: str) -> int:
        done = 0
        while True:
            rec = await self.store.get(bid)
            if rec is None:
                return done
            entry = next((e for e in rec.outbox if e["state"] == "pending"), None)
            if entry is None or entry["nextAttemptAt"] > self._clock():
                return done
            seq, payload = entry["seq"], entry["payload"]
            status, body, err = 0, {}, None
            exhausted = False
            try:
                status, body = await self.fuzefront.post_callback(
                    rec.callback_url, payload, bid
                )
                outcome = classify_callback(status, body)
            except RegistryTransient as exc:
                outcome, err = "retry", str(exc)[:200]
            err = err or (f"HTTP {status}" if outcome != "delivered" else None)

            def apply(r: BuildRecord) -> None:
                nonlocal exhausted
                e = next((x for x in r.outbox if x["seq"] == seq), None)
                if e is None or e["state"] != "pending":
                    return
                e["attempts"] += 1
                e["lastStatus"] = status or None
                e["lastError"] = err
                if outcome == "delivered":
                    e["state"] = "delivered"
                elif outcome == "moot":
                    e["state"] = "rejected"
                elif outcome == "halt":
                    e["state"] = "rejected"
                    r.callbacks_halted = str(body.get("code") or "terminal_conflict")
                    r.supersede_pending()
                elif (
                    outcome == "dead"
                    or e["attempts"] >= self.settings.callback_max_attempts
                ):
                    e["state"] = "dead"
                    exhausted = True
                else:  # retry with bounded exponential backoff
                    delay = min(
                        self.settings.callback_max_delay_s,
                        self.settings.callback_base_delay_s
                        * (2 ** (e["attempts"] - 1)),
                    )
                    e["nextAttemptAt"] = self._clock() + delay

            await self.store.update(bid, apply)
            lvl = logging.INFO if outcome in ("delivered", "moot") else logging.WARNING
            logger.log(
                lvl,
                "app_build callback build_session_id=%s seq=%d status_reported=%s outcome=%s http=%s",
                bid,
                seq,
                payload.get("status"),
                outcome,
                status or None,
            )
            if exhausted:
                logger.error(
                    "app_build callback undeliverable build_session_id=%s seq=%d",
                    bid,
                    seq,
                )
            done += 1
            if outcome in ("retry", "halt"):
                return done  # retry: wait for nextAttemptAt; halt: nothing further is pending
