# E2 — Calibração, abstenção e previsão conformal do fusor

> Estado: **aguardando aprovação**. Faz parte de
> [Diferenciais](2026-10-14-diferenciais-visao-geral.md).

## Objetivo

Responder três perguntas:

- A probabilidade do **fusor** merece confiança?
- Quando o Fraus **não** deve responder?
- Que garantia estatística acompanha a resposta?

Isto fecha a lacuna que Limitações admite. O notebook 05 calibra as cabeças
BERTimbau; nada mede o fusor, que é de onde sai a nota.

## Desenho

**1. Medição de calibração** (`scripts/medir_calibracao.py`, no estilo de
`medir_faixas.py`: instrumento, não botão, não grava nada).

- **Entrada:** o cache `{xt, yt, xe, ye}` de
  `retreinar_fusor_local.py --cache`, que é o holdout B2W de 300 conversas
  (semente 999).
- **Entrada secundária**, reportada à parte: as 600 conversas do simulador
  usadas no cartão (semente 20260915).
- **Saída:** ECE e MCE da confiança máxima e ECE por classe (classwise), com
  10 faixas de confiança. O IC de 95% vem de bootstrap com 1.000 reamostras e
  semente fixa.
- **Também sai:** o reliability diagram em PNG, em
  `docs/diferenciais/img/calibracao-*.png`, e uma tabela por fatia (falas do
  cliente, emoji, latência), que vai para o cartão do modelo.
- **Se a descalibração for relevante** (ECE acima de 0,05 com IC que não cruza
  esse valor), o script **propõe** uma temperatura para o fusor e mostra quanto
  ela mudaria. **Não aplica.** Aplicar mudaria a régua e exigiria repontuar
  tudo. Cabe ao João decidir.

**2. Conformal sobre o score gravado (Mondrian, por classe).** A escolha que
evita schema novo:

- A não conformidade usa **só o score 0–100 gravado**.
- Para cada classe `y`, o conjunto de calibração dá os quantis do score das
  conversas daquela classe. A classe `y` entra no conjunto da conversa se o
  score dela cai dentro do intervalo de quantis
  `[q_y(α/2), q_y(1 − α/2)]`, com a correção de amostra finita
  `⌈(n_y + 1)(1 − α/2)⌉ / n_y`.
- **Garantia:** cobertura **por classe** de pelo menos `1 − α` sob
  permutabilidade. A garantia vale para qualquer não conformidade, e é mais
  forte que a marginal.
- **Vantagem:** é derivado na leitura a partir do que já está gravado, então
  funciona na lista, no filtro e no agregado, sem rodar modelo nem migrar.
- **Custo:** é menos eficiente que usar as três probabilidades. O tamanho
  médio do conjunto é medido e reportado como sair.

**3. Divisão.** O holdout de 300 é dividido em **calibração (150) × avaliação
(150)** com semente fixa e estratificado por classe. Nada vem do treino de
900.

- Cerca de 50 por classe dá granularidade de cerca de 2 p.p. na cobertura, e
  isso é declarado.
- **Alvo padrão: 90%**, configurável no script.

**4. Artefato.** `fraus/dados/conformal_fusor.json`, versionado como
`comparacao_modelos.json`. Fica fora de `modelos/`, que não pode ser tocado.
Contém o alvo, os quantis por classe, `n` por classe, a semente e a origem.
Também contém **`Fusor.assinatura()`**, que é o que amarra o artefato ao
modelo.

- **Falha explícita:** sem o artefato, ou com assinatura diferente da do fusor
  carregado, as rotas que expõem conjunto ou abstenção respondem 503 com o
  motivo.
- **Nunca devolvem conjunto vazio fingindo confiança.** Mesmo espírito da
  invariante 7.
- Os indicadores existentes não dependem dele e continuam funcionando.

**5. Abstenção** ("leitura sem confiança suficiente"). É da mesma família da
contestação: **marca e informa, não corrige**, e a conversa **continua no NPS
e no CSAT**.

- **Na lista:** dispara quando o conjunto tem mais de uma classe.
- **No detalhe e na análise,** onde as features existem, também dispara
  quando alguma feature tem `|z| > 4` (o critério de `/saude/deriva`).
- A tela nomeia qual dos dois critérios disparou. A lista não afirma nada
  sobre deriva.

**6. Curva cobertura × acurácia** (`scripts/medir_abstencao.py`). Sobre a
avaliação de 150:

- acurácia das conversas que **não** abstêm, em função de `α`;
- curva risco × cobertura;
- ponto de operação no alvo de 90%.

## Métrica de aceitação

- **Cobertura:** a cobertura empírica no conjunto de avaliação fica em pelo
  menos o alvo menos a tolerância. A tolerância é o desvio binomial de
  `n = 150`, cerca de 2,5 p.p. a 90%, e é declarada. Também é reportada a
  cobertura por classe.
- **Falha explícita:** artefato ausente ou de outra assinatura gera 503 e um
  teste vermelho antes da implementação.
- **Regressão:** os scores, as notas e as categorias gravadas são idênticos
  antes e depois, e há teste para isso. O NPS e o CSAT agregados não mudam
  com a abstenção.
- **Instrumentos:** `medir_calibracao.py` e `medir_abstencao.py` rodam e
  imprimem as tabelas.
- **Cartão do modelo:** ganha a calibração por fatia.

## Dados

- Holdout B2W de 300 conversas: reconstruído por semente, exige os pesos e o
  download do B2W em tempo de avaliação, nunca em runtime.
- Simulador, como conjunto secundário.

## Limitações declaradas

- **A permutabilidade não vale** sob mudança de distribuição, e atendimento
  real **é** mudança de distribuição em relação ao holdout sintético.
- A garantia é sobre o conjunto de calibração usado, não sobre produção.
- O sinal de tempo foi treinado em dado sintético.
- O `n` de calibração é pequeno, e por isso o IC acompanha cada número.

## Desvios aceitos

Registrados na entrega, em relação ao desenho acima:

- **Exposição por duas rotas próprias** (`GET /conversas/{id}/confianca` e
  `GET /indicadores/confianca`), e não na lista de conversas.
- **O agregado usa só o critério de conjunto**; o critério de deriva
  (`|z| > 4`) não é aplicado nele.
- **Artefato chaveado pela régua** (`regua_do_fusor`: fusor mais regra de
  cortesia) em vez de `Fusor.assinatura()`.
- **Conjunto vazio conta como abstenção** (critério `conjunto_vazio`).
- **Mínimo de 5 exemplos por classe em cada metade** nos scripts: escolha de
  projeto, sem procedência na literatura.
- **Mediana do bootstrap** impressa, com nota de viés.
- **Desvio de TDD na Tarefa 4:** a primeira passada não teve RED; registrado
  com honestidade.
- **Nenhum número medido:** fusor log1p ausente na máquina de desenvolvimento
  em 14/10/2026; a tabela de aceitação fica "não verificado".

## Fora de escopo

- Aplicar recalibração.
- Gravar probabilidades (seria schema e regra 5).
- Conformal usando as três probabilidades (exigiria rodar os modelos na
  lista).
