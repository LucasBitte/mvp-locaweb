-- Mart para o K-Means (equivalente a ml_cluster_dataset.parquet). Subconjunto
-- causa+efeito de ml.ml_base_features -- na clusterizacao nao ha problema de
-- vazamento de dados (o objetivo e descrever o passado completo, nao prever
-- o futuro). duracao_horas_scaled/cluster_id ficam NULL aqui e sao
-- preenchidas pelo notebook de clustering depois do treino (mesma
-- convencao do parquet original).
-- Grão: 1 linha por incidente.
CREATE TABLE IF NOT EXISTS ml.ml_cluster_dataset (
    incident_id text PRIMARY KEY REFERENCES ml.ml_base_features,
    prioridade_num int NOT NULL,
    grupo_designado text NOT NULL,
    categoria text NOT NULL,
    subcategoria text NOT NULL,
    produto text NOT NULL,
    hora_abertura int NOT NULL,
    turno_abertura text NOT NULL,
    dia_semana_num int NOT NULL,
    fora_horario_comercial boolean NOT NULL,
    abriu_fim_de_semana boolean NOT NULL,
    mes_abertura int NOT NULL,
    trimestre int NOT NULL,
    possui_pai boolean NOT NULL,
    is_filho_de_problema boolean NOT NULL,
    triagem_incompleta boolean NOT NULL,
    duracao_horas numeric NOT NULL,
    horas_ate_resolucao numeric,
    foi_resolvido boolean NOT NULL,
    excedeu_tempo_esperado boolean NOT NULL,
    fechado_sem_tecnico boolean NOT NULL,
    target_risco_sla smallint NOT NULL,
    kpi_status_int smallint NOT NULL,
    score_risco_operacional smallint NOT NULL,
    duracao_horas_scaled double precision,   -- preenchido pelo notebook de clustering
    cluster_id text                          -- preenchido pelo notebook de clustering
);
