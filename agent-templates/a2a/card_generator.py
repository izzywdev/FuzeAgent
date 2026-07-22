"""Agent Card generator (projection).

Implements ``contracts/a2a/v1/card-projection.md`` NORMATIVELY. The card is a *pure
function* of two inputs already present in every repo::

    .fuze/manifest.json                 -> identity, provider, interface, docs
    agent-templates/roles/*/role.json   -> skills

Purity is the whole point: the card is the published capability boundary, so it MUST
NOT be hand-authored and MUST be byte-identical for identical inputs (modulo
``signatures``). Iteration order is explicit (lexicographic by role key unless
``servingRoles`` fixes an order) — never filesystem order.

What is DELIBERATELY not projected (card-projection.md §3/§7): ``tools``,
``mcp_servers``, ``system``/``system_append``, ``persona``, ``model``,
``environment`` and ``vault`` bindings. Leaking any of them would tell a caller which
credentials the callee holds — exactly the coupling A2A removes.
"""

from __future__ import annotations

import json
from typing import Any, Callable, Iterable

from ._contract import CONTRACT_ROOT

PROVIDER_ORG = "FuzeOne"
PROVIDER_URL = "https://github.com/izzywdev"
IN_CLUSTER_URL = "http://a2a-shared.fuzeagent.svc.cluster.local:8080/rpc"
DEFAULT_INPUT_MODES = ["text/plain", "application/json"]
DEFAULT_OUTPUT_MODES = ["text/plain", "application/json"]
DEFAULT_ISSUER = "https://auth.prod.fuzefront.com"

#: Signer signature: (signing_input_bytes) -> {"protected", "signature", "header"?}.
Signer = Callable[[bytes], dict]

# The placeholder emitted when no real signer is injected. Key material and rotation
# are a devops concern (card-projection.md §6); the generator owns only the mechanism
# and the invariant that signatures[] is present and non-empty (Fuze profile).
_PLACEHOLDER_SIGNATURE = {
    "protected": "eyJhbGciOiJFUzI1NiIsImtpZCI6ImZ1emUtYTJhLTIwMjYtMDcifQ",
    "signature": "PLACEHOLDER-jws-signature-emitted-by-the-card-generator",
    "header": {"kid": "fuze-a2a-2026-07"},
}


class CardProjectionError(ValueError):
    """A role cannot be projected (e.g. a skill with no description)."""


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def repo_name(repo: str) -> str:
    """The canonical agent identity: the segment after '/' in ``owner/name``."""
    return repo.rsplit("/", 1)[-1]


def contract_version() -> str:
    return (CONTRACT_ROOT / "VERSION").read_text(encoding="utf-8").strip()


def _a2a(block: dict | None) -> dict:
    return dict(block or {})


def is_exec_role(role: dict) -> bool:
    return (role.get("metadata") or {}).get("tier") == "executive"


def _service_tags(role: dict) -> list[str]:
    services = role.get("services") or {}
    return [key for key, grant in services.items() if grant and grant != "none"]


def project_tags(role_key: str, role: dict, manifest: dict) -> list[str]:
    """Derived tags UNION ``a2a.tags``, de-duplicated and sorted (card-projection.md §3).

    Derived (always included): the role key; ``manifest.tier``; ``"executive"`` when
    ``metadata.tier == "executive"``; each ``services`` key whose grant is not
    ``"none"``. Sorting is the deterministic order — the examples in the contract are
    hand-authored illustrations and are intentionally not relied on for tag ORDER,
    only for the tag SET.
    """
    a2a = _a2a(role.get("a2a"))
    tags: set[str] = {role_key}
    if manifest.get("tier"):
        tags.add(manifest["tier"])
    if is_exec_role(role):
        tags.add("executive")
    tags.update(_service_tags(role))
    tags.update(a2a.get("tags") or [])
    return sorted(tags)


def project_skill(role_key: str, role: dict, manifest: dict) -> dict:
    """One role.json -> one AgentSkill (card-projection.md §3)."""
    name = role.get("name")
    if not name:
        raise CardProjectionError(f"role {role_key!r} has no name; cannot project a skill")
    description = role.get("description")
    if not description:
        # An undescribed skill is unroutable; failing is better than a placeholder.
        raise CardProjectionError(
            f"role {role_key!r} has no description; refusing to emit a placeholder skill"
        )

    a2a = _a2a(role.get("a2a"))
    skill: dict[str, Any] = {
        "id": role_key,
        "name": name,
        "description": description,
        "tags": project_tags(role_key, role, manifest),
    }
    if a2a.get("examples"):
        skill["examples"] = list(a2a["examples"])
    if a2a.get("inputModes"):
        skill["inputModes"] = list(a2a["inputModes"])
    if a2a.get("outputModes"):
        skill["outputModes"] = list(a2a["outputModes"])
    if a2a.get("scopes"):
        skill["securityRequirements"] = [{"fuze-oidc": list(a2a["scopes"])}]
    return skill


def _security_schemes(external: bool, issuer_url: str) -> dict:
    schemes: dict[str, Any] = {
        "fuze-oidc": {
            "openIdConnectSecurityScheme": {
                "description": "FuzeKeys OIDC. The validated subject is the calling repo identity.",
                "openIdConnectUrl": issuer_url.rstrip("/") + "/.well-known/openid-configuration",
            }
        }
    }
    # mTLS is declared only for in-cluster (non-external) surfaces (card-projection.md §4).
    if not external:
        schemes["fuze-mtls"] = {
            "mtlsSecurityScheme": {
                "description": "In-cluster mutual TLS, defence in depth alongside the bearer token."
            }
        }
    return schemes


def _interface(tenant: str, *, external: bool, repo_slug: str) -> dict:
    if external:
        url = f"https://a2a.{repo_slug.lower()}.prod.fuzefront.com/rpc"
    else:
        url = IN_CLUSTER_URL
    return {
        "url": url,
        "protocolBinding": "JSONRPC",
        "protocolVersion": "1.0",
        "tenant": tenant,
    }


def _capabilities() -> dict:
    return {"streaming": True, "pushNotifications": False, "extendedAgentCard": True}


def _doc_url(manifest: dict) -> str:
    a2a = _a2a(manifest.get("a2a"))
    return a2a.get("documentationUrl") or f"https://github.com/{manifest['repo']}"


# --------------------------------------------------------------------------- #
# role selection
# --------------------------------------------------------------------------- #
def select_serving_roles(
    manifest: dict, roles: dict[str, dict], *, visibility: str = "public"
) -> list[str]:
    """Ordered role keys projected into ``skills`` (card-projection.md §3).

    Base source set excludes ``_base``, coordinators, and (in v1) exec roles which get
    their own per-role cards. Within that set:

    * ``public``   -> drop ``a2a.publish == false`` and ``a2a.extendedOnly == true``.
    * ``extended`` -> keep them (the authenticated caller may see more; authz.md §5).

    Order: ``manifest.a2a.servingRoles`` verbatim if given, else lexicographic by key.
    """
    a2a = _a2a(manifest.get("a2a"))
    serving = a2a.get("servingRoles")
    ordered = list(serving) if serving else sorted(roles)

    out: list[str] = []
    for key in ordered:
        role = roles.get(key)
        if role is None:
            if serving:
                raise CardProjectionError(f"servingRoles names {key!r} but no such role.json")
            continue
        if key == "_base":
            continue
        if role.get("coordinator"):
            continue
        if is_exec_role(role):
            continue  # exec roles project through project_exec_cards, not the product card
        r_a2a = _a2a(role.get("a2a"))
        if visibility == "public":
            if r_a2a.get("publish") is False:
                continue
            if r_a2a.get("extendedOnly") is True:
                continue
        out.append(key)
    return out


# --------------------------------------------------------------------------- #
# card assembly
# --------------------------------------------------------------------------- #
def _base_card(
    *,
    name: str,
    description: str,
    version: str,
    doc_url: str,
    interface: dict,
    external: bool,
    issuer_url: str,
    skills: list[dict],
    icon_url: str | None,
) -> dict:
    card: dict[str, Any] = {
        "name": name,
        "description": description,
        "provider": {"organization": PROVIDER_ORG, "url": PROVIDER_URL},
        "version": version,
        "documentationUrl": doc_url,
        "supportedInterfaces": [interface],
        "capabilities": _capabilities(),
        "securitySchemes": _security_schemes(external, issuer_url),
        "securityRequirements": [{"fuze-oidc": []}],
        "defaultInputModes": list(DEFAULT_INPUT_MODES),
        "defaultOutputModes": list(DEFAULT_OUTPUT_MODES),
        "skills": skills,
    }
    if icon_url:
        card["iconUrl"] = icon_url
    return card


def _product_description(manifest: dict, roles: dict[str, dict], serving: Iterable[str]) -> str:
    repo = repo_name(manifest["repo"])
    sentence = (
        f"{repo} agent. Give it a goal in its domain and it will accomplish it using its "
        f"own tooling and credentials; callers need no tools of their own."
    )
    expert = manifest.get("expert")
    if expert:
        sentence += f" Consults the {expert} for repo context."
    return sentence


def project_product_card(
    manifest: dict,
    roles: dict[str, dict],
    *,
    issuer_url: str = DEFAULT_ISSUER,
    version: str | None = None,
    visibility: str = "public",
    external: bool | None = None,
    sign: bool = True,
    signer: Signer | None = None,
) -> dict:
    """Project a product/infra repo into ONE Agent Card (card-projection.md §1–4)."""
    repo = repo_name(manifest["repo"])
    a2a = _a2a(manifest.get("a2a"))
    external = a2a.get("external", False) if external is None else external

    serving = select_serving_roles(manifest, roles, visibility=visibility)
    if not serving:
        raise CardProjectionError(
            f"{repo}: no serving roles project to skills; a card needs at least one skill"
        )
    skills = [project_skill(k, roles[k], manifest) for k in serving]

    card = _base_card(
        name=f"{repo} agent",
        description=_product_description(manifest, roles, serving),
        version=version or contract_version(),
        doc_url=_doc_url(manifest),
        interface=_interface(repo, external=external, repo_slug=repo),
        external=external,
        issuer_url=issuer_url,
        skills=skills,
        icon_url=a2a.get("iconUrl"),
    )
    return sign_card(card, signer) if sign else card


def _exec_description(role_key: str, role: dict) -> str:
    base = role.get("description") or (f"Executive {role_key.upper()} authority agent for FuzeOne.")
    return (
        f"{base} Binding decisions pause the task in TASK_STATE_INPUT_REQUIRED while a "
        f"human is reached via their digital persona — callers must not impose short timeouts."
    )


def project_exec_card(
    role_key: str,
    role: dict,
    manifest: dict,
    *,
    issuer_url: str = DEFAULT_ISSUER,
    version: str | None = None,
    sign: bool = True,
    signer: Signer | None = None,
) -> dict:
    """Project ONE exec role into its OWN card with tenant ``Exec-<role>``.

    Exec deltas (card-projection.md §5): one card per exec role; name
    ``"FuzeOne <ROLE> agent"``; ``external`` forced false; tags always include
    ``executive`` and the role key.
    """
    tenant = f"Exec-{role_key}"
    # Exec skills carry the "exec" tier tag regardless of the source repo's tier
    # (card-projection.md §5.3: tags always include the exec tier + "executive").
    exec_manifest = {**manifest, "tier": "exec"}
    skill = project_skill(role_key, role, exec_manifest)
    card = _base_card(
        name=f"{PROVIDER_ORG} {role_key.upper()} agent",
        description=_exec_description(role_key, role),
        version=version or contract_version(),
        doc_url=_doc_url(manifest),
        interface=_interface(tenant, external=False, repo_slug=repo_name(manifest["repo"])),
        external=False,  # exec agents are never published externally
        issuer_url=issuer_url,
        skills=[skill],
        icon_url=None,
    )
    return sign_card(card, signer) if sign else card


def generate_cards(
    manifest: dict,
    roles: dict[str, dict],
    *,
    issuer_url: str = DEFAULT_ISSUER,
    version: str | None = None,
    sign: bool = True,
    signer: Signer | None = None,
) -> list[tuple[str, dict]]:
    """Every card a repo publishes, as ``(tenant, card)`` pairs.

    A ``tier == "exec"`` repo, or any repo that carries exec roles
    (``metadata.tier == "executive"``), yields one card per exec role. A
    product/infra repo yields a single card keyed by its repo name. A repo may yield
    both (product skills + exec roles) — each exec role is always its own card.
    """
    out: list[tuple[str, dict]] = []
    exec_keys = sorted(k for k, r in roles.items() if is_exec_role(r))

    product_roles = select_serving_roles(manifest, roles, visibility="public")
    if product_roles:
        card = project_product_card(
            manifest, roles, issuer_url=issuer_url, version=version, sign=sign, signer=signer
        )
        out.append((repo_name(manifest["repo"]), card))

    for key in exec_keys:
        card = project_exec_card(
            key,
            roles[key],
            manifest,
            issuer_url=issuer_url,
            version=version,
            sign=sign,
            signer=signer,
        )
        out.append((f"Exec-{key}", card))
    return out


# --------------------------------------------------------------------------- #
# signing (mechanism only; key material is injected by devops)
# --------------------------------------------------------------------------- #
def canonicalize(card: dict) -> bytes:
    """RFC 8785 (JCS)-compatible canonical bytes of the card EXCLUDING ``signatures``.

    A card's value types are strings, booleans, arrays and objects (no floats), so
    canonical JSON with lexicographically sorted keys and no insignificant whitespace
    is a faithful JCS encoding for this document.
    """
    body = {k: v for k, v in card.items() if k != "signatures"}
    return json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def sign_card(card: dict, signer: Signer | None = None) -> dict:
    """Return a copy of ``card`` with a non-empty ``signatures[]`` (Fuze profile §6).

    With no ``signer`` a deterministic placeholder is emitted so the card validates
    against the profile in tests and local runs; production injects a real JWS signer.
    """
    signed = {k: v for k, v in card.items() if k != "signatures"}
    if signer is None:
        signed["signatures"] = [dict(_PLACEHOLDER_SIGNATURE)]
    else:
        signed["signatures"] = [signer(canonicalize(card))]
    return signed
