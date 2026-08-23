-- Migration 033: ml.alertas_ativos
-- Objetivo: tabela referenciada pelo router /api/alertas (Fase 3.2) nunca
-- existiu em produção nem em nenhum outro schema. Foi criada primeiro em
-- ml_dev (Fase 4.2, scripts/create_and_populate_alertas_dev.py) para não
-- afetar produção enquanto a regra era validada; esta migration promove o
-- mesmo schema para `ml` (Fase 5).
--
-- Alertas ativos são gerados por REGRA (nunca por modelo diretamente) sobre
-- saídas dos modelos já persistidas (ml.fct_perfil_cluster, ml.fct_pressao_equipe).

CREATE TABLE IF NOT EXISTS ml.alertas_ativos (
    id TEXT PRIMARY KEY,
    severidade TEXT NOT NULL,
    condicao TEXT NOT NULL,
    cluster_id TEXT,
    equipe_id TEXT,
    origem TEXT NOT NULL DEFAULT 'regra',
    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_alertas_ativos_severidade ON ml.alertas_ativos (severidade);
