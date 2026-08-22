-- "Pressão Operacional Prevista" por equipe (PLAN.md Fase 3): compara o
-- forecast D+1..D+7 de ml.fct_previsao_grupo contra a média histórica diária
-- da própria equipe (nunca capacidade real, headcount ou saturação
-- contratual — é volume previsto vs. o próprio histórico da equipe).
--
-- pressao_relativa_pct = ((yhat_previsto - media_historica_diaria) / media_historica_diaria) * 100
--
-- nivel_pressao (faixa fixa, documentada em notebooks/pressao_equipe.py,
-- não é saída de modelo): <=10% normal, 10-30% atenção, >30% crítico.
--
-- Para equipes de Grupo C (metodo_origem='split_proporcional', média diária
-- histórica < 1 incidente/dia — ver docs/forecast-por-equipe.md), a métrica
-- em % é mais ruidosa por construção (denominador pequeno); nivel_pressao
-- ainda é calculado, mas deve ser lido com essa ressalva.
--
-- Grão: 1 linha por (origem, ds, dim_grupo_sk). Append, idempotente por
-- origem (DELETE + INSERT), mesmo padrão de ml.fct_previsao_grupo.
CREATE TABLE IF NOT EXISTS ml.fct_pressao_equipe (
    pressao_equipe_sk      text PRIMARY KEY,                              -- MD5(origem||ds||dim_grupo_sk)
    origem                  date NOT NULL,
    h                       smallint NOT NULL,
    horizonte               text NOT NULL,                                 -- 'D+1'..'D+7'
    ds                      date NOT NULL,
    dim_grupo_sk            text NOT NULL REFERENCES dw.dim_grupo (dim_grupo_sk),
    yhat_previsto           numeric NOT NULL,                              -- ml.fct_previsao_grupo.yhat
    media_historica_diaria  numeric NOT NULL,                              -- média diária histórica da própria equipe (2025 completo, calendário zero-fill)
    pressao_relativa_pct    numeric NOT NULL,
    nivel_pressao           text NOT NULL,                                 -- 'normal' | 'atencao' | 'critico'
    metodo_origem           text NOT NULL,                                 -- 'metodo' de ml.fct_previsao_grupo (prophet_individual/prophet_semanal/split_proporcional)
    modelo_versao           text NOT NULL,
    data_execucao            timestamp NOT NULL,
    UNIQUE (origem, ds, dim_grupo_sk)
);
CREATE INDEX IF NOT EXISTS ix_fct_pressao_equipe_ds ON ml.fct_pressao_equipe (ds);
