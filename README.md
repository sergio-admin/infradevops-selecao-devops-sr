# API de Comentários — Desafio DevOps 

API REST de comentários em Python (FastAPI) rodando no **Amazon EKS**, com banco **Amazon RDS MySQL** privado, infraestrutura em **Terraform**, pipeline **GitHub Actions** e observabilidade com **Prometheus + Grafana**.

> O enunciado original do desafio está em [DESAFIO.md](DESAFIO.md).
> Decisões, problemas encontrados e testes estão em [COMMENTS.md](COMMENTS.md).
> SLO/SLI em [docs/SLO.md](docs/SLO.md) e runbooks em [docs/RUNBOOKS.md](docs/RUNBOOKS.md).

## Arquitetura

```
GitHub Actions: build → scan (Trivy + Checkov) → package (ECR) → deploy (Helm)
        │
        ▼
AWS us-east-2 — VPC 10.0.0.0/16 (2 AZs)
 ├─ Subnets públicas:  Load Balancer · NAT Gateway (1)
 ├─ Subnets privadas:  EKS 1.35 (2 nós m7i-flex.large)
 │     ├─ namespace comments:          API (Deployment + HPA 2–5 + probes)
 │     ├─ namespace external-secrets:  External Secrets Operator (Pod Identity)
 │     └─ namespace monitoring:        Prometheus · Grafana · Alertmanager
 └─ Subnets de banco:  RDS MySQL 8.4 (sem IP público, só aceita os nós do EKS)

Senha do banco: gerada pelo RDS → Secrets Manager → External Secrets → Secret do K8s → pod
```

## Estrutura do repositório

| Pasta | Conteúdo |
|---|---|
| `app/` | API, testes, Dockerfile e docker-compose |
| `infra/terraform/` | VPC, EKS, RDS, ECR, IAM |
| `helm/comments-api/` | Chart da API (Deployment, Service, HPA, ExternalSecret, ServiceMonitor) |
| `ops/` | Valores do kube-prometheus-stack, dashboard Grafana (`grafana/`) e alertas (`alerts/`) |
| `.github/workflows/` | Pipeline CI/CD |
| `docs/` | SLO/SLI e runbooks |

## Endpoints

| Método | Rota | Descrição |
|---|---|---|
| POST | `/api/comment/new` | Cria comentário (`email`, `comment`, `content_id`) |
| GET | `/api/comment/list/{content_id}` | Lista comentários da matéria |
| GET | `/health` | Liveness (processo vivo) |
| GET | `/ready` | Readiness (testa conexão com o banco) |
| GET | `/metrics` | Métricas Prometheus |

```bash
curl -X POST http://ENDERECO/api/comment/new -H "Content-Type: application/json" -d '{"email":"a@b.com","comment":"teste","content_id":1}'
curl http://ENDERECO/api/comment/list/1
```

## Rodar localmente (dev)

Requisitos: Docker.

```bash
cd app
docker compose up -d --build
curl http://localhost:8000/health
docker compose down
```

Testes (sem precisar de Python instalado):

```bash
cd app
docker run --rm -v ${PWD}:/app -w /app python:3.13-slim sh -c "pip install -q -r requirements-dev.txt && pytest -v"
```

## Provisionar e fazer deploy na AWS

Requisitos: AWS CLI, Terraform, kubectl, Helm e Docker, com credenciais AWS de administrador configuradas.

### 1. Infraestrutura

```bash
cd infra/terraform
terraform init
terraform apply
aws eks update-kubeconfig --region us-east-2 --name comments
kubectl get nodes
```

### 2. Componentes de plataforma

```bash
helm repo add external-secrets https://charts.external-secrets.io
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm install external-secrets external-secrets/external-secrets -n external-secrets --create-namespace --wait
helm install monitoring prometheus-community/kube-prometheus-stack -n monitoring --create-namespace -f ops/monitoring-values.yaml --wait --timeout 10m
kubectl create configmap comments-dashboard -n monitoring --from-file=ops/grafana/comments-dashboard.json
kubectl label configmap comments-dashboard -n monitoring grafana_dashboard=1
kubectl apply -f ops/alerts/comments-alerts.yaml
```

### 3. Pipeline

1. Gerar a chave do usuário do pipeline: `aws iam create-access-key --user-name comments-github-actions`
2. Cadastrar em **Settings → Secrets and variables → Actions**: `AWS_ACCESS_KEY_ID` e `AWS_SECRET_ACCESS_KEY`
3. Ajustar em `helm/comments-api/values.yaml` os valores `database.host` e `database.secretArn` com a saída de `terraform output`
4. Fazer push na `main`: o pipeline testa, escaneia, publica a imagem e faz o deploy

```bash
kubectl get pods,svc,hpa -n comments
```

## Métricas e dashboard

```bash
kubectl port-forward -n monitoring svc/monitoring-grafana 3000:80
```

Acessar `http://localhost:3000` → **Dashboards → Comments API**. Painéis: RPS, erros 5xx, latência p50/p95/p99, respostas por status, réplicas do HPA, CPU e memória por pod. Alertas em **Alerting → Alert rules** (definidos em `ops/alerts/`).

Prometheus (opcional): `kubectl port-forward -n monitoring svc/monitoring-kube-prometheus-prometheus 9090`

## Gestão de segredos

- A senha do banco é **gerada e armazenada pelo próprio RDS** no AWS Secrets Manager (`manage_master_user_password`). Ninguém a digita ou vê.
- O **External Secrets Operator** lê esse segredo e cria o Secret `comments-db` no namespace da API.
- O External Secrets se autentica via **EKS Pod Identity**, com uma role IAM que só permite ler **aquele** segredo.
- Nenhuma senha está no código, no repositório ou no state do Terraform.
- Credenciais do pipeline ficam em GitHub Secrets (ver trade-off em COMMENTS.md).

## CI/CD

| Stage | O que faz | Quando |
|---|---|---|
| build | Testes (pytest) e build da imagem | push e PR |
| scan | Trivy (relata HIGH, bloqueia CRITICAL) e Checkov (Terraform, Dockerfile, workflow) | push e PR |
| package | Push da imagem no ECR com tag = SHA do commit | push na main |
| deploy | `helm upgrade --install` com a nova tag e verificação do rollout | push na main |

## Destruir o ambiente

Ver [docs/RUNBOOKS.md](docs/RUNBOOKS.md#5-destruir-o-ambiente). A ordem importa: remover os releases Helm antes do `terraform destroy`, porque o Load Balancer é criado pelo Kubernetes.

## Transparência

- **Uso de IA:** Claude (Anthropic) foi usado para planejamento, geração do código da API, Terraform, Helm chart, pipeline, dashboard, alertas e documentação. Todo o conteúdo foi revisado, executado e validado por mim, e os problemas encontrados durante a execução estão registrados em COMMENTS.md.
- **Templates/módulos de terceiros:** módulos Terraform oficiais da comunidade `terraform-aws-modules/vpc` e `terraform-aws-modules/eks`; charts Helm `external-secrets` e `kube-prometheus-stack`.
- **Bibliotecas:** FastAPI, Uvicorn, PyMySQL, prometheus-fastapi-instrumentator, pytest.
- **Referências:** documentação da AWS (EKS, RDS, Pod Identity, Secrets Manager), Terraform Registry, External Secrets Operator, Prometheus Operator, Helm.
- **Tempo aproximado gasto:** 8 horas.
