-- Importância global de features do XGBoost de risco de SLA (|SHAP| médio
-- por coluna, normalizado em %). Recarregada por completo (truncate+insert)
-- a cada execução. Alimenta o gráfico "Feature Importance" da tela Fatores.
-- Grão: 1 linha por (modelo_versao, feature) -- só a última execução é
-- mantida.
CREATE TABLE IF NOT EXISTS ml.fct_importancia_feature (
    importancia_sk text PRIMARY KEY,
    modelo_versao text NOT NULL,
    data_execucao timestamp NOT NULL,
    feature text NOT NULL,
    importance_pct numeric NOT NULL,
    rank smallint NOT NULL
);
