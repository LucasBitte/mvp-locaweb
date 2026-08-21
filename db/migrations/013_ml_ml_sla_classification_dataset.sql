-- Mart para o classificador de risco de SLA (XGBoost), equivalente a
-- ml_sla_classification_dataset.parquet. Livre de vazamento de dados: só
-- features disponíveis no minuto 0 de abertura do chamado (prioridade,
-- grupo, categoria, se tem pai, timestamp de abertura) -- nada que só
-- existe depois do encerramento/resolução. target_risco_sla e
-- target_excedeu_tempo são os dois rótulos possíveis para o treino.
-- Grão: 1 linha por incidente.
CREATE TABLE IF NOT EXISTS ml.ml_sla_classification_dataset (
    incident_id text PRIMARY KEY REFERENCES ml.ml_base_features,
    prioridade_num int NOT NULL,
    grupo_designado text NOT NULL,
    categoria text NOT NULL,
    subcategoria text NOT NULL,
    possui_pai boolean NOT NULL,
    is_filho_de_problema boolean NOT NULL,
    triagem_incompleta boolean NOT NULL,
    hora_abertura int NOT NULL,
    dia_semana_num int NOT NULL,
    turno_abertura text NOT NULL,
    fora_horario_comercial boolean NOT NULL,
    abriu_fim_de_semana boolean NOT NULL,
    semana_ano int NOT NULL,
    mes_abertura int NOT NULL,
    duracao_horas numeric NOT NULL,
    target_risco_sla smallint NOT NULL,
    target_excedeu_tempo boolean NOT NULL
);
