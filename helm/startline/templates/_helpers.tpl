{{- define "startline.name" -}}
{{- .Chart.Name -}}
{{- end -}}

{{- define "startline.fullname" -}}
{{- if contains .Chart.Name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name .Chart.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "startline.labels" -}}
app.kubernetes.io/name: {{ include "startline.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Values.image.tag | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
app.kubernetes.io/part-of: startline
helm.sh/chart: {{ printf "%s-%s" .Chart.Name .Chart.Version }}
{{- end -}}

{{/* selector labels for one component: include "startline.selector" (list . "backend") */}}
{{- define "startline.selector" -}}
{{- $ctx := index . 0 -}}
app.kubernetes.io/name: {{ include "startline.name" $ctx }}
app.kubernetes.io/instance: {{ $ctx.Release.Name }}
app.kubernetes.io/component: {{ index . 1 }}
{{- end -}}

{{- define "startline.dbSecretName" -}}
{{- default (printf "%s-db" (include "startline.fullname" .)) .Values.database.existingSecret -}}
{{- end -}}

{{/* registry/name:tag, or name:tag when the image was loaded into the cluster directly */}}
{{- define "startline.image" -}}
{{- $ctx := index . 0 -}}
{{- if $ctx.Values.image.registry -}}
{{- printf "%s/%s:%s" $ctx.Values.image.registry (index . 1) $ctx.Values.image.tag -}}
{{- else -}}
{{- printf "%s:%s" (index . 1) $ctx.Values.image.tag -}}
{{- end -}}
{{- end -}}

{{- define "startline.podSecurity" -}}
runAsNonRoot: true
seccompProfile:
  type: RuntimeDefault
{{- end -}}

{{- define "startline.containerSecurity" -}}
allowPrivilegeEscalation: false
readOnlyRootFilesystem: true
capabilities:
  drop: ["ALL"]
{{- end -}}
