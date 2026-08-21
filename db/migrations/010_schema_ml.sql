-- Marts de features para os modelos de ML (forecast, clustering, risco),
-- espelhando as antigas marts dbt do projeto AWS. Separado de dw porque o
-- grão/uso é orientado a modelo (feature matrix), não a análise dimensional.
CREATE SCHEMA IF NOT EXISTS ml;
