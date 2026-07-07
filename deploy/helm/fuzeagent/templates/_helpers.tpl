{{/* Full release name, capped at 63 chars. */}}
{{- define "fuzeagent.fullname" -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/* ServiceAccount name used by the orchestrator (and RBAC). */}}
{{- define "fuzeagent.serviceAccountName" -}}
{{- if .Values.serviceAccount.name -}}
{{- .Values.serviceAccount.name -}}
{{- else -}}
{{- include "fuzeagent.fullname" . }}-orchestrator
{{- end -}}
{{- end -}}

{{/* Name of the Secret the workloads read from (SealedSecret provides it). */}}
{{- define "fuzeagent.secretName" -}}
{{- if .Values.secret.existingSecret -}}
{{- .Values.secret.existingSecret -}}
{{- else -}}
fuzeagent-secrets
{{- end -}}
{{- end -}}

{{/* Common labels. */}}
{{- define "fuzeagent.labels" -}}
app.kubernetes.io/part-of: fuzeagent
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version }}
{{- end -}}

{{/*
Shared DB/queue/cache env vars for the backend services (orchestrator, hierarchy-api).
POSTGRES_PASSWORD / RABBITMQ_PASSWORD come from the SealedSecret and are referenced by
DATABASE_URL / RABBITMQ_URL via $(VAR) interpolation (same-container env expansion).
Service names match docker-compose (postgres/redis/rabbitmq) so the app's hardcoded
hosts + the orchestrator entrypoint waits resolve in-namespace.
*/}}
{{- define "fuzeagent.backendEnv" -}}
- name: POSTGRES_PASSWORD
  valueFrom:
    secretKeyRef:
      name: {{ include "fuzeagent.secretName" . }}
      key: POSTGRES_PASSWORD
- name: RABBITMQ_PASSWORD
  valueFrom:
    secretKeyRef:
      name: {{ include "fuzeagent.secretName" . }}
      key: RABBITMQ_PASSWORD
- name: DATABASE_URL
  value: "postgresql://{{ .Values.postgres.user }}:$(POSTGRES_PASSWORD)@postgres:{{ .Values.postgres.port }}/{{ .Values.postgres.database }}"
- name: REDIS_URL
  value: "redis://redis:{{ .Values.redis.port }}"
- name: RABBITMQ_URL
  value: "amqp://{{ .Values.rabbitmq.user }}:$(RABBITMQ_PASSWORD)@rabbitmq:{{ .Values.rabbitmq.port }}/"
{{- end -}}
