# SLO / SLI — API de Comentários

## SLIs (o que medimos)

| SLI | Definição | Query (PromQL) |
|---|---|---|
| Disponibilidade | Proporção de requisições sem erro 5xx | `1 - sum(rate(http_requests_total{namespace="comments",status="5xx"}[5m])) / sum(rate(http_requests_total{namespace="comments"}[5m]))` |
| Latência | Percentil 95 do tempo de resposta | `histogram_quantile(0.95, sum(rate(http_request_duration_highr_seconds_bucket{namespace="comments"}[5m])) by (le))` |

## SLOs (os objetivos)

| SLO | Objetivo | Janela |
|---|---|---|
| Erros 5xx | **< 1%** das requisições (disponibilidade ≥ 99%) | 30 dias |
| Latência | **p95 < 300 ms** | 30 dias |

**Error budget:** 1% das requisições em 30 dias pode falhar. Se o orçamento estiver sendo consumido rápido, a prioridade passa de novas features para estabilidade.

## Alertas ligados aos SLOs

Definidos em `ops/alerts/comments-alerts.yaml`:

| Alerta | Condição | Severidade |
|---|---|---|
| CommentsApiHighErrorRate | 5xx > 1% por 5 min | critical |
| CommentsApiHighLatencyP95 | p95 > 300 ms por 5 min | warning |
| CommentsApiDown | Nenhum pod respondendo por 1 min | critical |
| CommentsApiPodRestarting | Mais de 2 restarts em 10 min | warning |
| CommentsApiHpaAtMax | HPA no máximo de réplicas por 10 min | warning |

## Medição real (teste de carga)

10 conexões simultâneas por 3 minutos no endpoint de listagem:

- 12.804 requisições, **0% de erro** → dentro do SLO
- **p95 = 209 ms** → dentro do SLO (folga de ~30%)
- p99 = 282 ms
