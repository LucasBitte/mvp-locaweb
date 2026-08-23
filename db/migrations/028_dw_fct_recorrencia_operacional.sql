-- Análise de recorrência (PLAN.md Fase 5) — não existia antes desta migration.
-- Regra de negócio determinística sobre dw.fct_incidentes (mesmo espírito de
-- dw.ref_meta_sla_anual: não é saída de modelo de ML). Compara os últimos 30
-- dias contra os 30 dias imediatamente anteriores, por 4 granularidades
-- candidatas (produto, categoria, produto+categoria, categoria+subcategoria).
--
-- Recorrência != apenas volume alto: `status_recorrencia` combina
-- `delta_pct` (volume atual vs. baseline) com `cobertura_dias_atual_pct`
-- (em quantos dos 30 dias da janela atual a entidade teve pelo menos 1
-- incidente) — uma entidade pode ter poucos incidentes mas aparecer toda
-- semana (recorrente) ou muitos incidentes concentrados em 1-2 dias (pico
-- pontual, não recorrente). Regras completas e limiares fixos documentados
-- em notebooks/recorrencia.py.
--
-- Grão: 1 linha por (janela_referencia, granularidade, entidade). Recarregada
-- por completo a cada execução (não é append por origem — é sempre a leitura
-- mais recente da janela móvel).
CREATE TABLE IF NOT EXISTS dw.fct_recorrencia_operacional (
    recorrencia_sk              text PRIMARY KEY,          -- MD5(janela_referencia||granularidade||entidade)
    janela_referencia            date NOT NULL,             -- último dia da janela atual (30d)
    granularidade                text NOT NULL,             -- 'produto' | 'categoria' | 'produto_categoria' | 'categoria_subcategoria'
    entidade                     text NOT NULL,             -- valor(es), legível (ex.: 'lhco' ou 'Infraestrutura | Rede')
    produto                      text,
    categoria                    text,
    subcategoria                 text,
    volume_atual                 integer NOT NULL,          -- últimos 30 dias
    volume_baseline              integer NOT NULL,          -- 30 dias anteriores
    delta_pct                    numeric,                    -- NULL quando volume_baseline = 0
    dias_com_incidente_atual     smallint NOT NULL,          -- de 0 a 30
    cobertura_dias_atual_pct     numeric NOT NULL,           -- dias_com_incidente_atual / 30 * 100
    status_recorrencia           text NOT NULL,
    data_execucao                 timestamp NOT NULL,
    UNIQUE (janela_referencia, granularidade, entidade)
);
CREATE INDEX IF NOT EXISTS ix_fct_recorrencia_status ON dw.fct_recorrencia_operacional (status_recorrencia);
