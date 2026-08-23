"""Gráficos comentados do modelo Prophet (forecast total) — complemento
educacional, não faz parte do pipeline de produção.

`notebooks/forecast_incidentes_revisado.py` deliberadamente não gera
imagem (comentário no próprio script: "cada painel do antigo gráfico vira
um parquet... quem quiser o gráfico plota a partir daqui"). Este script lê
só os parquets já persistidos em `data/ml/prophet/` (execução real) e
plota — não re-treina Prophet, não roda backtest, não escreve em
`ml.fct_previsao_*` nem em nenhuma tabela do banco `fiap`.

Rodar depois de `python notebooks/forecast_incidentes_revisado.py --fonte sql`
(precisa que os parquets já existam):

    ./venv/bin/python3 notebooks/forecast_incidentes_graficos.py

Ver `docs/guia-modelo-prophet-forecast.md` para a leitura de cada gráfico.
"""
import os
from pathlib import Path

import numpy as np
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
_OUT_DIR = Path(os.getenv('ML_OUTPUT_DIR', _PROJECT_ROOT / 'data' / 'ml' / 'prophet'))
_PLOT_DIR = _OUT_DIR / 'plots'
_PLOT_DIR.mkdir(parents=True, exist_ok=True)

sns.set_style('whitegrid')
MODELO_PRODUCAO = 'prophet_regime'
COR_MODELOS = {
    'prophet_regime': '#1E6FD9', 'prophet_hist_completo': '#7A8498',
    'mediana_dow_4sem': '#0F9D58', 'snaive_lag7': '#8a6210',
    'ma7': '#D64545', 'ma28': '#f59e0b', 'ens_ma7_ma28': '#3b82f6',
    'naive_ultimo': '#101C2E',
}

serie = pd.read_parquet(_OUT_DIR / 'serie_diaria.parquet')
backtest = pd.read_parquet(_OUT_DIR / 'backtest_bruto.parquet')
metricas = pd.read_parquet(_OUT_DIR / 'metricas_avaliacao_final.parquet')
por_horizonte = pd.read_parquet(_OUT_DIR / 'diagnostico_por_horizonte.parquet')
acf = pd.read_parquet(_OUT_DIR / 'acf_residuos.parquet')
forecast_futuro = pd.read_parquet(_OUT_DIR / 'forecast_d1_d7.parquet')

# =============================================================================
# FIGURA 1 -- Real vs. previsto e comparacao de modelos
# =============================================================================
fig1, ax1 = plt.subplots(1, 2, figsize=(15, 5.5))

# 1. Real vs. previsto ao longo do tempo (h=1, periodo de avaliacao final --
# o mesmo periodo que gera os numeros de metricas_avaliacao_final.parquet,
# nao o de tuning). Mostra o modelo de producao com faixa de intervalo.
bt_h1 = backtest[(backtest.modelo == MODELO_PRODUCAO) & (backtest.h == 1) & (backtest.periodo == 'avaliacao_final')].sort_values('ds')
ax1[0].fill_between(bt_h1.ds, bt_h1.lo, bt_h1.hi, alpha=0.2, color=COR_MODELOS[MODELO_PRODUCAO], label='intervalo previsto')
ax1[0].plot(bt_h1.ds, bt_h1.y, color='#101C2E', linewidth=1.5, label='real')
ax1[0].plot(bt_h1.ds, bt_h1.yhat, color=COR_MODELOS[MODELO_PRODUCAO], linewidth=1.5, linestyle='--', label=f'{MODELO_PRODUCAO} (previsto)')
ax1[0].set_xlabel('Data')
ax1[0].set_ylabel('Incidentes/dia')
ax1[0].set_title(f'Real vs. previsto -- D+1, período de avaliação final\n({MODELO_PRODUCAO}, n={len(bt_h1)} origens)')
ax1[0].legend(fontsize=8)
ax1[0].tick_params(axis='x', rotation=30)

# 2. Comparacao de modelos -- MAE de cada um dos 8 modelos testados no
# backtest, ordenado do melhor pro pior. O modelo de producao (prophet_regime)
# NAO e o melhor -- mediana_dow_4sem (um baseline simples, mediana das
# ultimas 4 semanas no mesmo dia da semana) tem MAE menor. Achado ja
# documentado em docs/metricas-validacao.md, este grafico so o visualiza.
met_ord = metricas.sort_values('MAE')
cores_barra = [COR_MODELOS.get(m, '#7A8498') for m in met_ord.modelo]
bordas = ['#101C2E' if m == MODELO_PRODUCAO else 'none' for m in met_ord.modelo]
bars = ax1[1].barh(met_ord.modelo, met_ord.MAE, color=cores_barra, edgecolor=bordas, linewidth=2)
for i, v in enumerate(met_ord.MAE):
    ax1[1].text(v + 0.5, i, f'{v:.1f}', va='center', fontsize=8)
ax1[1].set_xlabel('MAE (erro médio absoluto, incidentes/dia)')
ax1[1].set_title('Comparação de modelos -- MAE no backtest\n(borda escura = modelo em produção; menor é melhor)')

fig1.suptitle('Figura 1 -- Acurácia do forecast e comparação com baselines', fontsize=13, y=1.03)
fig1.tight_layout()
fig1.savefig(_PLOT_DIR / 'figura1_acuracia_comparacao.png', dpi=110, bbox_inches='tight')
plt.close(fig1)
print('Figura 1 salva.')

# =============================================================================
# FIGURA 2 -- Degradacao por horizonte e ruido residual (ACF)
# =============================================================================
fig2, ax2 = plt.subplots(1, 2, figsize=(13, 5.5))

# 3. MAE e cobertura por horizonte (D+1..D+7) -- mostra a degradacao
# monotonica: o modelo erra mais e cobre menos conforme o horizonte cresce,
# que e o esperado (mais incerteza mais longe no futuro), mas quantifica
# exatamente o tamanho dessa degradacao.
ph = por_horizonte[por_horizonte.modelo == MODELO_PRODUCAO].sort_values('h')
ax2b = ax2[0].twinx()
l1 = ax2[0].plot(ph.h, ph.MAE, marker='o', color='#D64545', label='MAE')
l2 = ax2b.plot(ph.h, ph['cobertura%'], marker='s', color='#1E6FD9', label='Cobertura %')
ax2b.axhline(80, color='#1E6FD9', linestyle=':', linewidth=1, alpha=0.6, label='nível nominal (80%)')
ax2[0].set_xlabel('Horizonte (D+h)')
ax2[0].set_ylabel('MAE', color='#D64545')
ax2b.set_ylabel('Cobertura do intervalo (%)', color='#1E6FD9')
ax2[0].set_title(f'MAE e cobertura por horizonte\n({MODELO_PRODUCAO}: erro sobe, cobertura cai)')
lines = l1 + l2
ax2[0].legend(lines, [l.get_label() for l in lines], fontsize=8, loc='center left')

# 4. Autocorrelacao dos residuos (h=1) -- residuos de um bom modelo devem
# se parecer com ruido branco (ACF baixa em todos os lags). ACF alta em
# algum lag = ainda sobra padrao sistematico que o modelo nao capturou.
acf_h1 = acf[(acf.modelo == MODELO_PRODUCAO) & (acf.horizonte == 1)].sort_values('lag')
cores_acf = ['#D64545' if abs(v) > 0.2 else '#1E6FD9' for v in acf_h1.autocorrelacao]
ax2[1].bar(acf_h1.lag, acf_h1.autocorrelacao, color=cores_acf)
ax2[1].axhline(0, color='#101C2E', linewidth=1)
ax2[1].axhline(0.2, color='#B0B0B0', linestyle='--', linewidth=1)
ax2[1].axhline(-0.2, color='#B0B0B0', linestyle='--', linewidth=1, label='limiar informal ±0,2')
ax2[1].set_xlabel('Lag (dias)')
ax2[1].set_ylabel('Autocorrelação')
ax2[1].set_title(f'Autocorrelação dos resíduos (D+1)\n(vermelho = acima do limiar informal, ainda há padrão não capturado)')
ax2[1].legend(fontsize=8)

fig2.suptitle('Figura 2 -- Degradação por horizonte e qualidade dos resíduos', fontsize=13, y=1.03)
fig2.tight_layout()
fig2.savefig(_PLOT_DIR / 'figura2_horizonte_residuos.png', dpi=110, bbox_inches='tight')
plt.close(fig2)
print('Figura 2 salva.')

# =============================================================================
# FIGURA 3 -- Serie historica (com quebra de patamar) e previsao futura
# =============================================================================
fig3, ax3 = plt.subplots(1, 2, figsize=(14, 5.5))

# 5. Serie historica completa com a(s) quebra(s) de patamar detectada(s) --
# recalculo LEVE (mediana movel de 28 dias, razao m/m.shift(28), quebra se
# razao>2 ou <0.5 -- mesma logica de validar_serie() no script de producao,
# celula nao re-treina Prophet, só lê serie_diaria.parquet já persistido).
serie_ord = serie.sort_values('ds').reset_index(drop=True)
m28 = serie_ord.y.rolling(28).median()
razao = m28 / m28.shift(28)
quebras = serie_ord.loc[(razao > 2) | (razao < 0.5), 'ds']

ax3[0].plot(serie_ord.ds, serie_ord.y, color='#101C2E', linewidth=1, alpha=0.5, label='y (diário)')
ax3[0].plot(serie_ord.ds, m28, color='#1E6FD9', linewidth=2, label='mediana móvel 28d')
for i, q in enumerate(quebras):
    ax3[0].axvline(q, color='#D64545', linestyle='--', linewidth=1, alpha=0.7,
                    label='quebra de patamar detectada' if i == 0 else None)
ax3[0].set_xlabel('Data')
ax3[0].set_ylabel('Incidentes/dia')
ax3[0].set_title(f'Série histórica 2025 -- {len(quebras)} quebra(s) de patamar detectada(s)\n(razão mediana 28d atual/anterior > 2x ou < 0,5x)')
ax3[0].legend(fontsize=8)
ax3[0].tick_params(axis='x', rotation=30)

# 6. Previsao futura D+1..D+7 com intervalo (fan chart) -- a previsao que
# de fato alimenta o dashboard (Painel), com a incerteza crescente que a
# Figura 2 (cobertura por horizonte) já quantificou numericamente.
ax3[1].fill_between(forecast_futuro.horizonte, forecast_futuro.yhat_lower, forecast_futuro.yhat_upper,
                     alpha=0.25, color='#1E6FD9', label='intervalo (80%)')
ax3[1].plot(forecast_futuro.horizonte, forecast_futuro.yhat, marker='o', color='#1E6FD9', linewidth=2, label='previsto')
for _, r in forecast_futuro.iterrows():
    ax3[1].annotate(f'{r.yhat:.0f}', (r.horizonte, r.yhat), textcoords='offset points', xytext=(0, 8), fontsize=8, ha='center')
ax3[1].set_xlabel('Horizonte')
ax3[1].set_ylabel('Incidentes/dia previstos')
ax3[1].set_title(f'Previsão D+1..D+7 (origem {forecast_futuro.origem.iloc[0].date()})\ncom intervalo de 80%, alarga com o horizonte')
ax3[1].legend(fontsize=8)

fig3.suptitle('Figura 3 -- Estabilidade da série e previsão futura', fontsize=13, y=1.03)
fig3.tight_layout()
fig3.savefig(_PLOT_DIR / 'figura3_serie_previsao_futura.png', dpi=110, bbox_inches='tight')
plt.close(fig3)
print('Figura 3 salva.')

# =============================================================================
# OUTRA METRICA RECOMENDADA -- Pinball Loss (Quantile Loss) do intervalo
# =============================================================================
# As metricas ja reportadas (MAE/RMSE/WAPE/MASE) avaliam so o PONTO central
# da previsao (yhat); cobertura% avalia SE o intervalo contem o valor real,
# mas nao QUANTO ele erra quando erra, nem se o intervalo e desnecessariamente
# largo. Pinball Loss (quantile loss) penaliza tanto a distancia quanto a
# assimetria: errar pra fora do intervalo custa mais que a distancia até a
# borda mais próxima, ponderado pelo quantil (aqui, 10% e 90%, para o
# intervalo de 80%).
def pinball_loss(y_true, y_pred_quantil, quantil):
    erro = y_true - y_pred_quantil
    return np.mean(np.maximum(quantil * erro, (quantil - 1) * erro))

bt_final = backtest[(backtest.modelo == MODELO_PRODUCAO) & (backtest.periodo == 'avaliacao_final')]
pl_10 = pinball_loss(bt_final.y.values, bt_final.lo.values, 0.10)
pl_90 = pinball_loss(bt_final.y.values, bt_final.hi.values, 0.90)

print()
print('Outra métrica recomendada (partição de avaliação final, complementa MAE/RMSE/WAPE/MASE/cobertura já reportados):')
print(f'  Pinball Loss (quantil 10%, borda inferior) : {pl_10:.2f}')
print(f'  Pinball Loss (quantil 90%, borda superior) : {pl_90:.2f}')
print()
print('Por que priorizar esta métrica: cobertura% só diz SE o real caiu dentro do')
print('intervalo, não QUANTO o modelo errou quando caiu fora, nem se o intervalo é')
print('mais largo do que precisaria ser. Pinball Loss avalia a qualidade do')
print('intervalo inteiro (não só o ponto central yhat), penalizando erros fora do')
print('intervalo proporcionalmente à distância -- métrica padrão para forecast')
print('probabilístico (usada, por exemplo, na competição M5 de forecasting).')
