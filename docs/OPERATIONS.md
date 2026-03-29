# Manual de Operações — Oute Muscle

Este manual cobre tudo que um operador, engenheiro de suporte ou administrador de sistema precisa saber para manter a plataforma funcionando.

**Audiência**: SRE, DevOps, engenheiros de suporte, administradores de tenant.

---

## Índice

1. [Visão geral do sistema](#visão-geral-do-sistema)
2. [Ambientes e URLs](#ambientes-e-urls)
3. [Monitoramento e observabilidade](#monitoramento-e-observabilidade)
4. [Health checks](#health-checks)
5. [Logs](#logs)
6. [Alertas e resposta a incidentes](#alertas-e-resposta-a-incidentes)
7. [Administração de banco de dados](#administração-de-banco-de-dados)
8. [Administração de tenants](#administração-de-tenants)
9. [Workers e background jobs](#workers-e-background-jobs)
10. [Segredos e credenciais](#segredos-e-credenciais)
11. [Escalabilidade e capacidade](#escalabilidade-e-capacidade)
12. [Procedimentos de manutenção](#procedimentos-de-manutenção)
13. [Troubleshooting](#troubleshooting)
14. [Runbook de rollback](#runbook-de-rollback)
15. [Referência de recursos GCP](#referência-de-recursos-gcp)

---

## Visão geral do sistema

```
GitHub PR → GitHub Actions (CI) → POST /v1/scans → Cloud Run (API)
                                                          │
                                              ┌───────────┼───────────┐
                                              │           │           │
                                          Semgrep      pgvector   Vertex AI
                                          (L1 rules) (L2 RAG)  (L3 synthesis)
                                              │           │           │
                                          Cloud SQL (PostgreSQL 16 + pgvector)
```

**Stack de produção:**
- API: Cloud Run (`oute-prod-api`), mín 1 instância, máx 20
- DB: Cloud SQL `oute-postgres`, PostgreSQL 16, instância `db-f1-micro`, database `oute_muscle_prod`, user `muscle_app`
- LLM: Vertex AI (Gemini 2.5 Flash/Pro) + Anthropic Claude Sonnet 4
- Workers: background tasks rodando dentro do processo da API (asyncio)
- Imagens: Artifact Registry `oute-prod-docker`
- Estado Terraform: `gs://oute-terraform-state/oute-muscle/prod/`

---

## Ambiente e URL

Ambiente único: **prod** — Trunk-Based CD. Merge em `main` deploya automaticamente.

| Ambiente | API URL | Trigger de deploy |
|----------|---------|-------------------|
| Prod | `https://oute-prod-api-ujzimacvza-uc.a.run.app` | Merge em `main` |

**Console GCP**: https://console.cloud.google.com/run?project=oute-488706

**GitHub Actions**: https://github.com/renatobardi/oute-muscle/actions

---

## Monitoramento e observabilidade

### Cloud Run metrics (GCP Console)

Acesse: **Cloud Run → oute-prod-api → Metrics**

Métricas críticas a acompanhar:

| Métrica | Alerta sugerido | Significado |
|---------|----------------|-------------|
| Request latency (p99) | > 3s | API lenta — verificar DB ou LLM |
| Request count | Spike > 10x baseline | Possível abuso ou load incomum |
| Instance count | Máximo atingido (20) | Necessidade de escalar limites |
| Container startup latency | > 30s | Cold start excessivo |
| Error rate (5xx) | > 1% | Falhas sistêmicas |

### Cloud SQL metrics

Acesse: **Cloud SQL → oute-postgres → Monitoring**

| Métrica | Alerta sugerido |
|---------|----------------|
| CPU utilization | > 80% por 5 min |
| Memory usage | > 85% |
| Connections | > 80% do max_connections |
| Disk usage | > 80% |
| Query latency (p99) | > 500ms |

### Logs-based metrics (criar no GCP Logging)

```
# Erros 5xx
resource.type="cloud_run_revision"
resource.labels.service_name="oute-prod-api"
httpRequest.status>=500

# Slow queries
resource.type="cloud_run_revision"
jsonPayload.duration_ms>2000

# Rate limit hits
resource.type="cloud_run_revision"
jsonPayload.event="rate_limit_exceeded"
```

---

## Health checks

### Endpoints

| Endpoint | Uso | Resposta esperada |
|----------|-----|------------------|
| `GET /health/live` | Cloud Run liveness probe | 200 sempre (processo vivo) |
| `GET /health/ready` | Cloud Run readiness probe | 200 se DB + LLM OK; 503 se não |
| `GET /health/startup` | Cloud Run startup probe | 200 após boot completo; 503 se não |

### Verificação rápida

```bash
# Prod — liveness
curl https://oute-prod-api-ujzimacvza-uc.a.run.app/health/live

# Readiness (verifica DB + LLM)
curl https://oute-prod-api-ujzimacvza-uc.a.run.app/health/ready
```

**Resposta saudável do `/health/ready`:**
```json
{
  "status": "ok",
  "version": "0.1.0",
  "uptime_seconds": 3600.5,
  "checks": [
    {"name": "database", "status": "ok", "latency_ms": 2.1},
    {"name": "llm_router", "status": "ok", "latency_ms": 0.1}
  ]
}
```

**Resposta degradada:**
```json
{
  "status": "error",
  "checks": [
    {"name": "database", "status": "error", "detail": "Connection refused"},
    {"name": "llm_router", "status": "ok"}
  ]
}
```

---

## Logs

### Estrutura dos logs

Todos os logs são JSON estruturado (structlog), compatível com Cloud Logging.

Campos padrão em todo log:

```json
{
  "timestamp": "2026-03-28T21:00:00Z",
  "level": "info",
  "event": "mensagem do log",
  "correlation_id": "req-uuid",
  "tenant_id": "tenant-uuid",
  "user_id": "user-uuid"
}
```

### Consultas no Cloud Logging

```bash
# Todos os erros de prod (últimos 60 min)
gcloud logging read \
  'resource.type="cloud_run_revision"
   resource.labels.service_name="oute-prod-api"
   severity>=ERROR' \
  --limit=100 --freshness=1h \
  --format='json' | jq '.[].jsonPayload'

# Erros de um tenant específico
gcloud logging read \
  'resource.type="cloud_run_revision"
   resource.labels.service_name="oute-prod-api"
   jsonPayload.tenant_id="TENANT_UUID"
   severity>=ERROR' \
  --limit=50

# Requests de um correlation_id específico (para rastrear um request completo)
gcloud logging read \
  'resource.type="cloud_run_revision"
   jsonPayload.correlation_id="REQ_UUID"' \
  --limit=50

# Scans com latência > 5s
gcloud logging read \
  'resource.type="cloud_run_revision"
   resource.labels.service_name="oute-prod-api"
   jsonPayload.event="scan_completed"
   jsonPayload.duration_ms>5000' \
  --limit=20
```

### Níveis de log

| Nível | Quando usar / o que significa |
|-------|------------------------------|
| `DEBUG` | Fluxo interno — desabilitado em prod |
| `INFO` | Operações normais (scan concluído, regra criada, usuário convidado) |
| `WARNING` | Situação incomum mas não fatal (retry, degraded dependency) |
| `ERROR` | Falha operacional — requer atenção |
| `CRITICAL` | Falha sistêmica — requer ação imediata |

---

## Alertas e resposta a incidentes

### Severity levels

| Severity | Definição | SLA de resposta |
|----------|-----------|----------------|
| P1 | Plataforma inteira fora / 100% dos scans falhando | 15 minutos |
| P2 | Feature crítica degradada (L1 failing, DB connection dropping) | 1 hora |
| P3 | Feature não-crítica com problema (L3 synthesis, advisories) | 4 horas |
| P4 | Lentidão / problema cosmético | Próximo dia útil |

### Runbook: API retornando 5xx em massa

```bash
# 1. Verificar se o container está respondendo
curl https://oute-prod-api-ujzimacvza-uc.a.run.app/health/live

# 2. Ver logs de erro recentes
gcloud logging read \
  'resource.type="cloud_run_revision"
   resource.labels.service_name="oute-prod-api"
   severity>=ERROR' \
  --limit=20 --freshness=10m --format=json | jq '.[].jsonPayload'

# 3. Ver revisões ativas
gcloud run revisions list \
  --service=oute-prod-api \
  --region=us-central1 \
  --limit=5

# 4. Se o problema começou após um deploy, fazer rollback
gcloud run services update-traffic oute-prod-api \
  --region=us-central1 \
  --to-revisions=oute-prod-api-XXXXXX-xxx=100

# 5. Verificar health novamente
curl https://oute-prod-api-ujzimacvza-uc.a.run.app/health/ready
```

### Runbook: DB inacessível

```bash
# 1. Verificar status da instância Cloud SQL
gcloud sql instances describe oute-postgres --format=json | jq '.state'

# 2. Ver métricas de conexões
gcloud sql instances describe oute-postgres \
  --format="value(settings.databaseFlags)"

# 3. Verificar se Cloud Run consegue alcançar o DB
# (via /health/ready — verifica DB)
curl https://oute-prod-api-ujzimacvza-uc.a.run.app/health/ready

# 4. Reiniciar instância Cloud SQL (último recurso)
gcloud sql instances restart oute-postgres

# 5. Se o problema for de conexões esgotadas, forçar recycle das instâncias Cloud Run
gcloud run services update oute-prod-api \
  --region=us-central1 \
  --max-instances=20   # trigger revision update
```

### Runbook: Vertex AI / LLM indisponível

O L3 synthesis e o ingest-url dependem do Vertex AI. Se estiver fora:

```bash
# 1. Verificar status do Vertex AI
gcloud ai operations list --region=us-central1 2>/dev/null

# 2. Checar status page da GCP
# https://status.cloud.google.com/

# 3. O sistema degrada graciosamente:
#    - L1 continua funcionando (sem LLM)
#    - L2 RAG continua funcionando (sem LLM)
#    - L3 synthesis falha com erro — candidatos ficam com status "failed"
#    - /incidents/ingest-url retorna 503

# 4. Workers de synthesis têm retry automático com backoff
#    Candidatos com status "failed" podem ser re-tentados manualmente
POST /v1/synthesis/candidates/{id}/retry
```

---

## Administração de banco de dados

### Conectar ao banco (prod)

```bash
# Via Cloud SQL Auth Proxy (recomendado para acesso ad-hoc)
# 1. Instalar o proxy
curl -o cloud-sql-proxy https://storage.googleapis.com/cloud-sql-connectors/cloud-sql-proxy/v2.11.4/cloud-sql-proxy.linux.amd64
chmod +x cloud-sql-proxy

# 2. Conectar
./cloud-sql-proxy oute-488706:us-central1:oute-postgres --port=5433

# 3. Em outro terminal
psql "host=127.0.0.1 port=5433 dbname=oute_muscle_prod user=muscle_app"
# (senha em: gcloud secrets versions access latest --secret=oute-prod-db-password)
```

### Migrations

```bash
# Aplicar migrations pendentes
make migrate-up

# Verificar estado atual
alembic -c packages/db/alembic.ini current

# Histórico de migrations aplicadas
alembic -c packages/db/alembic.ini history

# Rollback de uma migration
make migrate-down
```

### Migrations forçadas (prod — use com cuidado)

As migrations rodam automaticamente no CI/CD antes do deploy. Para rodar manualmente em prod:

```bash
# Via Cloud Run Job ou via proxy
DATABASE_URL="postgresql+asyncpg://muscle_app:PASSWORD@127.0.0.1:5433/oute_muscle_prod" \
  alembic -c packages/db/alembic.ini upgrade head
```

### Tabelas principais

| Tabela | Descrição | Isolamento |
|--------|-----------|-----------|
| `tenants` | Organizações | Sem RLS (tabela mestre) |
| `users` | Usuários por tenant | RLS por `tenant_id` |
| `incidents` | Incidentes documentados, embedding vector | RLS por `tenant_id` |
| `semgrep_rules` | Regras Semgrep (yaml_content, test_file) | RLS por `tenant_id` |
| `scans` | Histórico de scans, risk_score | RLS por `tenant_id` |
| `findings` | Findings por scan | RLS por `tenant_id` |
| `advisories` | Resultados L2 RAG (confidence, reasoning) | RLS por `tenant_id` |
| `synthesis_candidates` | Candidatos L3 pendentes | RLS por `tenant_id` |
| `audit_log_entries` | Trilha de auditoria (changes JSONB) | RLS por `tenant_id` |

### Row-Level Security

Todas as tabelas de dados (exceto `tenants`) têm RLS ativo. O middleware seta `app.tenant_id` no início de cada request via `SET LOCAL`. Verificação:

```sql
-- Verificar RLS ativo
SELECT tablename, rowsecurity FROM pg_tables
WHERE schemaname = 'public' AND rowsecurity = true;

-- Simular query como tenant específico
SET app.tenant_id = 'TENANT_UUID';
SELECT * FROM incidents LIMIT 5;
RESET app.tenant_id;
```

### Queries úteis de administração

```sql
-- Tenants ativos (últimos 30 dias de scans)
SELECT t.id, t.name, t.plan, COUNT(s.id) as scans_30d
FROM tenants t
LEFT JOIN scans s ON s.tenant_id = t.id AND s.created_at > NOW() - INTERVAL '30 days'
GROUP BY t.id ORDER BY scans_30d DESC;

-- Regras com mais falsos positivos
SELECT r.id, r.rule_id, COUNT(f.id) as fp_count
FROM rules r
JOIN findings f ON f.rule_id = r.id AND f.status = 'false_positive'
GROUP BY r.id ORDER BY fp_count DESC LIMIT 20;

-- Candidatos de synthesis pendentes há mais de 24h
SELECT id, anti_pattern_hash, advisory_count, created_at
FROM synthesis_candidates
WHERE status = 'pending_review'
  AND created_at < NOW() - INTERVAL '24 hours'
ORDER BY created_at;

-- Tamanho das tabelas
SELECT relname, pg_size_pretty(pg_total_relation_size(relid))
FROM pg_catalog.pg_statio_user_tables
ORDER BY pg_total_relation_size(relid) DESC;
```

---

## Administração de tenants

### Ver tenants e planos

```bash
# Via API (admin interno — endpoint não exposto ao público ainda)
psql ... -c "SELECT id, name, plan, created_at FROM tenants ORDER BY created_at DESC LIMIT 20;"
```

### Alterar plano de um tenant

```sql
UPDATE tenants
SET plan = 'enterprise'  -- 'free', 'team', 'enterprise'
WHERE id = 'TENANT_UUID';
```

### Soft-delete de um tenant

Nunca fazer DELETE direto. Usar o campo `deleted_at`:

```sql
UPDATE tenants
SET deleted_at = NOW()
WHERE id = 'TENANT_UUID';
```

Isso impede o login mas preserva todos os dados para fins de auditoria.

### Audit log de um tenant

```bash
# Via API (Enterprise only)
curl https://oute-prod-api-ujzimacvza-uc.a.run.app/v1/audit-log \
  -H "X-API-Key: sk-..." \
  -G --data-urlencode "from=2026-03-01" --data-urlencode "per_page=200"

# Via banco
SELECT entity_type, action, actor_email, created_at, before, after
FROM audit_log
WHERE tenant_id = 'TENANT_UUID'
ORDER BY created_at DESC
LIMIT 100;
```

---

## Workers e background jobs

Os workers rodam dentro do processo da API (asyncio tasks). Em caso de crash do container, os jobs em andamento são interrompidos e re-tentados na próxima invocação.

| Worker | Arquivo | Função | Trigger |
|--------|---------|--------|---------|
| `synthesis` | `apps/api/src/workers/synthesis.py` | Gera candidatos L3 via Vertex AI, valida com `semgrep --test` | Cloud Tasks HTTP |
| `rag_worker` | `apps/api/src/workers/rag_worker.py` | Pipeline RAG L2: embed diff → vector search → LLM → Advisory | Cloud Run Job |
| `retention_purge` | `apps/api/src/workers/retention_purge.py` | Remove findings expirados (Free: 90d, Team: 365d, Enterprise: 730d) | Cloud Scheduler |
| `synthesis_archive` | `apps/api/src/workers/synthesis_archive.py` | Arquiva candidatos pendentes há mais de 30 dias | Cloud Scheduler |

### Monitorar workers

```bash
# Logs de um worker específico
gcloud logging read \
  'resource.type="cloud_run_revision"
   resource.labels.service_name="oute-prod-api"
   jsonPayload.worker="synthesis"' \
  --limit=50 --freshness=1h

# Candidatos de synthesis com falha
psql ... -c "SELECT id, failure_count, failure_reason, updated_at
             FROM synthesis_candidates
             WHERE status = 'failed'
             ORDER BY updated_at DESC LIMIT 20;"
```

### Retry manual de candidatos com falha

```bash
# Via API
POST /v1/synthesis/candidates/{id}/retry

# Em lote (via script)
for id in $(psql ... -t -c "SELECT id FROM synthesis_candidates WHERE status='failed'"); do
  curl -X POST ".../v1/synthesis/candidates/$id/retry" -H "X-API-Key: ..."
done
```

---

## Segredos e credenciais

### Secret Manager (GCP)

| Secret | Conteúdo | Usado por |
|--------|----------|-----------|
| `oute-prod-db-password` | Senha do `muscle_app` no Cloud SQL | Cloud Run (prod API) |

### Acessar um segredo

```bash
# Último valor
gcloud secrets versions access latest --secret=oute-prod-db-password

# Versão específica
gcloud secrets versions access 3 --secret=oute-prod-db-password
```

### Rotacionar a senha do banco

```bash
# 1. Gerar nova senha
NEW_PASS=$(openssl rand -base64 32)

# 2. Atualizar no PostgreSQL
psql ... -c "ALTER USER muscle_app PASSWORD '$NEW_PASS';"

# 3. Criar nova versão no Secret Manager
echo -n "$NEW_PASS" | gcloud secrets versions add oute-prod-db-password --data-file=-

# 4. Forçar nova revisão no Cloud Run para pegar a nova versão
gcloud run services update oute-prod-api \
  --region=us-central1 \
  --update-env-vars=SECRET_ROTATION=$(date +%s)  # trigger revision

# 5. Verificar health após rotação
curl https://oute-prod-api-ujzimacvza-uc.a.run.app/health/ready
```

### GitHub Actions — Workload Identity Federation

A autenticação CI/CD usa WIF — sem service account keys. Se o deploy falhar com erro de autenticação:

```bash
# Verificar provider
gcloud iam workload-identity-pools providers describe oute-prod-gh-provider \
  --workload-identity-pool=oute-prod-gh-pool \
  --location=global

# Verificar binding
gcloud iam service-accounts get-iam-policy \
  oute-prod-gh-actions@oute-488706.iam.gserviceaccount.com

# Re-executar bootstrap se necessário
bash scripts/deploy-bootstrap.sh prod
```

---

## Escalabilidade e capacidade

### Cloud Run scaling

```bash
# Ver configuração atual
gcloud run services describe oute-prod-api \
  --region=us-central1 \
  --format="value(spec.template.spec.containerConcurrency,spec.template.metadata.annotations)"

# Aumentar instâncias máximas
gcloud run services update oute-prod-api \
  --region=us-central1 \
  --max-instances=50

# Aumentar concorrência por instância (default: 80 requests/instância)
gcloud run services update oute-prod-api \
  --region=us-central1 \
  --concurrency=100
```

### Cloud SQL scaling

```bash
# Ver tier atual
gcloud sql instances describe oute-postgres --format="value(settings.tier)"

# Upgrade de tier (downtime de ~1 min)
gcloud sql instances patch oute-postgres \
  --tier=db-custom-2-7680  # 2 vCPU, 7.5 GB RAM

# Aumentar disco (sem downtime)
gcloud sql instances patch oute-postgres \
  --storage-size=50GB
```

### Limites de rate (configuráveis)

Os limites atuais estão hardcoded no middleware `rate_limit`. Para alterar:

1. Editar `apps/api/src/middleware/rate_limit.py`
2. Fazer commit e deploy

Limites atuais (hardcoded em `rate_limit.py`):

| Plano | Requests/min | Burst Limit | Burst Window |
|-------|-------------|-------------|--------------|
| Free | 30 | 60 | 10s |
| Team | 120 | 240 | 10s |
| Enterprise | 600 | 1200 | 10s |

---

## Procedimentos de manutenção

### Deploy de emergência (hotfix)

```bash
# 1. Criar branch de hotfix a partir do último tag de prod
git checkout v0.1.0
git checkout -b hotfix/descricao-do-problema

# 2. Aplicar fix, commit, push
git add ...
git commit -m "fix(api): descrição do problema"
git push origin hotfix/descricao-do-problema

# 3. Abrir PR para main, merjar após CI verde
# 4. Criar novo tag de patch
git tag v0.1.1
git push origin v0.1.1

# 5. Acompanhar deploy
gh run watch $(gh run list --workflow=deploy.yml --limit=1 --json databaseId -q '.[0].databaseId')

# 6. Smoke test
curl https://oute-prod-api-ujzimacvza-uc.a.run.app/health/live
```

### Manutenção programada (janela de manutenção)

1. Agendar com pelo menos 24h de antecedência — comunicar tenants por email
2. Colocar Cloud Run em modo de manutenção (min-instances=0, limitar tráfego)
3. Executar operação de manutenção
4. Restaurar configuração
5. Verificar todos os health endpoints
6. Comunicar fim da manutenção

### Purga de dados (GDPR / política de retenção)

O worker `retention_purge` roda automaticamente e remove dados conforme configuração de retenção do plano. Para purga manual de um tenant específico:

```sql
-- Soft-delete incidentes mais antigos que X dias
UPDATE incidents
SET deleted_at = NOW()
WHERE tenant_id = 'TENANT_UUID'
  AND created_at < NOW() - INTERVAL '365 days';

-- Purgar scans (hard delete — sem dados pessoais)
DELETE FROM scans
WHERE tenant_id = 'TENANT_UUID'
  AND created_at < NOW() - INTERVAL '90 days';
```

---

## Troubleshooting

### Problema: Scans retornando 401

**Causa**: API key inválida ou ausente.

**Verificação:**
```bash
# Testar a key diretamente
curl -I https://oute-prod-api-ujzimacvza-uc.a.run.app/v1/incidents \
  -H "X-API-Key: sk-..."
```

**Se a key está no banco (quando DB auth estiver implementado):**
```sql
SELECT id, tenant_id, last_used_at, revoked_at
FROM api_keys
WHERE key_hash = encode(sha256('sk-...'), 'hex');
```

### Problema: Scans muito lentos (> 10s)

**Causa provável**: L2 RAG com muitos vetores sem índice, ou Vertex AI com latência alta.

**Diagnóstico:**
```bash
# Verificar latência nos logs
gcloud logging read \
  'resource.type="cloud_run_revision"
   resource.labels.service_name="oute-prod-api"
   jsonPayload.event="scan_completed"' \
  --limit=20 --format=json | jq '.[].jsonPayload.duration_ms'

# Verificar índice HNSW no pgvector
psql ... -c "\d incidents" | grep vector
psql ... -c "SELECT indexname, indexdef FROM pg_indexes WHERE tablename = 'incidents';"

# Re-criar índice se necessário
psql ... -c "REINDEX INDEX CONCURRENTLY ix_incidents_embedding;"
```

### Problema: Synthesis candidates sempre em "failed"

**Causa provável**: Vertex AI indisponível, quota esgotada, ou prompt inválido.

**Diagnóstico:**
```bash
gcloud logging read \
  'resource.type="cloud_run_revision"
   jsonPayload.worker="synthesis"
   severity>=ERROR' \
  --limit=20

# Verificar quota Vertex AI
gcloud ai quotas list --region=us-central1

# Testar acesso ao Vertex AI manualmente
gcloud ai models list --region=us-central1
```

### Problema: Migrations falhando no deploy

**Causa provável**: migration incompatível com dados existentes, ou schema já alterado parcialmente.

```bash
# Ver estado atual
alembic -c packages/db/alembic.ini current

# Ver histórico
alembic -c packages/db/alembic.ini history

# Se migration parcialmente aplicada — corrigir manualmente e marcar como aplicada
alembic -c packages/db/alembic.ini stamp {revision_id}
```

### Problema: Cloud Run não sobe (startup probe falhando)

```bash
# Ver logs de startup
gcloud logging read \
  'resource.type="cloud_run_revision"
   resource.labels.service_name="oute-prod-api"
   jsonPayload.event="startup"' \
  --limit=10 --freshness=10m

# Verificar se a imagem está acessível
gcloud artifacts docker images list \
  us-central1-docker.pkg.dev/oute-488706/oute-prod-docker

# Verificar variáveis de ambiente da revisão
gcloud run revisions describe REVISION_NAME \
  --region=us-central1 \
  --format=json | jq '.spec.template.spec.containers[0].env'
```

### Problema: RLS vazando dados entre tenants

Isso é um incidente P1. Ação imediata:

```bash
# 1. Verificar se RLS está ativo em todas as tabelas
psql ... -c "SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname='public' AND rowsecurity=false;"

# 2. Se alguma tabela está sem RLS — ativar imediatamente
psql ... -c "ALTER TABLE nome_da_tabela ENABLE ROW LEVEL SECURITY;"

# 3. Verificar políticas existentes
psql ... -c "SELECT tablename, policyname, cmd, qual FROM pg_policies WHERE schemaname='public';"

# 4. Escalar imediatamente — esse é um incidente de segurança
```

---

## Runbook de rollback

### Rollback de revisão Cloud Run

Use quando um deploy introduziu regressão:

```bash
# 1. Listar revisões recentes
gcloud run revisions list \
  --service=oute-prod-api \
  --region=us-central1 \
  --limit=5

# 2. Identificar a revisão boa (anterior ao problema)
# Nomenclatura: oute-prod-api-{NNNNN}-{xxx}

# 3. Rotear 100% do tráfego para a revisão boa
gcloud run services update-traffic oute-prod-api \
  --region=us-central1 \
  --to-revisions=oute-prod-api-00003-xyz=100

# 4. Verificar que a revisão boa está respondendo
curl https://oute-prod-api-ujzimacvza-uc.a.run.app/health/live

# 5. Documentar o rollback e abrir issue de investigação
```

### Rollback de migration

Só deve ser feito se a migration introduziu problema. Risco: possível perda de dados se o schema já foi usado.

```bash
# 1. Verificar migration atual
alembic -c packages/db/alembic.ini current

# 2. Reverter uma migration
make migrate-down

# 3. Verificar que o schema voltou ao estado correto
alembic -c packages/db/alembic.ini current

# 4. Fazer rollback da imagem do Cloud Run para versão anterior (sem a migration)
# (ver rollback de revisão acima)
```

---

## Referência de recursos GCP

| Recurso | Identificador | Acesso |
|---------|--------------|--------|
| Projeto | `oute-488706` | https://console.cloud.google.com/home/dashboard?project=oute-488706 |
| Cloud Run (prod) | `oute-prod-api` | https://console.cloud.google.com/run/detail/us-central1/oute-prod-api/metrics?project=oute-488706 |
| Cloud SQL | `oute-postgres` | https://console.cloud.google.com/sql/instances/oute-postgres/overview?project=oute-488706 |
| Artifact Registry (prod) | `oute-prod-docker` | `us-central1-docker.pkg.dev/oute-488706/oute-prod-docker` |
| Secret Manager | — | https://console.cloud.google.com/security/secret-manager?project=oute-488706 |
| Terraform state | `oute-terraform-state` | `gs://oute-terraform-state/oute-muscle/prod/` |
| Cloud Logging | — | https://console.cloud.google.com/logs/query?project=oute-488706 |
| Vertex AI | — | https://console.cloud.google.com/vertex-ai?project=oute-488706 |
| IAM | — | https://console.cloud.google.com/iam-admin/iam?project=oute-488706 |
| WIF Pool (prod) | `oute-prod-gh-pool` | https://console.cloud.google.com/iam-admin/workload-identity-pools?project=oute-488706 |
| GH Actions SA (prod) | `oute-prod-gh-actions@oute-488706.iam.gserviceaccount.com` | — |
