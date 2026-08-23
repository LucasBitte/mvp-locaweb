# Fase 3 — Especificação de Endpoints da API FastAPI

Base: Parte D (Blueprint das 6 telas) e Parte F (Plano por arquivo)  
Atualização: 2026-08-23

## Endpoints a Implementar (6 totais)

Cada endpoint mapeia a 1 ou mais telas do dashboard e deve ser `GET` com parâmetros query/path conforme descrito.

---

### 1. **GET `/api/painel`** — Tela 01 (resumo executivo)

**Descrição**: Cockpit executivo — 4 KPIs + visão rápida das 3 lentes.

**Query Params** (opcionais):
- `data_base`: `YYYY-MM-DD` (default: hoje)

**Response** (Pydantic):
```python
class PrevisaoPonto(BaseModel):
    ds: date
    y: float  # volume previsto
    yhat: float  # predição Point
    yhat_lower: float  # intervalo 80% inferior (NOVO)
    yhat_upper: float  # intervalo 80% superior (NOVO)

class PressaoEquipe(BaseModel):
    grupo_id: str
    pressao_relativa_pct: float
    metodo_origem: str  # NOVO: 'prophet_individual'|'prophet_semanal'|'split_proporcional'

class PainelResponse(BaseModel):
    total_chamados: int
    kpi_status_agregado: float  # % de OLA cumprido
    previsao_d1: PrevisaoPonto
    pressao_d1_a_d7_media: float
    pressao_equipes: list[PressaoEquipe]
    volume_total_ano_referencia: int  # NOVO (de /api/kpi)
    forecast_top_categoria: str
    risco_principal: str
    data_execucao: datetime
    origem: str  # 'DADOS REAIS · API · FASE 15'
```

**Fonte de dados**:
- `ml.fct_previsao_diaria_total` (yhat, yhat_lower, yhat_upper)
- `ml.fct_previsao_prioridade` (volume por prioridade)
- `ml.fct_pressao_equipe` (pressão)
- `ml.fct_previsao_grupo` (metodo_origem) — NOVO
- `dw.fct_incidentes` (volume atual)
- `dw.ref_meta_sla_anual` (meta)

**Validação** (Parte C, matriz de rastreabilidade):
- ✅ Requisito "O que vai acontecer" — volume total D+1..D+7
- ✅ Requisito "Qual equipe exige atenção" — pressão por equipe

---

### 2. **GET `/api/detalhe`** — Tela 02 (forecast & capacidade, detalhe)

**Query Params**:
- `prioridade`: `'P2'|'P3'` (default: `P2,P3`)
- `categoria`: opcional, filtro por categoria
- `horizonte_dias`: `int` 1..7 (default: 7)

**Response**:
```python
class PrevisaoCategoria(BaseModel):
    categoria: str
    yhat: float
    delta_pct: float  # % de crescimento vs. baseline
    cobertura_dias_atual_pct: float  # recorrência

class RecorrenciaOperacional(BaseModel):
    produto_categoria: str
    tipo: str  # 'tendencia'|'sazonal'|'erro'
    evidencia: float

class DetalheResponse(BaseModel):
    prioridades_filtradas: list[str]
    previsao_por_categoria: list[PrevisaoCategoria]
    recorrencias_top: list[RecorrenciaOperacional]
    historico_serie: list[PrevisaoPonto]  # 14 dias atrás até hoje
    data_execucao: datetime
```

**Fonte de dados**:
- `ml.fct_previsao_categoria` (previsão por categoria)
- `dw.fct_recorrencia_operacional` (recorrência)
- `ml.ml_forecast_dataset` (série histórica)
- `dw.fct_incidentes` (baseline)

**Validação**:
- ✅ Requisito "Onde vai estar concentrado"
- ✅ Requisito "Sazonalidade / recorrência operacional"

---

### 3. **GET `/api/fatores`** — Tela 03 (risco & explicabilidade)

**Query Params**:
- `incidente_id`: opcional (se fornecido, retorna SHAP do incidente específico)
- `prioridade`: opcional

**Response**:
```python
class ShapDecomposicao(BaseModel):
    base_value: float  # saída BRUTA do XGBoost (NOVO, achado #7)
    shap_values: dict[str, float]  # {"feature": shap_contribution}
    saida_bruta_xgboost: float
    score_calibrado: float

class QualidadeModelo(BaseModel):
    auc_roc: float  # NOVO, achado #8
    mcc: float  # NOVO
    brier: float  # NOVO
    precision: float
    recall: float
    threshold_atual: float
    tn: int
    fp: int
    fn: int
    tp: int
    calibration_curve: list[tuple[float, float]]  # (pred_prob, true_freq)
    auc_por_prioridade: dict[str, float]  # NOVO

class FatoresResponse(BaseModel):
    ranking_incidentes: list[dict]  # top N de maior risco
    incidente_selecionado: int | None
    shap_decomposicao: ShapDecomposicao | None  # se incidente_id fornecido
    importancia_global: dict[str, float]  # por conceito
    qualidade_modelo: QualidadeModelo  # NOVO
    heatmap_categoria_dia: dict[str, dict[str, float]]
    data_execucao: datetime
```

**Fonte de dados**:
- `ml.fct_risco_incidente` (scores)
- `ml.fct_shap_incidente` (SHAP + base_value NOVO)
- `ml.fct_importancia_conceito` (importância global)
- `ml.fct_importancia_feature` (por feature)
- `ml_dev.fct_avaliacao_modelo` (dimensao=null, modelo=xgboost) — NOVO, para qualidade

**Validação**:
- ✅ Requisito "Por que existe risco"
- ✅ Achado #7: base_value presente e validado
- ✅ Achado #8: métricas de qualidade

---

### 4. **GET `/api/clusters`** — Tela 04 (perfis operacionais)

**Query Params**:
- Nenhum obrigatório

**Response**:
```python
class DiagnosticoKmeans(BaseModel):
    k: int
    silhouette: float
    davies_bouldin: float
    pca_variancia: float

class PerfilCluster(BaseModel):
    cluster_id: str
    nome_perfil: str
    n_incidentes: int
    pct_volume: float
    duracao_media_horas: float
    taxa_excedeu_tempo_esperado_pct: float  # renomeado
    pca_coord_1: float
    pca_coord_2: float
    impacto_volume_excedencia_pct: float  # NOVO, regra inicial (volume × taxa)

class ClustersResponse(BaseModel):
    clusters: list[PerfilCluster]
    diagnostico_kmeans: list[DiagnosticoKmeans]  # k=2..8 (NOVO, achado #9)
    composicao_por_prioridade: dict[str, dict[str, float]]  # cluster × prioridade
    composicao_por_categoria: dict[str, dict[str, float]]  # cluster × categoria
    data_execucao: datetime
```

**Fonte de dados**:
- `ml.dim_cluster` (metadados)
- `ml.fct_perfil_cluster` (métricas)
- `ml.ml_cluster_dataset` (composição)
- `ml_dev.fct_avaliacao_modelo` (dimensao='k') — NOVO

**Validação**:
- ✅ Requisito "Quais padrões estruturais existem"
- ✅ Achado #9: diagnóstico k presente

---

### 5. **GET `/api/kpi`** — Tela 01.5 (OLA & Metas, expansível)

**Query Params**:
- `prioridade`: opcional (default: P2,P3)
- `indicador`: `'ola_quebrado'|'volume_tratado'` (default: ambos)

**Response**:
```python
class FaixaMeta(BaseModel):
    limite_inferior: float
    limite_superior: float
    cor_hex: str

class KPIResponse(BaseModel):
    metricas: list[dict]  # {prioridade, indicador, status, projecao_atingimento_meta_pct}
    faixas_por_prioridade_indicador: dict  # {(p2, ola_quebrado): [FaixaMeta...]}
    probabilidade_atingir_meta_pct: float  # RENOMEADO de probabilidade (NOVO, achado #25)
    metodologia_probabilidade: str  # 'projecao_linear' (documentado)
    volume_total_ano_referencia: int  # NOVO
    data_execucao: datetime
```

**Fonte de dados**:
- `dw.ref_meta_sla_anual` (faixas, metas)
- `dw.fct_incidentes` (volume atual)

**Validação**:
- ✅ Requisito "Como estamos contra a meta contratual oficial"
- ✅ Achado #25: campo renomeado de `probabilidade_atingir_meta_pct` → `projecao_atingimento_meta_pct`

---

### 6. **GET `/api/alertas`** — Tela 05 (ações & governança)

**Query Params**:
- `severidade`: opcional
- `limit`: int (default: 20)

**Response**:
```python
class Alerta(BaseModel):
    id: str
    severidade: str
    condicao: str  # descrição legível
    cluster_id: str | None
    equipe_id: str | None
    origem: str  # regra ou modelo
    timestamp: datetime

class SaudeModelo(BaseModel):
    modelo: str
    status: str  # 'ok'|'degradado'|'abaixo_meta'
    metrica_chave: float
    limitacao: str

class AlertasResponse(BaseModel):
    alertas_ativos: list[Alerta]
    recomendacoes: list[dict]  # {acao, owner, prioridade, origem}
    saude_modelos: list[SaudeModelo]  # NOVO (achados #5/#8/#9/#14)
    limitacoes_sistema: list[str]  # declaradas
    data_execucao: datetime
```

**Fonte de dados**:
- `etl/alertas.py` (regras de alerta)
- `ml_dev.fct_avaliacao_modelo` (saúde dos modelos) — NOVO

**Validação**:
- ✅ Requisito "O que fazer"
- ✅ Achado consolidado #5/#8/#9/#14: saúde dos modelos

---

## Cronograma de Implementação

**Fase 3.1** (próximo): Criar models Pydantic para tipos acima  
**Fase 3.2**: Implementar routers (1 endpoint por dia)  
**Fase 3.3**: Conectar ao banco via queries SQL  
**Fase 3.4**: Testes de contrato (Fase 6 depois)

---

## Notas de Implementação

- Todos os endpoints devem estar **read-only** (apenas SELECT)
- Sempre incluir `data_execucao` e `origem` na resposta
- Usar `ml_dev.*` para dados novos (não afetar produção em Fase 3)
- Transições para `ml.*` e `dw.*` vêm em Fase 5 (após QA)
