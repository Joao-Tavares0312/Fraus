# Diferenciais — roteiro da demonstração

Roteiro para apresentar os diferenciais na banca de **09/12/2026**, em cerca de
10 minutos. Conferido contra o código em 16/11/2026 e **ensaiado localmente com
o motor real em 19/11/2026** (ids e propriedades abaixo, banco SQLite
temporário, sem rede). Produção e projetor ainda precisam do ensaio físico.
Cada passo diz:

- o que mostrar;
- o que falar;
- o que **não** afirmar.

A comparação com produtos do mercado está em [concorrentes](concorrentes.md), e cada afirmação ali tem fonte e data.

## Antes de começar

- **Dados.** Empresa fictícia **Lumen Telecom** (provedor de internet):
  156 atendimentos fabricados em `dados_demo/lumen-telecom.csv`
  (`scripts/gerar_empresa_ficticia.py`), de 08/11 a 07/12/2026, ids
  `sintetica-lumen-*`, canais webchat, WhatsApp e Instagram. O canal Telegram
  traz atendimentos **reais** pelo Tars, com o voto Resolveu / Não resolveu.
  Use o período **08/11/2026 – 07/12/2026** em toda a demo.
- **Carga.** Uma conta `dev` cria em Integrações três fontes (canal `webchat`,
  `whatsapp`, `instagram`) e gera a chave de cada uma; depois
  `FRAUS_CHAVE_FONTE_WEBCHAT=… FRAUS_CHAVE_FONTE_WHATSAPP=… FRAUS_CHAVE_FONTE_INSTAGRAM=… uv run python scripts/carregar_empresa_ficticia.py --url <API>`.
  Os ids gravados ficam `fonte:<n>:sintetica-lumen-*`; reenviar substitui.
  Não use a tela Analisar para isso: ela troca o id por hash e para em 10
  atendimentos por arquivo.
- **Com os modelos reais:** a API precisa dos classificadores obrigatórios e
  do fusor compatível com a escala `log1p`; a régua dos registros também precisa
  ser compatível. Só execute explicação, contrafactual, drivers e Replay como
  prova do modelo se esses requisitos estiverem atendidos.
- **Plano B (produção fora do ar).** Na raiz, com `modelos-onnx/` e
  `modelos/fusor.joblib` do pacote `42cd90c2…` extraídos:
  `FRAUS_BACKEND=onnx uv run python -m uvicorn fraus.api.main:app --port 8001`
  e, em `dashboard/`, `FRAUS_API_URL=http://127.0.0.1:8001 npm run dev`.
  Carregue o CSV com `scripts/carregar_empresa_ficticia.py` (fontes criadas na
  API local). Ensaiado em 19/11 **sem rede**: prontidão 200 com motor real,
  156/156 aceitos, NPS inferido −26, confiança 200, dashboard renderizando.
  Diga em voz alta que é ambiente local, mesmo motor, dados fabricados. As
  conversas reais do Tars não existem no plano B: use as capturas de produção.
  `scripts/api_demo.py` não é o plano B: pode subir com dublê.
- **Confiança (E2).** O artefato conformal está versionado desde 19/11/2026,
  com a régua do fusor de produção. Confira `/indicadores/confianca` em 200
  pelo proxy antes da banca; se responder 503, mostre o estado indisponível e
  não rode calibração para contornar. Modelos continuam congelados.
- Use conta `dev` se for mostrar **Replay**: essa aba não aparece para
  `usuario`. Os dois papéis podem abrir **Modelo** e a explicação do detalhe.
- **Atendimentos escolhidos** (propriedades conferidas no ensaio de 19/11; o
  prefixo `fonte:<n>:` depende da ordem em que as fontes foram criadas):
  0. `sintetica-lumen-tese` — abertura: o cliente reclama da espera, o bot
     resolve tarde, ele fecha com “ok, obrigado 🙂” e a estimativa sai
     **detrator, nota 2**. Sem sinalizador e sem abstenção.
  1. `sintetica-lumen-espera` — primeira resposta em 420 s, nota 0. O
     contrafactual de **60 s** foi aceito: +18,8 pontos no score, continua
     detrator.
  2. `sintetica-lumen-0145` — nota 9, promotor; conjunto conformal
     {neutro, satisfeito} → **abstenção por conjunto múltiplo**; sinalizador
     `abandono`, que aqui é o falso positivo declarado (despedida do bot).
  3. `sintetica-lumen-replay` — 14 falas do cliente, de cordial a irritado; o
     Replay marca a deterioração na mensagem 23 (4 falas antes do fim).
  Se no dia algum não exibir a propriedade, troque por outro que exiba e anote
  o id aqui. Não altere modelo nem dado para forçar.
- Confira **Usar tema claro** ou **Usar tema escuro** no menu da conta no
  equipamento da apresentação. O tema já existe; legibilidade no projetor
  precisa de ensaio físico, não de um novo “modo apresentação”.

### O que é sintético, real e inferido

| | o que é | como dizer |
|---|---|---|
| Sintético | os 156 atendimentos da Lumen Telecom, escritos por gerador determinístico | “atendimentos fabricados para a demonstração” |
| Real | os atendimentos do canal Telegram, feitos por colegas no bot do Tars, com voto | “atendimentos reais, poucos; não validam o modelo” |
| Inferido | nota, categoria e NPS, pelo motor real | “estimativa do texto, não pesquisa” |
| Limitação | tempo de treino sintético, ironia fora do vetor, generalização inconclusiva | ver [Limitações](../limitacoes.md) |

## 1. A tese (1 min)

**Falar:**

> O Fraus estima a satisfação a partir da conversa, sem exigir pesquisa e sem
> LLM no caminho de predição. A inferência usa modelos locais em CPU.
> Vou mostrar as capacidades disponíveis neste ambiente:
>
> - explica a estimativa a partir da decomposição do fusor;
> - informa abstenção quando a confiança pode ser calculada;
> - marca riscos sem pontuar o atendente;
> - permite examinar influência dos sinais e associação entre tema e NPS.

**Não afirmar:** que o NPS foi perguntado ao cliente. Apresente-o como
**inferido**, com a qualificação de estimativa, não como resposta de pesquisa.

## 2. Um atendimento, de ponta a ponta (4 min)

Abra o atendimento 1 (`sintetica-lumen-espera`) em **Atendimentos** e comece pela **Transcrição**.
Para mostrar os três gráficos por fala, use também o resultado de **Analisar**:
**Satisfação**, **Emoção** e **Ironia** descrevem a mensagem, não a nota da
conversa. Os detalhes da análise começam abertos; **Ocultar detalhes da análise**
e **Recolher os sinais** permitem simplificar a leitura. A ironia não entra
no vetor do fusor; uma probabilidade alta não confirma ironia real.

1. **Nota, categoria e “estimativa”.** A nota vem do servidor. Diferencie espera
   observada de satisfação inferida; “contido no bot” não prova resolução.
2. Expanda **Por que esta nota?**. Mostre **Falas que inclinaram a nota** e
   **Contribuições das features neste atendimento** (E1).
   - **Falar:** “O saldo de probabilidades da fala e a contribuição das features
     são objetos diferentes. A explicação por template usa a decomposição do
     fusor; as contribuições com intercepto reproduzem seus logits.”
   - **Não afirmar:** que o destaque de uma frase mede efeito causal de palavras
     ou que os efeitos por família somam a nota: esses recálculos não são aditivos.
3. No campo **E se a primeira resposta tivesse chegado em**, digite **60**
   segundos e clique em **Calcular**, se esse cenário tiver sido aceito no ensaio.
   - **Falar:** “Com estes horários hipotéticos, o modelo daria esta estimativa.
     Nada é gravado. Isso não prevê como o cliente teria reagido.”
   - Se houver recusa, leia o motivo. A rota pode recusar a própria conversa
     original ou a hipótese por sair da faixa de treino; não force um número.
4. **Confiança (E2).** No atendimento 2 (`sintetica-lumen-0145`), leia a classe ou o conjunto compatível com
   a nota e o alvo de calibração **retornado pelo servidor**. Não fixe 90% como
   promessa do ambiente. A classe de satisfação não é a categoria NPS.
   - Se existir um caso com **Leitura sem confiança suficiente**, mostre os
     critérios e a frase **Continua contando no NPS**. O conjunto pode ser
     múltiplo, vazio, ou a leitura pode ser marcada por deriva.
   - Sem artefato compatível, mostre a indisponibilidade. Não rode o script de
     calibração para contornar esse estado.
   - **Não afirmar:** garantia em atendimentos reais. O método exige
     permutabilidade com o holdout, cujo tempo é sintético.
5. **Sinalizadores (E5).** Mostre as regras acima da transcrição e as mensagens
   marcadas por elas.
   - **Falar:** “As regras usam sinais do cliente e do bot, contagens e posição;
     não leem texto nem relógio da fala humana e não alteram a nota. Os testes
     verificam a implementação; precisão e recall reais continuam não medidos.”

## 3. O agregado (2 min)

1. Em **Modelo**, expanda **Como o modelo foi avaliado**, encontre
   **O que influenciou as notas** e clique em **Ver influência dos sinais** (E1).
   O painel saiu da Visão geral e considera **todo o histórico** acessível,
   não o período da Visão geral.
   - **Falar:** “Esta é a amostra declarada de elegíveis; as contribuições estão
     na escala interna do modelo, não em pontos de nota. Intervalos só aparecem
     quando há dados para calculá-los. É associação, não causa.”
2. Menu da conta → **Operação → Radar**: abra **Evidências e NPS estimado** de
   um tema para mostrar **Impacto por tema (E6)**. No ensaio, quatro temas
   tiveram impacto numérico (cobrança indevida −52 [−81; −20]; segunda via do
   boleto +74 [35; 107]; troca de plano e visita do técnico com intervalo
   cruzando zero). “Internet caindo” se dividiu por vocabulário em grupos
   abaixo de 30, que mostram “n abaixo do mínimo” — bom exemplo do estado.
   - **Falar:** “Compara o NPS inferido do tema ao restante do recorte, não
     somente o NPS do tema isolado. O intervalo cobre incerteza amostral, não
     erro do modelo. Com menos de 30 conversas com sinal em qualquer lado, o
     sistema informa a falta em vez de mostrar impacto numérico.”
   - Se não houver tema recorrente ou amostra suficiente, mostre o estado vazio
     ou a insuficiência. Não produza conversas extras como se fossem dados reais.
3. Abaixo dos quatro indicadores, a linha **Voto do cliente** compara o voto
   dos atendimentos reais do Tars com a estimativa e mostra o denominador.
   - **Falar:** “Resolveu é resposta de resolução, não nota de NPS. Com este
     punhado de votos, isto é ilustração do ciclo, não validação.”

## 4. Retrospectiva de uma conversa (1 min)

Com conta `dev`, abra menu da conta → **Operação → Replay** e selecione o
atendimento 3 (`sintetica-lumen-replay`) em **Conversa do recorte**. Use **Anterior**, **Próxima** ou a
lista de mensagens. O limite é de 80 mensagens, até 40 do cliente; caso
incompatível não deve ser substituído silenciosamente por outro resultado.

- **Falar:** “Cada ponto considera somente o prefixo já ocorrido. Quando
  existe, a linha tracejada marca o início a partir do qual a estimativa ficou
  detratora e não voltou. É retrospectivo, não um alerta durante o atendimento.”
- Se não houver marca, mostre a ausência. Ela não é garantida para toda conversa.
- **Não afirmar:**
  - que o lead time medido prevê o de produção, porque o simulador não gera trajetória;
  - que essa marca detecta mais detratores que o score final, porque, por construção, não detecta.

## 5. O que o Fraus não faz (slide, 1 min)

| não faz | por quê |
|---|---|
| Não pontua atendente humano | É política do produto. Os sinalizadores não leem texto nem relógio da fala humana; isso não significa que todo cálculo ignore a transferência ou o tempo de atendimento. |
| Não oferece alerta ao vivo | Ingestão pode atualizar a conversa a cada turno do Tars, mas a marca do Replay é retrospectiva, não previsão ou alerta operacional. |
| Não decide nada sozinho | Abstenção, sinalizadores e deterioração marcam e informam. A nota não muda. |
| Não usa LLM na predição | São classificadores locais e um fusor linear. A explicação vem da decomposição, não de geração por LLM. |
| Não afirma causa | Drivers e impacto por tema são associação. |
| Não troca ausência por zero | Sem sinal, ou com amostra pequena, a tela nomeia o que falta. |
| Não chama de NPS declarado | É NPS **inferido**, sempre com a etiqueta de estimativa. |

## 6. Perguntas prováveis da banca

**"Por que não usar um LLM?"** Custo, latência, determinismo e execução local. A explicação do Fraus é exata porque o modelo final é linear. A comparação numérica com LLM foi **descartada** do escopo (E4); não há número para citar.

**"Esses números foram medidos no modelo real?"** Identifique primeiro o motor
do ambiente da apresentação. Depois consulte o [relatório](relatorio.md):
implementação de E1/E2/E5/E6 não comprova a validação real que falta. Só cite
resultados com fonte e data; a revisão documental não executou as medições.

**"O sinal de tempo é real?"** Os timestamps e as esperas de uma conversa podem
ser observados. O **treino do sinal de tempo**, porém, usou dados sintéticos
calibrados pela literatura, porque os corpora usados não traziam timestamps de
diálogo. Isso limita a transferência para atendimentos reais.

**"Como vocês sabem que os sinalizadores acertam?"** Os casos construídos verificam a implementação. Precisão e recall em dado real dependem de uma amostra anotada que ainda não existe.

**"Qual a diferença para os produtos do mercado?"** Comece pelo mais próximo: o Intercom CX Score também infere sem pesquisa, explica por motivos, deixa sem nota a conversa sem informação e não avalia atendente individual. Diga isso antes que a banca diga. O que é diferente, com fonte em [concorrentes](concorrentes.md):

- o Fraus não usa LLM (o Intercom declara usar LLM de terceiros);
- a explicação do Fraus é a decomposição exata do modelo;
- o Fraus implementa incerteza conformal por classe, com pressupostos e artefato
  explícitos; isso não demonstra cobertura real no ambiente desta apresentação.
  Nos concorrentes consultados, a pesquisa não encontrou esse mesmo contrato;
- Zendesk QA, Observe.AI e Medallia incluem avaliação de agentes nos produtos
  comparados; o Fraus não pontua atendentes.

## Base do roteiro

Controles conferidos em `dashboard/components/analisar/Analisador.tsx`,
`dashboard/app/dashboard/atendimentos/[id]/page.tsx`,
`dashboard/components/PorQueEstaNota.tsx`, `dashboard/components/SeloConfianca.tsx`,
`dashboard/app/dashboard/modelo/page.tsx`,
`dashboard/components/operacao/ConsoleOperacao.tsx`,
`dashboard/components/operacao/Leituras.tsx` e
`dashboard/components/operacao/Planejamento.tsx`. Recusas e limites vêm de
`fraus/api/rotas/conversas.py`, `fraus/api/rotas/confianca.py` e
`fraus/api/rotas/operacao.py`. O modo de demonstração está em
`scripts/api_demo.py`. São evidências de código, não de ensaio ou deploy.
