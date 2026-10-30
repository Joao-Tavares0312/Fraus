# Cartão do modelo

> Formato de *model card* (Mitchell et al., 2019): o que cada peça é, com o que
> foi treinada, o que mediu, **onde erra** e para que **não** pode ser usada.
> **Métricas históricas de 15/09/2026**, não uma reavaliação do checkpoint
> publicado hoje. As fatias foram medidas com `scripts/avaliar_por_fatias.py`
> (`--n 600`, semente `20260915`). A investigação de 26–27/10/2026, os baselines
> locais e a campanha concluída de três sementes por cabeça estão em
> [Generalização e evidências](generalizacao.md); não sobrescrevem estas
> medições nem identificam os pesos publicados. As curvas sustentam sobreajuste
> **dos candidatos novos**, não um diagnóstico dos modelos antigos.

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

1. **Conversa de uma fala só é a fatia mais fraca** (0,733). É esperado — há
   menos texto para agregar —, e é o caso comum de "cliente respondeu uma vez e
   sumiu". A nota dessas conversas merece menos confiança do que a das longas.
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
"valeu, resolveu na hora" continua pontuada. O conserto de verdade é retreinar a
emoção separando gratidão de alegria.

## A cabeça de ironia — taxa de erro histórica publicada

Contra-exemplos escritos para quebrar o atalho que o gerador ensinou: falas
**sinceras com marcador de discurso** ("nossa", "realmente", "né", "que ...") e
**ironias sem marcador**, em que o elogio é desmentido pela situação.

| conjunto | erro |
|---|---|
| sincera com marcador marcada como irônica | **70%** (7 de 10) |
| irônica sem marcador que passou como sincera | **40%** (4 de 10) |

Os erros vêm saturados: "realmente, agora funcionou" → 0,999 de ironia;
"perfeito, cancelaram sem avisar" → 0,001. A cabeça aprendeu **registro e
marcador**, não pragmática. É por isso que ela **não entra na nota** desde
04/09/2026 e que a interface a mostra com ressalva, nunca como veredito. A lista
completa, fala a fala, sai do script.

## Calibração e conformal do fusor

O fusor dispõe de conjunto conformal (Mondrian por classe, sobre o score
gravado) e instrumentos de calibração. O protocolo histórico dividia um
holdout B2W de 300 conversas em calibração (150) e avaliação (150),
estratificado, com semente fixa. **Nenhum número da tabela abaixo foi
medido**: o fusor compatível com `log1p` não estava disponível na máquina
de desenvolvimento em 14/10/2026. O cache posicional antigo não comprova
isolamento por produto ou independência das cabeças e não deve ser reutilizado
no novo experimento.

A campanha de 26–27/10/2026 produziu um **candidato novo**, com avaliação
sintética e ECE top-1, descritos em [Generalização](generalizacao.md).
Essa medição não preenche retroativamente a tabela histórica abaixo:
MCE, calibração por classe/fatia e cobertura/abstenção conformal não foram
medidos nessa campanha. O relatório original conservador de independência
foi preservado e complementado por cruzamentos textuais dos treinos reais;
isso não transforma conversas sintéticas em atendimento real rotulado.

### Comandos atuais para preparar um candidato

Defina `B2W` como o CSV exato, `EXPERIMENTO` como diretório de pesquisa
**externo ao repositório e aos checkpoints** e `CABECAS` como a raiz dos
checkpoints candidatos. Reserve o manifesto **antes** do treino de satisfação
e passe-o ao notebook 01 por `FRAUS_MANIFESTO_FUSOR`; só execute a extração
depois de congelar os candidatos. Não há opção de promoção nesta sequência.

```bash
# 1. Reserva a divisão agrupada; não faz inferência.
uv run python scripts/retreinar_fusor_local.py \
  --b2w "$B2W" --manifesto "$EXPERIMENTO/manifesto.json" --gerar-manifesto
# 2. Extrai features e avalia candidatos/ablações, sem ler ou substituir fusor ativo.
uv run python scripts/retreinar_fusor_local.py \
  --b2w "$B2W" --manifesto "$EXPERIMENTO/manifesto.json" \
  --modelos "$CABECAS" --backend torch \
  --cache "$EXPERIMENTO/features-fusor.json" --saida "$EXPERIMENTO/candidato"
# 3. Instrumentos sobre o candidato explícito, sem ler fusor ativo ou gravar conformal ativo.
# É outra medição; não sobrescreve a tabela histórica abaixo.
uv run python scripts/calibrar_conformal.py \
  --fusor "$EXPERIMENTO/candidato/fusor.joblib" --cache "$EXPERIMENTO/features-fusor.json"
uv run --with matplotlib python scripts/medir_calibracao.py \
  --fusor "$EXPERIMENTO/candidato/fusor.joblib" \
  --cache "$EXPERIMENTO/features-fusor.json" --png "$EXPERIMENTO/calibracao.png"
uv run python scripts/medir_abstencao.py \
  --fusor "$EXPERIMENTO/candidato/fusor.joblib" --cache "$EXPERIMENTO/features-fusor.json"
```

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
sintético); o sinal de tempo do fusor é sintético. Com 150 exemplos de
avaliação a cobertura tem granularidade de cerca de 2 a 3 pontos percentuais.
Os scripts exigem no mínimo 5 exemplos por classe em cada metade (escolha de
projeto, sem procedência na literatura), e a mediana do bootstrap é impressa
com uma nota de viés.

## Limitações que valem para tudo acima

- **Tempo sintético.** Latência, escalação e abandono do treino do fusor vêm de
  distribuições da literatura, não de atendimento observado.
- **Texto fora de domínio.** Satisfação aprendeu com resenha de produto; emoção,
  com Reddit traduzido por máquina.
- **Acurácia alta pede investigação**, não celebração automática (invariante 10).
  Os 0,947 e 0,940 acima são medidas sintéticas históricas, não uma estimativa
  ou um teto demonstrado de desempenho em atendimentos reais.

Ver também [Limitações conhecidas](limitacoes.md).
