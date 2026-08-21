-- Mesmo racional de ml.fct_previsao_prioridade, quebrado por categoria.
-- Usa a coluna "categoria" (texto simples) em vez de referenciar
-- dw.dim_produto_categoria: o grão dessa dimensão é produto+categoria+
-- subcategoria, mais fino do que a tela "Top 5 categorias" do mockup
-- precisa (que agrupa só por categoria, ex: "Infraestrutura", "Rede").
-- Grão: 1 linha por (origem, ds, categoria).
CREATE TABLE IF NOT EXISTS ml.fct_previsao_categoria (
    previsao_categoria_sk text PRIMARY KEY,
    origem date NOT NULL,
    h smallint NOT NULL,
    horizonte text NOT NULL,
    ds date NOT NULL,
    categoria text NOT NULL,
    share_historico numeric NOT NULL,
    yhat_categoria numeric NOT NULL,
    modelo_versao text NOT NULL,
    data_execucao timestamp NOT NULL,
    UNIQUE (origem, ds, categoria)
);
