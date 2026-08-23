# Changelog — Fase 15 (religar o React à API real), 2026-08-22

> Continuação da Fase 14 (`docs/changelog-fase14-api-2026-08-22.md`): o
> React (`app/web/`) parou de consumir dado estático (`dashboardData.ts`
> com arrays hardcoded) e passou a buscar as 6 telas ao vivo em `app/api/`.
> **Nenhuma tabela, migration ou modelo de ML foi alterado** — só código em
> `app/web/` e um campo novo em `app/api/routers/kpi.py`.

## 1. O que foi construído

| Arquivo | Conteúdo |
|---|---|
| `app/web/src/lib/api.ts` | Cliente HTTP tipado — uma interface + função por endpoint, espelhando exatamente os `pydantic.BaseModel` dos routers |
| `app/web/src/lib/useApi.ts` | Hook `useApi<T>(fetcher, deps)` — loading/erro/dado, cancela requisição obsoleta ao trocar de tela |
| `app/web/src/components/ApiStatus.tsx` | `<Loading/>` e `<ErrorState/>` compartilhados pelas 6 telas |
| `app/web/src/data/dashboardData.ts` | Reescrito por inteiro — cada `computeXxx()` passou a receber a resposta real da API como parâmetro (era um array hardcoded interno) e devolve a mesma estrutura pronta-pra-renderizar de antes |
| `app/web/src/components/screens/*.tsx` (6 arquivos) | Cada tela busca seu endpoint via `useApi`, trata loading/erro, chama os `computeXxx()` com o dado real |
| `app/web/.env.example` | `VITE_API_BASE_URL` (default `http://localhost:8000` se o arquivo não existir) |
| `app/api/routers/kpi.py` | Ganhou o campo `faixas` (as 6 faixas completas por combinação prioridade×indicador — antes só vinha a faixa que bateu com a contagem atual) |

## 2. Redesenhos de tela (não foi só trocar a fonte do dado)

A maior parte das telas foi troca direta (`computeXxx()` hardcoded →
`computeXxx(dadoReal)`), mas três pontos exigiram redesenho porque o dado
real não sustenta o que a tela estática mostrava:

- **Tela KPI**: o design estático tinha 4 linhas (P1-P4) com faixas
  inventadas — `dw.ref_meta_sla_anual` só define meta para **P2/P3**.
  Redesenhada para mostrar as 4 combinações reais (P2/P3 ×
  `ola_quebrado`/`volume_tratado`), cada uma com a grade de 6 faixas reais
  (exigiu o campo `faixas` novo em `/api/kpi`, §1). O enquadramento também
  era mensal ("dias decorridos em dezembro") — a API só tem acumulado
  anual; a tela agora mostra o ano corretamente.
- **Tela Detalhe**: "% do limite mensal" tinha uma barra de progresso com
  percentual inventado — não existe (nem existiu) fonte real para limite
  mensal de volume por prioridade (`is_placeholder_limite=true` sempre).
  Trocado por um texto explícito "sem fonte" em vez de uma barra fabricada.
- **Tela Clusters**: bolhas e chips agora usam `cor_hex` real de
  `ml.dim_cluster` em vez de uma cor calculada por limiar (o limiar antigo
  não fazia sentido para `taxa_excedeu_tempo_esperado_pct`, que fica entre
  94-98% em todos os 4 clusters reais — ver achado de auditoria da Fase 14).
  Rótulo trocado de "Violação de OLA" para "Excedeu tempo esperado" para
  não contradizer a tela KPI. Rótulos do gráfico de bolhas ganharam
  escalonamento vertical para não colidir quando dois clusters reais ficam
  próximos em duração/taxa (ex.: clusters A e C).

## 3. Verificação

- `tsc -b` e `npm run build`: limpos.
- `./venv/bin/python3 -m pytest tests/`: 38 testes, ✅ (inclui o teste novo
  de contrato de `/api/kpi` para o campo `faixas`).
- Os 6 tabs rodados num Chromium headless (Playwright) contra a API real:
  **zero erros de console, zero requisições falhas**, nenhuma tela presa em
  loading/erro. Screenshots conferidos visualmente (KPI e Clusters, as
  telas mais redesenhadas).

## 4. Achado de ambiente encontrado nesta rodada

`./venv/bin/pytest`, `./venv/bin/uvicorn` e `./venv/bin/pip` falhavam com
`cannot execute: required file not found` — o venv foi originalmente criado
em `/home/fiap/fiap-incidentes-dashboard/venv` e movido para
`/home/fiap/mvp-locaweb/venv`; os console-scripts instalados antes da
mudança têm o shebang hardcoded pro caminho antigo. Contorno documentado em
`CLAUDE.md` §10 e aplicado em todos os comandos deste changelog: invocar via
`./venv/bin/python3 -m <comando>` em vez do script direto.

## 5. O que NÃO mudou

- Nenhuma tabela, migration ou modelo de ML.
- Os 2 achados de auditoria da Fase 14 (`taxa_sla_violado_pct` renomeada;
  taxonomia de `ml.dim_cluster` divergente das métricas reais) continuam
  como estavam — só agora visíveis na UI real em vez de só na API/docs.
- `requirements.txt`/`requirements-notebooks.txt`: intocados.
