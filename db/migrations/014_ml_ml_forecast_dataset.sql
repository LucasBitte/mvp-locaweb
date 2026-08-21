-- Mart para o forecast (Prophet), equivalente a ml_forecast_dataset.parquet.
-- Muda de grão em relação às outras marts: sobe de incidente individual
-- para DIA. Cada linha é um dia completo de operação, com volume total e
-- breakdowns por prioridade -- é o que o Prophet precisa para aprender
-- sazonalidade.
-- Grão: 1 linha por data_abertura.
CREATE TABLE IF NOT EXISTS ml.ml_forecast_dataset (
    data_abertura date PRIMARY KEY,
    dia_semana_num int NOT NULL,
    semana_ano int NOT NULL,
    mes_abertura int NOT NULL,
    trimestre int NOT NULL,
    ano_mes text NOT NULL,
    is_fim_de_semana boolean NOT NULL,
    total_chamados int NOT NULL,
    total_p1 int NOT NULL,
    total_p2 int NOT NULL,
    total_p3 int NOT NULL,
    total_p4 int NOT NULL,
    total_criticos int NOT NULL,
    total_violacoes_sla int NOT NULL,
    pct_violacao_sla numeric,
    pressao_operacional_dia int NOT NULL,
    score_risco_medio_dia numeric,
    media_horas_resolucao numeric
);
