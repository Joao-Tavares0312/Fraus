# Diferenciais — roteiro da demonstração

Roteiro para apresentar os diferenciais na banca, em cerca de 10 minutos.
Conferido contra o código em **16/11/2026**, sem executar o ensaio nem consultar
produção. Cada passo diz:

- o que mostrar;
- o que falar;
- o que **não** afirmar.

A comparação com produtos do mercado está em [concorrentes](concorrentes.md), e cada afirmação ali tem fonte e data.

## Antes de começar

- Prepare uma instalação de demonstração isolada, com dados autorizados ou
  sintéticos **identificados como tais**. Confira o ambiente antes da banca:
  página publicada e serviço de saúde disponíveis não provam inferência real.
- **Com os modelos reais:** a API precisa dos classificadores obrigatórios e
  do fusor compatível com a escala `log1p`; a régua dos registros também precisa
  ser compatível. Só execute explicação, contrafactual, drivers e Replay como
  prova do modelo se esses requisitos estiverem atendidos.
- **Sem os modelos:** `uv run python scripts/api_demo.py` prepara um banco
  temporário com conversas sintéticas. O script tenta o motor real e pode
  usar um dublê explícito; confira o anúncio de inicialização e diga qual foi
  carregado. Com dublê, apresente apenas a navegação e os estados disponíveis,
  não explicação exata, contrafactual, confiança ou Replay como inferência real.
  Nunca use esse servidor em produção.
- **Confiança (E2)** depende de artefato conformal existente e compatível com a
  régua. Não há comprovação de disponibilidade nesta revisão. Se faltar, mostre
  o estado indisponível, não invente selo ou cobertura medida. Desde
  **16/11/2026**, modelos estão congelados: não execute calibração, retreino,
  promoção ou troca de pesos para preparar a demo.
- Use conta `dev` se for mostrar **Replay**: essa aba não aparece para
  `usuario`. Os dois papéis podem abrir **Modelo** e a explicação do detalhe.
- Escolha antes três atendimentos acessíveis no período:
  1. um com sinal e par cliente → resposta para o contrafactual, dentro da faixa
     aceita pelo modelo;
  2. um com sinalizador e, **se disponível**, abstenção;
  3. um compatível com o Replay e, **se existente**, uma marca de deterioração.
  Não prometa encontrar essas propriedades só porque o caso é detrator.
- Na preparação, faça o percurso **Analisar** → arrastar arquivo →
  **Conferir colunas**, se solicitado → **Analisar**. Com horários reais, a
  gravação é solicitada automaticamente; espere a confirmação
  **atendimento(s) salvo(s) nos indicadores** e use **Ver atendimentos**.
  Sem horários, demonstre leitura avulsa, sem nota nem incorporação ao NPS.
- Confira **Usar tema claro** ou **Usar tema escuro** no menu da conta no
  equipamento da apresentação. O tema já existe; legibilidade no projetor
  precisa de ensaio físico, não de um novo “modo apresentação”.

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

Abra o atendimento 1 em **Atendimentos** e comece pela **Transcrição**.
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
4. **Confiança (E2), se disponível.** Leia a classe ou o conjunto compatível com
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
   um tema para mostrar **Impacto por tema (E6)**.
   - **Falar:** “Compara o NPS inferido do tema ao restante do recorte, não
     somente o NPS do tema isolado. O intervalo cobre incerteza amostral, não
     erro do modelo. Com menos de 30 conversas com sinal em qualquer lado, o
     sistema informa a falta em vez de mostrar impacto numérico.”
   - Se não houver tema recorrente ou amostra suficiente, mostre o estado vazio
     ou a insuficiência. Não produza conversas extras como se fossem dados reais.

## 4. Retrospectiva de uma conversa (1 min)

Com conta `dev`, abra menu da conta → **Operação → Replay** e selecione o
atendimento 3 em **Conversa do recorte**. Use **Anterior**, **Próxima** ou a
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
