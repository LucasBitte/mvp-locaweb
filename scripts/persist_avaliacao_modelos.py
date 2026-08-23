#!/usr/bin/env python3
"""
Fase 2 — Persistência de artefatos de avaliação em ml_dev.fct_avaliacao_modelo

Lê os 3 CSVs locais já existentes e escreve em formato longo na tabela genérica:
  1. Comparação Prophet vs. baseline (data/ml/prophet/metricas_avaliacao_final.csv)
  2. Backtest por equipe (data/ml/forecast_equipe/metricas_backtest_equipe.csv)
  3. Diagnóstico k=2..8 do K-Means (data/ml/kmeans/diagnostico_k_2_a_8.csv)

Todas as métricas entram em ml_dev.fct_avaliacao_modelo(modelo, metrica, valor, dimensao, chave_dimensao, is_baseline)

Uso:
  python3 scripts/persist_avaliacao_modelos.py [--schema ml|ml_dev]

  --schema ml_dev (default) para desenvolvimento/teste, não afeta produção
  --schema ml para sobrescrever a produção (requer confirmação)
"""
import argparse
import os
import sys
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pandas as pd
import psycopg2
from psycopg2.extras import execute_batch


def find_project_root(start: Path = None) -> Path:
    start = start or Path.cwd()
    if (start / ".git").exists() or (start / "etl" / "db.py").exists():
        return start
    if start.parent == start:
        raise RuntimeError("mvp-locaweb root not found")
    return find_project_root(start.parent)


def load_env():
    env_vars = {}
    env_file = find_project_root() / ".env"
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env_vars[k] = v
    return env_vars


def connect_db(env_vars):
    return psycopg2.connect(
        host=env_vars["FIAP_DB_HOST"],
        port=int(env_vars["FIAP_DB_PORT"]),
        database=env_vars["FIAP_DB_NAME"],
        user=env_vars["FIAP_DB_USER"],
        password=env_vars["FIAP_DB_PASSWORD"],
    )


def persist_prophet_baseline(conn, schema: str = "ml_dev"):
    """Lê data/ml/prophet/metricas_avaliacao_final.csv e persiste como linhas de (modelo, metrica, valor, is_baseline)"""
    print("\n[1/3] Prophet vs. Baseline...")

    root = find_project_root()
    csv_path = root / "data" / "ml" / "prophet" / "metricas_avaliacao_final.csv"

    if not csv_path.exists():
        print(f"  ⚠️  Arquivo não encontrado: {csv_path}")
        return 0

    df = pd.read_csv(csv_path)
    print(f"  Lido {len(df)} linhas do CSV")

    # Esperado: colunas como 'modelo', 'mae', 'wape', 'mase' e possivelmente 'baseline'
    # Transformar em formato longo: (modelo, metrica, valor, is_baseline)

    records = []
    data_execucao = datetime.now()

    for _, row in df.iterrows():
        modelo = row.get("modelo", "prophet_total")
        is_baseline = row.get("is_baseline", False)
        baseline_nome = row.get("baseline_nome", None) if is_baseline else None

        for csv_col, metric_name in [("MAE", "mae"), ("RMSE", "rmse"), ("WAPE%", "wape"), ("MASE", "mase")]:
            if csv_col in df.columns and pd.notna(row[csv_col]):
                sk = str(uuid4())
                records.append((
                    sk,
                    modelo,
                    "prophet_v1",
                    data_execucao,
                    None,  # dimensao
                    None,  # chave_dimensao
                    metric_name,
                    float(row[csv_col]),
                    is_baseline,
                    baseline_nome,
                    "scripts/persist_avaliacao_modelos.py"
                ))

    # Inserir
    cur = conn.cursor()
    sql = f"""
        INSERT INTO {schema}.fct_avaliacao_modelo
        (avaliacao_sk, modelo, modelo_versao, data_execucao, dimensao, chave_dimensao, metrica, valor, is_baseline, baseline_nome, origem)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    execute_batch(cur, sql, records, page_size=100)
    conn.commit()
    print(f"  ✓ {len(records)} registros inseridos em {schema}.fct_avaliacao_modelo")

    return len(records)


def persist_backtest_equipe(conn, schema: str = "ml_dev"):
    """Lê data/ml/forecast_equipe/metricas_backtest_equipe.csv"""
    print("\n[2/3] Backtest por equipe...")

    root = find_project_root()
    csv_path = root / "data" / "ml" / "forecast_equipe" / "metricas_backtest_equipe.csv"

    if not csv_path.exists():
        print(f"  ⚠️  Arquivo não encontrado: {csv_path}")
        return 0

    df = pd.read_csv(csv_path)
    print(f"  Lido {len(df)} linhas do CSV")

    records = []
    data_execucao = datetime.now()

    for _, row in df.iterrows():
        equipe = row.get("equipe") or row.get("grupo_id") or row.get("team_id")

        for csv_col, metric_name in [("MAE", "mae"), ("RMSE", "rmse"), ("WAPE%", "wape"), ("MASE", "mase")]:
            if csv_col in df.columns and pd.notna(row[csv_col]):
                sk = str(uuid4())
                records.append((
                    sk,
                    "prophet_equipe",
                    "prophet_v1",
                    data_execucao,
                    "equipe",  # dimensao
                    str(equipe),  # chave_dimensao
                    metric_name,
                    float(row[csv_col]),
                    False,  # is_baseline
                    None,  # baseline_nome
                    "scripts/persist_avaliacao_modelos.py"
                ))

    cur = conn.cursor()
    sql = f"""
        INSERT INTO {schema}.fct_avaliacao_modelo
        (avaliacao_sk, modelo, modelo_versao, data_execucao, dimensao, chave_dimensao, metrica, valor, is_baseline, baseline_nome, origem)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    execute_batch(cur, sql, records, page_size=100)
    conn.commit()
    print(f"  ✓ {len(records)} registros inseridos")

    return len(records)


def persist_diagnostico_kmeans(conn, schema: str = "ml_dev"):
    """Lê data/ml/kmeans/diagnostico_k_2_a_8.csv"""
    print("\n[3/3] Diagnóstico K-Means (k=2..8)...")

    root = find_project_root()
    csv_path = root / "data" / "ml" / "kmeans" / "diagnostico_k_2_a_8.csv"

    if not csv_path.exists():
        print(f"  ⚠️  Arquivo não encontrado: {csv_path}")
        return 0

    df = pd.read_csv(csv_path)
    print(f"  Lido {len(df)} linhas do CSV")

    records = []
    data_execucao = datetime.now()

    for _, row in df.iterrows():
        k = row.get("k") or row.get("n_clusters")

        for metric_col in ["silhouette", "davies_bouldin", "pca_variancia", "inertia"]:
            if metric_col in df.columns and pd.notna(row[metric_col]):
                sk = str(uuid4())
                records.append((
                    sk,
                    "kmeans",
                    "kmeans_v1",
                    data_execucao,
                    "k",  # dimensao
                    str(k),  # chave_dimensao
                    metric_col,
                    float(row[metric_col]),
                    False,  # is_baseline
                    None,  # baseline_nome
                    "scripts/persist_avaliacao_modelos.py"
                ))

    cur = conn.cursor()
    sql = f"""
        INSERT INTO {schema}.fct_avaliacao_modelo
        (avaliacao_sk, modelo, modelo_versao, data_execucao, dimensao, chave_dimensao, metrica, valor, is_baseline, baseline_nome, origem)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    execute_batch(cur, sql, records, page_size=100)
    conn.commit()
    print(f"  ✓ {len(records)} registros inseridos")

    return len(records)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schema", default="ml_dev", choices=["ml", "ml_dev"],
                       help="Schema de destino (ml_dev para dev, ml para produção)")
    args = parser.parse_args()

    if args.schema == "ml":
        print("⚠️  Você está prestes a escrever em PRODUÇÃO (schema ml).")
        confirm = input("Digite 'sim' para confirmar: ")
        if confirm.lower() != "sim":
            print("Cancelado.")
            return

    env_vars = load_env()
    conn = connect_db(env_vars)

    try:
        total = 0
        total += persist_prophet_baseline(conn, schema=args.schema)
        total += persist_backtest_equipe(conn, schema=args.schema)
        total += persist_diagnostico_kmeans(conn, schema=args.schema)

        print(f"\n{'='*70}")
        print(f"✓ Fase 2: Persistência concluída")
        print(f"  Total de registros: {total}")
        print(f"  Schema: {args.schema}")
        print(f"{'='*70}")
    except Exception as e:
        print(f"✗ Erro: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
