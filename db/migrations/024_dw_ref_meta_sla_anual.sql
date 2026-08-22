-- Tabela de referência (não é fato de ML nem dimensão clássica): metas
-- anuais de SLA por prioridade, definidas pelo Dicionário de Dados oficial
-- do desafio. Só existem metas para P2 (Alta) e P3 (Média), em dois
-- indicadores independentes -- "ola_quebrado" (contagem anual de violações
-- de SLA) e "volume_tratado" (contagem anual de chamados tratados) -- cada
-- um com 6 faixas e um % de atingimento associado (150/125/100/75/50/0).
--
-- A meta é anual, mas o acompanhamento é mensal: não existe uma meta
-- mensal própria, o que se acompanha mês a mês é a posição acumulada do
-- ano-corrente frente a estas faixas anuais. A lógica de lookup de faixa
-- (dado prioridade + indicador + contagem acumulada, retornar a faixa e o
-- % de atingimento) é regra de negócio determinística, implementada fora
-- do banco -- NÃO é saída de modelo de ML e não deve ser apresentada como
-- tal no dashboard. Projeção/probabilidade de fechar o ano em qual faixa
-- fica fora de escopo desta tabela (decisão de produto pendente sobre
-- metodologia).
--
-- Grão: 1 linha por (prioridade_num, indicador, faixa). Faixas contíguas
-- e sem sobreposição -- faixa_min/faixa_max NULL só nas pontas abertas
-- ("< N" e "> N").
CREATE TABLE IF NOT EXISTS dw.ref_meta_sla_anual (
    ref_meta_sla_anual_sk text PRIMARY KEY,
    prioridade_num smallint NOT NULL,
    indicador text NOT NULL,
    faixa_min integer,
    faixa_max integer,
    pct_atingimento numeric NOT NULL,
    ordem_faixa smallint NOT NULL
);

INSERT INTO dw.ref_meta_sla_anual (
    ref_meta_sla_anual_sk, prioridade_num, indicador, faixa_min, faixa_max, pct_atingimento, ordem_faixa
)
VALUES
    -- P2 - Alta | ola_quebrado (meta oficial: max 31 quebras/ano)
    (MD5('2|ola_quebrado|' || COALESCE(NULL::text, '') || '|' || COALESCE(30::text, '')), 2, 'ola_quebrado', NULL, 30, 150, 1),
    (MD5('2|ola_quebrado|' || COALESCE(31::text, '') || '|' || COALESCE(35::text, '')), 2, 'ola_quebrado', 31, 35, 125, 2),
    (MD5('2|ola_quebrado|' || COALESCE(36::text, '') || '|' || COALESCE(39::text, '')), 2, 'ola_quebrado', 36, 39, 100, 3),
    (MD5('2|ola_quebrado|' || COALESCE(40::text, '') || '|' || COALESCE(45::text, '')), 2, 'ola_quebrado', 40, 45, 75, 4),
    (MD5('2|ola_quebrado|' || COALESCE(46::text, '') || '|' || COALESCE(53::text, '')), 2, 'ola_quebrado', 46, 53, 50, 5),
    (MD5('2|ola_quebrado|' || COALESCE(54::text, '') || '|' || COALESCE(NULL::text, '')), 2, 'ola_quebrado', 54, NULL, 0, 6),

    -- P3 - Média | ola_quebrado (meta oficial: max 201 quebras/ano)
    (MD5('3|ola_quebrado|' || COALESCE(NULL::text, '') || '|' || COALESCE(200::text, '')), 3, 'ola_quebrado', NULL, 200, 150, 1),
    (MD5('3|ola_quebrado|' || COALESCE(201::text, '') || '|' || COALESCE(230::text, '')), 3, 'ola_quebrado', 201, 230, 125, 2),
    (MD5('3|ola_quebrado|' || COALESCE(231::text, '') || '|' || COALESCE(263::text, '')), 3, 'ola_quebrado', 231, 263, 100, 3),
    (MD5('3|ola_quebrado|' || COALESCE(264::text, '') || '|' || COALESCE(290::text, '')), 3, 'ola_quebrado', 264, 290, 75, 4),
    (MD5('3|ola_quebrado|' || COALESCE(291::text, '') || '|' || COALESCE(320::text, '')), 3, 'ola_quebrado', 291, 320, 50, 5),
    (MD5('3|ola_quebrado|' || COALESCE(321::text, '') || '|' || COALESCE(NULL::text, '')), 3, 'ola_quebrado', 321, NULL, 0, 6),

    -- P2 - Alta | volume_tratado
    (MD5('2|volume_tratado|' || COALESCE(NULL::text, '') || '|' || COALESCE(4584::text, '')), 2, 'volume_tratado', NULL, 4584, 150, 1),
    (MD5('2|volume_tratado|' || COALESCE(4585::text, '') || '|' || COALESCE(5388::text, '')), 2, 'volume_tratado', 4585, 5388, 125, 2),
    (MD5('2|volume_tratado|' || COALESCE(5389::text, '') || '|' || COALESCE(6168::text, '')), 2, 'volume_tratado', 5389, 6168, 100, 3),
    (MD5('2|volume_tratado|' || COALESCE(6169::text, '') || '|' || COALESCE(6252::text, '')), 2, 'volume_tratado', 6169, 6252, 75, 4),
    (MD5('2|volume_tratado|' || COALESCE(6253::text, '') || '|' || COALESCE(6336::text, '')), 2, 'volume_tratado', 6253, 6336, 50, 5),
    (MD5('2|volume_tratado|' || COALESCE(6337::text, '') || '|' || COALESCE(NULL::text, '')), 2, 'volume_tratado', 6337, NULL, 0, 6),

    -- P3 - Média | volume_tratado
    (MD5('3|volume_tratado|' || COALESCE(NULL::text, '') || '|' || COALESCE(19488::text, '')), 3, 'volume_tratado', NULL, 19488, 150, 1),
    (MD5('3|volume_tratado|' || COALESCE(19489::text, '') || '|' || COALESCE(22116::text, '')), 3, 'volume_tratado', 19489, 22116, 125, 2),
    (MD5('3|volume_tratado|' || COALESCE(22117::text, '') || '|' || COALESCE(22524::text, '')), 3, 'volume_tratado', 22117, 22524, 100, 3),
    (MD5('3|volume_tratado|' || COALESCE(22525::text, '') || '|' || COALESCE(23892::text, '')), 3, 'volume_tratado', 22525, 23892, 75, 4),
    (MD5('3|volume_tratado|' || COALESCE(23893::text, '') || '|' || COALESCE(24276::text, '')), 3, 'volume_tratado', 23893, 24276, 50, 5),
    (MD5('3|volume_tratado|' || COALESCE(24277::text, '') || '|' || COALESCE(NULL::text, '')), 3, 'volume_tratado', 24277, NULL, 0, 6)
ON CONFLICT (ref_meta_sla_anual_sk) DO NOTHING;
