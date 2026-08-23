"""Gráficos comentados do modelo Prophet por equipe — complemento
educacional, não faz parte do pipeline de produção.

`notebooks/forecast_equipe.py` não persiste nenhum parquet local (só grava
em `ml.fct_previsao_grupo` via SQL) — este script lê direto do banco
`fiap` (SELECT read-only, sem nenhum INSERT/UPDATE/DELETE) e plota. Não
re-treina Prophet, não roda backtest.

Rodar (precisa que `notebooks/forecast_equipe.py` já tenha sido executado
ao menos uma vez, para `ml.fct_previsao_grupo`/`ml.fct_pressao_equipe`
terem dado real):

    ./venv/bin/python3 notebooks/forecast_equipe_graficos.py

Ver `docs/guia-modelo-prophet-equipe.md` para a leitura de cada gráfico.
"""
import os
from pathlib import Path

import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns

def _find_project_root(start: Path) -> Path:
    for p in [start, *start.parents]:
        if (p / '.git').exists():
            return p
    return start

_PROJECT_ROOT = _find_project_root(Path.cwd())
_OUT_DIR = Path(os.getenv('ML_OUTPUT_DIR', _PROJECT_ROOT / 'data' / 'ml' / 'forecast_equipe'))
_PLOT_DIR = _OUT_DIR / 'plots'
_PLOT_DIR.mkdir(parents=True, exist_ok=True)

import sys
sys.path.insert(0, str(_PROJECT_ROOT))
from etl.db import get_engine

sns.set_style('whitegrid')
COR_METODO = {'prophet_individual': '#1E6FD9', 'prophet_semanal': '#f59e0b', 'split_proporcional': '#7A8498'}
COR_NIVEL = {'critico': '#D64545', 'atencao': '#E8A317', 'normal': '#0F9D58'}

engine = get_engine()

# fct_previsao_grupo nao tem parquet local (arquitetura A/B/C so persiste em
# SQL) -- leitura read-only direta do banco fiap, sem nenhum INSERT/UPDATE.
metodo_equipe = pd.read_sql(
    """
    SELECT dg.grupo_designado, fpg.metodo
    FROM ml.fct_previsao_grupo fpg
    JOIN dw.dim_grupo dg ON fpg.dim_grupo_sk = dg.dim_grupo_sk
    WHERE fpg.origem = (SELECT MAX(origem) FROM ml.fct_previsao_grupo) AND fpg.h = 1
    """,
    engine,
)
media_diaria = pd.read_sql(
    """
    SELECT dg.grupo_designado, COUNT(*)::float / 365 AS media_diaria
    FROM dw.fct_incidentes fi
    JOIN dw.dim_grupo dg ON fi.dim_grupo_sk = dg.dim_grupo_sk
    GROUP BY dg.grupo_designado
    """,
    engine,
)
pressao = pd.read_sql(
    """
    SELECT dg.grupo_designado, fpe.yhat_previsto, fpe.media_historica_diaria,
           fpe.pressao_relativa_pct, fpe.nivel_pressao, fpe.metodo_origem
    FROM ml.fct_pressao_equipe fpe
    JOIN dw.dim_grupo dg ON fpe.dim_grupo_sk = dg.dim_grupo_sk
    WHERE fpe.origem = (SELECT MAX(origem) FROM ml.fct_pressao_equipe) AND fpe.h = 1
    """,
    engine,
)
previsao_curva = pd.read_sql(
    """
    SELECT dg.grupo_designado, fpg.metodo, fpg.horizonte, fpg.h, fpg.yhat,
           fpg.yhat_lower, fpg.yhat_upper
    FROM ml.fct_previsao_grupo fpg
    JOIN dw.dim_grupo dg ON fpg.dim_grupo_sk = dg.dim_grupo_sk
    WHERE fpg.origem = (SELECT MAX(origem) FROM ml.fct_previsao_grupo)
      AND dg.grupo_designado IN ('Team14', 'Team03', 'Team06')
    ORDER BY dg.grupo_designado, fpg.h
    """,
    engine,
)

merged = metodo_equipe.merge(media_diaria, on='grupo_designado')

# =============================================================================
# FIGURA 1 -- Arquitetura hibrida A/B/C: distribuicao e criterio
# =============================================================================
fig1, ax1 = plt.subplots(1, 2, figsize=(14, 5.5))

# 1. Distribuicao de metodo -- quantas das 16 equipes caem em cada metodo.
contagem = merged.metodo.value_counts().reindex(['prophet_individual', 'prophet_semanal', 'split_proporcional']).fillna(0)
ax1[0].bar(contagem.index, contagem.values, color=[COR_METODO[m] for m in contagem.index])
for i, v in enumerate(contagem.values):
    ax1[0].text(i, v + 0.2, f'{int(v)} equipes', ha='center', fontsize=10)
ax1[0].set_ylabel('Número de equipes')
ax1[0].set_title('Distribuição do método -- 16 equipes\n(escolhido por volume médio diário)')
ax1[0].set_ylim(0, 10)

# 2. Criterio de escolha -- volume medio diario por equipe (ordenado),
# colorido por metodo, com linhas de threshold em 1 e 5 incidentes/dia.
# Mostra visualmente POR QUE cada equipe caiu no metodo que caiu -- e por
# que Team12/Team17/Team02 (grupo "B" por volume) na pratica rodaram
# prophet_individual (so Team03 de fato caiu para semanal).
merged_ord = merged.sort_values('media_diaria', ascending=True)
cores_barra = [COR_METODO[m] for m in merged_ord.metodo]
ax1[1].barh(merged_ord.grupo_designado, merged_ord.media_diaria, color=cores_barra)
ax1[1].axvline(1, color='#101C2E', linestyle='--', linewidth=1, alpha=0.6, label='limiar 1/dia (C -> tenta B)')
ax1[1].axvline(5, color='#101C2E', linestyle='-', linewidth=1, alpha=0.6, label='limiar 5/dia (B -> A)')
ax1[1].set_xlabel('Média diária de incidentes (2025, calendário completo)')
ax1[1].set_title('Volume médio por equipe -- critério de escolha do método')
handles = [plt.Rectangle((0, 0), 1, 1, color=COR_METODO[m]) for m in COR_METODO] + \
          [plt.Line2D([0], [0], color='#101C2E', linestyle='--'), plt.Line2D([0], [0], color='#101C2E', linestyle='-')]
labels = list(COR_METODO.keys()) + ['limiar 1/dia', 'limiar 5/dia']
ax1[1].legend(handles, labels, fontsize=7, loc='lower right')

fig1.suptitle('Figura 1 -- Arquitetura híbrida A/B/C (Prophet individual / semanal / split proporcional)', fontsize=12, y=1.03)
fig1.tight_layout()
fig1.savefig(_PLOT_DIR / 'figura1_arquitetura_hibrida.png', dpi=110, bbox_inches='tight')
plt.close(fig1)
print('Figura 1 salva.')

# =============================================================================
# FIGURA 2 -- Pressao operacional por equipe (D+1) e curvas de previsao
# =============================================================================
fig2, ax2 = plt.subplots(1, 2, figsize=(14, 6))

# 3. Pressao relativa por equipe (D+1) -- desvio do previsto frente a
# media historica DA PROPRIA equipe (nao volume absoluto -- uma equipe
# pequena que dobra de volume pesa igual a uma grande que sobe 10%).
pressao_ord = pressao.sort_values('pressao_relativa_pct', ascending=True)
cores_pressao = [COR_NIVEL[n] for n in pressao_ord.nivel_pressao]
ax2[0].barh(pressao_ord.grupo_designado, pressao_ord.pressao_relativa_pct, color=cores_pressao)
ax2[0].axvline(0, color='#101C2E', linewidth=1)
ax2[0].set_xlabel('Pressão relativa (%) vs. média histórica da própria equipe')
ax2[0].set_title('Pressão operacional por equipe -- D+1\n(desvio relativo, não volume absoluto)')
handles2 = [plt.Rectangle((0, 0), 1, 1, color=COR_NIVEL[n]) for n in COR_NIVEL]
ax2[0].legend(handles2, list(COR_NIVEL.keys()), fontsize=8, loc='lower right', title='nível')

# 4. Curvas de previsao D+1..D+7 para 3 equipes representativas, uma de
# cada metodo -- mostra a "forma" da previsao por tipo de arquitetura:
# Team14 (prophet_individual, alto volume) tem curva propria com forma
# diaria; Team03 (prophet_semanal) e mais suave; Team06 (split_proporcional,
# volume quase zero) segue a proporcao do total, sem forma propria.
for equipe in ['Team14', 'Team03', 'Team06']:
    d = previsao_curva[previsao_curva.grupo_designado == equipe].sort_values('h')
    metodo = d.metodo.iloc[0]
    ax2[1].plot(d.h, d.yhat, marker='o', color=COR_METODO[metodo], label=f'{equipe} ({metodo})')
    ax2[1].fill_between(d.h, d.yhat_lower, d.yhat_upper, alpha=0.12, color=COR_METODO[metodo])
ax2[1].set_xlabel('Horizonte (D+h)')
ax2[1].set_ylabel('Incidentes/dia previstos')
ax2[1].set_title('Previsão D+1..D+7 -- 1 equipe por método\n(forma da curva varia com a arquitetura)')
ax2[1].legend(fontsize=8)

fig2.suptitle('Figura 2 -- Pressão operacional e formato da previsão por método', fontsize=12, y=1.03)
fig2.tight_layout()
fig2.savefig(_PLOT_DIR / 'figura2_pressao_curvas.png', dpi=110, bbox_inches='tight')
plt.close(fig2)
print('Figura 2 salva.')

# =============================================================================
# FIGURA 3 -- Metricas de backtest por equipe (Grupo A/B), a partir do CSV
# persistido por forecast_equipe.py (metricas_backtest_equipe.csv). So le e
# plota o modelo que efetivamente roda em producao por equipe (prophet_regime
# para quem ficou diario, a comparacao completa contra baselines fica no CSV
# para quem quiser conferir -- aqui so o resumo de producao).
# =============================================================================
metricas_equipe = pd.read_csv(_OUT_DIR / 'metricas_backtest_equipe.csv')
producao = metricas_equipe[metricas_equipe['modelo'] == 'prophet_regime'].sort_values('MAE')

COR_GRUPO = {'A': '#1E6FD9', 'B': '#7A8498'}

fig3, ax3 = plt.subplots(1, 2, figsize=(14, 5.5))

cores_grupo = [COR_GRUPO[g] for g in producao.grupo]
ax3[0].barh(producao.equipe, producao.MAE, color=cores_grupo)
ax3[0].set_xlabel('MAE (incidentes/dia, backtest de avaliação final)')
ax3[0].set_title('MAE por equipe -- modelo diário (prophet_regime)\nGrupo A vs. Grupo B')

ax3[1].barh(producao.equipe, producao['WAPE%'], color=cores_grupo)
ax3[1].set_xlabel('WAPE (%)')
ax3[1].set_title('WAPE por equipe -- modelo diário (prophet_regime)')

handles3 = [plt.Rectangle((0, 0), 1, 1, color=COR_GRUPO[g]) for g in COR_GRUPO]
ax3[0].legend(handles3, [f'Grupo {g}' for g in COR_GRUPO], fontsize=8, loc='lower right')

fig3.suptitle('Figura 3 -- Backtest por equipe: MAE e WAPE do modelo diário (Grupo A/B)', fontsize=12, y=1.03)
fig3.tight_layout()
fig3.savefig(_PLOT_DIR / 'figura3_metricas_backtest_equipe.png', dpi=110, bbox_inches='tight')
plt.close(fig3)
print('Figura 3 salva.')

print()
print('Nota sobre métricas: agora persistidas em')
print(f'{_OUT_DIR / "metricas_backtest_equipe.csv"} (uma linha por equipe x modelo')
print('testado no backtest -- prophet_regime + baselines), gravado por')
print('forecast_equipe.py a cada execução. Fecha a lacuna antes reportada aqui')
print('(só stdout) e na tabela copiada manualmente de docs/forecast-por-equipe.md §4.')
