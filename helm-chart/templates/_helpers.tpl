{{- define "job-aggregator.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "job-aggregator.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "job-aggregator.componentFullname" -}}
{{- printf "%s-%s" (include "job-aggregator.fullname" .root) .name | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "job-aggregator.labels" -}}
app.kubernetes.io/name: {{ include "job-aggregator.name" .root }}
helm.sh/chart: {{ .root.Chart.Name }}-{{ .root.Chart.Version | replace "+" "_" }}
app.kubernetes.io/instance: {{ .root.Release.Name }}
app.kubernetes.io/managed-by: {{ .root.Release.Service }}
app.kubernetes.io/component: {{ .name }}
{{- end -}}

{{- define "job-aggregator.selectorLabels" -}}
app.kubernetes.io/name: {{ include "job-aggregator.name" .root }}
app.kubernetes.io/instance: {{ .root.Release.Name }}
app.kubernetes.io/component: {{ .name }}
{{- end -}}

{{- define "job-aggregator.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{- default (include "job-aggregator.fullname" .) .Values.serviceAccount.name -}}
{{- else -}}
{{- default "default" .Values.serviceAccount.name -}}
{{- end -}}
{{- end -}}

{{- define "job-aggregator.sharedDataClaimName" -}}
{{- if .Values.sharedData.existingClaim -}}
{{- .Values.sharedData.existingClaim -}}
{{- else -}}
{{- printf "%s-shared-data" (include "job-aggregator.fullname" .) | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "job-aggregator.natsClaimName" -}}
{{- if .Values.nats.persistence.existingClaim -}}
{{- .Values.nats.persistence.existingClaim -}}
{{- else -}}
{{- include "job-aggregator.componentFullname" (dict "root" . "name" "nats") -}}
{{- end -}}
{{- end -}}

{{- define "job-aggregator.componentImage" -}}
{{- $tag := .component.image.tag | default .root.Values.global.imageTag -}}
{{- printf "%s:%s" .component.image.repository $tag -}}
{{- end -}}

{{- define "job-aggregator.renderEnv" -}}
{{- $root := .root -}}
{{- range .items }}
- name: {{ .name }}
  {{- if hasKey . "value" }}
  value: {{ tpl (printf "%v" .value) $root | quote }}
  {{- else if hasKey . "valueFrom" }}
  valueFrom:
    {{- toYaml .valueFrom | nindent 4 }}
  {{- end }}
{{- end -}}
{{- end -}}

{{- define "job-aggregator.componentDeployment" -}}
{{- $root := .root -}}
{{- $component := .component -}}
{{- $defaultEnv := default (list) .defaultEnv -}}
{{- $useGlobalEnv := true -}}
{{- if hasKey $component "useGlobalEnv" -}}
{{- $useGlobalEnv = $component.useGlobalEnv -}}
{{- end -}}
{{- $globalEnv := ternary (default (list) $root.Values.global.env) (list) $useGlobalEnv -}}
{{- $componentEnv := default (list) $component.env -}}
{{- $useGlobalEnvFrom := true -}}
{{- if hasKey $component "useGlobalEnvFrom" -}}
{{- $useGlobalEnvFrom = $component.useGlobalEnvFrom -}}
{{- end -}}
{{- $globalEnvFrom := ternary (default (list) $root.Values.global.envFrom) (list) $useGlobalEnvFrom -}}
{{- $componentEnvFrom := default (list) $component.envFrom -}}
{{- $defaultVolumeMounts := default (list) .defaultVolumeMounts -}}
{{- $defaultVolumes := default (list) .defaultVolumes -}}
{{- $globalPodLabels := default (dict) $root.Values.global.podLabels -}}
{{- $componentPodLabels := default (dict) $component.podLabels -}}
{{- $globalPodAnnotations := default (dict) $root.Values.global.podAnnotations -}}
{{- $componentPodAnnotations := default (dict) $component.podAnnotations -}}
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "job-aggregator.componentFullname" (dict "root" $root "name" .name) }}
  labels:
    {{- include "job-aggregator.labels" (dict "root" $root "name" .name) | nindent 4 }}
spec:
  {{- if not $component.autoscaling.enabled }}
  replicas: {{ $component.replicaCount }}
  {{- end }}
  selector:
    matchLabels:
      {{- include "job-aggregator.selectorLabels" (dict "root" $root "name" .name) | nindent 6 }}
  template:
    metadata:
      labels:
        {{- include "job-aggregator.selectorLabels" (dict "root" $root "name" .name) | nindent 8 }}
        {{- with $globalPodLabels }}
        {{- toYaml . | nindent 8 }}
        {{- end }}
        {{- with $componentPodLabels }}
        {{- toYaml . | nindent 8 }}
        {{- end }}
      {{- if or $globalPodAnnotations $componentPodAnnotations }}
      annotations:
        {{- with $globalPodAnnotations }}
        {{- toYaml . | nindent 8 }}
        {{- end }}
        {{- with $componentPodAnnotations }}
        {{- toYaml . | nindent 8 }}
        {{- end }}
      {{- end }}
    spec:
      serviceAccountName: {{ include "job-aggregator.serviceAccountName" $root }}
      {{- with $root.Values.global.imagePullSecrets }}
      imagePullSecrets:
        {{- toYaml . | nindent 8 }}
      {{- end }}
      containers:
        - name: {{ .name }}
          image: {{ include "job-aggregator.componentImage" (dict "root" $root "component" $component) | quote }}
          imagePullPolicy: {{ $component.image.pullPolicy | default $root.Values.global.imagePullPolicy }}
          {{- with $component.command }}
          command:
            {{- toYaml . | nindent 12 }}
          {{- end }}
          {{- with $component.args }}
          args:
            {{- toYaml . | nindent 12 }}
          {{- end }}
          {{- with $component.containerPorts }}
          ports:
            {{- toYaml . | nindent 12 }}
          {{- end }}
          {{- if or $defaultEnv $globalEnv $componentEnv }}
          env:
            {{- include "job-aggregator.renderEnv" (dict "root" $root "items" $defaultEnv) | nindent 12 }}
            {{- include "job-aggregator.renderEnv" (dict "root" $root "items" $globalEnv) | nindent 12 }}
            {{- include "job-aggregator.renderEnv" (dict "root" $root "items" $componentEnv) | nindent 12 }}
          {{- end }}
          {{- if or $globalEnvFrom $componentEnvFrom }}
          envFrom:
            {{- toYaml (concat $globalEnvFrom $componentEnvFrom) | nindent 12 }}
          {{- end }}
          {{- with $component.resources }}
          resources:
            {{- toYaml . | nindent 12 }}
          {{- end }}
          {{- $sharedDataEnabled := or $root.Values.sharedData.enabled $root.Values.sharedData.existingClaim }}
          {{- if or (and $component.persistence.useSharedData $sharedDataEnabled) $defaultVolumeMounts $component.volumeMounts }}
          volumeMounts:
            {{- if and $component.persistence.useSharedData $sharedDataEnabled }}
            - name: shared-data
              mountPath: {{ $root.Values.sharedData.mountPath }}
            {{- end }}
            {{- with $defaultVolumeMounts }}
            {{- toYaml . | nindent 12 }}
            {{- end }}
            {{- with $component.volumeMounts }}
            {{- toYaml . | nindent 12 }}
            {{- end }}
          {{- end }}
          {{- with $component.livenessProbe }}
          livenessProbe:
            {{- toYaml . | nindent 12 }}
          {{- end }}
          {{- with $component.readinessProbe }}
          readinessProbe:
            {{- toYaml . | nindent 12 }}
          {{- end }}
      {{- if or (and $component.persistence.useSharedData (or $root.Values.sharedData.enabled $root.Values.sharedData.existingClaim)) $defaultVolumes $component.volumes }}
      volumes:
        {{- if and $component.persistence.useSharedData (or $root.Values.sharedData.enabled $root.Values.sharedData.existingClaim) }}
        - name: shared-data
          persistentVolumeClaim:
            claimName: {{ include "job-aggregator.sharedDataClaimName" $root }}
        {{- end }}
        {{- with $defaultVolumes }}
        {{- toYaml . | nindent 8 }}
        {{- end }}
        {{- with $component.volumes }}
        {{- toYaml . | nindent 8 }}
        {{- end }}
      {{- end }}
{{- end -}}

{{- define "job-aggregator.componentService" -}}
{{- $root := .root -}}
{{- $component := .component -}}
{{- if $component.service.enabled }}
apiVersion: v1
kind: Service
metadata:
  name: {{ include "job-aggregator.componentFullname" (dict "root" $root "name" .name) }}
  labels:
    {{- include "job-aggregator.labels" (dict "root" $root "name" .name) | nindent 4 }}
spec:
  type: {{ $component.service.type }}
  selector:
    {{- include "job-aggregator.selectorLabels" (dict "root" $root "name" .name) | nindent 4 }}
  ports:
    - name: {{ $component.service.name | default "http" }}
      port: {{ $component.service.port }}
      targetPort: {{ $component.service.targetPort }}
      protocol: TCP
    {{- with $component.service.extraPorts }}
    {{- toYaml . | nindent 4 }}
    {{- end }}
{{- end }}
{{- end -}}

{{- define "job-aggregator.componentHpa" -}}
{{- $root := .root -}}
{{- $component := .component -}}
{{- if $component.autoscaling.enabled }}
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: {{ include "job-aggregator.componentFullname" (dict "root" $root "name" .name) }}
  labels:
    {{- include "job-aggregator.labels" (dict "root" $root "name" .name) | nindent 4 }}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {{ include "job-aggregator.componentFullname" (dict "root" $root "name" .name) }}
  minReplicas: {{ $component.autoscaling.minReplicas }}
  maxReplicas: {{ $component.autoscaling.maxReplicas }}
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: {{ $component.autoscaling.targetCPUUtilizationPercentage }}
{{- end }}
{{- end -}}
