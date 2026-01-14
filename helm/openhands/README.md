# OpenHands Helm Chart

This Helm chart deploys [OpenHands](https://github.com/OpenHands/OpenHands), an AI-driven development platform, on a Kubernetes cluster.

## TL;DR

```bash
helm install my-openhands ./helm/openhands \
  --set config.llm.apiKey=YOUR_API_KEY
```

## Introduction

OpenHands is a platform for AI software development, capable of executing complex engineering tasks and collaborating actively with users on software projects.

This chart bootstraps an OpenHands deployment on a [Kubernetes](https://kubernetes.io) cluster using the [Helm](https://helm.sh) package manager.

## Prerequisites

- Kubernetes 1.19+
- Helm 3.2.0+
- PV provisioner support in the underlying infrastructure (for persistence)
- An LLM API key (OpenAI, Anthropic, etc.)

## Installing the Chart

To install the chart with the release name `my-openhands`:

```bash
helm install my-openhands ./helm/openhands \
  --set config.llm.apiKey=YOUR_API_KEY \
  --set config.llm.model=gpt-4o
```

These commands deploy OpenHands on the Kubernetes cluster with the default configuration. The [Parameters](#parameters) section lists the parameters that can be configured during installation.

> **Tip**: List all releases using `helm list`

## Uninstalling the Chart

To uninstall/delete the `my-openhands` deployment:

```bash
helm uninstall my-openhands
```

The command removes all the Kubernetes components associated with the chart and deletes the release.

## Parameters

### Global Parameters

| Name                         | Description                                     | Value |
| ---------------------------- | ----------------------------------------------- | ----- |
| `global.imageRegistry`       | Global Docker image registry                    | `""`  |
| `global.imagePullSecrets`    | Global Docker registry secret names as an array | `[]`  |

### Common Parameters

| Name                | Description                                        | Value |
| ------------------- | -------------------------------------------------- | ----- |
| `nameOverride`      | String to partially override common.names.fullname | `""`  |
| `fullnameOverride`  | String to fully override common.names.fullname     | `""`  |
| `namespaceOverride` | String to fully override the namespace             | `""`  |

### OpenHands Image Parameters

| Name                 | Description                      | Value                  |
| -------------------- | -------------------------------- | ---------------------- |
| `image.registry`     | OpenHands image registry         | `docker.io`            |
| `image.repository`   | OpenHands image repository       | `openhands/openhands`  |
| `image.tag`          | OpenHands image tag              | `""`                   |
| `image.digest`       | OpenHands image digest           | `""`                   |
| `image.pullPolicy`   | OpenHands image pull policy      | `IfNotPresent`         |
| `image.pullSecrets`  | OpenHands image pull secrets     | `[]`                   |

### Runtime (Sandbox) Image Parameters

| Name              | Description                              | Value                                               |
| ----------------- | ---------------------------------------- | --------------------------------------------------- |
| `runtime.image`   | Runtime container image for code execution | `docker.openhands.dev/openhands/runtime:1.1-nikolaik` |
| `runtime.enabled` | Enable runtime sandbox                   | `true`                                              |

### OpenHands Deployment Parameters

| Name                                      | Description                                | Value       |
| ----------------------------------------- | ------------------------------------------ | ----------- |
| `replicaCount`                            | Number of OpenHands replicas to deploy     | `1`         |
| `podSecurityContext.enabled`              | Enable pod security context                | `true`      |
| `podSecurityContext.fsGroup`              | Group ID for the pod                       | `42420`     |
| `securityContext.enabled`                 | Enable container security context          | `true`      |
| `securityContext.runAsUser`               | User ID for the container                  | `42420`     |
| `securityContext.runAsNonRoot`            | Force the container to run as non-root     | `true`      |
| `securityContext.privileged`              | Run container in privileged mode           | `false`     |
| `securityContext.allowPrivilegeEscalation`| Allow privilege escalation                 | `false`     |
| `securityContext.readOnlyRootFilesystem`  | Mount root filesystem as read-only         | `false`     |

### Resource Limits

| Name                        | Description                | Value   |
| --------------------------- | -------------------------- | ------- |
| `resources.limits.cpu`      | CPU limit                  | `2000m` |
| `resources.limits.memory`   | Memory limit               | `4Gi`   |
| `resources.requests.cpu`    | CPU request                | `1000m` |
| `resources.requests.memory` | Memory request             | `2Gi`   |

### Service Parameters

| Name                       | Description                    | Value       |
| -------------------------- | ------------------------------ | ----------- |
| `service.type`             | Kubernetes service type        | `ClusterIP` |
| `service.port`             | Service HTTP port              | `3000`      |
| `service.targetPort`       | Container target port          | `3000`      |
| `service.nodePort`         | NodePort if service type is NodePort | `""`  |
| `service.annotations`      | Service annotations            | `{}`        |
| `service.sessionAffinity`  | Session Affinity               | `None`      |

### Ingress Parameters

| Name                   | Description                                    | Value              |
| ---------------------- | ---------------------------------------------- | ------------------ |
| `ingress.enabled`      | Enable ingress record generation               | `false`            |
| `ingress.className`    | IngressClass that will be used                 | `""`               |
| `ingress.annotations`  | Additional annotations for the Ingress         | `{}`               |
| `ingress.hosts`        | Ingress hosts configuration                    | See `values.yaml`  |
| `ingress.tls`          | Ingress TLS configuration                      | `[]`               |

### Persistence Parameters

| Name                            | Description                               | Value           |
| ------------------------------- | ----------------------------------------- | --------------- |
| `persistence.enabled`           | Enable persistence using PVC              | `true`          |
| `persistence.storageClass`      | Persistent Volume storage class           | `""`            |
| `persistence.accessModes`       | Persistent Volume access modes            | `[ReadWriteOnce]` |
| `persistence.size`              | Persistent Volume size                    | `10Gi`          |
| `persistence.annotations`       | Persistent Volume Claim annotations       | `{}`            |
| `persistence.existingClaim`     | Name of an existing PVC to use            | `""`            |
| `fileStore.enabled`             | Enable file store persistence             | `true`          |
| `fileStore.storageClass`        | Storage class for file store PVC          | `""`            |
| `fileStore.accessModes`         | File store PVC access modes               | `[ReadWriteOnce]` |
| `fileStore.size`                | File store PVC size                       | `5Gi`           |
| `fileStore.existingClaim`       | Name of an existing PVC for file store    | `""`            |

### OpenHands Configuration

#### LLM Configuration

| Name                             | Description                  | Value      |
| -------------------------------- | ---------------------------- | ---------- |
| `config.llm.apiKey`              | LLM API key (required)       | `""`       |
| `config.llm.model`               | LLM model to use             | `gpt-4o`   |
| `config.llm.baseUrl`             | Custom API base URL          | `""`       |
| `config.llm.customProvider`      | Custom LLM provider          | `""`       |
| `config.llm.temperature`         | Temperature for responses    | `0.0`      |
| `config.llm.maxInputTokens`      | Maximum input tokens         | `0`        |
| `config.llm.maxOutputTokens`     | Maximum output tokens        | `0`        |

#### Core Configuration

| Name                               | Description                     | Value                 |
| ---------------------------------- | ------------------------------- | --------------------- |
| `config.core.workspaceBase`        | Base path for workspace         | `/opt/workspace_base` |
| `config.core.maxIterations`        | Maximum number of iterations    | `500`                 |
| `config.core.maxBudgetPerTask`     | Maximum budget per task         | `0.0`                 |
| `config.core.defaultAgent`         | Default agent to use            | `CodeActAgent`        |

#### Sandbox Configuration

| Name                                | Description                  | Value   |
| ----------------------------------- | ---------------------------- | ------- |
| `config.sandbox.timeout`            | Sandbox timeout in seconds   | `120`   |
| `config.sandbox.userId`             | User ID for sandbox          | `0`     |
| `config.sandbox.useHostNetwork`     | Use host network             | `false` |
| `config.sandbox.enableAutoLint`     | Enable auto-linting          | `false` |

#### Security Configuration

| Name                                        | Description                    | Value   |
| ------------------------------------------- | ------------------------------ | ------- |
| `config.security.confirmationMode`          | Enable confirmation mode       | `false` |
| `config.security.securityAnalyzer`          | Security analyzer (llm/invariant) | `llm` |
| `config.security.enableSecurityAnalyzer`    | Enable security analyzer       | `true`  |

### ServiceAccount Parameters

| Name                         | Description                              | Value  |
| ---------------------------- | ---------------------------------------- | ------ |
| `serviceAccount.create`      | Specifies whether a ServiceAccount should be created | `true` |
| `serviceAccount.annotations` | ServiceAccount annotations               | `{}`   |
| `serviceAccount.name`        | The name of the ServiceAccount to use    | `""`   |

### RBAC Parameters

| Name           | Description                                | Value   |
| -------------- | ------------------------------------------ | ------- |
| `rbac.create`  | Specifies whether RBAC resources should be created | `false` |
| `rbac.rules`   | Custom RBAC rules to create                | `[]`    |

### Autoscaling Parameters

| Name                                          | Description                             | Value   |
| --------------------------------------------- | --------------------------------------- | ------- |
| `autoscaling.enabled`                         | Enable Horizontal Pod Autoscaler        | `false` |
| `autoscaling.minReplicas`                     | Minimum number of replicas              | `1`     |
| `autoscaling.maxReplicas`                     | Maximum number of replicas              | `10`    |
| `autoscaling.targetCPUUtilizationPercentage`  | Target CPU utilization percentage       | `80`    |
| `autoscaling.targetMemoryUtilizationPercentage` | Target Memory utilization percentage  | `80`    |

### Additional Parameters

| Name                        | Description                          | Value   |
| --------------------------- | ------------------------------------ | ------- |
| `nodeSelector`              | Node labels for pod assignment       | `{}`    |
| `tolerations`               | Tolerations for pod assignment       | `[]`    |
| `affinity`                  | Affinity for pod assignment          | `{}`    |
| `podAnnotations`            | Annotations for pods                 | `{}`    |
| `podLabels`                 | Additional labels for pods           | `{}`    |
| `priorityClassName`         | Priority class name for pods         | `""`    |
| `hostAliases`               | Add entries to /etc/hosts            | `[]`    |
| `envVars`                   | Additional environment variables     | `[]`    |
| `envVarsSecret`             | Name of existing Secret for env vars | `""`    |

### Liveness and Readiness Probes

| Name                                    | Description                            | Value  |
| --------------------------------------- | -------------------------------------- | ------ |
| `livenessProbe.enabled`                 | Enable livenessProbe                   | `true` |
| `livenessProbe.initialDelaySeconds`     | Initial delay seconds                  | `30`   |
| `livenessProbe.periodSeconds`           | Period seconds                         | `10`   |
| `livenessProbe.timeoutSeconds`          | Timeout seconds                        | `5`    |
| `livenessProbe.failureThreshold`        | Failure threshold                      | `6`    |
| `livenessProbe.successThreshold`        | Success threshold                      | `1`    |
| `readinessProbe.enabled`                | Enable readinessProbe                  | `true` |
| `readinessProbe.initialDelaySeconds`    | Initial delay seconds                  | `10`   |
| `readinessProbe.periodSeconds`          | Period seconds                         | `10`   |
| `readinessProbe.timeoutSeconds`         | Timeout seconds                        | `5`    |
| `readinessProbe.failureThreshold`       | Failure threshold                      | `3`    |
| `readinessProbe.successThreshold`       | Success threshold                      | `1`    |

## Configuration Examples

### Basic Installation with OpenAI

```bash
helm install openhands ./helm/openhands \
  --set config.llm.apiKey=sk-... \
  --set config.llm.model=gpt-4o
```

### With Custom LLM Provider

```bash
helm install openhands ./helm/openhands \
  --set config.llm.apiKey=YOUR_API_KEY \
  --set config.llm.baseUrl=https://api.your-provider.com/v1 \
  --set config.llm.model=your-model
```

### With Ingress Enabled

```bash
helm install openhands ./helm/openhands \
  --set config.llm.apiKey=YOUR_API_KEY \
  --set ingress.enabled=true \
  --set ingress.className=nginx \
  --set ingress.hosts[0].host=openhands.example.com \
  --set ingress.hosts[0].paths[0].path=/ \
  --set ingress.hosts[0].paths[0].pathType=Prefix
```

### With Custom Storage

```bash
helm install openhands ./helm/openhands \
  --set config.llm.apiKey=YOUR_API_KEY \
  --set persistence.storageClass=fast-ssd \
  --set persistence.size=50Gi \
  --set fileStore.storageClass=standard \
  --set fileStore.size=20Gi
```

### With Autoscaling

```bash
helm install openhands ./helm/openhands \
  --set config.llm.apiKey=YOUR_API_KEY \
  --set autoscaling.enabled=true \
  --set autoscaling.minReplicas=2 \
  --set autoscaling.maxReplicas=10 \
  --set autoscaling.targetCPUUtilizationPercentage=70
```

### Using values.yaml file

Create a `custom-values.yaml` file:

```yaml
config:
  llm:
    apiKey: "your-api-key-here"
    model: "gpt-4o"
    
ingress:
  enabled: true
  className: nginx
  hosts:
    - host: openhands.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: openhands-tls
      hosts:
        - openhands.example.com

persistence:
  size: 50Gi
  storageClass: fast-ssd

resources:
  limits:
    cpu: 4000m
    memory: 8Gi
  requests:
    cpu: 2000m
    memory: 4Gi
```

Then install:

```bash
helm install openhands ./helm/openhands -f custom-values.yaml
```

## Upgrading

To upgrade the `my-openhands` deployment:

```bash
helm upgrade my-openhands ./helm/openhands \
  --set config.llm.apiKey=YOUR_API_KEY
```

## Persistence

The chart mounts two Persistent Volumes at the following mount paths:

1. **Workspace Volume** (default: `/opt/workspace_base`): Stores project workspaces
   - Default size: 10Gi
   - Access mode: ReadWriteOnce

2. **File Store Volume** (default: `/.openhands`): Stores internal file data
   - Default size: 5Gi
   - Access mode: ReadWriteOnce

### Using Existing PersistentVolumeClaims

If you want to use existing PVCs:

```yaml
persistence:
  existingClaim: my-workspace-pvc

fileStore:
  existingClaim: my-filestore-pvc
```

### Disabling Persistence

To disable persistence (data will be lost on pod restart):

```yaml
persistence:
  enabled: false

fileStore:
  enabled: false
```

## Security Considerations

1. **API Keys**: Always store API keys securely. Consider using external secret management solutions like:
   - [External Secrets Operator](https://external-secrets.io/)
   - [Sealed Secrets](https://github.com/bitnami-labs/sealed-secrets)
   - Cloud provider secret managers (AWS Secrets Manager, GCP Secret Manager, Azure Key Vault)

2. **Security Context**: The chart runs as a non-root user (UID 42420) by default for enhanced security.

3. **Network Policies**: Consider implementing network policies to restrict traffic to/from OpenHands pods.

4. **RBAC**: Enable RBAC if OpenHands needs to interact with Kubernetes resources:

```yaml
rbac:
  create: true
  rules:
    - apiGroups: [""]
      resources: ["pods"]
      verbs: ["get", "list"]
```

## Troubleshooting

### Pod Fails to Start

Check the pod logs:
```bash
kubectl logs -l app.kubernetes.io/name=openhands
```

Common issues:
- Missing or invalid API key
- Insufficient resources
- PVC provisioning failures

### API Key Not Working

Ensure the API key is correctly set and the secret is created:
```bash
kubectl get secret -o yaml | grep llm-api-key
```

### Storage Issues

Check PVC status:
```bash
kubectl get pvc
```

Ensure your cluster has a storage provisioner configured.

### Service Not Accessible

For LoadBalancer services, ensure your cluster supports LoadBalancer services (cloud providers typically do).

For ClusterIP, use port-forwarding:
```bash
kubectl port-forward svc/openhands 3000:3000
```

## Contributing

Contributions to improve this Helm chart are welcome! Please submit issues and pull requests to the [OpenHands repository](https://github.com/OpenHands/OpenHands).

## License

This chart is licensed under the MIT License. See the [LICENSE](../../LICENSE) file for details.

## Support

- **Documentation**: https://docs.openhands.dev
- **GitHub Issues**: https://github.com/OpenHands/OpenHands/issues
- **Slack Community**: https://dub.sh/openhands
