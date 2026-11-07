# Decisões, problemas e testes

## 1. Decisões técnicas

| Tema | Escolha | Por quê |
|---|---|---|
| Nuvem | AWS | Free tier com créditos e familiaridade com o ecossistema |
| Linguagem | Python + FastAPI | Código curto e legível; validação de entrada automática (Pydantic) |
| Acesso ao banco | SQL puro com PyMySQL | Fácil de ler e explicar; queries parametrizadas evitam SQL injection |
| Banco | RDS MySQL 8.4, db.t4g.micro | MySQL 8.0 já está em suporte estendido (cobrado à parte); menor instância disponível |
| Compute | EKS (preferencial no desafio) | Permite HPA, rollback via Helm e os demais diferenciais |
| IaC | Terraform com módulos `terraform-aws-modules` | Padrão de mercado; menos código próprio para manter |
| Deploy | Helm chart próprio | Versionamento de releases e rollback nativo (`helm history` / `helm rollback`) |
| Exposição | Service LoadBalancer | Sem componente extra (ALB Controller); suficiente para o escopo |
| Segredos | RDS managed secret + External Secrets | Senha nunca passa por pessoas, código ou state |
| Tag da imagem | SHA do commit + ECR imutável | Rastreabilidade do código até o pod; rollback confiável |
| Probes | `/health` (liveness) separado de `/ready` (readiness) | Se o banco cair, o pod sai do balanceador mas não entra em loop de restart |
| Conexão com o banco | TLS (PyMySQL `ssl=`) | Tráfego até o RDS criptografado, mesmo dentro da VPC |
| Container | `python:3.13-slim`, UID 10001, filesystem read-only, sem capabilities | Superfície de ataque mínima |
| Observabilidade | kube-prometheus-stack + ServiceMonitor | Stack padrão; dashboard e alertas versionados como código |

## 2. Adaptações por restrições da conta AWS (Free plan)

A conta usada está no **AWS Free plan**, que aplica Service Control Policies (SCPs) bloqueando alguns recursos. Optei por adaptar a solução em vez de migrar para o plano pago, e registro aqui cada substituição:

| Pedido / planejado | Usado | Motivo |
|---|---|---|
| Região us-east-1 | **us-east-2** | SCP nega chamadas em us-east-1 (`ec2:DescribeAvailabilityZones` negado) |
| IRSA | **EKS Pod Identity** | SCP nega `iam:CreateOpenIDConnectProvider`. Pod Identity é o sucessor do IRSA recomendado pela AWS, não precisa de provedor OIDC e mantém o least privilege |
| OIDC GitHub → AWS | **Usuário IAM dedicado** com chave em GitHub Secrets | Mesmo bloqueio de OIDC. Mitigação: permissão mínima (push só neste ECR, `DescribeCluster` só neste cluster) e chave rotacionável |
| Nós t3.medium | **m7i-flex.large** | Free plan só permite tipos elegíveis (`free-tier-eligible=true`); m7i-flex.large tem 2 vCPU e 8 GB |

Em uma conta paga, os três últimos itens voltariam ao desenho original (IRSA e OIDC), sem chaves estáticas.

## 3. Problemas encontrados e soluções

| Problema | Diagnóstico | Solução |
|---|---|---|
| `terraform plan` falhando com "explicit deny in a service control policy" | Testei a mesma chamada em us-east-1 e us-east-2: só us-east-2 é permitida | Padronização em us-east-2 |
| `apply` falhando ao criar provedores OIDC e o node group | SCP do Free plan + tipo de instância não elegível | Pod Identity, usuário IAM para o pipeline, m7i-flex.large |
| `docker login` no ECR retornando 400 | O pipe (`\|`) do Windows PowerShell 5.1 altera a codificação do token | Passar o token por variável |
| `helm upgrade` falhando após o teste de carga: conflito em `.spec.replicas` | Helm 4 usa server-side apply; depois que o HPA escalou, ele virou "dono" do campo `replicas`, e o chart tentava sobrescrevê-lo | Remover `replicas` do Deployment; o HPA (com `minReplicas: 2`) passa a ser o único dono. Teria quebrado o pipeline no próximo deploy após qualquer escalonamento |
| API não subia no `docker compose` local | No primeiro start, a imagem do MySQL sobe um servidor temporário sem rede; o healthcheck (`mysqladmin ping` via socket) já passava nele, e a API conectava cedo demais e parava | Healthcheck via TCP (`127.0.0.1`) com o usuário da aplicação + `restart: on-failure` na API |

## 4. Testes executados e resultados

| Teste | Resultado |
|---|---|
| Ambiente local (`docker compose`): health, ready, POST e GET | Todos OK após a correção do healthcheck |
| Testes unitários (pytest, 6 casos: health, criar, email inválido → 422, listar, readiness sem banco → 503, métricas) | **6 passed**, localmente e no pipeline |
| Infra: nós e pods de sistema | 2 nós `Ready`, todos os pods de sistema `Running` |
| Segredos: ExternalSecret | `SecretSynced` / `Ready=True` (Pod Identity + Secrets Manager funcionando) |
| API na nuvem: `/health`, `/ready`, POST e GET via Load Balancer | Todos OK; comentário gravado e lido do RDS |
| Pipeline completo (build, scan, package, deploy) | 4 stages verdes em ~2 min; imagem em produção com tag = SHA do commit |
| Carga: `hey`, 10 conexões, 3 minutos, endpoint de listagem (com banco) | **12.804 requisições, 100% status 200, 71 req/s, p50 114 ms, p95 209 ms, p99 282 ms** |
| HPA | 2 → 4 → 5 réplicas em ~1 minuto com CPU acima de 70%; retorno a 2 após a janela de estabilização |
| Rollback: deploy com imagem inexistente | Pod novo em `ErrImagePull`, **pods antigos continuaram atendendo** (API respondendo); `helm rollback` restaurou a revisão anterior |
| Dashboard e alertas | Dashboard com dados reais; regras de alerta carregadas no Prometheus |

## 5. Trade-offs assumidos (laboratório vs produção)

| No laboratório | Em produção |
|---|---|
| 1 NAT Gateway | 1 por AZ |
| RDS Single-AZ, backup de 1 dia, sem proteção contra deleção | Multi-AZ, retenção maior, `deletion_protection` |
| State do Terraform local | Backend S3 com lock |
| Usuário do pipeline com `AmazonEKSClusterAdminPolicy` | Permissão restrita ao namespace da aplicação |
| Checkov com `soft_fail` | Bloqueante, com exceções justificadas |
| Load Balancer HTTP, sem TLS | ALB + certificado ACM (HTTPS) |
| Grafana via port-forward, senha simples | Exposto com SSO |
| External Secrets e monitoramento instalados manualmente via Helm | Gerenciados por GitOps (Argo CD) ou Terraform |

## 6. Ideias de evolução (e como implementaria)

1. **Pool de conexões com o banco.** O teste de carga mostrou que cada requisição abre uma conexão TLS nova, e isso domina a latência e a CPU. Implementaria com um pool (ex.: SQLAlchemy `create_engine` com `pool_size`) e mediria de novo no mesmo teste.
2. **Métricas do banco.** Conexões ativas e uso de CPU do RDS via `prometheus-cloudwatch-exporter` ou métricas de pool expostas pela própria API.
3. **OIDC no GitHub Actions e IRSA**, em conta paga, eliminando a chave estática.
4. **GitOps com Argo CD**, com o pipeline apenas atualizando a tag no repositório.
5. **HTTPS** com AWS Load Balancer Controller + ACM.
6. **Alertmanager integrado** a Slack/e-mail.
7. **Migrações de banco** com Alembic, em vez do `CREATE TABLE IF NOT EXISTS` na inicialização.
8. **Assinatura de imagem** (cosign) e política de admissão que só aceita imagens assinadas.
9. **Paginação** no endpoint de listagem e rate limiting.
10. **Cluster autoscaling** (Karpenter) para os nós acompanharem o HPA.

## 7. Custos estimados e economia

Estimativa aproximada em us-east-2, ambiente ligado 24h:

| Item | US$/dia (aprox.) |
|---|---|
| EKS control plane | 2,40 |
| 2× m7i-flex.large | 4,50 |
| NAT Gateway | 1,10 |
| Load Balancer | 0,60 |
| RDS db.t4g.micro + 20 GB | 0,50 |
| IPs públicos, KMS, CloudWatch, Secrets Manager | 0,50 |
| **Total** | **~9,60** |

Medidas de economia: 1 NAT em vez de 2, menor classe de RDS, sem Multi-AZ, retenção do Prometheus de 2 dias, todo o ambiente recriável por código e destruído após a apresentação. Custos cobertos pelos créditos do Free plan.
