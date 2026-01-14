# OpenHands Helm Chart

This directory contains a Helm chart for deploying OpenHands on Kubernetes.

## Quick Start

```bash
# Install with minimum configuration
helm install openhands ./helm/openhands \
  --set config.llm.apiKey=YOUR_API_KEY

# Install with custom values
helm install openhands ./helm/openhands \
  -f helm/openhands/examples/production-values.yaml \
  --set config.llm.apiKey=YOUR_API_KEY
```

## Documentation

For detailed documentation, see [helm/openhands/README.md](./openhands/README.md)

## Examples

Example configurations are provided in the `examples/` directory:

- `dev-values.yaml` - Minimal development configuration
- `production-values.yaml` - Production-ready configuration with ingress, persistence, and enhanced security

## Prerequisites

- Kubernetes 1.19+
- Helm 3.2.0+
- An LLM API key (OpenAI, Anthropic, etc.)

## Chart Structure

```
helm/openhands/
├── Chart.yaml              # Chart metadata
├── values.yaml             # Default configuration values
├── README.md               # Detailed documentation
├── examples/               # Example configurations
│   ├── dev-values.yaml
│   └── production-values.yaml
└── templates/              # Kubernetes resource templates
    ├── _helpers.tpl        # Template helpers
    ├── deployment.yaml     # Main application deployment
    ├── service.yaml        # Kubernetes service
    ├── ingress.yaml        # Ingress resource (optional)
    ├── configmap.yaml      # Configuration data
    ├── secret.yaml         # Sensitive data
    ├── pvc.yaml            # Persistent volume claims
    ├── serviceaccount.yaml # Service account
    ├── rbac.yaml           # RBAC resources (optional)
    ├── hpa.yaml            # Horizontal Pod Autoscaler (optional)
    ├── pdb.yaml            # Pod Disruption Budget (optional)
    └── NOTES.txt           # Post-installation notes
```

## Features

- ✅ Configurable LLM integration (OpenAI, Anthropic, custom providers)
- ✅ Persistent storage for workspaces and data
- ✅ Ingress support with TLS
- ✅ Horizontal Pod Autoscaling
- ✅ Resource limits and requests
- ✅ Security contexts and RBAC
- ✅ Health checks (liveness and readiness probes)
- ✅ Pod Disruption Budgets
- ✅ Comprehensive configuration options
- ✅ Production and development presets

## Compatibility

This Helm chart has been tested with:

- Kubernetes 1.19+
- Helm 3.2.0+
- OpenHands 1.1.0

## Contributing

When making changes to the Helm chart:

1. Update version in `Chart.yaml`
2. Test with `helm lint helm/openhands/`
3. Validate rendering with `helm template test helm/openhands/`
4. Update documentation as needed
5. Test installation on a development cluster

## Support

For issues specific to the Helm chart, please open an issue on the [OpenHands repository](https://github.com/OpenHands/OpenHands/issues) with the `helm` label.

For general OpenHands support:
- Documentation: https://docs.openhands.dev
- Slack: https://dub.sh/openhands
