# Guia do Usuário — Oute Muscle

Este guia cobre o uso diário da plataforma: documentar incidentes, interpretar resultados de scans, gerenciar regras, administrar o time e entender o que cada camada de detecção faz.

---

## Índice

1. [Conceitos fundamentais](#conceitos-fundamentais)
2. [Primeiros passos](#primeiros-passos)
3. [Documentando incidentes](#documentando-incidentes)
4. [Scans e integrações CI](#scans-e-integrações-ci)
5. [Interpretando findings](#interpretando-findings)
6. [Gerenciando regras](#gerenciando-regras)
7. [Synthesis de novas regras (L3)](#synthesis-de-novas-regras-l3)
8. [Falsos positivos](#falsos-positivos)
9. [Gerenciamento de times](#gerenciamento-de-times)
10. [Planos e limites](#planos-e-limites)
11. [Referência de API](#referência-de-api)

---

## Conceitos fundamentais

### O que é um incidente?

Um incidente é qualquer evento de produção documentado que resultou de um padrão de código problemático. Não precisa ser um outage — basta ser algo que não deveria ter chegado a produção.

Exemplos: regex catastrófico que causou timeout, race condition em bulk update, endpoint sem rate limit que foi abusado.

### As três camadas de detecção

```
L1 — Semgrep (blocking)
  ↓ padrão estático encontrado em um PR → CI falha, merge bloqueado

L2 — RAG advisory (consultivo)
  ↓ código semanticamente parecido com incidente passado → aviso no PR, não bloqueia

L3 — Auto-synthesis (progressivo)
  ↓ padrão sem regra estática → LLM propõe nova regra → engenheiro aprova → vira L1
```

### Rastreabilidade

Toda regra L1 aponta para o incidente que a originou. Todo finding de um scan aponta para a regra, que aponta para o incidente, que tem o post-mortem. O loop está fechado.

---

## Primeiros passos

> **Status do beta**: a plataforma está em beta privado. O dashboard web está em desenvolvimento — durante o beta, o acesso é feito **exclusivamente via API**. Você receberá sua API Key diretamente pela equipe Oute ao ser onboardado.

### Solicitar acesso

1. Acesse [muscle.oute.pro](https://muscle.oute.pro) e preencha o formulário de **Request access**
2. Aguarde o contato da equipe Oute (beta por convite)
3. Você receberá sua **API Key** por email para começar a usar

### URLs atuais

| Serviço | URL |
|---------|-----|
| Landing page / waitlist | https://muscle.oute.pro *(em breve)* |
| API (prod) | https://oute-prod-api-ujzimacvza-uc.a.run.app |
| API (staging) | https://oute-staging-api-ujzimacvza-uc.a.run.app |
| Dashboard web | Em desenvolvimento |

### Usar a API Key

A key recebida é enviada no header `X-API-Key` em todas as chamadas:

```bash
curl -H "X-API-Key: sk-..." https://oute-prod-api-ujzimacvza-uc.a.run.app/v1/incidents
```

---

## Documentando incidentes

### Via dashboard *(em desenvolvimento)*

O dashboard web ainda não está disponível no beta atual. Use a API diretamente (seções abaixo). O dashboard será disponibilizado nas próximas semanas.

### Via URL (extração automática)

Se você tem o post-mortem em uma URL pública (Notion, Confluence, GitHub issue):

```bash
curl -X POST https://oute-prod-api-ujzimacvza-uc.a.run.app/v1/incidents/ingest-url \
  -H "X-API-Key: sk-..." \
  -H "Content-Type: application/json" \
  -d '{"url": "https://notion.so/seu-post-mortem"}'
```

O LLM extrai os campos automaticamente e cria um **draft** para revisão. Confirme com um `PUT /v1/incidents/{id}` com `status: published`.

### Via API (criar diretamente)

```bash
curl -X POST https://oute-prod-api-ujzimacvza-uc.a.run.app/v1/incidents \
  -H "X-API-Key: sk-..." \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Regex catastrófico em validação de email",
    "category": "unsafe-regex",
    "severity": "high",
    "anti_pattern": "Uso de re.compile() com input não sanitizado do usuário",
    "remediation": "Valide o tamanho do input antes do match. Use timeout ou RE2.",
    "affected_languages": ["python"],
    "code_example": "pattern = re.compile(user_input)\npattern.match(email)",
    "source_url": "https://...",
    "date": "2026-01-15",
    "static_rule_possible": true
  }'
```

### Categorias de incidente

| Categoria | Exemplos típicos |
|-----------|-----------------|
| `unsafe-regex` | Backtracking catastrófico, quantificadores sem limite |
| `injection` | SQL injection, command injection, template injection |
| `race-condition` | TOCTOU, estado compartilhado sem lock, bulk updates sem serialização |
| `missing-error-handling` | Erros swallowed, exceções não tratadas, retornos não verificados |
| `resource-exhaustion` | Loops sem limite, queries sem paginação, uploads sem size limit |
| `missing-safety-check` | Input não validado, guards ausentes |
| `deployment-error` | Migrations que dropam colunas em uso, rollbacks impossíveis |
| `data-consistency` | Atualizações parciais sem transação, dual-write sem atomicidade |
| `unsafe-api-usage` | APIs deprecadas, uso incorreto de primitivas de concorrência |
| `cascading-failure` | Ausência de circuit breaker, retry storms, timeouts ausentes |

---

## Scans e integrações CI

### Como funciona um scan

Você envia um **diff** (unified diff de um PR) para a API. O sistema:

1. **L1**: roda Semgrep com todas as regras do seu tenant → findings bloqueantes
2. **L2** (team+): compara semanticamente o código com incidentes passados → advisories
3. **L3** (enterprise): se encontrar padrão sem regra, sintetiza candidata automática

### Integração com GitHub Actions

Adicione ao seu workflow:

```yaml
# .github/workflows/oute-scan.yml
name: Oute Muscle Scan
on: [pull_request]

jobs:
  oute-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Generate diff
        run: git diff origin/${{ github.base_ref }}...HEAD > pr.diff

      - name: Run Oute Muscle scan
        env:
          OUTE_API_KEY: ${{ secrets.OUTE_API_KEY }}
        run: |
          RESULT=$(curl -s -X POST \
            https://oute-prod-api-ujzimacvza-uc.a.run.app/v1/scans \
            -H "X-API-Key: $OUTE_API_KEY" \
            -H "Content-Type: application/json" \
            -d "{
              \"diff\": $(cat pr.diff | jq -Rs .),
              \"repository\": \"${{ github.repository }}\",
              \"commit_sha\": \"${{ github.sha }}\",
              \"pr_number\": ${{ github.event.pull_request.number }}
            }")

          RISK=$(echo $RESULT | jq -r '.risk_level')
          FINDINGS=$(echo $RESULT | jq '.findings | length')

          echo "Risk level: $RISK"
          echo "Findings: $FINDINGS"

          if [ "$RISK" = "critical" ] || [ "$RISK" = "high" ]; then
            echo "::error::Oute Muscle blocked this PR: $FINDINGS finding(s) at $RISK risk"
            exit 1
          fi
```

Configure `OUTE_API_KEY` em **GitHub → Settings → Secrets and variables → Actions**.

### Scan via API (curl)

```bash
# Gerar o diff do PR
git diff origin/main...HEAD > pr.diff

# Enviar para scan (JSON)
curl -X POST https://oute-prod-api-ujzimacvza-uc.a.run.app/v1/scans \
  -H "X-API-Key: sk-..." \
  -H "Content-Type: application/json" \
  -d "{\"diff\": $(cat pr.diff | jq -Rs .), \"repository\": \"org/repo\"}"

# Enviar para scan (SARIF — para integrar com GitHub Code Scanning)
curl -X POST https://oute-prod-api-ujzimacvza-uc.a.run.app/v1/scans \
  -H "X-API-Key: sk-..." \
  -H "Accept: application/sarif+json" \
  -H "Content-Type: application/json" \
  -d "{\"diff\": $(cat pr.diff | jq -Rs .), \"repository\": \"org/repo\"}"
```

### Consultar resultado de um scan

```bash
GET /v1/scans/{scan_id}
```

```bash
curl https://oute-prod-api-ujzimacvza-uc.a.run.app/v1/scans/abc123 \
  -H "X-API-Key: sk-..."
```

---

## Interpretando findings

### Estrutura de um finding

```json
{
  "rule_id": "unsafe-regex-001",
  "incident_id": "550e8400-...",
  "incident_url": "https://oute.me/incidents/550e8400-...",
  "file_path": "src/validators.py",
  "start_line": 42,
  "end_line": 42,
  "severity": "high",
  "category": "unsafe-regex",
  "message": "Potential unsafe regex pattern detected. Use RE2 or add input length validation.",
  "remediation": "Validate input length before matching. Consider using timeout or RE2."
}
```

### Níveis de risco (`risk_level`)

| Nível | Significa | Ação recomendada |
|-------|-----------|-----------------|
| `critical` | Finding crítico no diff | Bloquear o PR obrigatoriamente |
| `high` | Finding de alta severidade | Bloquear o PR (configurável) |
| `medium` | Finding de severidade média | Avisar, não bloquear |
| `low` | Sem findings ou apenas advisories | Aprovar normalmente |

### Advisories L2 (semânticos)

Advisories são retornados no campo `advisories` da resposta. Eles não bloqueiam — são contexto:

```json
{
  "advisories": [
    {
      "incident_id": "...",
      "similarity_score": 0.87,
      "incident_title": "Regex DoS em validação de CPF — Jan 2026",
      "incident_url": "...",
      "advice": "Este código se parece com o padrão que causou o incidente acima."
    }
  ]
}
```

---

## Gerenciando regras

### Ver regras ativas

Durante o beta, as regras são gerenciadas via API. O dashboard web (em desenvolvimento) trará uma interface visual para isso.

```bash
# Listar regras ativas (endpoint em desenvolvimento)
GET /v1/rules
```

As regras Semgrep do seu tenant ficam no repositório `packages/semgrep-rules/`, organizadas por categoria.

### Regras por categoria

As regras são organizadas em 10 categorias (veja [Documentando incidentes → Categorias](#categorias-de-incidente)). Cada regra tem:

- **ID** — formato `{categoria}-{NNN}` (ex: `unsafe-regex-001`)
- **Severidade** — `ERROR` (bloqueia CI) ou `WARNING` (avisa)
- **Incidente de origem** — link para o post-mortem
- **Status** — `active` / `disabled`

### Desativar uma regra manualmente

Vá em **Rules → {regra} → Disable**. Só admins e editors podem desativar regras.

> A regra é desativada apenas para o seu tenant — não afeta outros clientes.

---

## Synthesis de novas regras (L3)

Disponível apenas no plano **Enterprise**.

### Como funciona

Quando o L2 detecta um padrão semanticamente similar a incidentes passados, mas sem regra estática correspondente, o L3 aciona um worker que:

1. Analisa o incidente mais próximo e o código do PR
2. Gera um rascunho de regra Semgrep via Gemini 2.5 Pro
3. Cria um **candidato** com status `pending_review`

### Revisar candidatos

Durante o beta, a revisão de candidatos é feita via API. O dashboard trará uma fila visual de aprovação futuramente.

Para cada candidato você pode:

- **Approve** — a regra é adicionada ao conjunto ativo (vira L1)
- **Reject** — descarta o candidato com justificativa
- **Retry** — re-aciona a síntese se o LLM falhou

Via API:

```bash
# Aprovar
POST /v1/synthesis/candidates/{id}/approve
{"approved_by": "user@empresa.com"}

# Rejeitar
POST /v1/synthesis/candidates/{id}/reject

# Listar candidatos pendentes
GET /v1/synthesis/candidates?status=pending_review
```

---

## Falsos positivos

Se um finding é incorreto (a regra não se aplica ao contexto), qualquer **editor ou admin** pode reportá-lo:

```bash
POST /v1/findings/{finding_id}/false-positive
```

**Comportamento automático:**
- A cada reporte, `false_positive_count` é incrementado no finding
- Quando o count chega a **3**, a regra de origem é **automaticamente desativada** para revisão
- Um alerta é enviado ao admin do tenant

> Use com cuidado. Reportar falso positivo em massa desativa a proteção do time.

---

## Gerenciamento de times

### Papéis (roles)

| Role | Permissões |
|------|-----------|
| `admin` | Tudo — inclui convidar, alterar roles, desativar regras, acessar audit log |
| `editor` | Criar/editar incidentes, aprovar synthesis, reportar falsos positivos |
| `viewer` | Somente leitura — ver incidentes, scans, findings |

### Convidar um membro

Durante o beta, convites são feitos via API:

```bash
POST /v1/tenants/me/users/invite
{"email": "colega@empresa.com", "role": "editor"}
```

O usuário recebe um email de convite. A vaga só é consumida do plano quando o convite é aceito.

### Alterar role

```bash
PATCH /v1/tenants/me/users/{user_id}
{"role": "admin"}
```

Somente admins podem alterar roles.

---

## Planos e limites

| Feature | Free | Team | Enterprise |
|---------|------|------|-----------|
| Detecção L1 (Semgrep) | ✓ | ✓ | ✓ |
| Detecção L2 (RAG) | — | ✓ | ✓ |
| Detecção L3 (Synthesis) | — | — | ✓ |
| Audit log | — | — | ✓ |
| Membros do time | 1 | 10 | Ilimitado |
| Incidentes | 10 | 100 | Ilimitado |
| Repositórios conectados | 1 | 10 | Ilimitado |
| Suporte | Email | Email prioritário | Dedicado |

Ao atingir um limite, a API retorna `402 Payment Required` com `code: PLAN_LIMIT_EXCEEDED`.

---

## Referência de API

Base URL: `https://oute-prod-api-ujzimacvza-uc.a.run.app`

Documentação interativa (Swagger): `/docs` (disponível localmente em desenvolvimento)

### Autenticação

Todas as rotas (exceto `/health`, `/health/ready`, `/health/startup`, `POST /v1/waitlist`) exigem o header:

```
X-API-Key: sk-...
```

### Erros comuns

| Código | Significado | O que fazer |
|--------|------------|-------------|
| `401 Unauthorized` | API key ausente ou inválida | Verifique o header `X-API-Key` |
| `402 Payment Required` | Limite do plano atingido | Upgrade de plano |
| `403 Forbidden` | Role insuficiente | Peça ao admin para elevar seu role |
| `404 Not Found` | Recurso não existe | Verifique o ID |
| `409 Conflict` | Version mismatch (optimistic lock) | Re-faça o GET e tente novamente |
| `422 Unprocessable Entity` | Payload inválido | Verifique os campos obrigatórios |
| `429 Too Many Requests` | Rate limit atingido | Aguarde e tente novamente |
| `500 Internal Server Error` | Erro no servidor | Reporte em suporte |

### Paginação

Endpoints de listagem aceitam `page` (default: 1) e `per_page` (default: 50, max: 100):

```bash
GET /v1/incidents?page=2&per_page=20
```

Resposta sempre inclui `total`, `page`, `per_page`.

### Rate limits

- `POST /v1/scans`: 60 req/min por tenant
- Demais endpoints: 300 req/min por tenant
