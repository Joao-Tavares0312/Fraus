# Handoff — Fraus, atualizado em 02/10/2026 (treino do Laya e divisão do corpus de ironia)

Escrito para uma sessão que não viveu nada do que está aqui. O objetivo é que
você consiga **decidir**, não só executar: cada regra abaixo vem com o motivo,
porque várias delas parecem erro até você saber por que existem.

O trabalho é o **TCC do João** (pt-BR). Fale em português com ele.

---

## 1. O que o Fraus é, em três frases

Ferramenta que lê atendimento por chatbot e **estima satisfação sem perguntar
nada ao cliente** — a tese é que "ok, obrigado 🙂" e sair insatisfeito é o caso
que uma pesquisa de NPS declarada não captura.

**Requisito de banca: nenhum LLM em runtime.** Três BERTimbau fine-tunados
(satisfação, emoção, ironia) e um fusor `LogisticRegression`. Se você se pegar
propondo chamar uma API de LLM para resolver alguma coisa, parou — isso invalida
o trabalho.

Stack: FastAPI + PostgreSQL/Supabase em produção (SQLite local) + Pydantic no back; Next.js 16 + shadcn/ui + Tailwind v4
+ Recharts no front (`dashboard/`).

---

## 2.0 Para retomar — Laya e ironia, 02/10/2026

**Onde parou:** o código está na `main` (PRs #80 e #81, mesclados em
02/10/2026) e a API foi publicada da `main` no mesmo dia. Falta rodar dois
notebooks no Colab, e isso parou porque a cota gratuita de GPU da conta acabou
na tarde de 02/10/2026.

### O que foi feito e o que se concluiu

- O Laya (encoder mmBERT-base com cabeça de decisão; **não** é um LLM e roda em
  CPU) foi treinado para emoção e ironia no notebook 07: 2 épocas, 71.102
  casos, 89 minutos numa T4.
- **O Laya não é promovido.** Em emoção ele ganha por pouco no teste interno
  (+0,018 de F1-macro) e perde no XED-pt, que é independente (−0,033, intervalo
  de −0,043 a −0,023). Em CPU é de 1,7x a 2,9x mais lento. Motor e Fusor
  continuam com o BERTimbau; nada mudou no caminho de predição.
- **A comparação de ironia daquele treino não vale.** A divisão treino/teste do
  corpus de ironia estava com defeito (armadilha 000 da §8) e foi consertada em
  `fraus/divisao.py`. Os dois modelos precisam ser treinados de novo.
- A aba **Modelo → Comparação** mostra o laudo versionado em
  `fraus/dados/comparacao_modelos.json`, com uma ressalva sobre a ironia.

Números, tabelas e bibliografia: [nota do treino](notas/2026-10-02-treino-laya.md).
Regra da divisão e o antes/depois: `docs/treinamento.md`, notebook 04.

### Passo a passo para terminar

> **Suspenso em 08/10/2026 — leia [Ironia: corpus e Laya](ironia.md) antes.**
> O passo 1 rodou com a divisão certa (28.365 / 4.778) e o BERTimbau deu F1
> 0,994 no teste e P(irônico) = 1,0 em "ok, obrigado". A causa é o corpus: os
> tweets não irônicos do IDPT são 100% `#economia` de portais de notícia. O
> modelo não foi exportado e o passo 2 não rodou, porque o Laya veria o mesmo
> atalho. A nova ordem é consertar o negativo, construir a régua de pares
> mínimos, corrigir `laya_treinado_pelo_fraus` e só então treinar. Medições:
> `docs/notas/2026-10-08-ironia-corpus.md`.
> Próximo passo: a régua de pares (docs/ironia.md, "Régua de pares mínimos")
> — anotar, consolidar, congelar.

### Régua de ironia: o que fazer quando as respostas chegarem (estado de 08/10/2026)

A anotação mora no próprio Fraus (PRs #86, #87 e #88, `main` em `8671e60`,
API e dashboard publicadas em 08/10). A página do claude.ai foi abandonada:
ela exige conta, e os colegas não têm. Em 08/10 o João postou no grupo de
WhatsApp um **link de grupo de 5 vagas** (`/anotar/grupo/<token>`), criado
pelo console do navegador logado como dev. Cada pessoa que abre vira um
anotador próprio; abrir em outro aparelho gasta vaga nova.

Já anotado: as 300 respostas do João, dadas no claude.ai, em
`fraus/dados/anotacao_regua/anotador-claude-ai.json` (anotador
`claude-ai-1`). Sozinhas elas dão 225/300 frases no rótulo pretendido e só
82/150 pares inteiros. No estrato elogio, ele marcou "depende do contexto"
em 19 dos 50 irônicos.

Quando os colegas terminarem:

1. **Exportar.** Logado como dev em `https://fraus-one.vercel.app`, no
   console do navegador:
   `fetch('/api/fraus/anotacao/respostas').then(r => r.json()).then(d => { console.log(d.length + ' registros'); copy(JSON.stringify(d)); })`
   e colar num `respostas-grupo.json`. Respostas de link revogado já saem
   de fora. (O `scripts/exportar_anotacao.py` faz o mesmo, mas precisa da
   `FRAUS_CHAVE_ACESSO`, cujo valor ninguém sabe — ver o passo 6.)
2. **Consolidar.**
   `uv run python scripts/consolidar_regua_ironia.py fraus/dados/anotacao_regua/anotador-claude-ai.json respostas-grupo.json`.
   Grava em `fraus/dados/`:
   - `regua_ironia_pares.csv`;
   - `regua_ironia_descartes.csv`, com o motivo de cada descarte;
   - `regua_ironia_invariancia.csv`;
   - `regua_ironia_meta.json`, com o κ global e por estrato e as duas
     impressões, uma dos textos e outra de rótulos com pares.
3. **Ler o resultado antes de congelar.**
   - **Piso:** abaixo de 100 pares o script recusa e diz quantos faltam.
     Nesse caso, olhar `regua_ironia_descartes.csv` por estrato. O
     suspeito é o elogio. Reescrever os pares ambíguos no rascunho
     (`fraus/dados/regua_ironia_rascunho.csv`), mantendo a vírgula e o "?"
     iguais nos dois lados, e anotar só esses de novo com um link novo.
   - **κ baixo:** significa discordância entre os anotadores, não defeito
     do modelo, e deve ser publicado junto, com o número de anotadores.
4. **Congelar.** Versionar os quatro arquivos. O teste
   `test_regua_versionada_bate_com_o_meta`, que hoje fica pulado, passa a
   rodar e trava a régua. Mudar uma frase, um rótulo ou um par depois disso
   quebra o teste de propósito.
5. **Só então treinar.** A ordem segue `docs/ironia.md`:
   1. consertar os negativos do corpus;
   2. corrigir `laya_treinado_pelo_fraus`, que exige `emocao` no manifesto;
   3. fazer os três treinos;
   4. comparar cada candidato com o baseline só de estilo
      (`fraus/baseline_estilo.py`) usando
      `avaliar_conjunto(..., par_ids=...)`. Promove só com
      `candidato_vence_por_par = True`.
6. **Pendências de operação.**
   - **Chave técnica:** rotacionar a `FRAUS_CHAVE_ACESSO` no projeto `fraus`
     da Vercel. Ela está marcada como sensível e ninguém sabe o valor; sem
     ela, `scripts/criar_link_anotacao.py` e `scripts/exportar_anotacao.py`
     não rodam. A rota de dev também aceita o JWT de dev pelo proxy, que é o
     que se usou em 08/10.
   - **Fechar o grupo:** depois da anotação, revogar o link de grupo com
     `POST /anotacao/grupos/<g_id>/revogar` (a resposta da criação mostrou o
     `g_id`).

Quem roda o Colab é o João, na conta institucional dele (a da Unis).
O `colab-mcp` se liga à aba que estiver aberta e não escolhe conta: em
02/10/2026 ele rodou célula na conta errada. Por isso a célula 1 dos
notebooks 04 e 07 confere a conta do Drive montado (`CONTA_DRIVE`) e para com
erro se não for a da Unis: o runtime pode ser de outra conta, o Drive não.

1. **Notebook 04** — cabeça de ironia do BERTimbau, 3 épocas, GPU obrigatória:
   <https://colab.research.google.com/github/Joao-Tavares0312/Fraus/blob/main/notebooks/04_treino_ironia.ipynb>
   - Ele grava por cima de `fraus/modelos/bertimbau-ironia` no Drive. Para
     guardar o modelo anterior, renomeie a pasta antes.
   - A célula 5 tem de imprimir perto de **28.365 linhas no treino e 4.778 no
     teste, com cerca de 59% de irônicas dos dois lados**. Esses números foram
     medidos fora do Colab com a regra nova. Se a divisão sair diferente do
     pedido, `conferir_divisao` para o notebook com erro — é o comportamento
     certo, não contorne.
2. **Notebook 07** — Laya, abrindo pelo link para pegar a versão da `main`:
   <https://colab.research.google.com/github/Joao-Tavares0312/Fraus/blob/main/notebooks/07_treino_laya.ipynb>
   - Na célula 7: `MODO_FUMACA = False` e `EPOCAS = 2`. Estimativa de 1h50 na
     T4 (são mais casos de ironia que no primeiro treino); não há checkpoint
     por época, então sessão que cai recomeça.
   - A célula 5 para com erro se o BERTimbau do Drive não for o do passo 1. É a
     trava que garante que os dois modelos são avaliados no mesmo teste.
3. **Trazer os resultados.** No Drive, em `fraus/modelos/`:
   `comparacao_modelos.json` e `metricas_laya.json` (o que tem `_fumaca` no
   nome é da rodada de teste e não serve).
4. **Publicar o laudo novo.** Copie `comparacao_modelos.json` por cima de
   `fraus/dados/comparacao_modelos.json`. O arquivo do notebook não tem
   `ressalvas`; só escreva uma se houver algo a ressalvar. Confira com
   `uv run pytest -q tests/test_rota_comparacao.py` e atualize a tabela de
   resultados na nota do treino.
5. **Ler o resultado de ironia pelo recorte certo.** Nas notícias a fonte
   entrega o rótulo (Estadão é sempre não-irônico; os sites de sátira, sempre
   irônicos), então o número agregado deve sair alto e isso não é vitória. O
   que conta é "Ironia — só tweets" e a régua de domínio.
6. **Decidir a promoção, que são duas decisões separadas:**
   - *Laya no lugar do BERTimbau:* só se ganhar no XED-pt e na régua. O
     critério foi escrito antes do primeiro treino; não o afrouxe depois de ver
     o número.
   - *BERTimbau de ironia novo em produção:* passa pelo portão de
     `scripts/validar_candidato_ironia.py` (ver `docs/treinamento.md`, "Portão
     de promoção do artefato"). Promover exige exportar para ONNX e republicar
     o ZIP de modelos da API (`docs/deploy-vercel.md`).
7. Os dois notebooks clonam a `main` (`RAMO = 'main'` na célula 2). O ramo
   `feat/treino-laya` não é mais necessário. Como o repositório é público, o
   clone não precisa de `TOKEN_GITHUB`.

### Se a GPU não estiver disponível

O aviso "Cannot connect to GPU backend" é cota da conta, não defeito do
notebook. Ela costuma voltar em menos de um dia, e o Google não publica o
prazo. Não conecte sem GPU: o notebook 04 recusa na primeira célula e o Laya em
CPU levaria dias. A alternativa gratuita é o Kaggle, mas os dois notebooks usam
Drive e download do Colab e teriam de ser adaptados antes.

### O que não foi verificado

- Os notebooks 04 e 07 não rodaram no Colab depois do conserto da divisão. As
  células novas do 07 foram simuladas com o corpus real e predições falsas.
- A célula 10 do repositório grava os pesos em FP16 (metade do tamanho, sem
  trocar decisão). Ela nunca rodou no Colab: o treino de 02/10 usou a versão
  anterior e saiu em FP32, com 617 MB. INT8 dinâmico está descartado para este
  encoder — trocou 56% das decisões no modelo treinado.
- A medição de tempo do laudo roda o BERTimbau em PyTorch e o Laya em ONNX, na
  CPU do Colab. Não é o tempo de produção.

---

## 2.0.1 LP nova com vgpu — branch `feat/lp-nova-vgpu`, 09/10/2026

Experimento pedido pelo João: uma LP que vende o Fraus construída com o
[vgpu](https://vgpu.sh) (WebGPU da Vercel Labs), na rota **`/leitura`**. A
vitrine de `/` não foi tocada. Spec em
`docs/superpowers/specs/2026-10-09-lp-nova-vgpu-design.md`, plano em
`docs/superpowers/plans/2026-10-09-lp-nova-vgpu.md`, design em
`dashboard/DESIGN.md` (seção "LP nova").

**Mistura (mesmo dia, mesma rota):** a pedido do João, `/leitura` virou a
mistura da LP nova com a vitrine antiga, toda em vgpu: hero, leituras e textos
da nova + a máscara que vira constelação da antiga (39 nós por feature). A
versão só-vgpu com os 7 enxames fica no histórico (`e663e8b`).

**Passo humano que falta:** gravar as leituras com o motor real. Sem isso a
seção "Escolha uma conversa" mostra o estado vazio.

```bash
FRAUS_LP_API=<url da fraus-api> FRAUS_LP_TOKEN=<credencial> uv run python scripts/gravar_leituras_lp.py
git add dashboard/lib/lp-nova/leituras.json
```

O script recusa gravar se faltar leitura, se a conversa sem cliente voltar com
nota ou se outra voltar sem. Pôsteres: `cd dashboard && npm run posteres`
(determinístico, compara duas renderizações). Validação: `npm run wgsl`,
`npm run test:leitura` com o dev de pé.

**Armadilhas já pagas:** a doc do site do vgpu está à frente da 0.5.0
(`target.read()` não existe; a leitura é `alvo.color.read({ mipLevel: 0,
region: "all" })`; `surface` só desenha dentro de `frame()`). A doc certa é a
versionada: `npx vgpu docs`. O Dawn do Node sobe em modo de compatibilidade
(workgroup ≤ 128, zero storage buffer no vértice).

**Bug achado na `main`, fora deste branch:** em `next dev` a vitrine de `/`
perde o contexto WebGL. O StrictMode remonta o efeito, a limpeza chama
`loseContext()` e a segunda montagem pega o mesmo canvas com o contexto perdido
(8 erros "shader nao compilou null"). O build de produção não é afetado
(medido). Conserto pendente em branch próprio.

## 2. Estado em 30/09/2026, com o que mudou em 02/10/2026

**Em 02/10/2026:** PRs #78 (proxy só empresta a credencial do deploy onde não
há login), #79 (ícones de ação), #80 (treino do Laya, aba Comparação, divisão
do corpus de ironia) e #81 (trava da migração no Postgres, emoção pelo Laya
sem treino) entraram na `main`. A API foi publicada da `main` pela CLI no mesmo
dia (deploy `fraus-ajbdtr0gh`), com `/saude/prontidao` em 200. CI da `main`:
1.162 passed em SQLite e 1.163 em PostgreSQL; front com 195 testes em 23
arquivos. **O job de CI da dashboard entrou logo depois do PR #82** (`tsc` e `vitest` em
`.github/workflows/testes.yml`); antes dele só o pytest rodava. Mexer em
workflow exige credencial do GitHub com escopo `workflow`
(`gh auth refresh -h github.com -s workflow`, em terminal interativo).

**Qual cabeça lê ironia em produção:** o Laya **sem treino**, exportado para
ONNX (`FRAUS_IRONIA_BACKEND=laya-onnx` no projeto `fraus-api`). O BERTimbau de
ironia vai no pacote e não é carregado. Emoção e satisfação são BERTimbau. O
Laya treinado em 02/10 não foi promovido (§2.0).

**Regras que entraram com a auditoria de 02/10/2026 (PR #82, mesclado)** — cada uma
parece detalhe até alguém desfazer:

- **O dia de uma conversa é o dia de Brasília**, fixo em −03:00, na API
  (`fraus/fuso.py`) e na dashboard (`dashboard/lib/fuso.ts`). Antes a API
  agrupava pelo offset em que o instante foi gravado e a tela pelo fuso do
  navegador: a mesma conversa das 22:30 caía em dias diferentes no gráfico e na
  tabela. A coluna `iniciada_em` é gravada já em −03:00, porque o recorte por
  período corta os dez primeiros caracteres dela; `migrar()` reescreve as
  linhas antigas (`_normalizar_inicios`). Offset fixo, e não
  `America/Sao_Paulo`: o fuso nomeado devolve −02:00 nos verões anteriores a
  2019 e a tela discordaria da API.
- **Arquivo que não traz id de conversa não grava com o id do leitor**
  (`fraus/api/identidade.py`). Arquivo sem coluna de conversa virava a conversa
  `conversa`, e o segundo arquivo importado apagava o primeiro. Na importação
  da pasta o id é `arquivo:<nome>:<resumo do caminho>` — reimportar o mesmo
  arquivo corrige, outro arquivo é outra conversa. No upload de Analisar segue
  `analise:<resumo do conteúdo>`.
- **Transcrição em prosa traz a hora e não o dia** (`Extracao.tem_data`
  falso). A hora é lida como relógio de Brasília; o dia é o do envio e fica
  **fora do id**, senão o mesmo arquivo reenviado amanhã contaria duas vezes no
  NPS. O reenvio conserva o dia já gravado. A resposta avisa que o dia é o do
  envio. **Decisão em aberto, do João:** aceitar essas transcrições nos
  indicadores com o dia do envio (como está) ou pedir o dia a quem envia.
- **Convite de equipe é consumido no cadastro, não só no aceite.** A conta
  criada pelo link reserva um uso (`reservas` no documento do convite) na mesma
  transação; antes, um link de limite 1 criava contas sem fim numa instalação
  fechada por código. A reserva não filia: entrar na equipe continua sendo o
  aceite com JWT. Quem tem a reserva ainda vê o convite aberto — por isso a
  prévia pública lê a sessão quando ela vem.
- **Repontuar retoma, não recomeça.** Havendo conversa na régua anterior, só
  elas são percorridas. **Limite conhecido:** na Vercel a thread pode parar
  quando a instância é suspensa, e ninguém retoma sozinho — a execução parada
  segura o lock até o heartbeat vencer (15 min) e alguém precisa pedir de
  novo. Resolver de vez pede um executor fora da requisição (cron ou fila), e
  isso é decisão de infraestrutura.

O texto abaixo é o registro de 30/09 e continua valendo no que não foi citado
acima.

### Análise persistida e Operação — mescladas e publicadas

**Entrega fechada:** PR #75, commit da `main` `ab1b5da`. Dashboard publicada
após merge; API publicada separadamente no projeto `fraus-api`, deploy
`dpl_2ghd1GGyN6ftxYvZ7pgPwnA3KyvF`, confirmado `Ready` e associado a
`https://fraus-api.vercel.app`. A função construída tem **1,95 GB**; isso é
tamanho do pacote, não consumo de RAM. O 404 de Operação em produção foi
resolvido com esse deploy. [Registro completo](notas/2026-09-30-operacao-producao.md).

Validação em 30/09/2026:

- CI da `main`: **1.091 passed, 4 skipped, 1 deselected em cada dialeto**
  (SQLite e PostgreSQL), execução `36781395898`; documentação também aprovada.
- Dashboard: **163 testes em 20 arquivos**, TypeScript, lint dos arquivos
  alterados e build aprovados.
- Interface local `localhost:3001`: sete abas sem erro de JavaScript,
  hierarquia carregada e salvar equipe retornando 200.
- Produção: saúde com `motor=real`, login disponível; radar, equipes, jornadas,
  investigações, acessos e simulação retornando 200 pelo proxy da dashboard.
  OpenAPI confirmou edição de equipes, convites, aceite e gravação de análise.
  Esse smoke não executou aceite/cadastro nem gravou conversa de teste em produção.

**Pendências de configuração:** `production-api` estava sem os secrets do
workflow manual. O deploy acima usou a CLI autenticada; não declarar CI/CD da
API automático. Comparar fusores exige `FRAUS_FUSOR_CANDIDATO` configurado com
artefato compatível; sua presença em produção não foi confirmada.

- `POST /analisar/registrar` analisa com motor real, exige timestamps reais,
  confirma mapeamentos inferidos e grava o lote atomicamente. IDs canônicos no
  namespace `analise:` impedem duplicação por reenvio e sobrescrita de fontes.
  As rotas avulsas preservam o contrato anterior. Dashboard relê dados ao salvar,
  voltar à janela e receber atualização de outra aba.
- NPS usa AW(3,T); o cartão respeita `nps_intervalo.nps = null` abaixo de 30.
  Há testes de amostras unânimes e do exemplo publicado do método.
- `/dashboard/operacao` reaproveita Instrumento e oferece sete abas. Algoritmos
  em `fraus/operacao.py`, rotas em `fraus/api/rotas/operacao.py`; sem LLM.
- Metadados de equipe/jornada/problema/permissão/convite ficam em
  `operacao_registros`. Alterações de histórico e aceites concorrentes usam
  transações e locks em ambos os dialetos. Auditoria usa cadeia SHA-256, não
  assinatura nem defesa contra reescrita integral do banco.
- Proprietário administra hierarquia; gestor convida/remove membros; membro
  participa. Convite nunca promove para `dev`. Cadastro por convite tem escopo
  vazio na mesma transação de criação; aceite vincula e concede canais da
  equipe atomicamente. Remoção recalcula escopos originados de convites.
  Política manual do administrador prevalece. Equipe sem canais concede nenhum.
- JWT carrega versão de sessão, conferida no banco a cada acesso; revogação é
  imediata. `BancoComEscopo` limita lista, detalhe, indicadores, grafo, referência
  de vocabulário e gravação por canal. `dev` e credenciais técnicas seguem amplos.
- Exportação formal exige autorização temporária para `usuario`, incluindo o
  botão CSV existente. Isso controla a ação de exportar, não impede copiar os
  dados que a própria conta tem permissão de consultar.
- Lab e replay não alteram registros. Comparação exige arquivo compatível em
  `FRAUS_FUSOR_CANDIDATO`. Hipóteses, ausência de sinal e incerteza ficam visíveis.
- Validação reproduzível: `scripts/validar_operacao_real.py` usa ONNX real com
  SQLite temporário ou somente PostgreSQL local `fraus_validacao`; nunca escolhe
  o banco de produção. `--servir --porta 8017` mantém a instância de QA.
  A dashboard pode usar `FRAUS_DIST_DIR` para evitar disputa de cache com dev.

> **Atualização de 30/09/2026 (leia primeiro).**
>
> 1. **A interface foi redesenhada** (mundo "Instrumento"): números medidos são
>    display de sete segmentos (`components/instrumento/SegmentoLED.tsx`), "sem
>    sinal" é o segmento **apagado**, hairline de 1px, raio zero, Martian Mono +
>    Inter + Bricolage, e a vitrine tem um orbe em CSS. A "Pauta", o espaço
>    profundo e a Mona Sans foram descartados; o contrato é
>    `dashboard/DESIGN.md`.
> 2. **`scripts/api_demo.py` NÃO é mais dublê por padrão.** Ele carrega o motor
>    real quando os pesos estão no disco (`FRAUS_DEMO_DUBLE=1` força o dublê) e
>    sobe de um **snapshot versionado**, `dados_demo/fraus-demo.db` (64
>    conversas sintéticas, sem segredo), para o gráfico NPS × latência sempre ter
>    série. `FRAUS_DEMO_RESSEMEAR=1` recompõe do zero. Confira sempre o
>    `motor` em `/saude` (ver "Como saber em qual você está").
> 3. **Produção** = dois projetos Vercel (`fraus` e `fraus-api`, ONNX), Supabase
>    Postgres e ZIP de modelos no Oracle Object Storage
>    ([deploy-vercel.md](deploy-vercel.md)). A API esfria: o motor agora
>    aquece em segundo plano (boot e `GET /saude`) e o workflow `api-aquecer`
>    pede sonda a cada 5 min — mas o agendador do GitHub entregou 10 execuções
>    em 45 horas (medido em 02/10/2026), então **não conte com ele**: antes de
>    demonstrar, abra `/saude` e espere `/saude/prontidao` dar 200. Reduz o
>    cold start, não o elimina; o Render gratuito
>    não serve (512 MB contra ~1,06 GB medidos).
> 4. Os números da vitrine moram em `dashboard/components/lp/fatos.ts`.
>
> O restante desta seção descreve o estado de 08–15/09/2026 e ainda vale nos
> pontos que não contradizem o acima.

## 2.1 Estado de 08/09/2026

> **Atualização de 15/09/2026 (branch `feat/leva-1-api`, uma PR só).** Leia antes
> do resto desta seção, porque três coisas mudaram o que o sistema faz:
>
> 1. **A espera entra no fusor em `log1p`** (`FEATURES_EM_LOG` em `vetorizar`) e
>    o `fusor.joblib` foi **regerado** (acurácia 0,9467). O artefato carrega a
>    escala; `Fusor.carregar` **recusa** um de antes. Toda cópia do artefato
>    (VM, Drive) precisa ser regerada com `scripts/retreinar_fusor_local.py
>    --promover` ou pelo notebook 02. O P0 do tempo (§7) está resolvido.
> 2. **Conversa só de cortesia é sem sinal** (`fraus/cortesia.py`): "valeu"
>    sozinho saía promotor. O servidor manda `motivo_sem_sinal`.
> 3. **O banco existente está na régua anterior.** `/indicadores` ganhou
>    `pontuadas_com_regua_antiga` (léxico **ou** modelo), e o aviso da visão
>    geral oferece repontuar — agora **em segundo plano**, com progresso.
>
> E também: `FRAUS_BACKEND=onnx` (sem torch, 1,5× mais rápido, 0 categorias
> trocadas; torch virou extra), CI rodando a suíte em SQLite **e** Postgres,
> teto de corpo para `chunked`, cabeçalhos `no-store`/`nosniff`, e o
> [cartão do modelo](cartao-do-modelo.md) com avaliação por fatias.

| | |
|---|---|
| Testes históricos das branches | **1.057 passed, 1 deselected** (Python) · **144** (front, 17 arquivos) na branch do redesign; ~1.060 e 148 na branch do cold start. A entrega final de Operação passou com **1.091** por dialeto e **163** no front; veja §2 |
| Modelos | os três em `modelos/`, 1,3 GB, **fora do git**; fusor em dia (39 features, acurácia 0,950) |
| API real | `uv run python -m uvicorn fraus.api.main:app --port 8001 --reload --reload-dir fraus` → confira `/saude` e `/saude/prontidao` |
| API de demonstração | `uv run python scripts/api_demo.py` → :8000. Motor real se houver pesos (senão dublê, dito no boot); banco = snapshot `dados_demo/fraus-demo.db`. **Não é produção**: banco descartável e sem chave |
| Dashboard | `cd dashboard && npm run dev` (ou `npm run build && npx next start`) |

**A API nasce FECHADA**, e este parágrafo dizia o contrário até 08/09/2026. Na
primeira subida ela gera a mestra e uma chave de acesso e grava as duas em
`.fraus-chaves.txt` (caminho configurável por `FRAUS_CAMINHO_CHAVES`),
anunciando no boot. A dashboard lê a chave desse arquivo sozinha. `curl` na mão
precisa de `Authorization: Bearer <mestra>`; sem isso você toma 401 e vai achar
que quebrou alguma coisa.

**Armadilha de sessão: se você definir `FRAUS_CHAVE_MESTRA` e
`FRAUS_JWT_SEGREDO` sem `FRAUS_CODIGO_CONVITE`, a API responde 401 para anônimo
e mesmo assim está aberta** — `registrar` → `entrar` → o JWT lê tudo. Desde
08/09/2026 o boot grita quando essa combinação sobe. Ver `README.md`, seção "A
porta destrancada".

Com a mestra ligada, toda rota exige `Authorization: Bearer`, exceto duas,
que têm credencial própria: `POST /ingestao` (chave de fonte `frs_`) e
`POST /integracoes/webhook/{fonte_id}` (assinatura HMAC no corpo). A segunda é
**anônima por desenho** — a plataforma externa não tem, nem pode ter, uma chave
`fra_`; ver a armadilha 8. Ela é uma porta pública de **escrita**: quem publica
a API na internet precisa saber que ela existe. Ver `README.md` e
`docs/hospedagem.md`.

### A LP e a autenticação de usuário, em um parágrafo cada

**A raiz virou vitrine.** `/` descreve o produto (tese, sete sinais,
honestidade metodológica) e as telas moram em `/dashboard/*`, com redirect das
rotas antigas. Nenhum número da LP é inventado — 39 features e sete sinais são
fatos do código, e não há acurácia fabricada nem depoimento. **Isso impõe uma
obrigação:** quando `NOMES_FEATURES` mudar, os números da LP mudam junto
(hoje numa fonte só: `dashboard/components/lp/fatos.ts`). Em
04/09/2026 o contrato foi a 38 (e no mesmo dia a 39) e a LP ficou anunciando 35 — número falso numa
tela pública, exatamente o que esta seção promete que não acontece. Agora há
guarda: `tests/test_derivacoes_dashboard.py::test_a_vitrine_anuncia_o_numero_real_de_features`
lê `components/lp/fatos.ts` como texto e compara `features` com
`NOMES_FEATURES`, e varre `components/lp/` e `app/page.tsx` atrás de qualquer
outro "N features" digitado à mão (mutação conferida em 30/09/2026: as duas
divergências derrubam o teste). Prosa que cite o número por extenso, fora desse
formato, continua sendo conferência manual.

**Usuário é identidade, não credencial técnica.** Tabela `usuarios` (senha
scrypt em `fraus/usuarios.py`), JWT HS256 (`fraus/token_acesso.py`, PyJWT —
única dependência nova), rotas em `fraus/api/rotas/auth.py`. Papéis: `dev`
administra, `usuario` analisa — o portão de papel mora no middleware
(`seguranca.py`, `rota_administrativa`) e vale **nos dois modos**: JWT de
usuario apresentado toma 403 em rota administrativa mesmo com a API aberta.
Segredos no ambiente, nunca no banco: `FRAUS_JWT_SEGREDO` (assina o token; sem
ela o login responde 503 e a dashboard abre sem exigir login — modo aberto) e
`FRAUS_CODIGO_DEV` (código de convite; sem ela ninguém nasce dev; código
errado é 403 explícito, nunca rebaixamento silencioso). No Next, o token vive
em cookie httpOnly (`fraus_sessao`) e é o degrau ZERO da credencial do proxy —
vence a chave `fra_` do deploy de propósito, ou o portão de papel nunca veria
o papel. A recusa de login é uniforme em status, texto e tempo (o scrypt
deriva mesmo para e-mail inexistente).

### Como subir

```bash
uv run uvicorn fraus.api.main:app --port 8001 --reload --reload-dir fraus
cd dashboard && npm run dev
```

O `--reload` acima é para desenvolvimento local. A dashboard atualiza seus
componentes durante a edição, mas uma API iniciada sem recarga mantém as rotas
antigas em memória. Isso ocorreu nesta sessão: `/operacao/equipes` respondia
sem `integrantes` e `meu_papel`, enquanto edição e convites devolviam 404.
Reiniciar a API preservando o ambiente e o banco resolveu o problema em
`localhost:3001`; as sete abas e salvar equipe foram conferidos na interface.
No Windows, use `python.exe`/`uv run` para a recarga, com a janela oculta se
iniciada em segundo plano. O launcher `pythonw.exe` não iniciou o worker de
recarga nesta validação.

Aceitar convites exige uma sessão de usuário. Sem `FRAUS_JWT_SEGREDO`, o modo
local aberto permite administrar pela credencial técnica, mas não habilita
login/cadastro nem o aceite. Em produção, o merge da dashboard precisa ser
acompanhado pela publicação da API atualizada; o fluxo manual está em
`.github/workflows/api-deploy.yml`.

**Não suba `scripts/api_demo.py` achando que é a API de produção.** Ele usa
banco temporário sem autenticação, e cai no **motor dublê** se os pesos não
estiverem no disco — aí devolve números sintéticos com cara de predição e a
dashboard não distingue. Uma sessão já perdeu um dia inteiro com isso, inclusive
os pesos por feature, que saíam numa progressão `0,2 / 0,25 / 0,3` e passavam
por peso de regressão. (Desde 30/09/2026 o padrão é o motor real quando há
pesos; o boot imprime qual subiu.)

**Como saber em qual você está, em uma linha:** `curl -s :8001/saude` responde
`{"status":"ok","motor":"real"}` ou `"motor":"duble"`. Desde a PR #32 os
caminhos dos artefatos ancoram na raiz do projeto, então o diretório de onde
você lança o uvicorn não decide mais o motor — mas confira mesmo assim.

### Comandos de verificação

```bash
uv run pytest -q                 # 1213 passed, 6 skipped, 1 deselected (02/10/2026, ramo da auditoria)
uv run pytest -m lento           # o de minutos, obrigatório ao mexer no gerador
cd dashboard && npx tsc --noEmit # tipos
cd dashboard && npm run contraste # WCAG AA, por cálculo
```

---

## 3. As regras que governam este código

Não são preferências de estilo. Cada uma nasceu de um defeito real, e violá-las
é reintroduzir o defeito.

### 3.1 Ausência nunca vira zero

A regra mais importante do projeto. `None`/`null` e `0` significam coisas
diferentes e **não podem se confundir em lugar nenhum**:

- conversa sem fala do cliente tem `score: null`, não `0` — "o cliente não
  falou" não é "o cliente estava insatisfeito";
- conversa sem atendente humano tem `latencia_mediana_humano_s: null`, exibido
  como travessão e exportado como célula **vazia** no CSV — `0.0` numa coluna de
  tempo de resposta se lê como "respondeu na hora", e a conversa que nunca teve
  atendente apareceria como a mais ágil da operação;
- palavra acima do teto de medição tem `peso: null`, e palavra medida em zero
  tem `peso: 0` — "não medimos" e "medimos e não importou" são respostas
  diferentes;
- métrica não exportada é `null`, nunca `0%`.

Ordenação segue junto: nota e espera mandam a ausência **para o fim nos dois
sentidos** (`TabelaConversas.ausenciaPorUltimo`).

### 3.2 Sem horário, sem nota

Latência é uma das 39 features do fusor, com peso aprendido. Uma transcrição de
`.docx`/`.pdf` sem relógio não recebe nota, e a tela diz por quê.

Zerar os campos de tempo seria o caminho fácil e **zero não é neutro**: o modelo
aprendeu que resposta rápida acompanha cliente satisfeito, então a conversa
entraria como se toda resposta tivesse sido instantânea e a nota sairia melhor
que a verdade — sem nenhum erro aparecer. Ver `fraus/ingest/transcricao.py`.

### 3.3 O veredito é sempre derivado no servidor

`score`, `nota` e `categoria` nunca vêm do cliente. Campos com esses nomes no
corpo de uma requisição são **ignorados por construção** — há teste para
`/conversas/importar` e para `/ingestao`. O canal também: na ingestão ele vem
da **fonte cadastrada**, não do corpo.

A `nota` é derivada no Python e o front só exibe. Recalcular no JavaScript já
divergiu nas fronteiras 6/7 e 8/9 (arredondamento bancário contra meio-para-cima)
e fazia a tabela mostrar nota 7 ao lado de "Detrator".

### 3.4 Emoção pontua; ironia NÃO pontua mais, desde 04/09/2026

O fusor tem **39 features** (confira `fraus.fusor.NOMES_FEATURES`), de SETE
famílias. Emoção entrou no vetor em 21/08/2026 e continua lá. A **ironia
entrou junto e saiu em 04/09/2026**: medida no próprio corpus de treino
(B2W-Reviews01), a cabeça marca 74% das resenhas satisfeitas como irônicas
contra 9% das insatisfeitas — no corpus do fusor ela é um detector de
sentimento positivo, não de ironia, e o fusor aprendeu peso **+0,77** para
`ironia_prob_media`, empurrando ironia para SATISFEITO. Feature que mede outra
coisa que não o nome dela é pior que feature ausente. Ver
`docs/treinamento.md`, seção "A ironia sai do vetor".

A cabeça de ironia **continua carregada e obrigatória** (invariante 7) e
continua sendo lida por mensagem e exibida na dashboard — o que mudou é que
ela não pontua. A interface sempre manteve as leituras **visualmente separadas**
da nota, e isso vale independente de a feature pontuar ou não: encostar
"ironia 99%" na barra de satisfação convida a ler uma como causa da outra.

### 3.5 O que ficou de fora é relatado

Importação diz quantas linhas rejeitou e por quê. Análise diz quantas conversas
cortou. O adaptador da Totalk diz **o que inferiu**. "Importado com sucesso" sem
a contagem de rejeitadas esconde exatamente a linha que precisa de conserto.

### 3.6 Estado vazio nomeia o próximo passo

Nada de "sem dados". O estado vazio diz o endpoint ou o notebook que preenche
aquilo. Ver `components/EstadoVazio.tsx`.

### 3.7 Ressalva repetida vira ruído

Já corrigido duas vezes: o aviso de métrica suspeita era por cartão (3×) e virou
por cabeça; a prosa do desprezo/ironia era por mensagem (até 19×) e virou uma
vez na legenda do painel. Se você repetir uma explicação em cada item de uma
lista, ela para de ser lida.

---

## 4. Mapa do código

### Back — `fraus/`

| arquivo | o que é |
|---|---|
| `modelos.py` | modelo canônico: `Conversa`, `Mensagem`. Timestamp **timezone-aware** obrigatório. `tem_fala_cliente` (operação) ≠ `tem_sinal_cliente` (nota) |
| `cortesia.py` | fórmulas de cortesia: conversa só com elas é **sem sinal** (15/09/2026) |
| `fatias.py` | avaliação por fatia, parte pura — `scripts/avaliar_por_fatias.py` roda os modelos |
| `sinais/onnx.py` | o mesmo checkpoint no ONNX Runtime (`FRAUS_BACKEND=onnx`) |
| `api/repontuacao.py` | repontuar em segundo plano, um trabalho por processo, progresso em `GET /conversas/repontuar` |
| `fusor.py` | `LogisticRegression` + `StandardScaler`. `NOMES_FEATURES` é o contrato de 39 |
| `resumo.py` | ficha operacional: contagem por autor, latências **separadas** bot/humano, `desfecho` |
| `indicadores.py` | NPS, CSAT, contenção, série diária |
| `credencial.py` | chave de fonte (`frs_`): gerar, hash, conferir em tempo constante |
| `acesso.py` | chave de acesso (`fra_`) e a mestra — mesmo desenho do `credencial.py` |
| `db.py` | PostgreSQL/Supabase e SQLite, lote transacional e metadados de operação. `_fonte()` remove `chave_hash` **na origem** |
| `operacao.py` | temas, escala e cópias de cenário |
| `api/rotas/operacao.py` | contratos de equipes, convites, jornadas, investigações, replay, laboratório e acessos |
| `api/escopo.py` | canais autorizados antes de listar, consultar, agregar e gravar |
| `sinais/texto.py` | BERTimbau de satisfação — **o único que pontua** |
| `sinais/emocao.py` | 7 de Ekman + desprezo derivado (Plutchik, média geométrica) |
| `sinais/ironia.py` | binária. **Ver pendência 1** |
| `sinais/palavras.py` | peso por palavra via **oclusão** + vocabulário comparado |
| `sinais/tempo.py` | latências. `latencias_da_conversa` é pública de propósito |
| `ingest/csv_driver.py` | o driver **canônico** |
| `ingest/totalk.py` | adaptador do export da Totalk |
| `ingest/transcricao.py` | prosa (`Autor: mensagem`) de docx/pdf |
| `ingest/leitores.py` | formato → tabela: codificação, delimitador, JSON aninhado, WhatsApp `.txt` — só biblioteca padrão |
| `ingest/mapeador.py` | tabela de estrutura desconhecida → `Conversa`: papel de cada coluna por nome + conteúdo, ordem da data pela coluna, tudo relatado como aviso |
| `api/rotas/perfis.py` | `/perfis-mapeamento` — o mapeamento de colunas que o analista confirmou, chaveado pela assinatura das colunas |
| `ingest/arquivos.py` | decide o formato e traduz erro em mensagem útil |
| `ingest/gerador_ironia.py` | corpus sintético blindado contra vazamento |
| `api/main.py` | só a montagem (~420 linhas; as rotas moram em `api/rotas/`). `criar_app(banco, motor, raiz)` recebe tudo por parâmetro |
| `assinatura.py` | HMAC de webhook (Standard Webhooks): `whsec_<base64>`, chave = base64 **decodificado**, assina `{id}.{timestamp}.{corpo}`, janela de 5 min |
| `api/registro.py` | o miolo de `montar → pontuar → derivar → gravar`, compartilhado por `/ingestao` e `/integracoes/webhook/{id}`; é onde mora `resumo_validacao` |
| `api/rotas/webhook.py` | `POST /integracoes/webhook/{fonte_id}` — o porteiro na ordem identidade→autoridade→parse, com registro de entrega em `entregas_webhook` |

### Front — `dashboard/`

Rotas (mundo "Instrumento", 30/09/2026): `/` é a **vitrine** (`components/lp/`,
CSS em `app/vitrine.css`, números em `components/lp/fatos.ts`); a ferramenta
mora em `/dashboard` (visão geral), `/dashboard/atendimentos` (lista e
`[id]`), `/dashboard/analisar`, `/dashboard/modelo`, `/dashboard/grafo`,
`/dashboard/configuracoes` e `/dashboard/integracoes`; mais `/entrar`,
`/cadastrar` e o 404. Todo número medido passa por
`components/instrumento/SegmentoLED.tsx`; a faixa de telemetria é
`TelemetriaTopo`, e a navegação numerada vive em `lib/navegacao.ts`.

`lib/api.ts` é a **única** porta para a API — tipos e funções. `lib/formato.ts`
concentra formatação (`formatarEsperaOuTraco` é quem transforma `null` em `—`).

`components/CabecasDeLeitura.tsx` é **compartilhado** entre o simulador e a
análise. Desde 15/09/2026 ele desenha a **partitura da fala**
(`components/PartituraDaFala.tsx`, lógica em `lib/partitura.ts`): classe,
emoção e ironia no mesmo eixo 0–1, forma da nota dizendo a origem (cheia,
vazada, tracejada) e o colchete de disputa abaixo de 0,15 de margem —
número de interface, sem calibração. Não faça uma segunda cópia: duas cópias de um painel que explica um
modelo envelhecem separadas, e a que envelhece é sempre a que ninguém olha.

---

## 5. Design — leia antes de mexer em pixel

**`dashboard/DESIGN.md` e `dashboard/PRODUCT.md` são obrigatórios.** O mundo
visual se chama **"Instrumento"** (redesign de 30/09/2026: painel de instrumento
de laboratório, números em LED de sete segmentos, hero de orbe na vitrine; a
"Pauta" e o espaço profundo foram descartados) e a regra mestra continua:

> Acima da linha é o que foi **DITO**. Abaixo da linha é o que foi **MEDIDO**.

Encoding que atravessa tudo:

- **âmbar** (`--dito`) = fala, texto, emoji;
- **azul** (`--medido`) = score, probabilidade, tendência;
- **dourado** (`--primary`) = ação e foco, **nunca dado**.

O `--primary` é o dourado do R da logo, medido do arquivo. Ele convive com o
âmbar porque o que os separa é o **croma** (fosco contra saturado), e porque
nunca dividem superfície. O **LED é azul** (medido): número que o servidor
mediu vira display de sete segmentos, e "sem sinal" é o segmento **apagado**,
nunca zero (`components/instrumento/SegmentoLED.tsx`). Detalhes no `DESIGN.md`.

**Intocáveis declarados pelo João:** os textos de honestidade, o gráfico
sobreposto NPS × latência, e âmbar=dito / azul=medido.

`npm run contraste` verifica AA **por cálculo**, incluindo o rótulo dentro do
botão. Rode depois de mexer em cor.

---

## 6. Skills a usar

Instaladas em `~/.claude/skills/`. As que servem a este projeto:

| skill | quando |
|---|---|
| **impeccable** | qualquer trabalho de UI. Modo **Operate** (é ferramenta de dados, não landing page). `PRODUCT.md` e `DESIGN.md` já existem — ela os lê |
| **taste-skill** | auditoria de frontend, antes de propor redesenho |
| **redesign-skill** | auditoria de execução: ritmo tipográfico, densidade, estados |
| **security-audit** | **relevante de verdade aqui** — chaves, sessão de usuário, proxy e escopo por canal guardam dado de cliente |
| **superpowers:brainstorming** | antes de planejar feature nova |
| **superpowers:systematic-debugging** | antes de caçar bug |

As demais (`access`, `configure`, `silence`, `who`, `decisions`,
`flow-patterns`) são do assistente Discord do João, **não deste projeto**.

Ao invocar a `impeccable`, não deixe ela redirecionar a paleta: as decisões de
cor estão fechadas e documentadas.

---

## 7. Pendências, em ordem

O `README.md` tem a lista canônica e foi atualizado hoje. Resumo:

### Feita — API real hospedada sem VM — 17/09/2026

Dashboard e API agora são projetos Vercel independentes. A função FastAPI usa
ONNX Runtime, recebe os modelos de um bucket privado do Oracle Object Storage
durante o build e persiste no Supabase pelo transaction pooler. Produção foi
verificada direto e pelo proxy da dashboard com `motor=real`, além de uma
inferência autenticada.

O caminho remove quatro pendências antigas: capacidade Ampere A1, VPS paga,
túnel ligado na máquina local e SQLite efêmero. A sequência de falhas e
correções — tamanho, `.vercelignore`, dependência ONNX, inicialização tardia,
porta 6543 do pooler e isolamento do monorepo — está registrada em
[`docs/deploy-vercel.md`](deploy-vercel.md). Cold start e cotas gratuitas são
limites operacionais, não pendências de implementação.

### P0 — Retreinar a ironia — DÍVIDA ASSUMIDA, não mais pré-requisito

A cabeça reporta acurácia `1.0` e erra **6 em 10** falas sinceras de
atendimento, com 0,999 de confiança. Causa medida: vazamento de marcador de
discurso no gerador. **O gerador já foi corrigido**; falta rodar
`notebooks/04_treino_ironia.ipynb` no Colab e substituir
`modelos/bertimbau-ironia/`.

**O risco voltou a ser evitado em 04/09/2026, e não por causa deste retreino.**
Entre 21/08 e 04/09 a ironia pontuava, e o score carregava esse vazamento. Ela
saiu do vetor em 04/09 por um motivo diferente e mais grave (ver §3.4): no
corpus de treino do fusor ela funciona como detector de sentimento positivo.
Com ela fora, **o vazamento da cabeça não se propaga mais para a nota** — mas
ela continua obrigatória para a API subir e continua sendo exibida por
mensagem na dashboard, com a ressalva de confiabilidade que a tela já mostra.
Rodar o notebook 04 continua valendo; só deixou de ser urgente.

**Atualização de 02/10/2026:** a cabeça que está no Drive
(`fraus/modelos/bertimbau-ironia`), treinada com as fontes públicas do IDPT,
usou uma divisão treino/teste com defeito (armadilha 000 da §8): treinou só com
tweets e foi avaliada num teste 88% notícias. O F1-macro de 0,511 que o
notebook 07 recalculou para ela nesse teste mede mudança de domínio, não a
tarefa. A divisão foi consertada e o retreino é o passo 1 da §2.0.

Verificação: `uv run pytest tests/test_ironia_dominio.py`. Se o modelo melhorar,
**aperte os limiares desse arquivo junto** — limiar frouxo que nunca falha não
mede nada. E se `test_acuracia_perfeita_do_relatorio_vale_so_no_corpus_gerado`
passar a falhar, a limitação foi superada e os textos de ressalva na interface
precisam ser reescritos, não mantidos por inércia.

### P0 — A ironia continua escapando do score

**RESOLVIDO em 08/09/2026 o que travava esta seção:** o artefato foi
retreinado no contrato de 39 (`n_features_in_ = 39`, acurácia e F1-macro
**0,950**, contra 0,943 do de 38) e a API real sobe — verificado nesta data,
`{"status":"ok","motor":"real"}`. A recusa anterior era o comportamento correto
da invariante 7, não um bug: `Fusor.carregar` valida a dimensão. Confira
qualquer artefato com `uv run python scripts/conferir_fusor.py`.

**O que continua P0 é o caso em si:** a frase canônica segue saindo promotor
sempre que o relógio não a contradiz.

A feature que ataca o caso foi IMPLEMENTADA em 04/09/2026 e e a razao de o
contrato ter subido para 39: `incongruencia_situacao_negativa` marca elogio
convivendo com situacao negativa de atendimento na mesma fala. E a unica das
seis que alcanca a frase canonica, porque nao precisa de um segundo termo
polar no lexicon:

```
"que atendimento maravilhoso, so esperei 3 horas"            -> dispara
"Nossa, eu realmente gostei de ficar 5h esperando"           -> dispara
"esperei 3 horas e ninguem resolveu"        (reclamacao)     -> nao dispara
"nao gostei de ficar esperando"             (negado)         -> nao dispara
```

**O peso, agora medido:** −0,193 no eixo satisfeito−insatisfeito. A feature não
nasceu morta (nenhuma das 39 ficou com |peso| < 0,02, então o risco da
invariante 10 não se concretizou), e ainda assim **não vence** os +2,78 de
`texto_prob_satisfeito_media`. Nenhuma feature agregada de conversa reverte uma
probabilidade saturada por mensagem — é essa a conclusão que levou à
**contestação** de 08/09/2026, que marca em vez de corrigir (seção Feita,
abaixo), e à recusa de tentar a feature 40 cruzando tempo × texto (o corpus não
pode ensiná-la).
Ao conferir o artefato novo, o peso dela precisa sair NEGATIVO no eixo
satisfeito-menos-insatisfeito, como as outras cinco de incongruencia. Peso
positivo significaria que ela virou detector de satisfacao -- o mesmo modo de
falha que tirou a ironia do vetor -- e ai ela sai tambem.

Medicao feita ANTES de aceitar (invariante 10), no B2W, que e o corpus que da o
TEXTO do treino: dispara em 4,10% / 2,65% / 1,75% dos rotulos insatisfeito,
neutro e satisfeito. Tres rotulos, gradiente suave, razao 2,3:1 -- sinal, nao
previsor unilateral.

**Armadilha que quase me pegou aqui, e que vale para qualquer feature nova:**
medir no corpus do SIMULADOR dava zero nos tres rotulos, o que sugeriria peso
zero. Errado -- `FRASES_POR_ROTULO` NAO treina o fusor. O notebook 02 usa 400
frases do B2W por classe e pega do simulador so a ESTRUTURA da conversa. O
simulador importa para a guarda de previsor unilateral, nao para o peso. As
frases foram cruzadas nos tres rotulos mesmo assim, senao a guarda passaria por
vacuidade sobre a feature nova.

**A regra que vale sempre que o contrato mudar:** `Fusor.carregar` valida
`n_features_in_` contra `len(NOMES_FEATURES)` e levanta `FusorIncompativelError`
— a API não sobe com artefato desatualizado, e isso é o comportamento correto
da invariante 7, não um bug a consertar. Rodar o notebook 02 e substituir
`modelos/fusor.joblib` é o que destrava. Ver `docs/treinamento.md`.

### Feita — Autenticação, antes de hospedar

Resolvida em `feat/autenticacao` (300 testes, `tests/test_autenticacao.py`).
`FRAUS_CHAVE_MESTRA` ausente mantém a API aberta, como antes; presente, exige
`Authorization: Bearer` (mestra ou chave de acesso `fra_`) em toda rota, exceto
`POST /ingestao`, que segue só com chave de fonte `frs_`. Gerenciar chaves
(`POST`/`GET`/`DELETE /acesso/chaves`, e a chave de fonte) é privilégio
exclusivo da mestra — chave de acesso tentando recebe 403. A dashboard não fala
mais com a API direto: passa pelo proxy `app/api/fraus/[...caminho]/route.ts`,
que anexa a chave de acesso no servidor Next e nunca a deixa chegar ao
navegador. Ver `README.md` e `docs/hospedagem.md`. A branch `feat/autenticacao` já está
na `main`.

### Feita — A porta destrancada e o teto de `/ingestao` — 08/09/2026

Duas coisas que o levantamento de 08/09 achou, e uma que ele achou mentindo.

**A porta destrancada.** Com `FRAUS_CHAVE_MESTRA` + `FRAUS_JWT_SEGREDO` e sem
`FRAUS_CODIGO_CONVITE`, três chamadas (`registrar` → `entrar` → `GET
/conversas`) leem tudo que a mestra protege. **A tranca já existia** desde
02/09 — o que não existia era alguém dizer que ela estava aberta: os avisos de
boot só falavam de *ausência* de autenticação, e essa combinação não é
ausência, é as duas portas ligadas com uma delas destrancada. Agora
`aviso_de_porta_destrancada` (`fraus/api/main.py`) grita na subida. Continua
sendo aviso e não recusa de subir: cadastro aberto é o certo em `localhost`,
que é o uso declarado. `tests/test_aviso_de_porta_destrancada.py`.

**O teto de `/ingestao`.** 120 escritas por minuto, por fonte, com
`Retry-After` — OWASP API4:2023. Ele vive **na rota**, depois de
`fonte_autorizada`, e não no middleware onde mora o teto de `/auth/*`: o
middleware roda antes da autenticação e só poderia contar pela chave crua, mas
`credencial.fonte_da_chave` lê o id **sem conferir hash**, então um anônimo
mandando `frs_3_lixo` gastaria a janela da fonte 3. Defesa que o atacante usa
como arma é pior que nenhuma. `tests/test_vazao_de_ingestao.py`.

**A documentação que mentia.** O docstring de `fraus/credencial.py` afirmava
que "o resto da API continua sem autenticação" — verdade quando escrito, falso
desde 25/08. E o `CLAUDE.md` dizia "38 chaves de feature" na invariante 9 e
"(35)" no mapa: dois números de duas revisões, nenhum o vigente (**39**).
Corrigidos, e agora `test_o_CLAUDE_md_declara_o_mesmo_numero_de_features`
amarra o número do `CLAUDE.md` a `len(NOMES_FEATURES)` — a documentação que
governa toda sessão de agente passa a envelhecer com barulho.

### Feita — A contestação: o tempo contesta o elogio — 08/09/2026

A frase canônica sai promotor sempre que o relógio não a contradiz, e agora ela
**avisa**. Quando `score > 95` e `latencia_mediana_s > 180`, `/conversas` e `/conversas/{id}`
devolvem `contestacao` — derivada na leitura, sem coluna nova e sem chamada de
modelo, valendo retroativamente para o que já está no banco. A tabela de
Atendimentos e a tela do atendimento mostram a marca; o CSV leva a coluna.

**Ela marca, não corrige** — nenhum agregado muda, e há teste provando isso
(`test_o_atendimento_contestado_continua_contando_no_NPS`). Tirar do agregado
esvaziaria o indicador em silêncio se o limiar estivesse mal calibrado.

**Por que não virou feature 40**, e esta é a parte que economiza a próxima
sessão: o corpus não pode ensinar a interação tempo × texto. O texto vem do
B2W, a latência sai de distribuição **por rótulo**, e satisfeito-e-lento está
rotulado *satisfeito* por construção — a feature nasceria com peso **positivo**,
repetindo o modo de falha que tirou `ironia_prob_*` do vetor em 04/09. Isso é
leitura do corpus, **não experimento**; medir custaria um retreino e a API fora
do ar. Fica condicionado a corpus de atendimento real, a mesma condição da
cabeça de ironia.

Desenho, alternativas recusadas e as referências em
`docs/superpowers/specs/2026-09-08-abstencao-por-contestacao-design.md`.

O único número sem procedência é o **limiar de score em 95** — o de tempo vem
de IJHCI 2025. Está declarado assim no código e na spec.

**Verificado contra a API real** (`motor: real`), varrendo a latência com a
mesma fala: 99,92 em 10 s · 99,70 em 179 s · **99,69 em 181 s (contestada)** ·
**99,21 em 300 s (contestada)** · 93,25 em 600 s · 17,19 em 1800 s · 0,00 em
10800 s. A janela útil é de ~3 a ~9 minutos, e a estreiteza é a feature: abaixo
não há contradição a marcar, acima o modelo já acerta sozinho. **O "99,93" que
circulava aqui era o caso rápido** — com três horas dentro do log a conversa
pontua 0,00, e faltava esse qualificador em todo lugar.

### Feita (15/09/2026) — O tempo domina o score fora da distribuição de treino

**Resolvido com `log1p` sem teto** — as três saídas foram medidas contra o fusor
reproduzido e o teto p99 foi recusado (fazia 3 h pesarem o mesmo que 10 min);
tabela e números em `docs/treinamento.md`. O relógio agora empata com o texto em
613 s e com 3 h pesa 2,1× o texto (antes 20×). O texto abaixo é o registro do
achado.

**Achado de 08/09/2026, e é maior que o trabalho que o encontrou.** Atribuição
de uma conversa com 3 h de espera e uma única fala do cliente que a cabeça de
texto lê como 86% satisfeito:

```
latencia_primeira_resposta_s   -85,405
duracao_total_s                -35,759
latencia_mediana_s             -20,569
latencia_p90_s                 -12,326
texto_prob_satisfeito_media     +4,574   ← o texto inteiro
```

O tempo pesa **20× o texto**. As features de latência não têm teto e o corpus
de treino nunca passou de minutos (medianas 5/30/200 s): em 3 h o z-score do
`StandardScaler` explode e o relógio assume a nota. A conversa sai em `4,4e-24`.

O critério do próprio `docs/treinamento.md` diz o que isso é: *"se as features
que lideram forem as circunstanciais (tempo, contagem de turnos), procure o
vazamento."* É a **invariante 10 em runtime** — a guarda de vazamento olha a
distribuição no corpus, e o corpus não tem latência de três horas.

**MEDIDO em 08/09/2026** com `uv run python scripts/medir_dominio_do_tempo.py`
(instrumento novo, roda em segundos e não carrega BERTimbau nenhum):

| latência | contrib. tempo | contrib. texto | razão |
|---:|---:|---:|---:|
| 60 s | +0,48 | +4,57 | 0,1× |
| 300 s | −2,97 | +4,57 | 0,7× |
| **411 s** | **−4,57** | **+4,57** | **1,0× — o empate** |
| 600 s | −7,29 | +4,57 | 1,6× |
| 1800 s | −24,54 | +4,57 | 5,4× |
| 10800 s | −153,96 | +4,57 | 33,7× |

**O relógio empata com o texto em 411 s (6,9 min) e manda a partir dali.** Isso
é **4,0 desvios** acima da média de `latencia_mediana_s` no treino (67,0 s,
sigma 85,9 s) — ou seja, o ponto em que o relógio toma a nota está **fora** do
que o corpus mostrou ao modelo. Cada segundo de espera vale 0,0144 de
contribuição, **sem teto**.

O laudo bate com a varredura contra a API real: em 600 s o score já tinha caído
para 93,25, e em 300 s ainda estava em 99,21.

**Três saídas, e a terceira não é obviamente errada:**

1. **Escala log** (`log1p`) nas quatro features de tempo. É a mais defensável
   tecnicamente: o simulador gera latência **log-normal** de propósito
   (`docs/treinamento.md`), então a feature é de cauda pesada por construção e
   o `StandardScaler` — que pressupõe algo próximo de normal — é a ferramenta
   errada para ela. Custo: retreino, e os nomes `latencia_*_s` passariam a
   mentir sobre a unidade, então o contrato de 39 chaves mudaria de nome junto.
2. **Clipar num teto** (algo perto de 600 s). Mais barato de explicar e mantém
   os nomes. Custo: perde a distinção entre 10 min e 3 h — o que talvez não
   seja perda, porque acima de certo ponto "muito lento" é só "muito lento".
   Também exige retreino.
3. **Aceitar e declarar** como limitação. Custo zero em código, e o preço é
   defender numa banca um modelo em que o relógio vence o texto a partir de
   sete minutos — num produto cuja tese é justamente que o texto revela o que o
   relógio não mostra.

Decisão do dono do projeto — **não tomada**.

### Feita — Os três sinais invertidos do fusor — 08/09/2026

`conferir_fusor.py` marca três features como suspeitas desde o fusor de 35, e o
aviso sobreviveu a todos os retreinos: `texto_prob_satisfeito_ultima` (−0,49),
`emoji_frac_positivos` (−0,19) e `emoji_frac_negativos` (+0,59), todas com
sinal oposto ao esperado. Lido isolado, o terceiro diz "mais emoji negativo
empurra para satisfeito".

**A leitura isolada é que está errada.** Cada uma tem uma irmã forte com o sinal
certo — `emoji_score_medio` (+1,55), `texto_prob_satisfeito_media` (+2,78) — e
no corpus do simulador elas se movem quase juntas:

```
corr(score_medio, frac_positivos) = +0,941
corr(score_medio, frac_negativos) = -0,903
corr(frac_positivos, frac_negativos) = -0,885     (254 de 300 conversas)
```

Features colineares dividem um efeito único: a forte fica com ele, a redundante
vira termo de correção com sinal frequentemente oposto. **O efeito líquido da
família é o que se interpreta**, e ele aponta certo: de 4 emojis negativos a 4
positivos a contribuição somada da família emoji vai de **−0,06 para +1,93**;
no texto, de P(satisfeito) 0,05 a 0,95, de **−2,23 para +4,56**.

`uv run python scripts/investigar_sinais_invertidos.py` reproduz tudo em
segundos, sem BERTimbau.

**O aviso do `conferir_fusor.py` continua saindo, de propósito** — o dia em que
ele parar de sair para a quarta feature é o dia em que ele deixa de servir. Ele
agora aponta para este laudo, para ninguém reinvestigar o mesmo caso a cada
retreino.

**Uma armadilha de sonda que quase entrou no laudo:** varrendo só emoji polar,
`corr(frac_pos, frac_neg)` dá **−1,000** — mas isso é artefato, porque com
todos polares as duas somam 1 por construção. Emoji neutro quebra a soma. O
número honesto é o do corpus, acima.

### Feita — O teto de vazão do webhook — 08/09/2026

Fechou a metade que sobrou de manhã: `/ingestao` ganhou teto e o webhook não,
sendo que ele é o **outro** caminho de escrita pela rede, com a mesma exposição
(OWASP API4:2023) e **pior** em um aspecto — a rota é anônima por desenho, e
cada entrega aceita roda o Motor inteiro.

120 entregas por minuto por fonte, mesmo número de `/ingestao` de propósito: as
duas rotas fazem o mesmo trabalho depois de autenticar e custam o mesmo. Mas
**contadores separados** — uma fonte pode receber pelos dois caminhos, e janela
compartilhada faria o volume de uma rota cortar a outra.

**Três decisões que valem ser lidas antes de mexer:**

1. **O teto vive logo depois do HMAC**, e aqui isso pesa mais que em
   `/ingestao`: o `fonte_id` vem **na URL**, então qualquer anônimo escolhe
   contra qual fonte bater. Contar a tentativa recusada transformaria o teto no
   caminho mais curto para derrubar a integração alheia.
2. **O 429 é `Recusa`, não `HTTPException` direta** — toda recusa desta rota
   vira linha em `entregas_webhook`, e um 429 invisível ali seria justamente a
   recusa que o operador precisava ver: é ela que explica por que a plataforma
   começou a retentar. `Recusa` ganhou `cabecalhos` para o `Retry-After`.
3. **Isso só é seguro porque `entrega_ja_vista` conta apenas veredito
   "aceita".** Se um dia ela passar a contar qualquer veredito, este 429 vira
   uma forma de queimar um `webhook-id` legítimo — a plataforma retenta o mesmo
   id e leva "duplicada", e o atendimento some em silêncio. Há teste para isso
   (`test_o_429_nao_queima_o_webhook_id_para_a_retentativa`).

### P1 — Hospedagem sempre ligada — Oracle bloqueada por capacidade, 11/09/2026

> **Reenquadrada em 30/09/2026.** A API de produção já roda na Vercel
> (ver "Feita — API real hospedada sem VM", acima), então isto deixou de ser
> P0. Continua aberta como **o caminho para eliminar o cold start**: a Vercel é
> serverless e esfria; só um container sempre ligado (>= 1,5–2 GB de RAM) o
> elimina. O Render gratuito não serve (512 MB contra ~1,06 GB medidos, e dorme
> em 15 min). O texto abaixo é o estado de 11/09/2026.

> Estado completo, com o que foi medido e o que foi descartado:
> **[notas/2026-09-11-deploy-na-oracle.md](notas/2026-09-11-deploy-na-oracle.md)**

A API **com torch não cabe em serverless** (torch instalado mede 769 MB contra
o teto de 500 MB da Vercel, mais 1,3 GB de pesos) — o que foi resolvido em
17/09/2026 com ONNX e Large Function. Sem cold start, precisa de container com
volume e ~2 GB de RAM.

**Tudo está pronto menos a máquina.** A `oci` CLI está autenticada, a VCN e a
Security List existem (22, 80 e 443 abertas), e
`scripts/provisionar_oracle.sh <IP>` executa o deploy inteiro num comando. O
`Dockerfile` foi **ensaiado em container real** e devolve `motor: real` com
predição correta — inclusive `None` para conversa sem fala do cliente.

O que falta é hardware: `Out of capacity for shape VM.Standard.A1.Flex`, em
~35 tentativas. Já descartado por medição — não é a imagem, não é o tamanho do
shape (1/6 e 2/12 falham igual), não é cota (`used 0, available 2`), e **não é
resolvível trocando de região**: recurso Always Free só existe na região de
origem, que é `sa-saopaulo-1`. Um laço destacado segue pedindo a máquina.

A alavanca que sobra é upgrade para **Pay As You Go** — mantém a franquia
gratuita e costuma destravar a fila de A1, mas exige cartão e passa a cobrar
qualquer coisa além dela. Decisão do João.

### Feita — O site público da documentação

O workflow, o recorte e as camadas de guarda contra vazamento estão de pé, e o
site responde em <https://joao-tavares0312.github.io/fraus-docs/> (verificado
em 30/09/2026). `deploy-vercel.md` e `cloud-run.md` são **internos**, como
`hospedagem.md`: têm topologia e nomes de variáveis de segredo. Em 30/09/2026
o visual do site foi alinhado ao Instrumento.

### P2 — Dívida de escala

`GET /conversas?de=&ate=` e `GET /indicadores?de=&ate=`; agregado de léxico por
classe e de tempo mediano de resposta.

### P2 — Decisões do João

O repositório ficou **público** em 02/10/2026 e a documentação ainda o
descreve como privado (`CLAUDE.md`, `mkdocs-publico.yml`, `tests/test_documentacao.py`):
reescrever os textos ou voltar a privado. Com ele público, ligar no GitHub
*secret scanning*, *push protection* e proteção do ramo `main`. Fixar as
versões de `requirements.txt` (hoje com `>=`), que é o que a Vercel instala.
Dia das transcrições sem data e executor da repontuação: ver §2.

Empresa fictícia (não definida) e tema claro (dark-only hoje). O pin do
`scikit-learn==1.6.1` e a remoção de `content/fraus` já foram feitos.

---

## 8. Armadilhas já pagas — não repita

0000. **Duas instâncias frias migrando juntas se derrubavam — conserto de
   02/10/2026.** `Banco.migrar()` roda no boot de cada função da Vercel. Logo
   depois de um deploy todas as instâncias são novas; duas subiram no mesmo
   segundo, o DDL de uma esperou a tabela que a outra segurava e o Postgres
   matou uma delas com `DeadlockDetected`. As primeiras requisições da
   dashboard (`/auth/eu`, `/serie-temporal`) voltaram 500 e depois tudo
   "voltou sozinho" — o tipo de falha que ninguém investiga. Agora a migração
   começa por `pg_advisory_xact_lock`: uma instância migra, as outras esperam.
   A trava é de **transação**, não de sessão, porque a produção passa pelo
   pooler em modo transação. `tests/test_migracao_concorrente.py` reproduz com
   oito instâncias e só roda de verdade com `FRAUS_TESTE_POSTGRES_URL`.

000. **`astype(str)` transformou campo vazio no autor "nan" — conserto de
   02/10/2026.** A divisão "por autor" do corpus de ironia agrupava as linhas
   pelo autor para que a mesma pessoa não ficasse em treino e teste. As 18.373
   notícias não têm autor; o pandas lê o campo vazio como NaN, `astype(str)`
   devolve `"nan"`, e todas viraram um autor só, que caiu inteiro no teste. Foi
   pedido 15% para teste e saiu 63%; o treino ficou 86% irônico e só de tweets.
   Nada falhou: o notebook treinou, mediu e gravou. Quem denunciou foi o Laya
   respondendo "irônico" para tudo. **Divisão por grupo se confere pelo
   resultado**, não pela intenção do código: tamanho do teste e proporção de
   classe dos dois lados. É o que `fraus.divisao.conferir_divisao` faz, com
   erro. Parente direto da invariante 10.

00. **O proxy emprestava a credencial do deploy a quem não tinha sessão —
   conserto de 02/10/2026.** As páginas redirecionavam o visitante para
   `/entrar`, e por isso parecia fechado; `/api/fraus/*` respondia mesmo assim,
   porque sem cookie de sessão `autorizacaoDoServidor` caía para
   `FRAUS_CHAVE_ACESSO`. Redirect de página não é controle de acesso: quem nega
   dado é a API, e a API recebia do proxy uma credencial que passa por tudo.
   Agora a credencial do servidor só é emprestada em instalação **sem** login
   (`/auth/estado` com `disponivel: false`), e a dúvida fecha. Conferir depois
   de qualquer mudança nesse módulo, sem cookie nenhum:
   `curl -s -o /dev/null -w "%{http_code}" https://<dashboard>/api/fraus/conversas`
   tem de dar **401** onde há login.

0. **CORRIGIDO em 14/09/2026 — a vitrine ROLAVA sim, e o texto abaixo media
   errado.** `overflow-x: hidden` no body barra o arraste, **não** a rolagem
   programática: re-medido, `scrollTo(9999, 0)` a 390px andava **96px**. O
   culpado era a marca do fecho (`absolute -right-24`), e o conserto é
   `overflow-x-clip` no invólucro de `app/page.tsx` (`scrollWidth` 486 → 390,
   header sticky intacto). O parágrafo original fica como registro:

   ~~A vitrine NÃO rola na horizontal~~ — e o `scrollWidth` maior que a viewport
   não prova que role.** Medido em 08/09/2026 na `main` e na
   `feat/tipografia-e-heroi`, com resultado idêntico nas duas: em 360/390/440px
   o `document.scrollWidth` dá viewport + 96px, e mesmo assim
   `window.scrollTo(9999, 0)` deixa o `scrollX` em **0**. Motivo:
   `body { overflow-x: hidden }` (globals.css) **propaga para o viewport**,
   porque o `html` não declara overflow — então o excesso é recortado e não
   vira barra de rolagem. Os 96px são o `fixed inset-0` do ateliê (que se
   dimensiona pelo viewport de LAYOUT, e portanto acompanha o excesso em vez de
   causá-lo) mais a esteira `w-max`, que é faixa rolante por desenho.
   Nenhum conteúdo fica inalcançável: o container de conteúdo mede exatamente a
   viewport.

   **Antes de "consertar transbordo" nesta vitrine, meça `window.scrollX` depois
   de um `scrollTo`, não o `scrollWidth`.** Uma sessão já gastou uma hora
   perseguindo isso.

   Duas armadilhas de método que apareceram no mesmo dia: **a primeira carga
   depois de `npm run dev` não é representativa** (ela mediu "sem transbordo" e
   a segunda mediu 96px — o servidor ainda estava compilando), e uma sonda que
   procura o culpado do transbordo precisa ignorar quem tem ancestral
   recortante, senão lista só vítimas.

1. **`fullPage` do Playwright/headless NÃO dispara `whileInView`.** Confirmado
   de novo em 08/09/2026: a tela de Atendimentos sai com a tabela em branco na
   captura, e o DOM desmente — o HTML servido tem o conteúdo. Capture por
   viewport com rolagem, ou confira o HTML com `curl` em vez da imagem. Pelo
   mesmo motivo, `curl` no HTML é a prova mais barata de que algo **não**
   depende de JavaScript.


1. **Data da Totalk é `MM/DD/YYYY`**, não `DD/MM`. Lida como brasileira, espalha
   as mensagens por cinco meses e a latência sai absurda **em silêncio**.
2. **Não mate servidor com `pkill`** — não casa `npx next start`. Use a porta:
   `Get-NetTCPConnection -LocalPort 3000 -State Listen | Stop-Process -Force`.
3. **Não rode `npm run build` com o `next dev` do João no ar** — invalida os
   hashes dos chunks e a tela vira 403 em tudo. Já foi diagnosticado como "tela
   feia" uma vez.
4. **CORS é lista explícita**: `FRAUS_ORIGENS` libera 3000/3001. Teste na 3002 e
   a chamada do navegador falha — foi assim que descobrimos que a proteção
   funciona.
5. **Coluna ausente é defeito do ARQUIVO**, não da linha: o driver deixa o
   `KeyError` propagar e a borda HTTP traduz em 400 nomeando a coluna. Não
   capture no driver.
6. **`<input type=file>` só dispara `change` quando o valor muda.** Zere
   `evento.target.value` ou reenviar o mesmo arquivo não faz nada.
7. **Oclusão quebra expressão fixa**: "Bom dia" sem "dia" vira "Bom" solto, e
   "dia" recebe peso alto e enganoso. Está declarado na interface — não trate
   como bug.
8. **Rota de escrita com credencial própria precisa ser isenta no middleware
   de chave de acesso**, ou ele a recusa com 401 **antes** de olhar a
   credencial dela. `/integracoes/webhook/{id}` tem assinatura própria — a
   plataforma externa não tem, nem pode ter, uma chave `fra_`. Em
   `fraus/api/seguranca.py`, a tupla `ISENTAS` (`/ingestao`, `/acesso/estado`,
   `/saude`) compara caminho por **igualdade**, e não serviria aqui: o caminho
   do webhook carrega `{fonte_id}` variável. Por isso a isenção do webhook é
   uma condição **separada**, ao lado de `ISENTAS` no mesmo `or` —
   `caminho.startswith(PREFIXO_WEBHOOK + "/")`. O defeito só aparece com a
   mestra **ligada**, isto é, só em produção: o log de entregas fica vazio
   dizendo "não chegou nada" enquanto a plataforma recebe 401 em cada
   tentativa, e nada no ambiente de desenvolvimento (API aberta) revela o
   problema.
9. **`PRAGMA foreign_keys` vale por CONEXÃO no SQLite**, não por banco. Ligá-lo
   uma vez na criação do esquema não teria efeito nenhum nas conexões
   seguintes — cada `_conectar()` precisa executá-lo de novo — e sem isso o
   `ON DELETE CASCADE` de `entregas_webhook` seria documentação em vez de
   comportamento: apagar uma fonte deixaria as entregas órfãs, apontando para
   um `fonte_id` que ninguém mais consegue consultar.
10. **`str(ValidationError)` do Pydantic v2 embute o `input_value` recebido** —
    para JSON malformado, até o corpo cru inteiro; para campo de tipo errado,
    o valor daquele campo. Gravar essa mensagem num log ou devolvê-la no
    `detail` de uma resposta persiste ou vaza PII de cliente real. Por isso
    `fraus/api/registro.py` tem `resumo_validacao`, que usa só `loc` (onde) e
    `type` (o que) de `erro.errors()`, e descarta `input`/`msg`/`ctx` de
    propósito — qualquer um deles pode carregar o valor recebido.
11. **Dedupe de webhook só pode contar entregas com veredito `aceita`.**
    `entrega_ja_vista` filtra por `veredito = 'aceita'` de propósito: se
    contasse qualquer veredito, uma recusa registrada — inclusive de um
    anônimo com assinatura inválida, já que a rota é anônima por desenho —
    faria a entrega legítima seguinte com o mesmo `webhook-id` virar
    "duplicada", e o atendimento se perderia em silêncio. Tem variante
    auto-infligida: um 503 (variável de segredo ausente) grava a linha, o
    operador corrige a variável no ambiente e reinicia, e a retentativa da
    plataforma some como se já tivesse entrado.

---

## 9. Convenções

Commits em **conventional commits**, assunto **sem acento**, corpo em pt-BR
explicando **por quê** (veja o histórico — a régua é alta e é intencional; esses
commits são material de defesa do TCC).

**Não assine commits com Claude como co-autor.**

Comentários e docstrings em pt-BR sem acento no código Python; texto de
interface em pt-BR **com** acento.
