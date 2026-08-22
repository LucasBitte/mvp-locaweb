"""public.incidentes -> modelo dimensional (schema dw).

Replica a camada Silver + o star schema, lendo direto de public.incidentes no
banco fiap. Ver db/migrations/008_fct_incidentes.sql para as adaptações de
regra feitas nesta migração (threshold da heurística de P2, fechado_sem_tecnico,
COALESCE nas chaves MD5).
"""
from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd
from sqlalchemy import text

from etl.db import get_engine

MIN_DATE = "2025-01-01"

SLA_THRESHOLD_HORAS = {1: 4, 2: 4, 3: 12, 4: 24, 5: 96}

DIA_SEMANA_NOMES = ["Domingo", "Segunda", "Terca", "Quarta", "Quinta", "Sexta", "Sabado"]
MES_NOMES = [
    "Janeiro", "Fevereiro", "Marco", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]


def md5_key(*parts: str) -> str:
    return hashlib.md5("".join(parts).encode("utf-8")).hexdigest()


def extrair_bronze(engine) -> pd.DataFrame:
    return pd.read_sql(text("SELECT * FROM public.incidentes"), engine)


def aplicar_silver(df: pd.DataFrame) -> pd.DataFrame:
    """Filtros + features derivadas, equivalentes ao notebook 03 original."""
    df = df[df["status"] != "Sem Intervenção"].copy()
    df = df[df["aberto"] >= pd.Timestamp(MIN_DATE)].copy()

    df["produto_f"] = df["produto"].fillna("Não Classificado")
    df["categoria_f"] = df["categoria"].fillna("Não Classificado")
    df["subcategoria_f"] = df["subcategoria"].fillna("Não Informada")
    df["codigo_fechamento_f"] = df["codigo_fechamento"].fillna("Não Informado")

    df["prioridade_num"] = df["prioridade"].str[0].astype(int)

    entrou_kpi = df["entrou_kpi"].astype(bool)
    kpi_violado = df["kpi_violado"].fillna(False).astype(bool)
    df["kpi_status_int"] = np.select(
        [~entrou_kpi, kpi_violado],
        [-1, 1],
        default=0,
    )

    df["possui_pai"] = df["incidente_pai"].notna()
    df["is_filho_de_problema"] = df["possui_pai"]

    df["duracao_horas"] = df["duracao_min"] / 60.0
    df["horas_ate_resolucao"] = (
        df["resolvido"] - df["aberto"]
    ).dt.total_seconds() / 3600
    df["foi_resolvido"] = df["resolvido"].notna()

    df["triagem_incompleta"] = df["subcategoria"].isna()

    # Regra literal do original: vocabulário de codigo_fechamento desta base
    # não contém esses valores, então esta coluna é sempre False aqui.
    df["fechado_sem_tecnico"] = df["codigo_fechamento"].isin(
        ["Resolvido pelo Usuário", "Sem Descrição"]
    )

    limites = df["prioridade_num"].map(SLA_THRESHOLD_HORAS)
    df["excedeu_tempo_esperado"] = (
        limites.notna() & (df["duracao_horas"] > limites)
    ).fillna(False)

    df["exige_intervencao"] = True  # sempre True pós-filtro de status

    # Target_Risco_SLA em 3 camadas (ver docstring do módulo).
    target = df["kpi_status_int"].copy()

    # Camada 2 — heurística para KPI desconhecido: P2 (threshold_sla=4h) com
    # duração acima do threshold. P2=4h é o valor oficial do Dicionário de
    # Dados do desafio (fonte da verdade) — a versão anterior deste código
    # usava 8h aqui, "corrigido" a partir de um SLA_THRESHOLD_HORAS que
    # estava errado em dim_prioridade (ver docs/modelo-dimensional.md,
    # seção "Correção de thresholds de SLA").
    heuristica = (
        (df["kpi_status_int"] == -1)
        & (df["prioridade_num"] == 2)
        & (df["duracao_horas"] > 4)
    )
    target = target.where(~heuristica, 1)

    # Camada 3 — isenções: incidente filho não carrega risco próprio.
    isencao = df["possui_pai"] | ~df["exige_intervencao"]
    target = target.where(~isencao, 0)

    # Fecha o invariante (0/1): qualquer -1 remanescente (KPI desconhecido,
    # sem heurística aplicável, sem isenção) vira 0 — sem risco sinalizado.
    df["target_risco_sla"] = target.replace(-1, 0).astype(int)

    df["score_risco_operacional"] = (
        (df["target_risco_sla"] == 1).astype(int) * 3
        + (df["prioridade_num"] <= 2).astype(int) * 2
        + df["exige_intervencao"].astype(int) * 1
        + df["possui_pai"].astype(int) * 1
        + (
            (df["aberto"].dt.hour < 8) | (df["aberto"].dt.hour >= 18)
        ).astype(int)
        * 1
    ).astype(int)

    return df


def construir_dim_produto_categoria(df: pd.DataFrame) -> pd.DataFrame:
    dim = df[["produto_f", "categoria_f", "subcategoria_f"]].drop_duplicates()
    dim = dim.rename(
        columns={
            "produto_f": "produto",
            "categoria_f": "categoria",
            "subcategoria_f": "subcategoria",
        }
    )
    dim["dim_produto_categoria_sk"] = dim.apply(
        lambda r: md5_key(r["produto"], r["categoria"], r["subcategoria"]), axis=1
    )
    return dim


def construir_dim_grupo(df: pd.DataFrame) -> pd.DataFrame:
    dim = df[["grupo_designado"]].drop_duplicates()
    dim["dim_grupo_sk"] = dim["grupo_designado"].map(md5_key)
    return dim


def construir_dim_tempo(df: pd.DataFrame) -> pd.DataFrame:
    datas = df["aberto"].dt.date.drop_duplicates().to_frame("data_abertura")
    d = pd.to_datetime(datas["data_abertura"])
    datas["dim_tempo_sk"] = datas["data_abertura"].map(lambda x: md5_key(str(x)))
    datas["ano"] = d.dt.year
    datas["mes_num"] = d.dt.month
    datas["nome_mes"] = d.dt.month.map(lambda m: MES_NOMES[m - 1])
    datas["semana_ano"] = d.dt.isocalendar().week.astype(int)
    datas["trimestre"] = d.dt.quarter
    datas["ano_mes"] = d.dt.strftime("%Y-%m")
    datas["dia_semana_num"] = (d.dt.dayofweek + 1) % 7  # 0=domingo, como no original
    datas["nome_dia"] = datas["dia_semana_num"].map(lambda i: DIA_SEMANA_NOMES[i])
    datas["is_fim_de_semana"] = datas["dia_semana_num"].isin([0, 6])
    return datas


def construir_dim_status(df: pd.DataFrame) -> pd.DataFrame:
    dim = df[["status", "codigo_fechamento_f", "entrou_kpi"]].drop_duplicates(
        subset=["status", "codigo_fechamento_f"]
    )
    dim = dim.rename(columns={"codigo_fechamento_f": "codigo_fechamento"})
    dim["dim_status_sk"] = dim.apply(
        lambda r: md5_key(r["status"], r["codigo_fechamento"]), axis=1
    )
    return dim.drop_duplicates(subset=["dim_status_sk"])


def _bucket_prioridade(p: int) -> str:
    return {1: "P1 - Critica", 2: "P2 - Alta", 3: "P3 - Moderada", 4: "P4 - Baixa"}.get(
        p, "Nao Classificada"
    )


def construir_dim_prioridade(df: pd.DataFrame) -> pd.DataFrame:
    dim = df[["prioridade_num", "prioridade"]].drop_duplicates()
    dim = dim.rename(columns={"prioridade": "prioridade_texto"})
    dim["dim_prioridade_sk"] = dim["prioridade_num"].map(lambda p: md5_key(str(p)))
    dim["bucket_prioridade"] = dim["prioridade_num"].map(_bucket_prioridade)
    dim["nivel_criticidade"] = np.where(dim["prioridade_num"] <= 2, "Critico", "Normal")
    dim["threshold_sla_horas"] = dim["prioridade_num"].map(SLA_THRESHOLD_HORAS)
    return dim


def construir_dim_abertura(df: pd.DataFrame) -> pd.DataFrame:
    dim = df[["aberto"]].drop_duplicates().rename(columns={"aberto": "aberto_at"})
    dim["dim_abertura_sk"] = dim["aberto_at"].map(lambda t: md5_key(str(t)))
    dim["hora_abertura"] = dim["aberto_at"].dt.hour
    dim["turno_abertura"] = pd.cut(
        dim["hora_abertura"],
        bins=[-1, 5, 11, 17, 23],
        labels=["Madrugada", "Manha", "Tarde", "Noite"],
    ).astype(str)
    dim["fora_horario_comercial"] = ~dim["hora_abertura"].between(8, 18)
    dim["abriu_fim_de_semana"] = dim["aberto_at"].dt.dayofweek.isin([5, 6])
    return dim


def construir_fato(df: pd.DataFrame) -> pd.DataFrame:
    fato = pd.DataFrame()
    fato["incident_sk"] = df["numero"].map(md5_key)
    fato["dim_produto_categoria_sk"] = df.apply(
        lambda r: md5_key(r["produto_f"], r["categoria_f"], r["subcategoria_f"]), axis=1
    )
    fato["dim_grupo_sk"] = df["grupo_designado"].map(md5_key)
    fato["dim_tempo_sk"] = df["aberto"].dt.date.map(lambda x: md5_key(str(x)))
    fato["dim_status_sk"] = df.apply(
        lambda r: md5_key(r["status"], r["codigo_fechamento_f"]), axis=1
    )
    fato["dim_prioridade_sk"] = df["prioridade_num"].map(lambda p: md5_key(str(p)))
    fato["dim_abertura_sk"] = df["aberto"].map(lambda t: md5_key(str(t)))

    fato["incident_id"] = df["numero"]
    fato["duracao_horas"] = df["duracao_horas"]
    fato["duracao_minutos"] = df["duracao_min"]
    fato["kpi_status_int"] = df["kpi_status_int"]
    fato["target_risco_sla"] = df["target_risco_sla"]
    fato["exige_intervencao"] = df["exige_intervencao"]
    fato["possui_pai"] = df["possui_pai"]
    fato["horas_ate_resolucao"] = df["horas_ate_resolucao"]
    fato["foi_resolvido"] = df["foi_resolvido"]
    fato["is_filho_de_problema"] = df["is_filho_de_problema"]
    fato["triagem_incompleta"] = df["triagem_incompleta"]
    fato["fechado_sem_tecnico"] = df["fechado_sem_tecnico"]
    fato["excedeu_tempo_esperado"] = df["excedeu_tempo_esperado"]
    fato["score_risco_operacional"] = df["score_risco_operacional"]
    fato["aberto_at"] = df["aberto"]
    fato["resolvido_at"] = df["resolvido"]
    fato["encerrado_at"] = df["encerrado"]
    return fato


def carregar(engine, tabelas: dict[str, pd.DataFrame]) -> None:
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE dw.fct_incidentes"))
        for nome in [
            "dim_produto_categoria",
            "dim_grupo",
            "dim_tempo",
            "dim_status",
            "dim_prioridade",
            "dim_abertura",
        ]:
            conn.execute(text(f"TRUNCATE dw.{nome} CASCADE"))

    for nome in [
        "dim_produto_categoria",
        "dim_grupo",
        "dim_tempo",
        "dim_status",
        "dim_prioridade",
        "dim_abertura",
        "fct_incidentes",
    ]:
        tabelas[nome].to_sql(
            nome, engine, schema="dw", if_exists="append", index=False
        )
        print(f"  {nome}: {len(tabelas[nome]):,} linhas")


def main() -> None:
    engine = get_engine()

    print("Extraindo public.incidentes...")
    bronze = extrair_bronze(engine)
    print(f"  {len(bronze):,} linhas brutas")

    print("Aplicando filtros e features (camada Silver)...")
    silver = aplicar_silver(bronze)
    print(f"  {len(silver):,} linhas apos filtros (status <> 'Sem Intervencao' e aberto >= {MIN_DATE})")

    print("Construindo dimensoes e fato...")
    tabelas = {
        "dim_produto_categoria": construir_dim_produto_categoria(silver),
        "dim_grupo": construir_dim_grupo(silver),
        "dim_tempo": construir_dim_tempo(silver),
        "dim_status": construir_dim_status(silver),
        "dim_prioridade": construir_dim_prioridade(silver),
        "dim_abertura": construir_dim_abertura(silver),
        "fct_incidentes": construir_fato(silver),
    }

    print("Carregando no schema dw (truncate + insert)...")
    carregar(engine, tabelas)
    print("OK.")


if __name__ == "__main__":
    main()
