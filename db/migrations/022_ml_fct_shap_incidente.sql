-- Contribuições SHAP por feature, apenas para os TOP_N incidentes de maior
-- score a cada execução (não a população toda). Alimenta o painel "Valores
-- SHAP" da tela Fatores, reinterpretado como explicação dos incidentes de
-- maior risco (não do forecast de volume de amanhã -- decisão já tomada).
-- Grão: 1 linha por (incidente selecionado, feature).
CREATE TABLE IF NOT EXISTS ml.fct_shap_incidente (
    shap_sk text PRIMARY KEY,
    incident_sk text NOT NULL REFERENCES dw.fct_incidentes,
    incident_id text NOT NULL,
    modelo_versao text NOT NULL,
    data_execucao timestamp NOT NULL,
    feature text NOT NULL,
    shap_value numeric NOT NULL,
    direcao text NOT NULL,
    rank_abs smallint NOT NULL,
    score numeric NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_fct_shap_incidente_incident ON ml.fct_shap_incidente (incident_id);
