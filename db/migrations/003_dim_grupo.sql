-- Equipe designada para o atendimento. Grão: 1 linha por grupo_designado.
CREATE TABLE IF NOT EXISTS dw.dim_grupo (
    dim_grupo_sk text PRIMARY KEY,
    grupo_designado text NOT NULL
);
