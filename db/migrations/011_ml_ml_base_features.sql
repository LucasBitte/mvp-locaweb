-- Mart intermediária, equivalente a int_incidents_enriched / ml_base_features.parquet
-- do projeto original. Grão: 1 linha por incidente (mesma população de
-- staging.incidentes_silver: 41.441 linhas, ja filtrada a esforço real e
-- aberto >= 2025-01-01).
--
-- IMPORTANTE: target_risco_sla e score_risco_operacional aqui usam o valor
-- ja calculado pela camada Silver (heuristica original de P2=4h, sem o
-- clamp de -1 -> 0). Isso e DIFERENTE de dw.fct_incidentes, que tem a
-- correcao da Etapa 2 (P2=8h, sem -1 residual). Divergencia intencional:
-- esta mart espelha a linhagem original do projeto AWS (Silver -> mart de
-- ML), dw.* e a linhagem star-schema corrigida. Ver docs/modelo-dimensional.md.
CREATE TABLE IF NOT EXISTS ml.ml_base_features (
    incident_id text PRIMARY KEY,
    incidente_pai text,
    aberto_por text NOT NULL,
    prioridade text NOT NULL,
    prioridade_num int NOT NULL,
    produto text NOT NULL,
    categoria text NOT NULL,
    subcategoria text NOT NULL,
    grupo_designado text NOT NULL,
    item_configuracao text,
    status text NOT NULL,
    codigo_fechamento text NOT NULL,
    entrou_kpi boolean NOT NULL,
    kpi_violado boolean,
    kpi_status_int smallint NOT NULL,
    possui_pai boolean NOT NULL,
    exige_intervencao boolean NOT NULL,
    target_risco_sla smallint NOT NULL,
    duracao_horas numeric NOT NULL,
    duracao_segundos bigint NOT NULL,
    aberto_at timestamp NOT NULL,
    resolvido_at timestamp,
    encerrado_at timestamp NOT NULL,
    data_abertura date NOT NULL,
    hora_abertura int NOT NULL,
    dia_semana_num int NOT NULL,
    semana_ano int NOT NULL,
    mes_abertura int NOT NULL,
    trimestre int NOT NULL,
    ano_mes text NOT NULL,
    turno_abertura text NOT NULL,
    fora_horario_comercial boolean NOT NULL,
    abriu_fim_de_semana boolean NOT NULL,
    horas_ate_resolucao numeric,
    foi_resolvido boolean NOT NULL,
    is_filho_de_problema boolean NOT NULL,
    triagem_incompleta boolean NOT NULL,
    fechado_sem_tecnico boolean NOT NULL,
    excedeu_tempo_esperado boolean NOT NULL,
    score_risco_operacional smallint NOT NULL
);
