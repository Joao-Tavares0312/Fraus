# Régua de pares mínimos de ironia — design

Data: 08/10/2026. Contexto: [Ironia: corpus e Laya](../../ironia.md). O IDPT
entrega o rótulo pela fonte, então o teste interno não decide nada (o BERTimbau
marca 0,994 nele e P(irônico) = 1,0 em "ok, obrigado"). Esta régua é o
instrumento que decide qualquer modelo de ironia daqui em diante.

## Objetivo e critério de sucesso

Um conjunto **congelado** de frases de atendimento em pares mínimos, rotulado
**por humanos às cegas**, que:

1. um classificador que só enxerga estilo (caixa, pontuação, tamanho) **não
   consegue** resolver acima do acaso por par;
2. mede a diferença entre ironia e sentimento negativo (estrato B);
3. entra no laudo de `fraus/comparacao_modelos.py` com IC e teste pareado.

Critério de promoção de qualquer cabeça de ironia, escrito **antes** de
qualquer treino: **vencer o baseline só-estilo em acurácia por par na régua,
com IC 95% da diferença excluindo zero.** O teste interno do IDPT não entra
nessa decisão.

## Decisões tomadas (com o João, 08/10/2026)

- **Autoria:** a Neuro (Claude) rascunha; humanos rotulam às cegas. O rascunho
  é autoral; o rótulo que vale é o dos anotadores.
- **Ferramenta:** página web privada no claude.ai com banco compartilhado, uma
  frase por vez.

## 1. Conteúdo

**150 pares (300 frases)** em três estratos, 50 pares cada:

| Estrato | Lado A (não irônico) | Lado B (irônico) |
|---|---|---|
| A — elogio | elogio sincero: "ótimo serviço, resolveram rápido" | elogio irônico: "ótimo serviço, só esperei 3 horas" |
| B — reclamação | reclamação literal: "cobraram duas vezes, quero estorno" | reclamação irônica: "show, cobraram duas vezes" |
| C — neutra | pergunta ou informação: "qual o prazo de entrega?" | a mesma com ironia: "qual o prazo de entrega? o ano que vem?" |

Regras de redação:

- Os dois lados do par descrevem a **mesma situação** (mesmo produto, mesmo
  problema) e diferem no mínimo necessário para mudar o rótulo.
- **Registro equilibrado dentro do par**: os traços de superfície (minúscula
  inicial, ponto final, "vc/vcs", "kkk", emoji, caixa alta, tamanho) são
  sorteados por par e aplicados **aos dois lados**, nunca a um só. Assim
  nenhum traço acompanha o rótulo. Uma conferência automática (ver §4) prova
  isso na régua final.
- Domínios variados: banco/cartão, e-commerce/entrega, telecom/internet,
  saúde/plano, serviço público, delivery. Sem nome de empresa real, sem dado
  pessoal.
- Nenhuma frase da régua atual (`SINCERAS_COM_MARCADOR`, `IRONIAS_SEM_MARCADOR`)
  nem das sondas do notebook 04 é reaproveitada.

Mais **40 variantes de invariância** derivadas de 20 frases da régua (com e sem
ponto final, caixa alta, emoji neutro 🙂 no fim). Elas não são anotadas: herdam
o rótulo da frase de origem e medem só se a predição muda. Ficam fora da
métrica principal.

## 2. Anotação às cegas

**Página de anotação** (artifact privado no claude.ai, capacidades de banco
compartilhado e identidade do visitante):

- O anotador abre o link logado; a página o identifica e retoma de onde parou.
- Mostra **uma frase por vez**, numa ordem embaralhada **por anotador**
  (semente derivada do id do anotador), com os dois lados de um par nunca em
  sequência.
- Não mostra par, estrato, rótulo pretendido nem respostas de outros.
- Três botões: **irônico**, **não irônico**, **depende do contexto**. Atalhos
  de teclado. Contador "faltam N". Pode voltar e mudar a última resposta.
- Uma instrução curta no topo: o que é ironia aqui (dizer o contrário do que
  se quer dizer, em tom de crítica ou zombaria) e que "depende do contexto" é
  resposta legítima, não falha.
- Grava no banco `{anotador, frase_id, resposta, instante}`. As frases são
  publicadas na página **sem** o rótulo pretendido e sem `par_id`/`estrato`
  (só um `frase_id` opaco). O gabarito fica só no repositório.

Anotadores: o João e mais 1 ou 2 colegas. Estimativa de ~1h para 300 frases.

## 3. Consolidação e congelamento

`scripts/consolidar_regua_ironia.py` lê as respostas exportadas do banco
(JSON), junta com o gabarito do rascunho e decide:

- **κ de Fleiss** global e por estrato, sobre as três respostas.
- **Rótulo humano da frase:** maioria simples entre os anotadores; empate ou
  maioria "depende do contexto" → frase **ambígua**.
- **Um par entra** se os dois lados têm rótulo humano igual ao pretendido.
  Par com qualquer lado ambíguo ou divergente **sai** da régua e vai para
  `regua_ironia_descartes.csv` com o motivo — é dado, não lixo: mostra quanto
  da ironia é ambígua até para humanos.
- Se sobrarem menos de **100 pares**, a consolidação falha alto e diz quantos
  faltam: o IC por par fica largo demais abaixo disso.

Saída versionada:

- `fraus/dados/regua_ironia_pares.csv` — `par_id, estrato, lado, texto,
  rotulo, concordancia` (concordância = fração de anotadores com o rótulo).
- `fraus/dados/regua_ironia_invariancia.csv` — `frase_origem, variante, texto,
  rotulo`.
- `fraus/dados/regua_ironia_descartes.csv` — `par_id, estrato, lado, texto,
  motivo, respostas`.
- `fraus/dados/regua_ironia_meta.json` — anotadores (contagem, não nomes), κ,
  data, `impressao_dos_textos` da régua.

Um teste trava a impressão: mudar uma frase depois de congelada quebra o teste
e obriga a declarar a nova versão.

## 4. Código no Fraus

Em `fraus/avaliacao_ironia.py` (a régua de 20 continua lá, com o mesmo nome):

- `carregar_regua_pares()` → lista tipada de pares; confere a impressão contra
  o meta.
- `conferir_registro_equilibrado(pares)` → para cada traço de superfície,
  a proporção nos lados irônicos e não irônicos tem de bater dentro de
  tolerância; falha alta se um traço acompanhar o rótulo.

Em `fraus/comparacao_modelos.py`:

- `acuracia_por_par(rotulos, preditos, par_ids)` → fração de pares com os dois
  lados certos (acaso 25%).
- `bootstrap_por_par(...)` → IC da acurácia por par de **um** modelo e da
  **diferença** entre dois, reamostrando pares (não frases).
- `ece(probabilidades, rotulos, faixas=10)` → erro de calibração esperado.
- `avaliar_conjunto` passa a aceitar `par_ids` opcionais e, quando presentes,
  inclui acurácia por par e seu IC no resultado; o laudo marca a régua com
  `independente=True`.

Baseline só-estilo, em `fraus/baseline_estilo.py`:

- `tracos_de_superficie(texto)` → ~15 traços sem léxico: comprimento,
  proporção de maiúsculas, minúscula inicial, ponto final, `!`, `?`, `...`,
  dígitos, `R$`, URL, `@`, `#`, emoji, alongamento de letra, "kkk/haha".
- `BaselineEstilo` → regressão logística (scikit-learn, já dependência) sobre
  esses traços, treinada no mesmo corpus de treino do modelo comparado.
  Entra no laudo como mais um modelo.

## 5. Testes (TDD)

- Acurácia por par: par com um lado errado conta zero; acaso 25% num
  classificador aleatório simulado.
- Bootstrap por par reamostra pares inteiros (semente fixa, resultado estável).
- ECE: modelo perfeitamente calibrado → 0; superconfiante → > 0.
- `conferir_registro_equilibrado` reprova uma régua em que o ponto final só
  aparece nos irônicos.
- Baseline só-estilo: separa um conjunto sintético em que o rótulo é o ponto
  final; fica no acaso por par numa régua equilibrada.
- Consolidação: maioria, empate → ambígua, par com lado ambíguo sai, menos de
  100 pares falha alto, κ conferido num exemplo de livro.
- Impressão da régua congelada travada em teste.

## Fora do escopo

Consertar o corpus de treino, corrigir `laya_treinado_pelo_fraus`, treinar
qualquer modelo, mexer na dashboard. São os passos seguintes de
[Ironia: corpus e Laya](../../ironia.md).

## Riscos

- **Viés da autora do rascunho:** a Neuro viu as sondas e os modelos. Mitigado
  pela anotação às cegas e pela checagem de registro equilibrado; declarado no
  meta e no laudo.
- **Poucos anotadores:** com 2 ou 3, o κ é instável. Publicado com o n.
- **Ironia sem contexto é ambígua:** esperado; os descartes são publicados.
