#!/usr/bin/env python3
"""
Fase 2.2 — Computar base_value do SHAP

Carrega modelo XGBoost, calcula TreeExplainer, extrai base_value e valida.

Hipótese a validar:
  TreeExplainer explica a saída BRUTA do XGBoost (antes da calibração)
  Formula: base_value + Σshap_values == saída_bruta_xgboost

Uso:
  python3 scripts/compute_shap_base_value.py [--sample 100] [--output ml_dev]
"""
import argparse
import os
import sys
from pathlib import Path
from uuid import uuid4

import numpy as np
import pandas as pd
import psycopg2
from psycopg2.extras import execute_batch

try:
    import xgboost as xgb
    import shap
except ModuleNotFoundError as e:
    print(f"✗ Erro: {e}")
    print("  Instale: pip install xgboost shap")
    sys.exit(1)


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


def compute_base_value(sample_size: int = 100):
    """
    Calcula base_value do TreeExplainer.

    Returns:
      (base_value_scalar, shap_matrix, raw_predictions)
    """
    print("\n[1/3] Carregando modelo XGBoost...")

    # Carregar modelo
    model_path = Path("data/ml/xgboost/modelo_xgboost.pkl")
    if not model_path.exists():
        print(f"  ⚠️  Modelo não encontrado: {model_path}")
        print("  Procurando alternativas...")
        import glob
        candidates = glob.glob("notebooks/mlruns/**/xgboost_bundle.pkl", recursive=True)
        if candidates:
            model_path = Path(candidates[0])
            print(f"  → Encontrado: {model_path}")
        else:
            print("  ✗ Nenhum modelo encontrado")
            return None, None, None

    # Carregar dados de teste
    print("\n[2/3] Carregando dados de teste...")

    env_vars = load_env()
    conn = connect_db(env_vars)
    cur = conn.cursor()

    cur.execute("""
        SELECT * FROM ml.ml_sla_classification_dataset
        LIMIT %s
    """, (sample_size,))

    rows = cur.fetchall()
    column_names = [desc[0] for desc in cur.description]

    conn.close()

    # Montar DataFrame
    df = pd.DataFrame(rows, columns=column_names)

    # Remover colunas que não são features (id, target, etc)
    target_col = "excedeu_tempo_esperado"  # ou similar
    X = df.drop(columns=[col for col in df.columns if col in [target_col, 'id', 'incidente_id']], errors='ignore')

    print(f"  Shape: {X.shape}")
    print(f"  Features: {list(X.columns[:5])} ...")

    # Carregar modelo (simplificado — pode precisar ajuste conforme o formato real)
    print("\n[3/3] Calculando SHAP TreeExplainer...")
    try:
        # Tentar carregar do pickle
        import pickle
        with open(model_path, "rb") as f:
            modelo = pickle.load(f)
        print(f"  ✓ Modelo carregado: {type(modelo)}")
    except Exception as e:
        print(f"  ✗ Erro ao carregar: {e}")
        return None, None, None

    # TreeExplainer
    try:
        explainer = shap.TreeExplainer(modelo)
        print(f"  ✓ TreeExplainer criado")

        # Base value
        base_value = explainer.expected_value
        print(f"  ✓ Base value: {base_value}")

        # SHAP values
        shap_values = explainer.shap_values(X)
        print(f"  ✓ SHAP values shape: {shap_values.shape if hasattr(shap_values, 'shape') else type(shap_values)}")

        # Saídas brutas do XGBoost
        raw_pred = modelo.predict(X, output_margin=True)  # output_margin=True = saída bruta
        print(f"  ✓ Raw predictions shape: {raw_pred.shape}")

        return base_value, shap_values, raw_pred

    except Exception as e:
        print(f"  ✗ Erro no TreeExplainer: {e}")
        import traceback
        traceback.print_exc()
        return None, None, None


def validate_formula(base_value, shap_values, raw_pred, tolerance: float = 1e-3):
    """
    Valida: base_value + Σshap_values == raw_pred

    Returns: dict com estatísticas de erro
    """
    print("\n[Validação Matemática]")

    if shap_values is None:
        print("  ✗ SHAP values não calculados")
        return None

    # Somar SHAP values por linha
    if isinstance(shap_values, list):
        # Multi-class (retorna lista)
        shap_sum = np.array(shap_values[0]).sum(axis=1)  # classe 0
    else:
        # Binary
        shap_sum = shap_values.sum(axis=1)

    # Fórmula
    reconstructed = base_value + shap_sum

    # Erro
    errors = np.abs(reconstructed - raw_pred)

    print(f"  Base value: {base_value:.10f}")
    print(f"  Erro máximo: {errors.max():.10e}")
    print(f"  Erro médio: {errors.mean():.10e}")
    print(f"  Erro std: {errors.std():.10e}")
    print(f"  Registros com erro < 1e-6: {(errors < 1e-6).sum()} / {len(errors)}")

    result = {
        "base_value": float(base_value),
        "error_max": float(errors.max()),
        "error_mean": float(errors.mean()),
        "error_std": float(errors.std()),
        "records_within_tolerance": int((errors < tolerance).sum()),
        "total_records": len(errors),
        "formula_valid": errors.max() < tolerance,
    }

    if errors.max() < tolerance:
        print(f"  ✅ VALIDAÇÃO PASSOU: formula correta!")
    else:
        print(f"  ⚠️  Erro > {tolerance} — pode indicar:")
        print("     - SHAP explica saída calibrada (não bruta)")
        print("     - Unidades diferentes")
        print("     - Calibrador aplicado antes do SHAP")

    return result


def persist_to_db(base_value, schema: str = "ml_dev"):
    """Persiste base_value em ml_dev.fct_shap_incidente (nova coluna)"""
    print(f"\n[Persistência] Adicionando base_value ao schema {schema}")

    env_vars = load_env()
    conn = connect_db(env_vars)
    cur = conn.cursor()

    try:
        # Adicionar coluna se não existir
        cur.execute(f"""
            ALTER TABLE {schema}.fct_shap_incidente
            ADD COLUMN IF NOT EXISTS base_value NUMERIC;
        """)

        # Atualizar com valor calculado (simplificado)
        cur.execute(f"""
            UPDATE {schema}.fct_shap_incidente
            SET base_value = %s
            WHERE base_value IS NULL;
        """, (float(base_value),))

        conn.commit()
        print(f"  ✓ Coluna adicionada + {cur.rowcount} registros atualizados")
    except Exception as e:
        print(f"  ✗ Erro: {e}")
        conn.rollback()
    finally:
        conn.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", type=int, default=100, help="Tamanho da amostra")
    parser.add_argument("--output", default="ml_dev", choices=["ml", "ml_dev"], help="Schema de saída")
    parser.add_argument("--no-persist", action="store_true", help="Não persistir no DB")
    args = parser.parse_args()

    print("=" * 80)
    print("FASE 2.2 — Computar SHAP base_value")
    print("=" * 80)

    # Calcular
    base_value, shap_values, raw_pred = compute_base_value(sample_size=args.sample)

    if base_value is None:
        print("\n✗ Falha no cálculo — não foi possível continuar")
        sys.exit(1)

    # Validar
    result = validate_formula(base_value, shap_values, raw_pred)

    if result and result["formula_valid"]:
        print("\n" + "=" * 80)
        print("✅ SHAP base_value validado com sucesso!")
        print("=" * 80)
        print(f"base_value = {result['base_value']}")
        print(f"Fórmula: base_value + Σshap_values == saída_bruta_xgboost")
        print("\nPróximo: Persistir em ml_dev.fct_shap_incidente")

        if not args.no_persist:
            persist_to_db(base_value, schema=args.output)
    else:
        print("\n" + "=" * 80)
        print("⚠️  Validação inconclusa ou falhada")
        print("=" * 80)
        print("\nRecomendações:")
        print("1. Verificar se TreeExplainer explica saída calibrada (não bruta)")
        print("2. Conferir se há calibrador aplicado após o XGBoost")
        print("3. Revisar unidades das predições")


if __name__ == "__main__":
    main()
