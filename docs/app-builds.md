# App builds — "Build your application" (FuzeAgent side)

Counterpart of FuzeFront's `docs/planning/app-builder-and-ownership.md`. A user on FuzeFront's
Applications page asks FuzeAgent to develop an app and deploy it into their personal workspace or
an organization. FuzeFront's applications-service launches a session here and FuzeAgent reports
progress back through a status callback. Machine-readable contract:
[`contracts/app-builds.openapi.yaml`](../contracts/app-builds.openapi.yaml). Code:
`services/orchestrator/app_builds/`.

## Endpoints (orchestrator, port 8000)

| Method + path | Purpose |
|---|---|
| `POST /api/v1/app-builds` | Launch. **This is the value for FuzeFront's `FUZEAGENT_BUILD_API_URL`** (e.g. `http://orchestrator.<fuzeagent-ns>.svc.cluster.local:8000/api/v1/app-builds`). |
| `GET /api/v1/app-builds/{buildSessionId}` | Read session state (ops/debug). |
| `POST /api/v1/app-builds/{buildSessionId}/cancel` | Stop a non-terminal session; no-op (200, `cancelled:false`) on terminal ones. |

**Auth:** `Authorization: Bearer <APP_BUILD_API_TOKEN>`; FuzeFront's `FUZEAGENT_BUILD_API_TOKEN` must
hold the same value. Constant-time compare; `401` on missing/bad; if `APP_BUILD_API_TOKEN` is unset
the API answers `503 builder_unavailable` to everyone (fails closed, never unauthenticated). It
also answers 503 if the FuzeFront registry URL / registration token is unset.

**Flag:** release flag `fuzeagent.app-builds.enabled`, default **OFF** -> `503 feature_disabled`
(after auth, so a bad token is still 401). Evaluated by a static env provider
(`FEATURE_FLAG_FUZEAGENT_APP_BUILDS_ENABLED`, Helm `orchestrator.appBuilds.enabled`); the Python
orchestrator has no Unleash/OpenFeature client yet, so `app_builds/flags.py::set_provider` is the
seam. Owner: backend-engineer (flag admin: feature-flags-engineer). Removal: delete once enabled
at 100% in prod for two weeks without incident.

### Launch request (`201` first time, `200` on an idempotent replay)

```json
{ "buildSessionId": "front_abs_…", "organizationId": "org_…", "requestedByUserId": "usr_…",
  "context": "personal|organization", "name": "≤120 chars", "brief": "≤4000 chars",
  "callbackUrl": "https://app.fuzefront.com/api/v1/app-registry/build-sessions/<id>/status  (or the relative path)" }
```
Strict: unknown keys (including any `id`), over-length `brief`, bad `context`/id shapes -> `400
validation_error`. Response: `{ "agentSessionRef": "agent_abs_…", "buildSessionId", "status",
"agentSessionUrl"? }`. It returns as soon as the session is persisted and queued — the build runs
in the background. Idempotent on `buildSessionId` (same ref, one session); the same id with a
different body is `409 idempotency_conflict`. `agentSessionRef` is minted by FuzeAgent (TypeID,
namespace `agent`). `agentSessionUrl` is only returned when `APP_BUILD_SESSION_URL_TEMPLATE` is set:
FuzeAgent's UI has **no build-session view yet**, so there is no real route to link to.

`callbackUrl` is validated because the platform credential is sent there: its origin must be
`FUZEFRONT_PUBLIC_BASE_URL` / `FUZEFRONT_API_URL` (or `APP_BUILD_CALLBACK_ALLOWED_ORIGINS`) and
its path exactly `/api/v1/app-registry/build-sessions/{buildSessionId}/status`. A relative path is
resolved against `FUZEFRONT_PUBLIC_BASE_URL`, falling back to `FUZEFRONT_API_URL`.

## State machine and callbacks

`accepted` (internal) → `building` → `deploying` → `deployed` | `failed`; `cancelled` via the
cancel endpoint. Forward-only; terminal states are immutable. Each transition writes its callback
to a **transactional outbox** in the same store update; `deployed` cannot be created before the app
is registered (`BuildRecord.advance` refuses it).

Callback = `POST <callbackUrl>` `{status, appSlug?, errorCode?, errorMessage?}` with
`Authorization: Bearer <FUZEFRONT_REGISTRATION_TOKEN>` (the platform service account FuzeAgent
already uses to self-register). Delivery, in order per session:

| FuzeFront answer | FuzeAgent does |
|---|---|
| 2xx | delivered |
| 5xx / 429 / network | retry with exponential backoff (5s base, 300s cap), max 5 attempts, then `dead` (logged at ERROR) |
| 409 `ORG_MISMATCH` or "already <terminal>" | terminal: recorded, never retried, remaining callbacks superseded |
| 409 "cannot move X -> X" | stale entry (FuzeFront already advanced): recorded, delivery continues |
| other 4xx | `dead`, not retried |

The outbox and step results (artifact, chosen slug, registration) live in Postgres
(`app_build_sessions`, migration `20261004_120001`), so a pod restart resumes unfinished sessions
and undelivered callbacks. Single-replica assumption (orchestrator `replicas: 1`).

## Build + deploy

`AppDeployer` (`app_builds/deployer.py`) is the adapter that develops the app from the brief and
deploys it (`build` → artifact, `deploy` → manifest `integration`; both idempotent on
`buildSessionId`). **FuzeAgent has no such primitive today**, so the default is
`NotConfiguredDeployer`: the session reports `failed` with `errorCode=deployer_unavailable`
(no deploy is ever faked). Wire a real one via `start_app_builds(get_db_connection, deployer=…)`.

Registration (after a successful deploy) goes through FuzeFront's public API:
`GET /api/v1/app-registry/apps/{slug}` then `POST /api/v1/app-registry/apps` with
`{ manifest, organizationId }`, where `organizationId` is **the session's** org — never another.
Slugs are derived deterministically from the name (kebab, FuzeFront's `^[a-z0-9][a-z0-9-]{1,62}[a-z0-9]$`);
a slug that already exists, or a `409` on POST, moves to `base-<6hex of the session>`,
`…-2`, … **before** anything is registered. An existing app is never updated (no PUT). The chosen
slug is persisted before the POST, so a restart can't register a second copy.

## Configuration (all optional; defaults fail closed)

| Env | Helm | Meaning |
|---|---|---|
| `APP_BUILD_API_TOKEN` | SealedSecret key in `fuzeagent-secrets` (`optional: true`) | inbound bearer |
| `FEATURE_FLAG_FUZEAGENT_APP_BUILDS_ENABLED` | `orchestrator.appBuilds.enabled` (false) | release flag |
| `FUZEFRONT_API_URL` | `fuzefront.apiUrl` (existing) | registry + callback base (internal) |
| `FUZEFRONT_PUBLIC_BASE_URL` | `orchestrator.appBuilds.fuzefrontPublicBaseUrl` | relative-callback base / allowed origin |
| `FUZEFRONT_REGISTRATION_TOKEN` | secret `fuzefront-registration` key `token` (reused, `optional: true`) | outbound credential |
| `APP_BUILD_SESSION_URL_TEMPLATE` | `orchestrator.appBuilds.sessionUrlTemplate` | UI deep link |
| `APP_BUILD_CALLBACK_ALLOWED_ORIGINS`, `APP_BUILD_CALLBACK_MAX_ATTEMPTS`, `APP_BUILD_CALLBACK_BASE_DELAY_SECONDS`, `APP_BUILD_CALLBACK_MAX_DELAY_SECONDS`, `APP_BUILD_HTTP_TIMEOUT_SECONDS`, `APP_BUILD_REGISTRY_ATTEMPTS`, `APP_BUILD_POLL_INTERVAL_SECONDS` | — | tuning |

No secret values live in the repo. **Sealing step (operator):** generate a random token, then
`kubeseal` it into the existing `fuzeagent-secrets` SealedSecret under key `APP_BUILD_API_TOKEN`
(see `deploy/contabo/sealed/` and `seal-secrets.yml`), and give FuzeFront the same value as
`FUZEAGENT_BUILD_API_TOKEN`. In-cluster reachability needs a NetworkPolicy admitting
`fuzefront-applications` → `fuzeagent/orchestrator:8000` and `fuzeagent` → `fuzefront-applications:3003`
(FuzeInfra, delegate via `@fuzeinfra`).

Logging: boundary logs with elapsed ms on every FuzeFront call; ids and lengths only — the token,
the registration credential and the brief are never logged.
