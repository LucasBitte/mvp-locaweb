-- Enriquecimento do timestamp de abertura (turno, horário comercial) para
-- análise intradiária. Diferente de dim_tempo (grão de DIA), esta dimensão
-- tem grão de TIMESTAMP: 1 linha por instante distinto de abertura.
CREATE TABLE IF NOT EXISTS dw.dim_abertura (
    dim_abertura_sk text PRIMARY KEY,
    aberto_at timestamp NOT NULL,
    hora_abertura int NOT NULL,
    turno_abertura text NOT NULL,
    fora_horario_comercial boolean NOT NULL,
    abriu_fim_de_semana boolean NOT NULL
);
