-- Calendário da análise temporal. Grão: 1 linha por dia de calendário em que
-- houve ao menos um incidente aberto (não é uma tabela de calendário completa).
CREATE TABLE IF NOT EXISTS dw.dim_tempo (
    dim_tempo_sk text PRIMARY KEY,
    data_abertura date NOT NULL,
    ano int NOT NULL,
    mes_num int NOT NULL,
    nome_mes text NOT NULL,
    semana_ano int NOT NULL,
    trimestre int NOT NULL,
    ano_mes text NOT NULL,
    dia_semana_num int NOT NULL,
    nome_dia text NOT NULL,
    is_fim_de_semana boolean NOT NULL
);
