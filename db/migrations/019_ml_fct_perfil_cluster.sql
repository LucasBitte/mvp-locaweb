-- Métricas agregadas por cluster, recalculadas a cada execução do notebook
-- de K-Means (truncate+insert). Alimenta o gráfico de bolhas
-- (x=duracao_media_horas, y=taxa_sla_violado_pct, tamanho=n_incidentes) e os
-- cards de perfil na tela Clusters.
-- Grão: 1 linha por (cluster_id, data_execucao) -- só a última execução é
-- mantida (truncate+insert), sem histórico de execuções passadas.
CREATE TABLE IF NOT EXISTS ml.fct_perfil_cluster (
    perfil_cluster_sk text PRIMARY KEY,
    cluster_id text NOT NULL REFERENCES ml.dim_cluster,
    modelo_versao text NOT NULL,
    data_execucao timestamp NOT NULL,
    n_incidentes int NOT NULL,
    pct_volume numeric NOT NULL,
    duracao_media_horas numeric,
    taxa_resolucao_pct numeric,
    taxa_sla_violado_pct numeric
);
