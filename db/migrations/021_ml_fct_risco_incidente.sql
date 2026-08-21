-- Score de risco de violação de SLA por incidente (XGBoost calibrado).
-- Cobertura total da população elegível em dw.fct_incidentes. Só a última
-- execução é mantida (truncate+insert) -- sem histórico de score por
-- incidente nesta tabela.
-- Grão: 1 linha por incident_sk.
CREATE TABLE IF NOT EXISTS ml.fct_risco_incidente (
    incident_sk text PRIMARY KEY REFERENCES dw.fct_incidentes,
    incident_id text NOT NULL,
    modelo_versao text NOT NULL,
    data_execucao timestamp NOT NULL,
    score_bruto numeric NOT NULL,
    score_calibrado numeric NOT NULL,
    threshold_aplicado numeric NOT NULL,
    predicao_risco smallint NOT NULL,
    faixa_risco text NOT NULL,
    motivo_principal text,
    escopo_modelo text NOT NULL,
    particao text NOT NULL,
    y_real smallint
);

CREATE INDEX IF NOT EXISTS ix_fct_risco_incidente_faixa ON ml.fct_risco_incidente (faixa_risco);
