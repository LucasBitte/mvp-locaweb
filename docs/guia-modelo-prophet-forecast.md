# Guia educacional — Modelo Prophet (Forecast Total de Incidentes)

> Documento de apoio para ler e entender `notebooks/forecast_incidentes_revisado.py`
> e os gráficos de `notebooks/forecast_incidentes_graficos.py` (script novo,
> não faz parte do pipeline de produção — só lê os parquets já persistidos
> em `data/ml/prophet/` e plota) — explica cada gráfico, cada métrica, o
> resultado real medido e o porquê. Fecha com um glossário. Não substitui
> o script (fonte de verdade dos números) nem `docs/metricas-validacao.md`
> §1 (números já consolidados).

## 1. O que este modelo faz

Prevê **quantos incidentes vão abrir por dia**, de D+1 a D+7, olhando o
histórico diário completo de 2025 (365 dias). É a previsão que alimenta a
tela Painel do dashboard ("Previsão D+1", "Previsão D+7 · média/dia") e,
indiretamente (por proporção histórica), os splits por prioridade e
categoria.

O modelo é o **Prophet** (biblioteca de forecast de série temporal, feita
para sazonalidade + tendência), rodando em duas variantes:
`prophet_regime` (produção — treina só a partir de uma possível "quebra de
patamar" detectada na série) e `prophet_hist_completo` (treina com todo o
histórico disponível, sem restringir).

## 2. Como o modelo foi validado

- **Backtest de origem móvel**: em vez de validar uma vez só, o script
  simula "se eu estivesse rodando este modelo todo santo dia", treinando
  em 268 origens diferentes ao longo do ano e prevendo D+1 a D+7 a partir
  de cada uma — resultando em 15.008 previsões de teste no total.
- **Split tuning vs. avaliação final**: as primeiras origens (55% do
  período) calibram o intervalo de confiança; as últimas 45% (847
  previsões) são o número final reportado, nunca usado para ajustar nada.
- **6 baselines de comparação**: modelos simples (naive, médias móveis,
  mediana por dia da semana) rodados no mesmo backtest, para checar se o
  Prophet realmente agrega valor sobre uma alternativa ingênua.
- **Detector de "quebra de patamar"**: mediana móvel de 28 dias comparada
  com ela mesma 28 dias atrás — se a razão passa de 2× ou cai abaixo de
  0,5×, marca uma mudança de regime operacional (não um pico de um dia,
  uma mudança sustentada de patamar).

## 3. Os gráficos, um por um

### Figura 1 — Acurácia e comparação com baselines

**Painel 1 — Real vs. previsto (D+1, avaliação final).** A linha preta é o
valor real por dia; a linha azul tracejada é a previsão do modelo de
produção; a faixa azul clara é o intervalo de 80%.

- **Resultado real**: o modelo acompanha o padrão semanal razoavelmente
  bem, mas **erra feio nos picos extremos** (dois dias passam de 300-400
  incidentes/dia contra uma previsão de ~150 — o intervalo às vezes nem
  cobre o valor real).
- **Porquê importa**: mostra visualmente o que "cobertura de 78,6%"
  significa na prática — em ~1 a cada 5 dias, o real cai fora da faixa
  prevista, e os casos que mais importam (picos extremos) são justamente
  os que o modelo mais erra.

**Painel 2 — Comparação de modelos (MAE no backtest).** Uma barra por
modelo testado, do maior erro para o menor.

- **Resultado real**: `mediana_dow_4sem` (MAE=31,2 — um baseline simples:
  mediana das últimas 4 semanas no mesmo dia da semana) **supera**
  `prophet_regime` (MAE=35,7, produção) e `prophet_hist_completo`
  (MAE=35,7 — idênticos, porque não há quebra de patamar detectada na
  série agregada, então as duas variantes treinam igual).
- **Porquê importa**: é o achado central já documentado em
  `docs/metricas-validacao.md` — o modelo em produção não bate um baseline
  ingênuo em MAE/WAPE/MASE. O Prophet só ganha em cobertura de intervalo
  (o baseline de mediana não produz intervalo nenhum, então não há como
  comparar essa dimensão).

### Figura 2 — Degradação por horizonte e ruído residual

**Painel 3 — MAE e cobertura por horizonte (D+1 a D+7).** Eixo esquerdo =
erro médio; eixo direito = % de vezes que o real caiu dentro do intervalo.

- **Resultado real**: MAE sobe de 34,6 (D+1) a 37,5 (D+7); cobertura cai
  de 80,2% a 76,0% — os dois na direção esperada (mais incerteza mais
  longe no futuro), mas a queda de cobertura mostra que o intervalo não
  está se alargando o suficiente para compensar.
- **Porquê importa**: quantifica exatamente o quanto confiar menos na
  previsão de D+7 do que na de D+1.

**Painel 4 — Autocorrelação dos resíduos (D+1).** Se o modelo capturou
todo o padrão da série, o que sobra (resíduo = real − previsto) deveria
ser ruído — sem autocorrelação em nenhum lag.

- **Resultado real**: autocorrelação de 0,32 no lag 1 e ~0,20 no lag 7
  (acima do limiar informal de ±0,2 usado no gráfico).
- **Porquê importa**: autocorrelação no lag 1 sugere que erros de um dia
  se repetem no dia seguinte (o modelo é lento pra reagir a uma mudança);
  no lag 7, sugere padrão semanal residual que a sazonalidade do Prophet
  não capturou totalmente — os dois são pistas de onde o modelo tem
  espaço para melhorar.

### Figura 3 — Estabilidade da série e previsão futura

**Painel 5 — Série histórica com quebra de patamar marcada.**

- **Resultado real**: **0 quebras de patamar detectadas** na série
  agregada (recalculado com a mesma regra de `validar_serie()`, só
  lendo `serie_diaria.parquet`, sem re-treinar nada). Consistente com o
  Painel 2 — é por isso que `prophet_regime` e `prophet_hist_completo`
  dão exatamente o mesmo resultado.
- **Porquê importa**: mostra que a série TOTAL é relativamente estável
  (diferente de séries por equipe individuais, mais ruidosas — ver o guia
  do modelo Prophet por equipe, onde esse detector já causou um bug real).

**Painel 6 — Previsão futura D+1..D+7 com intervalo.** O "fan chart"
clássico de forecast — previsão central com a faixa de incerteza que
alarga (ou, aqui, oscila) com o horizonte.

- **Porquê importa**: é literalmente o número que a tela Painel do
  dashboard mostra, com a incerteza explícita ao redor.

## 4. As métricas, uma por uma

| Métrica | O que mede | prophet_regime (teste) | mediana_dow_4sem (melhor baseline) | Leitura |
|---|---|---|---|---|
| **MAE** | Erro médio absoluto (incidentes/dia) | 35,73 | 31,24 | Baseline vence — erro 12% menor |
| **RMSE** | Erro quadrático médio (penaliza mais os erros grandes) | 50,25 | 49,74 | Praticamente empatado |
| **WAPE%** | Erro absoluto total / soma do real, em % (escolhida no lugar de MAPE por não explodir quando o real é baixo) | 32,54% | 28,45% | Baseline vence |
| **Viés** | Erro médio com sinal (positivo = superestima) | 10,83 | 0,84 | Prophet superestima sistematicamente; baseline é quase neutro |
| **MASE** | MAE do modelo / MAE de um naive sazonal simples (abaixo de 1 = melhor que o naive) | 0,97 | 0,85 | Os dois batem o naive, mas o baseline bate por mais |
| **Cobertura%** | % de vezes que o real caiu dentro do intervalo previsto | 78,63% | — (sem intervalo) | Perto do nominal (80%), única dimensão onde o Prophet tem algo que o baseline não tem |

**Por que Pinball Loss foi adicionada** (bloco final do script): as
métricas acima avaliam o **ponto central** da previsão (MAE, RMSE, WAPE,
MASE) ou só **se** o intervalo cobriu o real (cobertura%) — nenhuma delas
diz o quanto o intervalo erra quando erra, nem se está desnecessariamente
largo. Pinball Loss (medida separadamente nas duas bordas do intervalo de
80%) é a métrica padrão para avaliar a qualidade de uma previsão
probabilística inteira, não só o ponto central — usada, por exemplo, na
competição de forecasting M5.

## 5. Glossário

- **Autocorrelação (ACF)**: correlação de uma série com ela mesma
  deslocada no tempo (lag); usada para checar se resíduos de um modelo
  ainda têm padrão não capturado.
- **Backtest de origem móvel**: validar um modelo simulando repetidas
  execuções reais ao longo do tempo (treina até um dia X, prevê os
  próximos dias, avança X, repete), em vez de um único treino/teste.
- **Baseline**: modelo simples usado como referência de comparação — se
  um modelo sofisticado não bate um baseline simples, isso é um sinal de
  alerta, não um detalhe.
- **Cobertura de intervalo**: % das vezes que o valor real caiu dentro do
  intervalo de confiança previsto; deveria ficar perto do nível nominal
  (aqui, 80%).
- **MAE (Mean Absolute Error)**: média do valor absoluto dos erros —
  métrica de erro na mesma unidade do dado original (incidentes/dia),
  fácil de interpretar.
- **MASE (Mean Absolute Scaled Error)**: MAE do modelo dividido pelo MAE
  de um modelo naive de referência — valores abaixo de 1 significam que o
  modelo bate o naive; permite comparar séries diferentes na mesma escala.
- **Naive sazonal (snaive)**: baseline que simplesmente repete o valor
  observado no mesmo dia da semana anterior (lag 7).
- **Pinball Loss (Quantile Loss)**: métrica que avalia a qualidade de uma
  previsão de quantil (ex.: a borda inferior ou superior de um intervalo),
  penalizando de forma assimétrica: prever abaixo do real custa diferente
  de prever acima, ponderado pelo quantil-alvo.
- **Prophet**: biblioteca de forecast de série temporal (originalmente do
  Facebook/Meta) que decompõe a série em tendência + sazonalidades
  (semanal, anual) + feriados, com intervalo de incerteza incluído.
- **Quebra de patamar / mudança de regime**: mudança sustentada no nível
  médio de uma série (não um pico isolado de um dia) — detectada aqui
  comparando a mediana móvel de 28 dias com ela mesma 28 dias antes.
- **RMSE (Root Mean Squared Error)**: raiz do erro quadrático médio;
  penaliza erros grandes mais que o MAE (por elevar ao quadrado antes de
  tirar a média).
- **Viés (bias)**: erro médio **com sinal** (não em valor absoluto) —
  positivo significa que o modelo tende a superestimar, negativo que tende
  a subestimar.
- **WAPE (Weighted Absolute Percentage Error)**: soma dos erros absolutos
  dividida pela soma dos valores reais, em % — alternativa ao MAPE que não
  explode quando o valor real é próximo de zero.
