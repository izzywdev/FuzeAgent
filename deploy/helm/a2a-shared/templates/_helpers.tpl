{{/*
Fixed workload name. binding.md §1/§4 and card-projection.md §2 HARDCODE the
in-cluster interface URL `http://a2a-shared.fuzeagent.svc.cluster.local:8080/rpc`,
so the Service (and thus this name) MUST be `a2a-shared`. Do not derive it from
.Release.Name — the card projection is a frozen contract value.
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
