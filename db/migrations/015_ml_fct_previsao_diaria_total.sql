-- Previsão Prophet de volume TOTAL diário, D+1 a D+7, a partir da última
-- origem (último dia com dado no histórico). Cada execução do script gera
-- 7 linhas novas; execuções antigas são mantidas (append, não
-- truncate+insert) para comparar previsto x realizado depois.
-- Grão: 1 linha por (origem, horizonte).
CREATE TABLE IF NOT EXISTS ml.fct_previsao_diaria_total (
    previsao_total_sk text PRIMARY KEY,
    origem date NOT NULL,
    h smallint NOT NULL,
    horizonte text NOT NULL,
    ds date NOT NULL,
    yhat numeric NOT NULL,
    yhat_lower numeric,
    yhat_upper numeric,
    modelo_versao text NOT NULL,
    data_execucao timestamp NOT NULL,
    UNIQUE (origem, ds)
);

CREATE INDEX IF NOT EXISTS ix_fct_previsao_total_ds ON ml.fct_previsao_diaria_total (ds);
