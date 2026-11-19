# Cartão do modelo

> Formato de *model card* (Mitchell et al., 2019): o que cada peça é, com o que
> foi treinada, o que mediu, **onde erra** e para que **não** pode ser usada.
> **Métricas históricas de 15/09/2026**, não uma reavaliação do checkpoint
> publicado hoje. As fatias foram medidas com `scripts/avaliar_por_fatias.py`
> (`--n 600`, semente `20260915`). A investigação de 26/10/2026, os baselines
> locais e seus limites de independência estão em
> [Generalização e evidências](generalizacao.md); eles não sobrescrevem estas
> medições. A campanha Colab de três sementes por cabeça não foi concluída.
> Revisão documental de **16/11/2026**: modelos congelados por decisão do
> projeto; retreino, calibração, promoção e troca de pesos/arquitetura estão
> fora da fila ativa. Os resultados antigos não validam o ambiente atual.

## Uso pretendido e uso proibido

**Pretendido:** estimar, a partir do texto e do ritmo de um atendimento de
chatbot, se o cliente saiu insatisfeito, neutro ou satisfeito, e agregar isso
num **NPS estimado** para quem opera o atendimento enxergar tendência e caso
problemático. Toda exibição carrega a etiqueta de estimativa: o NPS é
**inferido**, não perguntado.

**Proibido:**

- **Pontuar atendente.** "Score por atendente" é expansão de finalidade de alto
  impacto e permanece proibida por política do produto. O Fraus infere emoção
  de texto, não de dados biométricos; por isso a documentação não afirma mais
  enquadramento automático na definição do EU AI Act. Ver
  [Conformidade](conformidade.md).
- **Decidir sobre o cliente individualmente** (crédito, prioridade, cobrança).
  A nota de uma conversa é evidência para um humano olhar, não veredito.
- **Apresentar a nota como NPS declarado.**

## As peças — métricas históricas de 15/09/2026

| peça | o que é | treino | métrica declarada | onde a métrica engana |
|---|---|---|---|---|
| satisfação | BERTimbau, 3 classes por mensagem | B2W-Reviews01 (resenha de produto, não atendimento) | acurácia 0,783 · F1-macro 0,782 | domínio: resenha ≠ conversa de suporte |
| emoção | BERTimbau, 7 classes (+ desprezo derivado de raiva+nojo) | `go_emotions_ptbr` (tradução automática) | F1-macro 0,584; **0,281 no XED-pt** (sem tradução) | a queda no XED-pt é a medida honesta |
| ironia | BERTimbau binário | corpus **gerado** (`fraus.ingest.gerador_ironia`) | acurácia 1,0 | otimista por construção — ver abaixo; **não entra na nota** |
| fusor | `LogisticRegression` sobre 39 features (espera em `log1p`) | conversas sintéticas: texto do B2W + estrutura e tempo do simulador | acurácia 0,947 · F1-macro 0,947 (holdout do notebook 02) | o tempo é sintético; ver [Treinamento](treinamento.md) |

Os três BERTimbau rodam em CPU, por torch ou por ONNX Runtime
(`FRAUS_BACKEND`), com **0 de 180 categorias trocadas** entre os dois
executores. Ver [Encolher os modelos](encolhimento.md).

## Onde o fusor erra — avaliação histórica por fatia

600 conversas do simulador, fora das sementes usadas em outras medições.
**Isto mede onde o modelo erra dentro do domínio sintético, não desempenho em
atendimento real**: o projeto não dispõe de corpus PT-BR de atendimento
rotulado com timestamps para essa validação.

Acurácia geral: **0,940** (598 conversas com sinal; 2 eram só cortesia).

| eixo | fatia | n | acurácia | F1-macro |
|---|---|---|---|---|
| falas do cliente | 1 | 30 | **0,733** | **0,735** |
| falas do cliente | 2–3 | 424 | 0,936 | 0,936 |
| falas do cliente | 4+ | 144 | 0,993 | 0,992 |
| emoji | com | 524 | 0,952 | 0,953 |
| emoji | sem | 74 | **0,851** | **0,836** |
| escalou para humano | não | 454 | 0,947 | 0,948 |
| escalou para humano | sim | 144 | 0,917 | 0,887 |
| latência mediana | < 30 s | 236 | 0,936 | 0,918 |
| latência mediana | 30–180 s | 306 | 0,941 | 0,934 |
| latência mediana | > 180 s | 56 | 0,946 | 0,823 |

O que a tabela diz, e o que ela **não** pode dizer:

1. **Conversa de uma fala só foi a fatia mais fraca** (0,733) nesta medição.
   Havia menos texto para agregar, mas a tabela não demonstra que toda conversa
   longa mereça mais confiança, nem mede a confiança por conversa real.
2. **Sem emoji, o acerto cai 10 pontos.** Suspeita declarada: o simulador sorteia
   o emoji **por rótulo** (`EMOJIS_POR_ROTULO`), então parte do acerto "com
   emoji" pode ser o modelo lendo uma pista que o gerador plantou — a mesma
   família de defeito da invariante 10. Isso não permite prever a acurácia
   em atendimento real; a linha “sem emoji” ainda pertence ao simulador.
3. **A fatia de latência é parcialmente circular** pelo mesmo motivo: o
   simulador sorteia a latência por rótulo. O F1 menor acima de 180 s é a
   fatia a acompanhar: mesmo com a espera em `log1p` desde 15/09/2026, o relógio
   ainda empata com o texto por volta de 10 min
   (`scripts/medir_dominio_do_tempo.py`).

## Conversa só de cortesia — sem sinal desde 15/09/2026

"ok, obrigado" fecha atendimento bom **e** ruim, então não tem rótulo verdadeiro.
Medido antes da regra, com o bot respondendo em 10 s, o Fraus dava:

| fala | score (antes) | categoria (antes) | hoje |
|---|---|---|---|
| ok, obrigado | 76,2 | neutro | sem sinal |
| ta bom | 75,7 | neutro | sem sinal |
| ok | 79,0 | neutro | sem sinal |
| certo, entendi | 75,3 | neutro | sem sinal |
| valeu | 93,2 | **promotor** | sem sinal |
| obrigada | 92,9 | **promotor** | sem sinal |

Uma palavra de agradecimento, sozinha, bastava para **promotor**: o texto de
gratidão era lido como satisfação, e a emoção lia "ok, obrigado" como alegria
0,98 — o mapeamento do GoEmotions para as 6 de Ekman juntou `gratitude` com
`joy`. **Decisão:** conversa em que *toda* fala do cliente é fórmula de
cortesia é **sem sinal** (`score: None`, invariante 2), e não sinal fraco. A
lista é fechada e conservadora (`fraus/cortesia.py`): só casa a fala inteira, e
"valeu, resolveu na hora" continua pontuada. Separar gratidão de alegria seria
uma hipótese de pesquisa futura, não correção autorizada: os modelos estão
congelados por decisão de 16/11/2026.

## A cabeça de ironia — taxa de erro histórica publicada

Contra-exemplos escritos para quebrar o atalho que o gerador ensinou: falas
**sinceras com marcador de discurso** ("nossa", "realmente", "né", "que ...") e
**ironias sem marcador**, em que o elogio é desmentido pela situação.

| conjunto | erro |
|---|---|
| sincera com marcador marcada como irônica | **70%** (7 de 10) |
| irônica sem marcador que passou como sincera | **40%** (4 de 10) |

Nesse teste histórico, os erros vinham saturados: "realmente, agora funcionou"
→ 0,999 de ironia; "perfeito, cancelaram sem avisar" → 0,001. O diagnóstico de
marcadores vale para aquele checkpoint. A saída do vetor em 04/09/2026 teve
outro motivo medido: as features de ironia funcionavam como detector de
sentimento positivo no corpus do fusor. Não se deve atribuir a exclusão a
esta pequena régua, nem extrapolar sua taxa de erro a pesos atuais.

## Calibração e conformal do fusor

O código implementa conjunto conformal (Mondrian por classe, sobre o score
gravado) e instrumentos de calibração. **Não há
`fraus/dados/conformal_fusor.json` na árvore consultada em 16/11/2026**.
Implementação não significa cobertura validada ou confiança disponível no
ambiente publicado. Sem artefato compatível, as rotas falham explicitamente.

O protocolo histórico dividia um holdout B2W de 300 conversas em calibração
(150) e avaliação (150), estratificado, com semente fixa. **Nenhum número da
tabela abaixo foi medido**: a indisponibilidade do fusor `log1p` foi registrada
em 14/10/2026. O cache posicional antigo não comprova isolamento por produto
ou independência das cabeças e não deve ser reutilizado como prova atual.

A compatibilidade por régua é uma guarda parcial: `regua_do_fusor`
(`fraus/motor.py`) usa a assinatura do fusor e a lista de cortesias, não
identifica mudanças de checkpoint das cabeças ou de backend. Sozinha, ela não
demonstra proveniência ou estabilidade de todo o pipeline.

As tabelas históricas desta página são registros documentais das execuções
datadas, não resultados recalculados nesta revisão. O cálculo de fatias está
em `fraus/fatias.py` e `scripts/avaliar_por_fatias.py`; não há resultado JSON
da execução de 15/09 em `fraus/dados/` para reprodução independente. O
F1-macro por fatia considera apenas as classes presentes no rótulo real da
fatia, não necessariamente as três classes.

### Comandos atuais para preparar um candidato

**Fora da fila ativa desde 16/11/2026.** A preparação de candidato e a
calibração eram um protocolo de pesquisa, não uma próxima etapa vigente.
Os instrumentos permanecem no repositório (`scripts/retreinar_fusor_local.py`,
`scripts/calibrar_conformal.py`, `scripts/medir_calibracao.py` e
`scripts/medir_abstencao.py`), mas sua existência não comprova execução,
artefato conformal gerado ou promoção. A metodologia e os limites históricos
estão em [Generalização](generalizacao.md).

| Medida | Valor |
|---|---|
| ECE (top-1) | não verificado — fusor log1p ausente na máquina de desenvolvimento em 14/10/2026 |
| MCE | não verificado — idem |
| ECE por classe | não verificado — idem |
| ECE por fatia (falas, latência, emoji, escalou; "n/d" abaixo de 5 exemplos) | não verificado — idem |
| Cobertura empírica no alvo de 90% (total e por classe) | não verificado — idem |
| Acurácia das conversas que não abstêm (só o critério do conjunto; a rota de detalhe também abstém por deriva) | não verificado — idem |
| Taxa de abstenção no alvo de 90% | não verificado — idem |

Garantia: cobertura ≥ alvo **por classe**, sob permutabilidade com o conjunto de
calibração; **não vale** sob mudança de distribuição (atendimento real ≠ holdout
sintético); o sinal de tempo do fusor é sintético. No protocolo histórico,
150 exemplos de avaliação não sustentam uma medida fina de cobertura por
classe. Os scripts exigem no mínimo 5 exemplos por classe em cada metade
(escolha de projeto, sem procedência na literatura), e a mediana do bootstrap
é impressa com uma nota de viés.

## Limitações que valem para tudo acima

- **Tempo sintético.** Latência, escalação e abandono do treino do fusor vêm de
  distribuições da literatura, não de atendimento observado.
- **Texto fora de domínio.** Satisfação aprendeu com resenha de produto; emoção,
  com Reddit traduzido por máquina.
- **Acurácia alta pede investigação**, não celebração automática (invariante 10).
  Os 0,947 e 0,940 acima são medidas sintéticas históricas, não uma estimativa
  ou um teto demonstrado de desempenho em atendimentos reais.

Ver também [Limitações conhecidas](limitacoes.md).
