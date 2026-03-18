# Demo Apps - POC Argo Rollouts

Aplicaciones demo para demostrar estrategias de despliegue progresivo con Argo Rollouts e Istio en EKS.

## Estructura

```
├── canary-app/           # App demo para despliegue Canary
│   ├── app/              # Código fuente Python/Flask
│   ├── Dockerfile
│   ├── k8s/              # Manifiestos Kubernetes + Argo Rollouts
│   └── istio/            # VirtualService y DestinationRule
└── .github/workflows/    # GitHub Actions para build y push a ECR
```

## Canary App

Aplicación Flask con:
- Endpoints de salud (`/health`, `/ready`)
- Métricas Prometheus (`/metrics`)
- Inyección de fallos configurable (`FAILURE_RATE`)
- Latencia configurable (`LATENCY_MS`)
- Versionado por variable de entorno (`APP_VERSION`)

## CI/CD

El workflow de GitHub Actions se activa:
- Con push a `main` que modifique archivos en `canary-app/`
- Manualmente con `workflow_dispatch` (tag personalizado)

Construye imagen `linux/amd64` y la sube a ECR.

### Requisitos
- Secreto `AWS_ROLE_ARN` configurado en el repo (IAM Role con OIDC federation)
- Repositorio ECR `canary-demo` en `us-east-1`

## Despliegue en EKS

```bash
# Aplicar manifiestos
kubectl apply -f canary-app/k8s/namespace.yaml
kubectl apply -f canary-app/istio/
kubectl apply -f canary-app/k8s/service.yaml
kubectl apply -f canary-app/k8s/rollout-simple.yaml

# Actualizar imagen (trigger canary rollout)
kubectl argo rollouts set image canary-demo \
  canary-demo=226633502530.dkr.ecr.us-east-1.amazonaws.com/canary-demo:v2.0.0 \
  -n canary-demo

# Ver progreso del rollout
kubectl argo rollouts get rollout canary-demo -n canary-demo --watch
```
