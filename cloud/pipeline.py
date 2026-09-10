"""Comandos canônicos de CLAUDE.md; dependências explícitas, sem retreino implícito."""
import sys


def notebook(name):
    return [sys.executable, '-m', 'nbconvert', '--to', 'notebook', '--execute',
            '--inplace', '--ExecutePreprocessor.timeout=-1', f'notebooks/{name}.ipynb']


STEPS = {
    'silver': (notebook('03_bronze_silver_transformacao'), []),
    'dw': (notebook('04_dw_star_schema'), ['silver']),
    'marts': (notebook('05_ml_feature_marts'), ['dw']),
    'forecast_total': ([sys.executable, 'notebooks/forecast_incidentes_revisado.py', '--fonte', 'sql'], ['marts']),
    'forecast_equipe': ([sys.executable, 'notebooks/forecast_equipe.py', '--fonte', 'sql'], ['forecast_total']),
    'pressao': ([sys.executable, 'notebooks/pressao_equipe.py'], ['forecast_equipe']),
    'forecast_produto': ([sys.executable, 'notebooks/forecast_produto.py'], ['forecast_total']),
    'recorrencia': ([sys.executable, 'notebooks/recorrencia.py'], ['dw']),
    'clustering': (notebook('model_clustering_kmeans_Revisado'), ['marts']),
    'risco': (notebook('model_risk_xgboost_'), ['marts']),
    'diagnostico': ([sys.executable, 'notebooks/diagnostico_kmeans_k.py'], ['clustering']),
}
