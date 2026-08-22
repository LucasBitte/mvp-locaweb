-- Previsão de volume diário por equipe (grupo_designado), D+1 a D+7.
-- Grupo A: Prophet individual por equipe (metodo='prophet_individual').
-- Grupo B: Prophet semanal, distribuído por dia via share histórico de
-- dia-da-semana, quando o Prophet diário perde do melhor baseline
-- (metodo='prophet_semanal'); permanece 'prophet_individual' quando o
-- diário empata ou supera o baseline. Grupo C: split proporcional do yhat
-- de ml.fct_previsao_diaria_total pela participação histórica da equipe
-- (metodo='split_proporcional'). Mesmo padrão de ml.fct_previsao_diaria_total:
-- append (não truncate+insert), idempotente por origem via DELETE+INSERT.
-- Grão: 1 linha por (origem, ds, dim_grupo_sk).
CREATE TABLE IF NOT EXISTS ml.fct_previsao_grupo (
    previsao_grupo_sk  text PRIMARY KEY,
    origem              date NOT NULL,
    h                   smallint NOT NULL,
    horizonte           text NOT NULL,
    ds                  date NOT NULL,
    dim_grupo_sk        text NOT NULL REFERENCES dw.dim_grupo (dim_grupo_sk),
    yhat                numeric NOT NULL,
    yhat_lower          numeric,
    yhat_upper          numeric,
    metodo              text NOT NULL,
    modelo_versao       text NOT NULL,
    data_execucao        timestamp NOT NULL,
    UNIQUE (origem, ds, dim_grupo_sk)
);

CREATE INDEX IF NOT EXISTS ix_fct_previsao_grupo_ds ON ml.fct_previsao_grupo (ds);
