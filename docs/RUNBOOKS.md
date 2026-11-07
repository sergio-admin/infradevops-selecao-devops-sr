# Runbooks

Pré-requisito para todos: `aws eks update-kubeconfig --region us-east-2 --name comments`

## 1. Deploy

**Caminho normal:** merge/push na `main`. O pipeline testa, escaneia, publica a imagem com a tag do commit e roda `helm upgrade`.

Verificação:

```bash
kubectl get pods,hpa -n comments
helm history comments -n comments
kubectl get deployment comments -n comments -o jsonpath="{.spec.template.spec.containers[0].image}"
```

**Deploy manual (pipeline indisponível):**

```bash
helm upgrade comments ./helm/comments-api -n comments --reuse-values --set image.tag=SHA_DO_COMMIT
kubectl rollout status deployment/comments -n comments
```

## 2. Rollback

Sintomas: pods novos em erro (`ErrImagePull`, `CrashLoopBackOff`), aumento de 5xx ou de latência após um deploy.

```bash
helm history comments -n comments
helm rollback comments -n comments
kubectl rollout status deployment/comments -n comments
```

Para voltar a uma revisão específica: `helm rollback comments NUMERO -n comments`.

Alternativa pelo Kubernetes: `kubectl rollout undo deployment/comments -n comments`.

Depois do rollback, corrigir o problema no código e fazer um novo push. O próximo deploy do pipeline substitui a revisão de rollback.

**Testado:** deploy com imagem inexistente → pods antigos seguiram atendendo → `helm rollback` restaurou a revisão anterior.

## 3. Restore do banco

O RDS tem backup automático com retenção de 1 dia, o que permite restaurar para qualquer ponto nesse período (point-in-time restore). O restore sempre cria uma **instância nova**.

```bash
aws rds describe-db-instances --db-instance-identifier comments --query "DBInstances[0].LatestRestorableTime"
aws rds restore-db-instance-to-point-in-time --source-db-instance-identifier comments --target-db-instance-identifier comments-restore --restore-time 2026-11-07T15:00:00Z --db-instance-class db.t4g.micro --db-subnet-group-name comments --vpc-security-group-ids ID_DO_SG_RDS --no-publicly-accessible --manage-master-user-password
aws rds wait db-instance-available --db-instance-identifier comments-restore
aws rds describe-db-instances --db-instance-identifier comments-restore --query "DBInstances[0].[Endpoint.Address,MasterUserSecret.SecretArn]"
```

Apontar a aplicação para a nova instância atualizando `database.host` e `database.secretArn` em `helm/comments-api/values.yaml` e fazendo push (ou `helm upgrade` com `--set`). Se o segredo mudou, conceder leitura à role `comments-external-secrets` para o novo ARN.

Validar:

```bash
kubectl get externalsecret,pods -n comments
curl http://ENDERECO/ready
curl http://ENDERECO/api/comment/list/1
```

Antes de mudanças arriscadas, tirar um snapshot manual:

```bash
aws rds create-db-snapshot --db-instance-identifier comments --db-snapshot-identifier comments-antes-da-mudanca
```

**Status:** procedimento documentado, não executado no laboratório por tempo e custo.

## 4. Incidente: API fora do ar ou com erros

```bash
kubectl get pods -n comments
kubectl describe pod -n comments -l app=comments
kubectl logs -n comments -l app=comments --tail=50
kubectl get externalsecret -n comments
aws rds describe-db-instances --db-instance-identifier comments --query "DBInstances[0].DBInstanceStatus"
```

| Sintoma | Causa provável | Ação |
|---|---|---|
| Pods `0/1` (readiness falhando) | Banco inacessível ou senha errada | Ver status do RDS e do ExternalSecret |
| `CrashLoopBackOff` | Erro na aplicação ou na inicialização | Ver logs; rollback se veio de um deploy |
| `ErrImagePull` | Tag inexistente no ECR | Rollback |
| ExternalSecret não sincroniza | Permissão da role ou segredo trocado | `kubectl describe externalsecret -n comments` |
| Latência alta | Saturação de CPU ou banco | Ver dashboard (CPU por pod, réplicas do HPA) |

## 5. Destruir o ambiente

A ordem importa: o Load Balancer é criado pelo Kubernetes, não pelo Terraform. Se não for removido antes, o `terraform destroy` trava ao apagar a VPC.

```bash
helm uninstall comments -n comments
helm uninstall monitoring -n monitoring
helm uninstall external-secrets -n external-secrets
kubectl get svc -A
cd infra/terraform
terraform destroy
```

Conferir que nenhum `Service` do tipo LoadBalancer sobrou antes do `terraform destroy`. Depois, apagar as chaves do usuário `comments-github-actions`, se ainda existirem.
