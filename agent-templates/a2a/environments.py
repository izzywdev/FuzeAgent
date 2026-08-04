"""Resolve a role's ``environment`` basename to a provider environment id (FA-14).

Mirrors ``providers/provision.py``'s two-step lookup exactly — do not invent a new
scheme:

1. ``_env_basename_to_name``: a role's ``environment`` field is the BASENAME (no
   ``.json``) of an ``agent-templates/environments/<basename>.json`` file (schema:
   ``schema/environment.schema.json``); that file's ``name`` field is what batch
   provisioning actually registers with the provider.
2. ``env_ids.get(name)``: batch provisioning (``providers/provision.py:apply``) writes
   the resulting ``{name: id}`` map to ``<FUZE_STATE_DIR>/environment-ids.json``. At A2A
   dispatch time we do the SAME lookup against that file so ``create_session`` gets a
   real ``environment_id`` instead of always ``None`` (``adapter.py`` ``_provision``,
   FA-14 AC1).

Both file reads are cached: the adapter dispatches through this on every SendMessage, so
re-reading disk (a ConfigMap-backed mount, at runtime) per call would be needless I/O.
Construct ONE ``EnvironmentResolver`` per adapter/process — never per request.
"""

from __future__ import annotations

import json
import os
from pathlib import Path


class EnvironmentResolutionError(RuntimeError):
    """A role names an ``environment`` that could not be resolved to a provider id.

    Raised instead of silently falling back to ``None`` (FA-14 AC2). This is ONLY for a
    role that names a SPECIFIC environment which then turns out to be unresolvable —
    either the basename has no matching ``environments/<basename>.json``, that file has
    no ``name``, or its ``name`` has no entry in ``environment-ids.json`` (not yet
    provisioned). A role that names NO environment never reaches this class — that case
    resolves to ``None`` legitimately, one level up in ``adapter._resolve_environment_id``.
    """


#: Sibling of this package (mirrors ``provision.py``'s
#: ``ENV_DIR = os.path.join(TEMPLATES_ROOT, "environments")``, where ``TEMPLATES_ROOT``
#: is ``agent-templates/`` relative to ``providers/provision.py``; here it is
#: ``agent-templates/`` relative to ``a2a/environments.py``).
_DEFAULT_ENVIRONMENTS_DIR = Path(__file__).resolve().parent.parent / "environments"

#: Default state mount (a2a-shared chart's ``deploy.stateConfigMap: a2a-state``).
_DEFAULT_STATE_DIR = "/state"

#: Filename batch provisioning writes the name -> provider-id map to
#: (``providers/provision.py`` ``_write("environment-ids.json", env_ids)``).
ENV_IDS_FILENAME = "environment-ids.json"


class EnvironmentResolver:
    """Resolve an environment BASENAME -> provider environment id, caching both reads.

    ``environments_dir`` defaults to this repo's own ``agent-templates/environments/``
    (sibling to ``a2a/``); ``state_dir`` defaults to ``$FUZE_STATE_DIR`` or ``/state``.
    Both are read lazily, on first use, and held for the resolver's lifetime.
    """

    def __init__(
        self,
        *,
        environments_dir: str | Path | None = None,
        state_dir: str | Path | None = None,
    ):
        self._environments_dir = Path(environments_dir or _DEFAULT_ENVIRONMENTS_DIR)
        self._state_dir = Path(
            state_dir or os.environ.get("FUZE_STATE_DIR") or _DEFAULT_STATE_DIR
        )
        self._ids: dict[str, str] | None = None
        self._name_by_basename: dict[str, str] = {}

    def _basename_to_name(self, basename: str) -> str:
        if basename in self._name_by_basename:
            return self._name_by_basename[basename]
        path = self._environments_dir / f"{basename}.json"
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
            name = doc["name"]
        except (OSError, ValueError, KeyError) as exc:
            raise EnvironmentResolutionError(
                f"role names environment {basename!r} but {path} could not be read as "
                f'an environments/*.json with a "name" field: {exc}'
            ) from exc
        self._name_by_basename[basename] = name
        return name

    def _load_ids(self) -> dict[str, str]:
        if self._ids is None:
            path = self._state_dir / ENV_IDS_FILENAME
            try:
                self._ids = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                # Absent/unreadable state is fine for roles naming NO environment
                # (adapter never calls in here for those); a role naming one will
                # raise below via the empty map, per AC2 (never silently null).
                self._ids = {}
        return self._ids

    def __call__(self, basename: str) -> str:
        """Resolve a NAMED environment basename to a provider id, or raise.

        Only call this for a role that DOES name an environment — a role naming none
        resolves to ``None`` through a different path and must never reach here.
        """
        name = self._basename_to_name(basename)
        env_ids = self._load_ids()
        env_id = env_ids.get(name)
        if not env_id:
            raise EnvironmentResolutionError(
                f"role names environment {basename!r} (name={name!r}) but it has no "
                f"provisioned id in {self._state_dir / ENV_IDS_FILENAME} "
                "(has provisioning run for this environment?)"
            )
        return env_id
