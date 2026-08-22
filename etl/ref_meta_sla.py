"""Lookup de faixa em dw.ref_meta_sla_anual — regra de negócio determinística.

Esta função NÃO é saída de nenhum modelo de ML: é um lookup de tabela de
referência (dw.ref_meta_sla_anual, migration 024) contra os valores oficiais
do Dicionário de Dados do desafio. Nunca apresentar o resultado como
"previsão" ou "inteligência artificial" no dashboard — é aritmética simples
(em qual faixa uma contagem acumulada cai).

Não calcula projeção/probabilidade de fechar o ano em determinada faixa —
isso depende de uma decisão de metodologia (projeção linear? Poisson?) que
fica fora de escopo aqui. Esta função só resolve "dado N ocorrências
acumuladas no ano, em que faixa (e com que % de atingimento) eu estou hoje".
"""
from __future__ import annotations

from sqlalchemy import text

INDICADORES_VALIDOS = {"ola_quebrado", "volume_tratado"}


def faixa_meta_sla(engine, prioridade_num: int, indicador: str, contagem_acumulada: int) -> dict:
    """Retorna a faixa de dw.ref_meta_sla_anual em que `contagem_acumulada` cai.

    Só existem faixas para prioridade_num in (2, 3) — a meta anual de SLA só
    é definida para P2/P3 no Dicionário de Dados do desafio.
    """
    if indicador not in INDICADORES_VALIDOS:
        raise ValueError(f"indicador invalido: {indicador!r} (esperado um de {INDICADORES_VALIDOS})")
    if contagem_acumulada < 0:
        raise ValueError("contagem_acumulada nao pode ser negativa")

    sql = text(
        """
        SELECT prioridade_num, indicador, faixa_min, faixa_max, pct_atingimento, ordem_faixa
        FROM dw.ref_meta_sla_anual
        WHERE prioridade_num = :prioridade_num
          AND indicador = :indicador
          AND (faixa_min IS NULL OR :contagem >= faixa_min)
          AND (faixa_max IS NULL OR :contagem <= faixa_max)
        """
    )
    with engine.connect() as conn:
        row = conn.execute(
            sql,
            {"prioridade_num": prioridade_num, "indicador": indicador, "contagem": contagem_acumulada},
        ).mappings().first()

    if row is None:
        raise LookupError(
            f"nenhuma faixa cadastrada para prioridade_num={prioridade_num}, "
            f"indicador={indicador!r} — dw.ref_meta_sla_anual só cobre P2/P3"
        )
    return dict(row)
