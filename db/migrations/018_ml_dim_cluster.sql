-- Taxonomia curada dos 4 clusters do K-Means (k=4, rótulos A-D). NÃO é
-- reescrita a cada execução do notebook: nome/descrição/tags são
-- interpretação humana do perfil de cada cluster (vindas do mockup
-- docs/design/aiops_dashboard_redesign.html), editada manualmente se o
-- significado de um cluster mudar após retreinar. Métricas numéricas por
-- execução ficam em ml.fct_perfil_cluster.
-- Grão: 1 linha por cluster_id.
CREATE TABLE IF NOT EXISTS ml.dim_cluster (
    cluster_id text PRIMARY KEY,
    nome_perfil text NOT NULL,
    descricao_curta text NOT NULL,
    tags text NOT NULL,
    cor_hex text NOT NULL,
    modelo_versao_referencia text
);

INSERT INTO ml.dim_cluster (cluster_id, nome_perfil, descricao_curta, tags, cor_hex, modelo_versao_referencia)
VALUES
    ('A', 'Críticos prolongados', 'Alta duração · P2 dominante · Alto risco OLA', 'Infra,Rede,P2,Seg-Ter', '#ef4444', 'kmeans_v1'),
    ('B', 'Recorrentes rápidos', 'Alta frequência · Curta duração · Causas repetidas', 'DB,App,P3,Diário', '#f59e0b', 'kmeans_v1'),
    ('C', 'Sazonais previsíveis', 'Dias específicos · Padrão claro', 'Segunda,Início mês,Mix P2/P3', '#3b82f6', 'kmeans_v1'),
    ('D', 'Baixo impacto', 'Curta duração · Rotineiros · Sem violações', 'Storage,P3,Fds', '#10b981', 'kmeans_v1')
ON CONFLICT (cluster_id) DO NOTHING;
