# RAG in the shared A2A server

`agent-templates/a2a/rag/` gives the shared A2A server retrieval against the
family's Chroma instance. It ships in the `ghcr.io/izzywdev/fuze-a2a` image and
is **off unless the chart turns it on**.

## Retrieval only — and why that is not a limitation

The A2A pod never indexes. Indexing needs the original documents, and those
belong to whoever owns them (FuzeAgent's orchestrator keeps them on a filesystem
under `KNOWLEDGE_STORAGE_PATH`). A multi-tenant pod must not hold any tenant's
document store, so the split is deliberate:

| | indexes | retrieves |
|---|---|---|
| FuzeAgent orchestrator | ✅ `rag_integration.index_document` | ✅ |
| shared A2A server | ❌ never | ✅ `a2a.rag.RagRetriever.search` |

**No document database is needed for retrieval.** The indexer stores the chunk
*text* alongside each vector (`collection.add(..., documents=text_chunks)`) and
the query reads it back (`include=["documents", …]`). A second hop to Mongo or
Postgres to re-fetch the source would only be necessary if Chroma held vectors
alone — it does not. The document store exists for re-indexing and download, not
for answering a query.

## Isolation: one instance, A2A's own database, a collection per tenant

```
FuzeInfra Chroma instance
└── database: a2a                 ← allocated to A2A, not the default
    ├── collection: a2a-fuzeagent
    ├── collection: a2a-fuzebi
    └── collection: a2a-<tenant>
```

Per-tenant **collections**, not one collection with a `where` filter. A filter is
one forgotten argument away from returning another tenant's chunks; a separate
collection cannot be read by omission.

### That isolation is enforced by FuzeInfra's provider, NOT by stock Chroma

This matters enough to state plainly, because the obvious reading — "Chroma has
tenants and databases, so tenants and databases are isolated" — **is false for
every published version of Chroma**:

| CVE | What stock Chroma does |
|---|---|
| CVE-2026-45830 | *"lack of authorization validation … allows any authenticated user to arbitrarily read, write, update, or delete data in any tenant's collection regardless of which tenant they belong to"* (0.4.17+) |
| CVE-2026-45831 | `SimpleRBACAuthorizationProvider` *"evaluates whether a user holds a given permission but never checks which tenant, database, or collection that permission applies to"* (0.5.0+) |

Neither has an upstream fix in any release — verified with `pip-audit` across
0.4.24 → 1.3.0; **no version is clean**.

What closes it here is that FuzeInfra does not use the built-in provider. It
ships `TenantDatabaseAuthorizationProvider`
(`helm/fuzeinfra/templates/chroma-authz.yaml`), which resolves the immutable
collection UUID in SysDB rather than trusting the request's tenant/database —
its own comment says it *"prevents a token from using a known collection UUID to
cross an allocation boundary"* — and the provisioning job then **verifies** the
denial by attempting a foreign-tenant write with each token and requiring it to
be rejected.

So the isolation claim above rests on a replacement provider plus a test that
exercises it, not on a vendor feature. If that provider is ever swapped back to
the stock one, per-tenant collections stop being a boundary and become a naming
convention. Do not treat them as isolation on any Chroma deployment that has not
replaced the provider.

## Configuration

Set on the chart under `deploy.rag`; the deployment template projects them into
the container env. When `enabled: true`, `host`, `database` and
`authTokenSecretRef` are all `required` — `helm template` fails without them.

| env | chart key | notes |
|---|---|---|
| `A2A_RAG_ENABLED` | `deploy.rag.enabled` | unset/0 → `build_from_env()` returns `None` |
| `CHROMA_HOST` | `deploy.rag.host` | **no default** — see below |
| `CHROMA_PORT` | `deploy.rag.port` | 8000 |
| `CHROMA_SSL` | `deploy.rag.ssl` | |
| `CHROMA_TENANT` | `deploy.rag.tenant` | `fuzeagent` |
| `CHROMA_DATABASE` | `deploy.rag.database` | `a2a` |
| `CHROMA_COLLECTION_PREFIX` | `deploy.rag.collectionPrefix` | `a2a-` |
| `RAG_EMBEDDING_MODEL` | `deploy.rag.embeddingModel` | `all-MiniLM-L6-v2` |
| `CHROMA_AUTH_TOKEN` | `deploy.rag.authTokenSecretRef` | SealedSecret ref; no literal key exists |
| `CHROMA_ALLOW_UNAUTHENTICATED` | — | dev/CI escape, must be stated explicitly |

## Three defaults this package refuses to have

Every one is a defect that was live in `services/orchestrator/rag_integration.py`
and is fixed in the same change that added this package. Together they left
FuzeAgent's RAG **inert in production** while every log line, probe and endpoint
looked healthy.

1. **`CHROMA_HOST` did not default to `localhost` — it does not default at all.**
   Nothing set it in any manifest, so the pod dialled itself. A default that is
   wrong but still lets the process start is worse than no default.

2. **The auth provider is a dotted class path, never a keyword.** The code passed
   `chroma_client_auth_provider="basic"`. Chroma resolves that string as an import
   path, so `"basic"` resolved to nothing and the client was built *unauthenticated*
   while appearing to configure auth. The correct values live in one constant each
   (`TOKEN_AUTH_PROVIDER`, `BASIC_AUTH_PROVIDER`), and
   `services/orchestrator/tests/test_rag_provider_parity.py` fails if the
   orchestrator's copy and the A2A copy ever disagree.

3. **An empty credential never means "no auth wanted".** The code passed
   `chroma_client_auth_credentials=""`. Unauthenticated access now requires
   `CHROMA_ALLOW_UNAUTHENTICATED=1` — said out loud, in a values file.

And the fourth, which is what actually hid the other three:

4. **Unreachable is not empty.** A connect or query failure `raise`s
   `RagUnavailable`; it is never degraded into `[]`. The orchestrator's
   `/rag/search` and `/rag/enhance-prompt` return **503**, not 200-with-no-results.
   "The store is down" and "the corpus has nothing on that" are different answers
   and a caller — human or agent — must be able to tell them apart.

## Prerequisite: the FuzeInfra allocation

`deploy.rag.enabled` stays `false` until FuzeInfra provides:

FuzeInfra already has exactly the right mechanism — `serviceChromaCollections[]`
in `helm/fuzeinfra/values-contabo.yaml`, which provisions an isolated
tenant/database per consumer, seals a bearer token for it, and **verifies
cross-tenant denial** as part of the provisioning job. `fuzeplan-repo-digester`
and `fuzequality` are existing entries. So the request is one more entry, not a
new capability:

```yaml
- name: fuzeagent-a2a
  enabled: true
  tenant: fuzeagent
  database: a2a
  credentialSecret:
    name: fuzeagent-a2a-chroma-credentials
    key: token
  networkPolicy:
    namespace: fuzeagent
    podLabels:
      app.kubernetes.io/name: a2a-shared
  collections: []        # created on demand, one per A2A tenant
```

**Both `tenant` and `database` matter.** FuzeInfra's authorization provider binds
each token to exactly one `(tenant, database)` pair server-side, and the Chroma
client resolves both eagerly at construction — so a mismatch is not a subtle
permission error later, it is a failure to connect at all.

FuzeInfra is never edited from this repo — that request goes via `@claude` with
the allocation named. Turning the flag on before those exist does not produce a
degraded pod; it produces one that refuses to start, which is the intended
behaviour.
