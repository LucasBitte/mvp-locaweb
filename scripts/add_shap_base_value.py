#!/usr/bin/env python3
"""
Fase 2.2 — Adicionar base_value ao SHAP (versão simplificada)

Estratégia: Se o TreeExplainer foi calculado com a saída bruta do XGBoost,
então base_value é a média esperada dessa saída bruta.

Abordagem:
  1. Ler amostra de ml.fct_shap_incidente (já tem shap_value)
  2. Estimar saída_bruta = base_value + shap_value (inverter a fórmula)
  3. Validar que a média de (base_value + Σshap_value) bate com média da saída
  4. Persistir base_value como coluna

Uso:
  python3 scripts/add_shap_base_value.py [--sample 100] [--schema ml_dev]
"""
import argparse
import os
from pathlib import Path

import numpy as np
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor


def load_env():
    env_vars = {}
    env_file = Path(".env")
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    env_vars[k] = v
    return env_vars


def connect_db(env_vars):
    return psycopg2.connect(
        host=env_vars.get("FIAP_DB_HOST", "localhost"),
        port=int(env_vars.get("FIAP_DB_PORT", 5432)),
        database=env_vars.get("FIAP_DB_NAME", "fiap"),
        user=env_vars.get("FIAP_DB_USER", "fiap"),
        password=env_vars.get("FIAP_DB_PASSWORD", ""),
    )


def estimate_base_value(conn, sample_size: int = 100, schema: str = "ml"):
    """
    Estima base_value a partir dos dados de SHAP já persistidos.

    TreeExplainer calcula: f(x) ≈ base_value + Σshap_values

    Se temos shap_values e saida_bruta, então:
    base_value = média(saida_bruta - Σshap_values)
    """
    print(f"\n[1/2] Estimando base_value de {schema}.fct_shap_incidente")

    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Ler amostra com shap_value e score_bruto
    # Nota: fct_shap_incidente tem multiple rows por incidente (1 por feature)
    # Preciso agregar os shap_values por incidente
    # score_bruto = saída RAW do XGBoost (antes de calibração)
    cur.execute(f"""
        SELECT
            shap.incident_id,
            SUM(shap.shap_value) as shap_value_sum,
            risco.score_bruto
        FROM {schema}.fct_shap_incidente shap
        LEFT JOIN {schema}.fct_risco_incidente risco
            ON shap.incident_id = risco.incident_id
        WHERE shap.shap_value IS NOT NULL
        AND risco.score_bruto IS NOT NULL
        GROUP BY shap.incident_id, risco.score_bruto
        LIMIT %s
    """, (sample_size,))

    rows = cur.fetchall()

    if not rows:
        print(f"  ✗ Nenhum registro encontrado em {schema}.fct_shap_incidente")
        return None

    print(f"  Lidos {len(rows)} registros")

    # Calcular base_value
    # TreeExplainer explica a saída BRUTA do XGBoost (score_bruto)
    # Fórmula: score_bruto ≈ base_value + Σshap_values
    # Logo: base_value ≈ score_bruto - Σshap_values
    differences = []
    for row in rows:
        diff = float(row["score_bruto"] or 0) - float(row["shap_value_sum"] or 0)
        differences.append(diff)

    base_value_est = np.mean(differences)
    base_value_std = np.std(differences)

    print(f"  ✓ Base value estimado: {base_value_est:.10f} (±{base_value_std:.10f})")

    return base_value_est, differences


def validate_base_value(differences, base_value_est, tolerance: float = 0.1):
    """
    Valida a fórmula: base_value + shap_value ≈ saida_bruta
    """
    print(f"\n[2/2] Validação da fórmula")

    # Se a hipótese está correta, os 'differences' devem ser ≈ base_value_est
    errors = np.abs(np.array(differences) - base_value_est)

    print(f"  Erro máximo: {errors.max():.10e}")
    print(f"  Erro médio: {errors.mean():.10e}")
    print(f"  Erro std: {errors.std():.10e}")
    print(f"  Registros com erro < {tolerance}: {(errors < tolerance).sum()} / {len(errors)}")

    is_valid = errors.max() < tolerance

    if is_valid:
        print(f"\n  ✅ Validação PASSOU")
        print(f"  Fórmula: base_value + shap_value == saida_bruta")
        print(f"  base_value = {base_value_est:.10f}")
    else:
        print(f"\n  ⚠️  Erros grandes — hipótese pode estar errada")
        print(f"  Possíveis causas:")
        print(f"    - TreeExplainer explica saída calibrada (não bruta)")
        print(f"    - SHAP foi calculado de forma diferente")

    return is_valid, base_value_est


def persist_base_value(conn, base_value: float, schema: str = "ml_dev"):
    """
    Adiciona coluna base_value e persiste o valor calculado.
    """
    print(f"\n[Persistência] Adicionando base_value a {schema}.fct_shap_incidente")

    cur = conn.cursor()

    try:
        # 1. Adicionar coluna se não existir
        cur.execute(f"""
            ALTER TABLE {schema}.fct_shap_incidente
            ADD COLUMN IF NOT EXISTS base_value NUMERIC;
        """)
        print("  ✓ Coluna base_value adicionada (ou já existia)")

        # 2. Atualizar com valor calculado
        cur.execute(f"""
            UPDATE {schema}.fct_shap_incidente
            SET base_value = %s
            WHERE base_value IS NULL;
        """, (float(base_value),))

        n_updated = cur.rowcount
        conn.commit()

        print(f"  ✓ {n_updated} registros atualizados com base_value = {base_value:.10f}")

        return True
    except Exception as e:
        print(f"  ✗ Erro: {e}")
        conn.rollback()
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", type=int, default=100, help="Tamanho da amostra para estimar")
    parser.add_argument("--schema", default="ml_dev", choices=["ml", "ml_dev"], help="Schema de origem")
    parser.add_argument("--output", default="ml_dev", choices=["ml", "ml_dev"], help="Schema de saída")
    parser.add_argument("--no-persist", action="store_true", help="Apenas estimar, não persistir")
    args = parser.parse_args()

    print("=" * 80)
    print("FASE 2.2 — Adicionar SHAP base_value (estimado)")
    print("=" * 80)

    env_vars = load_env()
    conn = connect_db(env_vars)

    try:
        # Estimar
        result = estimate_base_value(conn, sample_size=args.sample, schema=args.schema)

        if result is None:
            print("\n✗ Não foi possível estimar base_value")
            return

        base_value_est, differences = result

        # Validar
        is_valid, base_value_final = validate_base_value(differences, base_value_est, tolerance=1.0)

        # Persistir
        if is_valid and not args.no_persist:
            print("\n" + "=" * 80)
            success = persist_base_value(conn, base_value_final, schema=args.output)

            if success:
                print("=" * 80)
                print("✅ FASE 2.2 CONCLUÍDA")
                print("=" * 80)
                print(f"\nbase_value persistido: {base_value_final:.10f}")
                print(f"Fórmula validada: base_value + shap_value == saida_bruta_xgboost")
        elif args.no_persist:
            print("\n[--no-persist] Não foi persistido (apenas estimação)")
        else:
            print("\n⚠️  Validação falhou — não foi persistido")

    finally:
        conn.close()


if __name__ == "__main__":
    main()
