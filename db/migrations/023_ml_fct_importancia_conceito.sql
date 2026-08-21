-- Importância do XGBoost agrupada por CONCEITO DE NEGÓCIO (ex: "Dia da
-- semana", "Categoria e triagem"), não por coluna crua ("hora_sin",
-- "vol_hora_grupo"). É essa granularidade que o painel "Fatores" do mockup
-- mostra (docs/design/aiops_dashboard_redesign.html) -- ml.fct_importancia_feature
-- (por coluna) é referência técnica, esta tabela é a leitura executiva.
-- Recarregada por completo (truncate+insert) a cada execução.
-- Grão: 1 linha por (modelo_versao, conceito).
CREATE TABLE IF NOT EXISTS ml.fct_importancia_conceito (
    importancia_conceito_sk text PRIMARY KEY,
    modelo_versao text NOT NULL,
    data_execucao timestamp NOT NULL,
    conceito text NOT NULL,
    n_colunas smallint NOT NULL,
    importance_pct numeric NOT NULL,
    rank smallint NOT NULL
);
