-- Fato central do star schema. GRÃO: 1 linha = 1 incidente (chamado) que
-- exigiu esforço humano real, aberto a partir de 2025-01-01.
--
-- Filtros aplicados na carga (replicam a camada Silver do projeto original,
-- adaptados de public.incidentes no lugar do S3/RDS):
--   - status <> 'Sem Intervenção'   (remove alertas de monitoramento que se
--     autorresolvem, ~65% da tabela bruta — não representam esforço real)
--   - aberto >= '2025-01-01'         (mesmo corte do projeto original)
--
-- Adaptações em relação ao projeto original (AWS):
--   - target_risco_sla, camada de heurística: usa threshold de 8h para P2
--     (corrigido para bater com dim_prioridade.threshold_sla_horas; o
--     original usava 4h ali, inconsistente com a própria dimensão)
--   - fechado_sem_tecnico: mantida a regra literal do original
--     (codigo_fechamento IN ('Resolvido pelo Usuário','Sem Descrição')).
--     Esses valores não existem no vocabulário de codigo_fechamento desta
--     base, então a coluna é sempre FALSE aqui — mantida por fidelidade à
--     regra original, não por engano.
--   - chaves MD5 usam COALESCE em todos os campos que podem ser nulos
--     (produto/categoria/subcategoria, status/codigo_fechamento). O
--     original não fazia isso de forma consistente entre a dimensão e a
--     fato, o que geraria FK nula para a maior parte das linhas aqui
--     (63% dos incidentes não têm produto/categoria preenchidos).
CREATE TABLE IF NOT EXISTS dw.fct_incidentes (
    incident_sk text PRIMARY KEY,
    dim_produto_categoria_sk text NOT NULL REFERENCES dw.dim_produto_categoria,
    dim_grupo_sk text NOT NULL REFERENCES dw.dim_grupo,
    dim_tempo_sk text NOT NULL REFERENCES dw.dim_tempo,
    dim_status_sk text NOT NULL REFERENCES dw.dim_status,
    dim_prioridade_sk text NOT NULL REFERENCES dw.dim_prioridade,
    dim_abertura_sk text NOT NULL REFERENCES dw.dim_abertura,

    -- Chave degenerada: número original do incidente, para drill-down
    -- sem precisar de join.
    incident_id text NOT NULL UNIQUE,

    -- Métricas brutas
    duracao_horas numeric NOT NULL,
    duracao_minutos int NOT NULL,

    -- -1 = isento/desconhecido, 0 = dentro do prazo, 1 = violou
    kpi_status_int smallint NOT NULL,

    -- Target de risco de SLA (0/1) — variável que o classificador prevê
    target_risco_sla smallint NOT NULL,

    exige_intervencao boolean NOT NULL,
    possui_pai boolean NOT NULL,

    -- Métricas calculadas
    horas_ate_resolucao numeric,
    foi_resolvido boolean NOT NULL,
    is_filho_de_problema boolean NOT NULL,
    triagem_incompleta boolean NOT NULL,
    fechado_sem_tecnico boolean NOT NULL,
    excedeu_tempo_esperado boolean NOT NULL,

    -- Score composto 0-8: soma de violou SLA (+3), prioridade crítica P1/P2
    -- (+2), exigiu intervenção (+1), tem incidente pai (+1), abriu fora do
    -- horário comercial (+1).
    score_risco_operacional smallint NOT NULL,

    -- Timestamps originais, preservados para drill-down de linha do tempo
    aberto_at timestamp NOT NULL,
    resolvido_at timestamp,
    encerrado_at timestamp NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_fct_incidentes_dim_tempo ON dw.fct_incidentes (dim_tempo_sk);
CREATE INDEX IF NOT EXISTS ix_fct_incidentes_dim_prioridade ON dw.fct_incidentes (dim_prioridade_sk);
CREATE INDEX IF NOT EXISTS ix_fct_incidentes_dim_grupo ON dw.fct_incidentes (dim_grupo_sk);
