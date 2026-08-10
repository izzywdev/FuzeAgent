{{/*
Fixed workload name for THIS (shared) deployment.

The in-cluster interface URL is no longer a generator constant: as of contract v1.2.0
it is `a2a.inClusterUrl`, defaulting to
`http://a2a-shared.fuzeagent.svc.cluster.local:8080/rpc` (card-projection.md §2). The
invariant is now an AGREEMENT rather than a hardcode — whatever this Service resolves
to MUST equal what `a2a.inClusterUrl` advertises, because callers follow the CARD, not
the Service object.

This chart leaves `a2a.inClusterUrl` unset, so the default applies and the Service MUST
stay `a2a-shared` in namespace `fuzeagent`. Do not derive it from .Release.Name. A
PER-PRODUCT pod is a separate deployment in the product's own repo and namespace; it
sets `a2a.inClusterUrl` to its own Service (docs/a2a/per-product-pod.md).
*/}}
{{- define "a2a.name" -}}
a2a-shared
{{- end -}}

{{/* Common labels. */}}
{{- define "a2a.labels" -}}
app.kubernetes.io/name: {{ include "a2a.name" . }}
app.kubernetes.io/part-of: fuzeagent
app.kubernetes.io/component: a2a-server
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version }}
{{- end -}}

{{/* Selector labels (stable across upgrades — never add version-bearing labels here). */}}
{{- define "a2a.selectorLabels" -}}
app.kubernetes.io/name: {{ include "a2a.name" . }}
app.kubernetes.io/component: a2a-server
{{- end -}}

{{/*
Lowercased repo-name segment ("izzywdev/FuzePlan" -> "fuzeplan"), used as the
external host slug per card-projection.md §2:
  https://a2a.<repo-slug>.prod.fuzefront.com/rpc
Argument: the tenant's `repo` string.
*/}}
{{- define "a2a.repoSlug" -}}
{{- $parts := splitList "/" . -}}
{{- last $parts | lower -}}
{{- end -}}
