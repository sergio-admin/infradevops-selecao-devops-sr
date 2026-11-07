# Vaga Analista DevOps Sênior — Desafio Técnico

## 📌 Considerações Gerais

Use **este repositório como base** do projeto: faça um **fork** (GitHub/GitLab) e **publique todos os commits** no seu fork. Queremos ver seu fluxo de trabalho (commits pequenos, mensagens claras, PR/MR).

Registre tudo:
- Testes executados e resultados.
- Ideias que faria com mais tempo (e como implementaria).
- Decisões técnicas e seus porquês.
- Arquiteturas tentadas e por que foram alteradas/abandonadas.

Crie `COMMENTS.md` ou `HISTORY.md` para registrar decisões e experimentos.

> **Transparência:** no `README`, inclua se usou ferramentas de IA, templates/boilerplates e **quais**; cite referências e **tempo aproximado** gasto.

---

## 🎯 Objetivo

Entregar uma solução **completa** que contemple:
- **Desenvolvimento** de uma **pequena API REST** (obrigatório) em **Python, Node ou Go**.
- **Infraestrutura como Código (IaC)**.
- **CI/CD**.
- **Execução exclusivamente em nuvem:** **AWS ou GCP** (escolha **uma** e padronize toda a solução).

---

## ☁️ Ambiente (escolha **AWS** ou **GCP**)

### AWS
- **Rede:** VPC com subnets públicas/privadas e NAT Gateway.
- **Compute:** EKS (preferencial) ou ECS Fargate.
- **Banco:** Amazon RDS (Postgres/MySQL) em subnets privadas, sem exposição pública.
- **Segredos:** AWS Secrets Manager ou SSM Parameter Store (+ External Secrets).
- **Identidade:** IAM com **least privilege**; roles para workloads (IRSA no EKS).

### GCP
- **Rede:** VPC com subnets regionais e Cloud NAT.
- **Compute:** GKE (Autopilot/Standard; preferencial) ou GCE.
- **Banco:** Cloud SQL (Postgres/MySQL) com **Private Service Connect**; sem IP público.
- **Segredos:** Secret Manager (+ External Secrets).
- **Identidade:** Workload Identity no GKE; **least privilege** em IAM.

> **Custo:** use tamanhos mínimos e, quando possível, *free tier*. Documente escolhas para evitar custos supérfluos.

---

## 📂 O Problema (API obrigatória)

Você deve **desenvolver** uma **API de Comentários** (backend) em **Python, Node ou Go**, contendo ao menos:

- `POST /api/comment/new` — inserir comentário (`email`, `comment`, `content_id`).
- `GET /api/comment/list/{id}` — listar comentários por matéria (`content_id`).
- `GET /health` — health check (para probes).
- `/metrics` — métricas no padrão Prometheus.

**Persistência obrigatória** em **banco relacional gerenciado (Postgres ou MySQL)** no **RDS (AWS)** ou **Cloud SQL (GCP)**.  

⚠️ Alternativas (ex.: SQLite) só serão aceitas com justificativa em `COMMENTS.md`.

---

## 🔧 Tarefas Técnicas

### 1) Obrigatório
- **API** em Python/Node/Go com endpoints e persistência em banco gerenciado.  
- **Container** com Dockerfile slim, rodando como usuário não-root.  
- **IaC** (Terraform) para rede, compute e banco.  
- **Pipeline CI/CD** (GitLab CI ou GitHub Actions) com stages:  
  - build  
  - scan (Trivy + Checkov)  
  - package (push para registry)  
  - deploy (kubectl/helm/terraform apply)  
- **Probes** de liveness/readiness configurados.  
- **Evidência** de ambiente rodando em nuvem (pods em `Running` + endpoint acessível).  

### 2) Diferencial (Bonus Points)
- **Observabilidade avançada**  
  - Dashboard Grafana JSON versionado (`ops/grafana/`).  
  - Métricas extras (latência p50/p95/p99, RPS, erros 5xx, CPU/Mem, conexões DB).  
  - Alert rules versionadas (`ops/alerts/`).  

- **Resiliência**  
  - Horizontal Pod Autoscaler (HPA).  
  - Teste de rollback (`kubectl rollout undo` ou Helm history).  

- **Documentação extra**  
  - SLO/SLI formais definidos (ex.: latência p95 < 300ms, erro 5xx < 1%).  
  - Runbooks para incidentes (deploy, rollback, restore do banco).  

---

## 📑 Entregáveis

1. **Repositório** com:  
   - Código da API e testes.  
   - IaC (`infra/terraform`).  
   - Manifests K8s/Helm chart.  
   - Pipeline CI/CD.  
2. **README.md** com:  
   - Como rodar a API localmente (para dev).  
   - Como provisionar e fazer deploy na nuvem escolhida.  
   - Como acessar métricas e dashboard.  
   - Gestão de segredos usada.  
   - Tempo gasto, recursos/IA utilizados.  
3. **COMMENTS.md/HISTORY.md** com:  
   - Decisões, trade-offs, experimentos.  
   - Testes realizados.  
   - Ideias de evolução.  

---

## 🧪 Critérios de Aceite (DoD)

### Obrigatório
- API funcionando com persistência em DB gerenciado.  
- Ambiente em nuvem rodando (EKS/ECS/GKE/GCE + RDS/CloudSQL).  
- Pipelines de CI/CD executando todas as etapas.  
- Probes configurados e passando.  
- Scans (Trivy + Checkov) no pipeline.  

### Diferencial
- Dashboard Grafana JSON e alert rules versionados.  
- Métricas avançadas (p95/p99, CPU/Mem, DB).  
- HPA funcionando.  
- Rollback testado.  
- SLO/SLI documentados.  
- Runbooks para operações críticas.  

---

## 🕒 Prazo
**7 dias corridos.** Use tamanhos mínimos e free tier quando possível; documente custos estimados e medidas de economia.


---

## ✅ Apresentação Final (obrigatória)

Faça uma apresentação cobrindo:
- Arquitetura na nuvem escolhida e racional das decisões.  
- Demonstração do pipeline e do deploy.  
- API rodando: chamadas de exemplo + métricas.  
- Dashboard e alertas (se implementados).  
- Próximos passos e melhorias.  
