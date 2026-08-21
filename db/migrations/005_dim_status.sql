-- Estado final do chamado e elegibilidade de KPI. Um mesmo status pode ter
-- múltiplos códigos de fechamento, por isso a chave combina os dois.
-- Grão: 1 linha por combinação distinta de (status, codigo_fechamento).
CREATE TABLE IF NOT EXISTS dw.dim_status (
    dim_status_sk text PRIMARY KEY,
    status text NOT NULL,
    codigo_fechamento text NOT NULL,
    entrou_kpi boolean NOT NULL
);
