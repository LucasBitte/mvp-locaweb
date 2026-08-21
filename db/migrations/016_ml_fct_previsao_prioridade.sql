-- Quebra do forecast total por prioridade, via SPLIT PROPORCIONAL histórico
-- (não é um Prophet por prioridade). share_historico é a fração do volume
-- histórico daquela prioridade no período de referência do treino;
-- yhat_prioridade = yhat do total (fct_previsao_diaria_total) * share_historico.
-- Grão: 1 linha por (origem, ds, prioridade_num).
CREATE TABLE IF NOT EXISTS ml.fct_previsao_prioridade (
    previsao_prioridade_sk text PRIMARY KEY,
    origem date NOT NULL,
    h smallint NOT NULL,
    horizonte text NOT NULL,
    ds date NOT NULL,
    prioridade_num int NOT NULL,
    share_historico numeric NOT NULL,
    yhat_prioridade numeric NOT NULL,
    modelo_versao text NOT NULL,
    data_execucao timestamp NOT NULL,
    UNIQUE (origem, ds, prioridade_num)
);
