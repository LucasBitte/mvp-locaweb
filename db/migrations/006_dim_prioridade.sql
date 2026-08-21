-- Prioridade como dimensão própria (não só uma coluna na fato) para poder
-- carregar bucket, criticidade e o threshold contratual de SLA sem poluir a
-- fato com texto. threshold_sla_horas reflete as regras contratuais da
-- operação (P1=4h, P2=8h, P3=24h, P4=72h); prioridades fora de 1-4 (ex:
-- "5 - Muito Baixa") não têm threshold definido (NULL).
-- Grão: 1 linha por prioridade_num.
CREATE TABLE IF NOT EXISTS dw.dim_prioridade (
    dim_prioridade_sk text PRIMARY KEY,
    prioridade_num int NOT NULL,
    prioridade_texto text NOT NULL,
    bucket_prioridade text NOT NULL,
    nivel_criticidade text NOT NULL,
    threshold_sla_horas int
);
