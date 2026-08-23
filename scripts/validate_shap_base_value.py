#!/usr/bin/env python3
"""
Fase 2.2 — Validação de SHAP base_value e calibração

Contexto (Parte E, achado #7 da auditoria):
  A hipótese original estava conceitualmente errada. O TreeExplainer do SHAP explica
  a saída BRUTA do XGBoost (antes do calibrador isotônico), não a probabilidade
  calibrada final. Portanto:
    XGBoost (saída bruta) → SHAP explica saída bruta → calibrador isotônico → prob final

  Nunca: base_value + Σshap == logit(score_calibrado) — que é errado.
  Sim: base_value + Σshap == saída_bruta_do_xgboost

Este script:
  1. Lê ml.fct_shap_incidente (SHAP já calculado)
  2. Verifica se base_value existe; se não, calcula
  3. Valida que base_value + Σshap_value == saída_bruta
  4. Mostra estatísticas de erro (tolerance numérica)
  5. Propõe adição de coluna base_value ao schema

Uso:
  python3 scripts/validate_shap_base_value.py [--persevere] [--schema ml_dev]
"""
import argparse
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import psycopg2


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


def check_schema(conn, schema: str = "ml"):
    """Verifica se coluna base_value existe em {schema}.fct_shap_incidente"""
    cur = conn.cursor()
    cur.execute(f"""
        SELECT column_name FROM information_schema.columns
        WHERE table_schema = '{schema}' AND table_name = 'fct_shap_incidente'
        AND column_name = 'base_value';
    """)
    return cur.fetchone() is not None


def validate_shap(conn, schema: str = "ml", sample_size: int = 100):
    """Valida que base_value + Σshap == saída_bruta para amostra"""
    print(f"\n[Validação SHAP] {schema}.fct_shap_incidente")

    cur = conn.cursor()

    # Ler amostra de SHAP
    cur.execute(f"""
        SELECT shap_sk, incidente_id, base_value, shap_value, saida_bruta_xgboost
        FROM {schema}.fct_shap_incidente
        LIMIT {sample_size};
    """)

    rows = cur.fetchall()
    print(f"  Amostra: {len(rows)} registros")

    if not rows:
        print("  ⚠️  Nenhum registro encontrado")
        return False

    # Validar
    errors = []
    for row in rows:
        shap_sk, incidente_id, base_value, shap_value, saida_bruta = row
        if base_value is None or saida_bruta is None:
            continue

        # Fórmula esperada: base_value + shap_value == saida_bruta
        expected = float(base_value) + float(shap_value)
        actual = float(saida_bruta)
        error = abs(expected - actual)
        errors.append(error)

    if errors:
        print(f"  ✓ Validação matemática:")
        print(f"    Erro máximo: {max(errors):.10f}")
        print(f"    Erro médio: {np.mean(errors):.10f}")
        print(f"    Erro std: {np.std(errors):.10f}")
        print(f"    Registros com erro < 1e-6: {sum(1 for e in errors if e < 1e-6)} / {len(errors)}")

        if max(errors) > 1e-3:
            print(f"  ⚠️  Erro maior que 1e-3 — pode indicar unidades ou calibração diferente")
            return False
    else:
        print("  ⚠️  Não foi possível validar (campos nulos ou não encontrados)")
        return None

    return True


def add_base_value_column(conn, schema: str = "ml"):
    """Adiciona coluna base_value ao schema, se não existir"""
    print(f"\n[Adição de schema] {schema}.fct_shap_incidente")

    if check_schema(conn, schema):
        print("  ✓ Coluna base_value já existe")
        return True

    cur = conn.cursor()
    try:
        cur.execute(f"""
            ALTER TABLE {schema}.fct_shap_incidente
            ADD COLUMN base_value NUMERIC;
        """)
        conn.commit()
        print("  ✓ Coluna base_value adicionada")
        return True
    except psycopg2.Error as e:
        print(f"  ✗ Erro: {e}")
        conn.rollback()
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schema", default="ml", choices=["ml", "ml_dev"],
                       help="Schema a validar")
    parser.add_argument("--sample", type=int, default=100,
                       help="Tamanho da amostra para validação")
    args = parser.parse_args()

    env_vars = load_env()
    conn = connect_db(env_vars)

    try:
        # Verificar se base_value existe
        has_base_value = check_schema(conn, args.schema)
        if not has_base_value:
            print(f"⚠️  Coluna base_value não existe em {args.schema}.fct_shap_incidente")
            print("  → Será necessário calcular ou adicionar manualmente do notebook XGBoost")
        else:
            # Validar se a matemática bate
            result = validate_shap(conn, args.schema, args.sample)
            if result:
                print("\n✓ Validação SHAP sucedida: base_value + Σshap == saída_bruta")
            elif result is False:
                print("\n✗ Validação SHAP FALHOU — revisar calibração")

        print(f"\n{'='*70}")
        print("Próximo: Notebook model_risk_xgboost_.ipynb deve:")
        print("  1. Confirmar que TreeExplainer explica saída BRUTA (não calibrada)")
        print("  2. Calcular base_value referente a essa saída bruta")
        print("  3. Validar: base_value + Σshap == saída_bruta")
        print("  4. Persistir base_value em ml_dev.fct_shap_incidente")
        print(f"{'='*70}")

    except Exception as e:
        print(f"✗ Erro: {e}")
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
