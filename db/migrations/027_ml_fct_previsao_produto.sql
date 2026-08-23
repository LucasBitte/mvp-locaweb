-- Mesmo racional de ml.fct_previsao_categoria (split proporcional histórico
-- sobre o yhat de ml.fct_previsao_diaria_total, NÃO é um Prophet por corte),
-- quebrado por "produto" em vez de "categoria" — PLAN.md Fase 4
-- (agrupamento=produto). Grão: 1 linha por (origem, ds, produto).
CREATE TABLE IF NOT EXISTS ml.fct_previsao_produto (
    previsao_produto_sk text PRIMARY KEY,
    origem date NOT NULL,
    h smallint NOT NULL,
    horizonte text NOT NULL,
    ds date NOT NULL,
    produto text NOT NULL,
    share_historico numeric NOT NULL,
    yhat_produto numeric NOT NULL,
    modelo_versao text NOT NULL,
    data_execucao timestamp NOT NULL,
    UNIQUE (origem, ds, produto)
);
