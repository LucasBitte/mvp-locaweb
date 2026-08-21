# Schema da tabela fonte — `public.incidentes` (banco `fiap`)

Levantado em 2026-08-21, conectando direto ao Postgres `fiap`. Grão: **1 linha = 1
chamado (incidente)**. 122.543 linhas, período de 2023-01-02 a 2025-12-31.

## Colunas

| Coluna | Tipo | Nulos | Observação |
|---|---|---|---|
| `numero` | text | 0% | PK. Ex: `INC8263208` |
| `prioridade` | text | 0% | 5 valores: `1 - Crítica` (1 linha), `2 - Alta`, `3 - Média`, `4 - Baixa`, `5 - Muito Baixa` |
| `produto` | text | 63.6% | 51 valores distintos (códigos curtos: `lhco`, `lsin`, `lcem`...) |
| `categoria` | text | 63.4% | 141 valores distintos (`cat71`, `cat77`...) |
| `subcategoria` | text | 63.4% | 447 valores distintos (`sub420`...) |
| `grupo_designado` | text | 0% | 17 valores (`Team01`..`Team17`); muito concentrado em `Team14` (92.775 / 75.7%) |
| `item_configuracao` | text | 1.5% | 9.171 valores distintos (CI — configuration item) |
| `aberto` | timestamp | 0% | Data/hora de abertura |
| `resolvido` | timestamp | 67.2% | Data/hora de resolução (pode ser nulo mesmo em incidentes encerrados) |
| `encerrado` | timestamp | 0% | Data/hora de encerramento — sempre >= `aberto` |
| `duracao_min` | integer | 0% | Duração em minutos. **Outlier**: máx = 88.280.481 min (~168 anos) — precisa de tratamento na fato, não confiar cegamente |
| `codigo_fechamento` | text | 66.7% | 17 valores (`Falha de Aplicação`, `Falha de Cloud`...) |
| `descricao_resumida` | text | ~0% | Texto livre |
| `solucao` | text | 87.5% | Texto livre |
| `aberto_por` | text | 0% | 2 valores: `Monitoramento` (85.1%), `Manual` (14.9%) |
| `incidente_pai` | text | 87.7% | Auto-referência a `numero`. **1.377 valores não encontram um `numero` correspondente** (dado órfão) |
| `status` | text | 0% | 4 valores: `Sem Intervenção`, `Encerrado Automaticamente`, `Encerrado`, `Aguardando Problema` (1 linha) |
| `entrou_kpi` | boolean | 0% | Se o incidente entrou no acompanhamento de KPI/SLA (21% `True`) |
| `kpi_violado` | boolean | 79.1%* | *Nulo exatamente quando `entrou_kpi = False`. Entre os que entraram: 248 violaram (~1%), 25.352 não |

## Achados relevantes para a modelagem

- **`entrou_kpi` + `kpi_violado`** é a informação de risco/violação de SLA — equivalente
  ao `target_risco_sla` / "OLA quebrado" do mockup e dos notebooks.
- **`aberto`** é a fonte de todos os atributos temporais derivados usados nos notebooks
  (`hora_abertura`, `turno_abertura`, `dia_semana_num`, `mes_abertura`, `trimestre`,
  `fora_horario_comercial`, `abriu_fim_de_semana`) — nenhum vem pronto na tabela, todos
  são calculados a partir dela.
- **`prioridade`** vem como texto `"N - Rótulo"` — precisa parse para virar `prioridade_num`.
- **Mudança de regime de volume**: ~10-50 chamados/mês até nov/2024, salto para
  ~3.200-4.000/mês em 2025 até agosto, e novo salto para ~21.000-27.000/mês a partir de
  set/2025. Mesmo padrão que o notebook de forecast já trata (`quebras_de_patamar_detectadas`).
- **Qualidade de dado a tratar no ETL**: `duracao_min` com outliers extremos;
  `incidente_pai` com 1.377 referências órfãs (não deve virar FK rígida); categorias com
  1 única ocorrência (`1 - Crítica`, `Team13`, `Aguardando Problema`).
- Não há colunas de cliente/tenant nem de SLA-alvo (ex: "4h para P2") — as metas de OLA
  mencionadas no painel KPI do mockup (ex: "máx 31 quebras/ano" para P2) **não existem
  na tabela fonte**; teriam que vir de uma tabela de referência à parte (parâmetro de
  negócio, não dado transacional).
