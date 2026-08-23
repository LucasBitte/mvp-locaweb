# Plano de Deploy — Docker em fiap.looplyai.com.br

> Reorganização de pastas (backend/frontend/pipeline) foi cancelada a
> pedido do usuário — este plano dockeriza a aplicação **mantendo os
> caminhos atuais** (`app/api/`, `app/web/`, `etl/`, `notebooks/`,
> `db/migrations/`). Nenhum arquivo Python muda de lugar nem de import.

## ✅ Executado (2026-08-22) — https://fiap.looplyai.com.br está no ar

Todas as fases abaixo foram aplicadas. As 6 telas rodam com dado real
através do domínio, confirmado com Chromium headless (zero erro de
console, zero request falha) e com `curl` direto nos 3 endpoints
principais (`/`, `/api/painel`, `/api/kpi`, `/api/clusters` → todos 200).

**Achado durante o deploy, fora do previsto no plano original**: o
`HEALTHCHECK` do `app/web/Dockerfile` usava `wget --spider http://localhost/`
— dentro do container Alpine, `localhost` resolve primeiro para `::1`
(IPv6), mas o `nginx` só escuta em `0.0.0.0:80` (IPv4). O healthcheck
falhava (`connection refused`), o Docker marcava o container como
`unhealthy`, e **o provider Docker do Traefik descarta containers
unhealthy ao montar as rotas** — por isso `https://fiap.looplyai.com.br/`
respondia 404 (a resposta genérica do próprio Traefik, "nenhuma rota
casou", não um 404 do nginx) mesmo com o container rodando e servível via
rede interna (`curl` de outro container pro IP dele funcionava). API não
foi afetada porque seu `HEALTHCHECK` já usava `http://localhost:8000/health`
e o Python/uvicorn escuta em ambas IPv4/IPv6 por padrão. Corrigido trocando
`localhost` por `127.0.0.1` no healthcheck do nginx — não precisou mexer
em roteamento, prioridade ou nomes dos routers Traefik (todas as hipóteses
intermediárias testadas durante o diagnóstico, sem efeito real).

## Contexto

Colocar a aplicação web (API FastAPI + frontend React) no ar via Docker,
atrás do Traefik que já roda neste VPS, no domínio `fiap.looplyai.com.br`.

Investigação já feita (2 agentes Explore + 1 agente Plan, mais checagens
diretas):

- **Repo**: sem nenhum Docker/CI existente hoje (greenfield).
  `requirements.txt` (API) é separado de `requirements-notebooks.txt`
  (pipeline) — a imagem da API só precisa do primeiro. `VITE_API_BASE_URL`
  em `app/web/src/lib/api.ts` é lido via `import.meta.env` — **valor
  gravado no bundle JS no momento do build**, não em runtime do container.
  Os 6 routers da API (`app/api/routers/*.py`) já usam
  `APIRouter(prefix="/api", ...)` cada um (`/health` é a única rota sem
  prefixo, em `app/api/main.py`). `app/web/src/App.tsx` não usa
  `react-router` (navegação por `useState` de aba) — sem necessidade
  funcional de fallback SPA, mas serve como proteção defensiva de qualquer
  forma. `app/api/deps.py` e `app/api/routers/kpi.py` importam de `etl/`
  (`etl.db`, `etl.ref_meta_sla`) — a imagem da API precisa copiar `etl/`
  junto.
- **VPS** (mesma máquina deste shell, `srv1115371`, IP público
  `147.93.15.20`): Docker 29.1.3 instalado, usuário `lucas` no grupo
  `docker`. Já existe **Traefik v3.7** rodando como container
  (`/home/lucas/docker/traefik/docker-compose.yml`), publicando 80/443,
  roteamento por label Docker (`exposedByDefault: false`), rede externa
  `proxy`, resolver Let's Encrypt `letsencrypt` (HTTP-01). Container
  `app-bio` é o padrão de referência real de como plugar um app novo
  nessa rede (`Host(...)` + labels, sem publicar porta de host). Postgres
  roda como container `postgres` (`postgres:16-alpine`, db `fiap`), só na
  rede `bridge` padrão, publicado em `0.0.0.0:5432` — **não** está na
  rede `proxy` nem em nenhuma rede com DNS por nome de container.
  `FIAP_DB_HOST=localhost` no `.env` local só funciona porque o dev roda
  direto no host.
- **DNS**: `fiap.looplyai.com.br` resolve via CNAME → `config.looplyai.com.br`
  → A `147.93.15.20` (confirmado com `dig` contra `8.8.8.8` e `1.1.1.1`) —
  já aponta para este VPS. TTL curto (300s) e controlado por outro
  registro fora deste projeto — vale reconferir na hora do deploy, mas não
  é mais um bloqueio de dias.

## Fase 1 — Dockerfile da API

`app/api/Dockerfile` — Python 3.12-slim, instala só `requirements.txt`
(não `requirements-notebooks.txt`), copia `app/api/`, `app/__init__.py` e
`etl/` (não `notebooks/` nem `db/` — irrelevantes para a API rodando,
mantém a imagem enxuta), roda como usuário não-root, expõe 8000,
`HEALTHCHECK` batendo em `/health` local:

```dockerfile
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /srv
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY app/api ./app/api
COPY app/__init__.py ./app/__init__.py
COPY etl ./etl
RUN useradd --system --create-home --uid 1001 appuser && chown -R appuser:appuser /srv
USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1
CMD ["uvicorn", "app.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Checar antes de fechar: confirmar que `app/__init__.py` existe (já
confirmado — está presente e vazio) para o import `app.api.main:app`
resolver dentro da imagem.

## Fase 2 — Dockerfile do frontend

`app/web/Dockerfile` (multi-stage: build com Node, serve com nginx) +
`app/web/nginx.conf` (SPA fallback defensivo) + `app/web/.dockerignore`
(`node_modules`, `dist`, `.vite`):

```dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -q --spider http://localhost/ || exit 1
```

```nginx
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;
    location / { try_files $uri $uri/ /index.html; }
}
```

Checar antes de fechar: `npm run build` local com Node 20 continua
funcionando (Vite 8 / TS 6 não deveriam exigir Node 22+, mas vale rodar
`nvm use 20 && npm run build` uma vez para confirmar, já que
`package.json` não trava versão de Node).

## Fase 3 — Roteamento: domínio único, por path

`fiap.looplyai.com.br/` → frontend; `fiap.looplyai.com.br/api/*` → API
(bate exatamente com o prefixo que os routers já usam — zero rewrite de
path no Traefik). Evita 2º registro DNS, 2º certificado, e torna CORS
irrelevante em produção (mesma origem). `/health` fica só como alvo do
healthcheck interno do container — sem regra Traefik própria, não
exposto externamente (não é exigido por nada do projeto).

Valores gravados em build-time / runtime:
- `VITE_API_BASE_URL=https://fiap.looplyai.com.br` (origem pura — o
  cliente já concatena `/api/...`)
- `API_CORS_ORIGINS=https://fiap.looplyai.com.br` (setado corretamente
  mesmo sendo redundante com same-origin, para não deixar o default
  `localhost:5173` vazando pra produção)

## Fase 4 — Alcançar o Postgres a partir do container

**Decisão**: `extra_hosts: ["host.docker.internal:host-gateway"]` no
serviço da API, com `FIAP_DB_HOST=host.docker.internal` **só** no novo
`.env.production` — nunca tocar o `.env` local (que precisa continuar com
`FIAP_DB_HOST=localhost` para o dev direto no host continuar funcionando).
Não muda nada fora deste repo; reversível apagando só o compose novo.

**Alternativa documentada, não executada sem confirmação explícita**:
`docker network connect proxy postgres` (ou uma rede nova) + `FIAP_DB_HOST=postgres`
— mexe num container compartilhado fora da posse deste projeto (adiciona
rede, não remove nada nem reinicia o container, mas ainda é uma mudança de
infraestrutura compartilhada). Só fazer isso se pedido explicitamente.

## Fase 5 — Compose, secrets e sequência de deploy

`docker-compose.prod.yml` (raiz) — 2 serviços (`api` build context `.` com
`dockerfile: app/api/Dockerfile`; `web` build context `./app/web`), ambos
só na rede externa `proxy` (nenhuma porta de host publicada), labels
Traefik espelhando o padrão real do `app-bio` (`traefik.enable=true`,
`Host(...)` [+ `PathPrefix('/api')` e `priority=10` na API, `priority=1`
no frontend — a prioridade explícita é necessária porque são routers
`Host()` separados, Traefik não infere especificidade entre eles
sozinho], `entrypoints=websecure`, `tls.certresolver=letsencrypt`,
`loadbalancer.server.port` = 8000/80).

`.env.production` (raiz, gitignorado — já coberto por `.env.*` no
`.gitignore`, sem precisar editá-lo): `FIAP_DB_HOST=host.docker.internal`,
`FIAP_DB_PORT=5432`, `FIAP_DB_USER=fiap`, `FIAP_DB_PASSWORD=<copiar
manualmente do .env local>`, `FIAP_DB_NAME=fiap`,
`API_CORS_ORIGINS=https://fiap.looplyai.com.br`.

`.dockerignore` (raiz): `.git`, `venv/`, `node_modules/`, `app/web/dist/`,
`data/`, `notebooks/`, `db/`, `docs/`, `tests/`, `.pytest_cache/`,
`__pycache__/`, `.env*` exceto `.env.example`.

**Sequência**:
```bash
dig +short fiap.looplyai.com.br            # reconferir na hora, TTL 300s
# criar .env.production manualmente (copiar FIAP_DB_PASSWORD do .env)
docker compose -f docker-compose.prod.yml --env-file .env.production build
docker compose -f docker-compose.prod.yml --env-file .env.production up -d
docker compose -f docker-compose.prod.yml ps
docker logs traefik --tail 100 | grep -i fiap      # confere rota + cert sem conflito
curl -sI https://fiap.looplyai.com.br/             # frontend, espera 200
curl -s  https://fiap.looplyai.com.br/api/painel   # API, espera JSON
docker exec mvp-locaweb-api curl -sf http://localhost:8000/health
```
Depois, abrir `https://fiap.looplyai.com.br` num navegador e conferir as 6
abas sem erro de console (mesmo padrão de verificação já usado nas Fases
14/15 — Playwright headless local antes, aqui é a checagem final em
produção).

**Redeploy/rollback**: sem CI (fora de escopo pro tamanho do projeto) —
`git pull && docker compose -f docker-compose.prod.yml --env-file .env.production build && ... up -d`;
rollback é `git checkout <commit anterior>` + repetir build/up.

## Pontos em aberto para checar durante a execução (não bloqueiam o plano)

1. Prioridade dos routers Traefik (`api`=10 > `web`=1) — conferir
   `docker logs traefik` por qualquer aviso de rota conflitante no primeiro
   `up`, e testar `curl /api/...` vs `curl /` separadamente.
2. Node 20 vs. versão mais nova para o build do frontend — rodar
   `npm run build` uma vez com Node 20 antes de confiar no Dockerfile.
3. Reconferir `dig fiap.looplyai.com.br` imediatamente antes do deploy —
   TTL de 300s, CNAME controlado fora deste projeto.
