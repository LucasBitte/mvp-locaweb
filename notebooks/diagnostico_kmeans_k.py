"""
=============================================================================================
 Diagnostico read-only de k (numero de clusters) — PLAN.md Fase 10 / Anexo A.4.
=============================================================================================

 NAO retreina nem altera o K-Means em producao (ml.dim_cluster/ml.fct_perfil_cluster
 permanecem intocados). Reproduz EXATAMENTE o pre-processamento de
 notebooks/model_clustering_kmeans_Revisado.ipynb (outlier removal, cause_cols,
 encoding ciclico, frequency encoding, StandardScaler, PCA(n_components=3) —
 mesmos hiperparametros da producao) e varre k=2..8 medindo silhouette,
 Davies-Bouldin e inertia, para reportar se k=4 (valor hardcoded hoje) e
 defensavel. Decisao de retreinar ou nao fica para checkpoint humano — este
 script so imprime/salva o relatorio, nunca escreve em ml.dim_cluster/
 ml.fct_perfil_cluster.
=============================================================================================
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import davies_bouldin_score, silhouette_score
from sklearn.preprocessing import StandardScaler


def find_project_root(start: Path) -> Path:
    for p in [start, *start.parents]:
        if (p / ".git").exists() or (p / "etl").is_dir():
            return p
    return start


PROJECT_ROOT = find_project_root(Path(__file__).resolve().parent if "__file__" in dir() else Path.cwd())
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

SEED = 42
K_RANGE = range(2, 9)
N_COMPONENTS_PRODUCAO = 3   # mesmo valor hardcoded em producao — diagnostico isola so o efeito de k
K_PRODUCAO = 4


def preparar_features(df: pd.DataFrame) -> pd.DataFrame:
    """Replica cell [4] do notebook de producao: outlier removal + cause_cols +
    encoding ciclico + frequency encoding. Mesma logica, sem nenhuma alteracao."""
    numeric_cols = df.select_dtypes(include=["int64", "float64"]).columns.tolist()
    numeric_cols = [c for c in numeric_cols if c not in ["incident_id", "cluster", "data_abertura"]]

    outlier_counts = pd.DataFrame(index=df.index)
    for col in numeric_cols:
        Q1, Q3 = df[col].quantile(0.25), df[col].quantile(0.75)
        IQR = Q3 - Q1
        lower, upper = Q1 - 1.5 * IQR, Q3 + 1.5 * IQR
        outlier_counts[col] = ~((df[col] >= lower) & (df[col] <= upper))
    outlier_mask = outlier_counts.sum(axis=1) <= len(numeric_cols) * 0.5
    df_clean = df[outlier_mask].copy()

    cause_cols = [
        "prioridade_num", "grupo_designado", "categoria", "subcategoria", "produto",
        "hora_abertura", "turno_abertura", "dia_semana_num", "fora_horario_comercial",
        "abriu_fim_de_semana", "mes_abertura", "trimestre", "possui_pai", "triagem_incompleta",
    ]
    cause_cols_valid = [c for c in cause_cols if c in df_clean.columns]
    df_features = df_clean[cause_cols_valid].copy()

    for col, period in {"hora_abertura": 24, "dia_semana_num": 7, "mes_abertura": 12}.items():
        if col in df_features.columns:
            df_features[f"{col}_sin"] = np.sin(2 * np.pi * df_features[col] / period)
            df_features[f"{col}_cos"] = np.cos(2 * np.pi * df_features[col] / period)
            df_features = df_features.drop(columns=[col])

    for col in ["grupo_designado", "subcategoria", "produto", "categoria", "turno_abertura"]:
        if col in df_features.columns:
            freq_map = df_features[col].value_counts(normalize=True).to_dict()
            df_features[col] = df_features[col].map(freq_map).fillna(0)

    return df_features


def diagnosticar(X_pca: np.ndarray) -> pd.DataFrame:
    linhas = []
    for k in K_RANGE:
        model = KMeans(n_clusters=k, random_state=SEED, n_init=10, max_iter=300)
        labels = model.fit_predict(X_pca)
        linhas.append({
            "k": k,
            "silhouette": silhouette_score(X_pca, labels),
            "davies_bouldin": davies_bouldin_score(X_pca, labels),
            "inertia": model.inertia_,
        })
    return pd.DataFrame(linhas)


def main() -> None:
    from etl.db import get_engine

    engine = get_engine()
    df = pd.read_sql("SELECT * FROM ml.ml_cluster_dataset", engine)

    df_features = preparar_features(df)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(df_features.fillna(0))

    pca = PCA(n_components=N_COMPONENTS_PRODUCAO, random_state=SEED)
    X_pca = pca.fit_transform(X_scaled)
    variancia_explicada = sum(pca.explained_variance_ratio_) * 100

    print(f"Dataset: {X_scaled.shape[0]:,} incidentes, {X_scaled.shape[1]} features -> "
          f"PCA({N_COMPONENTS_PRODUCAO}) explica {variancia_explicada:.2f}% da variancia "
          f"(mesmo espaço usado em produção, k={K_PRODUCAO}).")

    resultado = diagnosticar(X_pca)
    print("\n== Diagnostico k=2..8 (silhouette mais alto e melhor; Davies-Bouldin mais baixo e melhor) ==")
    print(resultado.round(4).to_string(index=False))

    melhor_silhouette = resultado.loc[resultado["silhouette"].idxmax(), "k"]
    melhor_db = resultado.loc[resultado["davies_bouldin"].idxmin(), "k"]
    linha_producao = resultado[resultado.k == K_PRODUCAO].iloc[0]

    print(f"\nk que maximiza silhouette: {int(melhor_silhouette)}")
    print(f"k que minimiza Davies-Bouldin: {int(melhor_db)}")
    print(f"k=4 (produção): silhouette={linha_producao.silhouette:.4f}, "
          f"davies_bouldin={linha_producao.davies_bouldin:.4f}")

    out_dir = PROJECT_ROOT / "data" / "ml" / "kmeans"
    out_dir.mkdir(parents=True, exist_ok=True)
    caminho = out_dir / "diagnostico_k_2_a_8.parquet"
    resultado.to_parquet(caminho, index=False)
    print(f"\nRelatorio salvo em {caminho} — NENHUMA tabela do banco (ml.dim_cluster/"
          f"ml.fct_perfil_cluster) foi alterada. Decisao de retreinar e checkpoint humano.")


if __name__ == "__main__":
    main()
