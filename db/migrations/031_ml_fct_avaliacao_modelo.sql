-- Migration 031: Tabela genérica para avaliação de modelos
-- Consolidada em formato longo para cobrir 3 casos de uso:
--   1. Comparação Prophet total vs. baseline (dimensao=null)
--   2. Backtest por equipe (dimensao='equipe', chave_dimensao='Team14' etc.)
--   3. Diagnóstico k=2..8 do K-Means (dimensao='k', chave_dimensao='2'..'8')
--
-- Design: append-only, cada linha é (execução × modelo × dimensão × métrica × valor)
-- Suporta baseline: is_baseline=true + baseline_nome='split proporcional' etc.

CREATE TABLE IF NOT EXISTS ml.fct_avaliacao_modelo (
    avaliacao_sk TEXT PRIMARY KEY,
    modelo TEXT NOT NULL,
    modelo_versao TEXT NOT NULL,
    data_execucao TIMESTAMP NOT NULL,

    -- Dimensão opcional (null = agregado, 'equipe' = por equipe, 'k' = por valor de k)
    dimensao TEXT,

    -- Chave da dimensão (null se dimensao=null, 'Team14' se dimensao='equipe', '4' se dimensao='k')
    chave_dimensao TEXT,

    -- Métrica calculada (e.g. 'mae', 'wape', 'auc', 'mcc', 'silhouette', etc.)
    metrica TEXT NOT NULL,

    -- Valor da métrica
    valor NUMERIC,

    -- Flag de baseline (comparação com modelo alternativo)
    is_baseline BOOLEAN DEFAULT FALSE,

    -- Nome do baseline se is_baseline=true (e.g. 'split proporcional', 'média móvel')
    baseline_nome TEXT,

    -- Metadados
    origem TEXT DEFAULT 'notebook',
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Índices para consulta rápida
CREATE INDEX IF NOT EXISTS idx_avaliacao_modelo_data
    ON ml.fct_avaliacao_modelo(modelo, data_execucao DESC);

CREATE INDEX IF NOT EXISTS idx_avaliacao_modelo_dimensao
    ON ml.fct_avaliacao_modelo(dimensao, chave_dimensao);

CREATE INDEX IF NOT EXISTS idx_avaliacao_modelo_metrica
    ON ml.fct_avaliacao_modelo(modelo, metrica);

-- Comentário de tabela
COMMENT ON TABLE ml.fct_avaliacao_modelo IS
    'Avaliação consolidada de modelos em formato longo. '
    'Formato: (modelo, modelo_versao, data_execucao, dimensao, chave_dimensao, metrica, valor, is_baseline, baseline_nome).'
    'Append-only, populada por: forecast_incidentes_revisado.py (Prophet total vs. baseline), '
    'forecast_equipe.py (backtest por equipe), diagnostico_kmeans_k.py (diagnóstico k).';

COMMENT ON COLUMN ml.fct_avaliacao_modelo.dimensao IS
    'Dimensão de agregação: null (agregado), ''equipe'' (por equipe), ''k'' (por valor de k do K-Means).';

COMMENT ON COLUMN ml.fct_avaliacao_modelo.chave_dimensao IS
    'Chave da dimensão: null se dimensao=null, ''Team14'' se dimensao=''equipe'', ''4'' se dimensao=''k''.';

COMMENT ON COLUMN ml.fct_avaliacao_modelo.is_baseline IS
    'TRUE se a linha representa um modelo alternativo (baseline) para comparação.';

COMMENT ON COLUMN ml.fct_avaliacao_modelo.baseline_nome IS
    'Nome legível do baseline: ''split proporcional'', ''média móvel'', etc. Preenchido apenas se is_baseline=true.';
