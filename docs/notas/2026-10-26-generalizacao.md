# Generalização — inventário de 26/10 e campanha concluída em 26–27/10/2026

## Escopo e base congelada

Esta nota preserva a investigação local de proveniência e a reconstrução da
separação posicional usada pelo fusor, seguidas do fechamento da **nova campanha
de candidatos de 26–27/10/2026**. A primeira parte não recupera o treino antigo;
as curvas novas sustentam sobreajuste somente desta reprodução. O agente não
promoveu pesos nem realizou inferência em produção; o checkpoint publicado
não foi identificado. O merge externo da PR #104 é registrado ao final.

- Commit de referência: `836d440bbe246018fb8808a4ede4c6f84d6a0ef9`.
- Inventário já existente:
  `/tmp/fraus-overfitting-20261026/experimentos/resultados/inventario.json`.
  A operação registrada é `inventario_estatico_sem_inferencia`, sem rede e
  sem leitura de pickle. O inventário não é um snapshot atômico de arquivos
  que outro processo possa alterar.
- Evidência agregada e manifesto privado desta reconstrução:
  `/tmp/fraus-overfitting-20261026/historico.json` (`versao: 1`). O manifesto
  contém índices de linha, SHA-256 de texto normalizado, rótulos e produtos;
  não copia texto bruto do corpus para esta documentação.
- Limite operacional prévio: o [handoff](../handoff.md) registra o fusor local
  incompatível com a escala `log1p`. Não se repetiu essa checagem nem se
  contornou a recusa de carga.

O SHA-256 identifica os bytes observados, não a origem antiga do treinamento.
Hash não é máquina do tempo: calcular uma impressão hoje não transforma um
arquivo local em manifesto preservado na data do treino.

## Ambiente observado

O inventário registra Python **3.14.7**, CPU **Intel Core i5-1135G7**, afinidade
em oito CPUs lógicas e **16.487.276.544 bytes de RAM**. As distribuições locais
registradas são NumPy 2.5.2, PyTorch 2.13.0, Transformers 4.57.6,
scikit-learn 1.6.1, safetensors 0.8.0 e ONNX Runtime 1.30.0. Essas versões
não identificam o ambiente dos treinos antigos nem o bundle de produção.

A consulta PCI desta investigação encontrou **Intel Iris Xe Graphics**;
`nvidia-smi` não estava no PATH. Nenhuma GPU foi alocada para esta auditoria.
Não se leu nem publicou dump de variáveis de ambiente, tokens ou credenciais.

Pandas não estava instalado no ambiente do projeto. A reconstrução usou um
ambiente temporário `uv run --no-project --with pandas --with numpy`, sem
alterar dependências do repositório. As versões efetivamente importadas no
cálculo foram **pandas 3.1.0 e NumPy 2.5.2**, com Python 3.14.7. Não se deve
atribuir essas versões ao ambiente histórico.

## Artefatos locais e candidatos encontrados

A árvore inspecionada foi `modelos/`, a mesma do inventário. Os hashes abaixo
são do inventário congelado; não houve carregamento dos pesos.

| Componente local | Arquivo | SHA-256 dos pesos |
|---|---|---|
| Satisfação | `modelos/bertimbau-satisfacao/model.safetensors` | `9f9448aed6c655ce0fab2d3e32db485d0b8de986c6d907eb82336f69c62edad2` |
| Emoção | `modelos/bertimbau-emocao/model.safetensors` | `e9735f12ef459ba93102d868be7455d9a0d453099530597f3855269b5ab83cd9` |
| Ironia | `modelos/bertimbau-ironia/model.safetensors` | `512841782d167327b21e1c2c98e602c28dbdf30d6fdafa9733b9f078f4d09388` |
| Ironia, diretório histórico | `modelos/bertimbau-ironia-2026-10-02/model.safetensors` | `f6c5ddab6ea47ee111c88720d5ee7f6a46c9363d9e4fcb69ca47f2e2dc6cb4ef` |
| Fusor | `modelos/fusor.joblib` | `dbd3e68672085e60b1473f673d77c16e307dc047c8a74c03575ab02cc1c15be8` |

`modelos/candidatos/` contém apenas `ironia-2026-10-19-19h11/`. Os pesos e o
`fraus_receita.json` desse candidato têm os mesmos hashes dos arquivos em
`modelos/bertimbau-ironia/`. Isso prova igualdade dos bytes inventariados,
não quando ou como foram copiados. `training_args.bin` está presente no
candidato, mas **não foi aberto**: sua desserialização não é necessária para
esta investigação.

Não foram encontrados candidatos de satisfação ou emoção de 19/10 nesse
diretório local. Isso não prova ausência no Drive ou em outro armazenamento.
O diretório `modelos-onnx/` está ausente segundo o inventário. Nenhum desses
achados permite identificar o checkpoint servido em produção.

## O que a proveniência permite afirmar

| Cabeça | Metadados disponíveis | Limite de independência e diagnóstico |
|---|---|---|
| Satisfação | `modelos/bertimbau-satisfacao/metricas.json`, F1 macro histórico 0,782155 | Não há receita, manifesto individual de treino ou curvas na árvore local inspecionada. A independência em relação ao teste do sistema é **não verificável**. |
| Emoção | `modelos/metricas_emocao.json`, F1 macro histórico 0,584373 e referência ao GoEmotions-PT | Não há receita, manifesto individual de treino ou curvas na árvore local inspecionada. Nomear o corpus não comprova quais exemplos ajustaram os pesos; independência **não verificável**. |
| Ironia | `modelos/bertimbau-ironia/fraus_receita.json` e `modelos/metricas_ironia.json` | Há semente, tamanhos, temperatura e impressão agregada do teste; não há manifesto individual de treino nem curvas comparáveis. Isso é proveniência parcial, não comprovação de independência do sistema completo. |

Na ironia, a receita registra semente 42, treino/validação/teste de
**1.126/292/462** exemplos, cinco épocas e temperatura **1,565486**. A impressão
de teste declarada é
`4eee9c62e8c9a11fb5e39d1609238b7175420ca171e8352a3516e4785693595e`.
O arquivo de métricas declara `commit_fraus: 3cc1d5e`, MultiPICo-PT agrupado
por post, seleção mediana na validação e F1 macro de teste **0,660294** para a
semente escolhida. São declarações dos metadados preservados, não uma nova
medição. `impressao_dos_textos`, em `fraus/divisao.py`, resume o conjunto de
textos ordenados; ela não contém os índices, grupos, rótulos e histórico de
seleção necessários para reconstruir toda a proveniência supervisionada.

A documentação da receita anterior à instrumentação desta campanha
(`fraus/receita_treino.py`, cabeçalho) registra seleção histórica da melhor
época no próprio teste até 19/10. Isso torna as métricas antigas de satisfação
e emoção otimistas por construção; **não é, sozinho, diagnóstico de
sobreajuste dos pesos locais encontrados**. A receita posterior escolhia
checkpoint e temperatura na validação, mas ainda calculava teste dentro de
cada chamada a `treinar_uma_semente` e não preservava `log_history` no JSON.
Ter métricas finais de três sementes não recupera curvas de aprendizagem.

Os atalhos de procedência do IDPT e do primeiro simulador estão documentados
em [Ironia — corpus de 08/10](2026-10-08-ironia-corpus.md) e em
[Treinamento](../treinamento.md). Esses achados históricos não devem ser
transferidos automaticamente a outro checkpoint ou à produção atual.

## Reconstrução medida dos pools posicionais do fusor

### Procedimento reproduzido

Foi reproduzido apenas o preparo de dados de
`scripts/retreinar_fusor_local.py`, linhas 51–79 na base congelada: nenhuma
chamada a `_extrair`, `montar_classificadores`, `montar_features` ou treinamento.
O script de referência tinha SHA-256
`c275ba0a920d923a5d83a17ed80baa9ad6691959cb56ca5cd500296663d6d546`.

O CSV local é
`/home/joaopedro/.cache/fraus/corpora/b2w/B2W-Reviews01.csv`, SHA-256
`821fb0bf9f7230b0fba4e4f9fadd75a66d1a9ff0b1657810791d33007eb2ab38`.
A reprodução preservou a ordem de linhas, `dropna` somente das três colunas
exigidas pela receita, recomendação `yes/no`, balanceamento pela menor
classe com semente 42 e embaralhamento com semente 42. `product_id` foi
retido somente como metadado de auditoria, sem filtrar ou reordenar linhas.
A normalização reutilizou `fraus.receita_treino.normalizar_texto`:
NFC, `casefold` e colapso de espaços.

Das **132.373 linhas brutas**, **129.080** são elegíveis para essa receita:
32.193 insatisfeitas, 16.008 neutras e 80.879 satisfeitas. A menor classe tem
16.008 exemplos; o balanceamento resulta em **48.024 linhas**. Por classe,
`[0:300]` forma o pool de treino e `[300:400]` o de teste. A receita depois
solicita 900 conversas com semente `20260813` e 300 com semente `999` ao
simulador. **Aqui foram auditados os pools de frases, não as mensagens
sintéticas resultantes dessas chamadas.**

| Medida nos pools | Treino | Teste |
|---|---:|---:|
| Linhas de origem | 900 | 300 |
| Linhas por classe | 300 | 100 |
| Textos normalizados únicos | 900 | 300 |
| Duplicatas normalizadas excedentes no próprio lado | 0 | 0 |
| Produtos únicos | 816 | 284 |
| Linhas sem produto | 0 | 0 |
| Linhas cujo alvo do fusor difere do alvo por estrelas | 16 | 5 |

**Interseção observada entre os pools:**

- **0 índices de linha** compartilhados;
- **0 textos normalizados** compartilhados, portanto 0 conflitos de rótulo
  entre textos compartilhados nesses dois pools;
- **41 produtos** compartilhados, envolvendo **63 linhas do treino e 52 do
  teste**.

A separação posicional é disjunta por linha e, neste CSV e nesta reconstrução,
por texto normalizado, mas **não por produto**. Há contaminação de grupos no
particionamento reconstruído; não se mediu o efeito causal desses 41 produtos
na métrica, nem se demonstrou que o arquivo de pesos local foi treinado
exatamente com este CSV. O manifesto privado gravado hoje permite reproduzir
a medição atual, não substituir um manifesto histórico ausente.

### Dois alvos distintos

A cabeça de satisfação usa `overall_rating`: estrelas 1–2 → insatisfeito,
3 → neutro, 4–5 → satisfeito (`fraus/corpora.py:rotulo_por_estrelas`). O fusor
usa **recomendação binária com neutro imposto pela estrela 3**: nota 3 →
neutro; nas demais notas, `recommend_to_a_friend == yes` → satisfeito e
`no` → insatisfeito. Não são a mesma variável supervisionada; as 16 e 5
linhas discordantes acima tornam essa diferença observável nos próprios
pools. A recomendação binária tampouco é uma resposta NPS declarada 0–10.

O fato de ambos usarem B2W exige verificar sobreposição com o treino
supervisionado da cabeça de satisfação. Sem seu manifesto histórico, o
resultado correto é **independência não verificável**, não “sem vazamento”.
Mesmo uma futura separação de produtos do fusor não comprovará retroativamente
que a cabeça antiga nunca viu os textos de teste.

## Conclusão desta evidência e estado da campanha

1. **Observado:** produtos cruzam os pools posicionais reconstruídos; textos
   normalizados não cruzam esses dois pools. Isso não avalia a separação
   entre corpora auxiliares nem entre esses pools e o treino das cabeças.
2. **Histórico documentado:** seleção no teste e atalhos do corpus/simulador
   comprometeram avaliações antigas. Não são diagnóstico automático do
   checkpoint local nem do publicado.
3. **Sobreajuste dos pesos antigos/publicados inconclusivo:** faltam curvas
   comparáveis e proveniência suficiente desses pesos. Métrica alta,
   transferência baixa ou falta de significância não comprovam isoladamente
   presença ou ausência de sobreajuste. As curvas da reprodução nova são outra
   evidência, detalhada em [Generalização](../generalizacao.md).
4. **Domínio:** o fusor avalia conversas sintéticas; não há aqui validação em
   atendimentos reais rotulados. Benchmarks já consultados não são teste
   virgem.

A primeira tentativa registrou **Google Colab CLI 0.7.5 instalada** e falhou
por ausência de ADC (`DefaultCredentialsError`), sem alocar GPU ou treinar.
Na retomada de 26/10, o usuário concluiu o login OAuth2 na conta autorizada.
A CLI alocou uma T4 na sessão própria. Depois da recuperação operacional
descrita no fechamento abaixo, foram concluídos os nove treinos e recuperados
os nove bundles. A sessão foi encerrada pela CLI antes do experimento local
do fusor. O diagnóstico se apoia nas curvas exportadas, não apenas na alocação.

Nesta fatia foram feitas inspeção estática e a medição de sobreposição acima.
Não foram executados testes, builds, lint ou carga de `fusor.joblib`,
`training_args.bin` ou outro pickle. Os demais resultados empíricos da
campanha devem manter sua própria origem, artefato, divisão e data, sem
sobrescrever estes registros históricos.

## Verificação local da instrumentação

A nova receita foi exercitada em CPU com um BERT **aleatório minúsculo**,
criado localmente, sem download de pesos. O smoke treinou duas épocas,
salvou e recarregou o candidato em
`/tmp/fraus-overfitting-20261026/smoke-bert/candidato/`. Foram observados:

- `fraus_receita.json` sem métricas de teste na fase de seleção;
- perdas e F1 do diagnóstico de treino e da validação nas duas épocas;
- melhor época registrada, argumentos efetivos e fingerprints dos três lados;
- `avaliacao_final.json` separado, com métricas, ECE bruto/calibrado e hashes;
- recusa de manifesto divergente antes da avaliação.

Isso verifica a implementação, **não mede generalização do Fraus**. Os 77
testes focados de receita, corpora, divisão, simulador e temperatura passaram;
os avisos de `pin_memory` sem acelerador e ordenação de checkpoints por
mtime não foram ocultados.

A CLI de auditoria também completou um smoke com arquivos sintéticos nos
cinco formatos, manifesto JSONL privado `0600` e nenhum modelo carregado.
Os 15 testes de isolamento/auditoria passaram. A auditoria integral dos dados
reais excedeu o primeiro prazo de 600 segundos; a execução seguinte concluiu
em 1.321 segundos, sem amostragem, em `auditoria.json`. O manifesto privado
tem 618.550.859 bytes, permissões `0600` e SHA-256
`7a77e64a3371b7ce45d8c1d845b597034b036b650ad2dac029d9c41e1f8787f8`.
As contagens agregadas publicáveis estão em [Generalização](../generalizacao.md);
os índices individuais e textos brutos não foram copiados para o site.

Também foi reservado `manifesto-fusor.json` sobre o B2W completo, com
95.722/12.058/18.895 exemplos de treino/validação/teste, antes de qualquer
novo ajuste de cabeça. Isso é uma reserva prospectiva, não comprovação
retroativa de independência dos pesos encontrados.

O smoke de orquestração executou as células reais de treino/exportação do
notebook 01 com BERT aleatório minúsculo em CPU: três sementes, seleção
congelada, avaliações finais, retomada sem novo treino/inferência e bundle
das três sementes com hash conferido. Não é a campanha T4 do Fraus.

O fusor passou em 56 testes focados (incluindo contrato de runtime e escala).
Um smoke de CLI com **features construídas** gravou e recarregou um candidato
externo e artefatos experimentais completo/texto/tempo, com 39/4/7 colunas.
Não usou cabeças reais para gerar essas features e não produz resultado
científico de generalização. O experimento posterior com cabeças reais foi
concluído separadamente após a recuperação dos candidatos Colab.

## Verificação da interface e documentação

Dashboard: 373 testes e build de produção passaram; detector visual sem
achados. O explorador foi operado em 1440/390px, claro/escuro e movimento
reduzido, sem overflow global. As três frases do plano foram classificadas
com **dublê explícito local**; as barras foram comparadas à resposta HTTP
única, sem impor classe esperada. A comparação tolera o arredondamento
próprio da serialização CSS do Chromium.

Uma fixture de transporte explicitamente sintética exercitou espera, 503,
ausência de emoção/ironia/estilo e probabilidade zero observada. Cinco
Ctrl+Enter durante a mesma espera produziram um único POST; selecionar
etapa não inferiu; espera/erro apagaram o resultado anterior; editar o
campo preservou a identificação da frase já classificada. Isso é prova de
interação, **não de inferência real do motor**. Os baselines Torch das
cabeças são evidências separadas.

Ao operar Analisar com TXT sem horário na demonstração, a prévia respondeu
200, mas a análise avulsa falhou: `MotorDuble` não implementa
`analisar_conversa`. Não se alterou esse dublê fora do escopo nem se
apresentou o erro como falha de produção.

187 testes focados de API/autenticação/documentação passaram. Os builds
estritos interno e público concluíram; a inspeção do artefato público não
encontrou diretórios/páginas internos nem corpos de funções na referência.
Os três percursos foram navegados em prévia pública. A revisão independente
estática científica e a revisão visual por capturas não encontraram achados
materiais no escopo revisado; não repetiram os smokes.

Os fingerprints fortes dos três lados do manifesto prospectivo do fusor
foram comparados aos da auditoria das cabeças e coincidiram:
95.722/12.058/18.895 exemplos. Isso confirma a reserva compartilhada desta
receita, não a origem dos pesos antigos.

O PDF foi gerado e seus três diagramas conferidos por rasterização.
O gerador inicialmente preservava `<code>` dentro de `<pre>` e o parser HTML
destruía a capitalização XML do SVG; a renderização agora remove o invólucro
e serializa o SVG no Chromium antes desse parser, sem `foreignObject`.
Os rótulos, `viewBox`, setas e a paginação foram observados em
`pdf-legivel-010.png`, `pdf-legivel-011.png` e `pdf-sequencia.png`.
Três guardas de falha do PDF passaram. Permanecem os avisos já observados de
Fontconfig e âncoras internas do WeasyPrint; não foram suprimidos.

O primeiro benchmark de satisfação atingiu o timeout externo de 3.600s:
5.000 previsões B2W e 3.008 ConsumerBR observadas, sem relatório final
persistido. Não se inferiram métricas desse progresso. A repetição mantém
a amostra aprovada de 5.000 por conjunto, sem esse timeout externo;
`satisfacao-tentativa-1.json` preserva o estado da tentativa interrompida.

A segunda execução de satisfação concluiu em 2.540s e gravou
`satisfacao-atual.json`, com 5.000 exemplos por conjunto e os fingerprints
das amostras. Os três baselines Torch reais estão concluídos;
`emocao-atual.json` e `ironia-atual.json` são os outros relatórios. A matriz
publicável registra as métricas e distingue teste reconstruído, transferência
já consultada e proveniência histórica não verificável. Nenhuma dessas
medições recupera as curvas dos pesos antigos ou valida suporte real.

Fechamento local: `reunir_docs.py`, build interno estrito, build público
estrito e PDF concluíram após a inclusão dos três baselines. A conferência
do HTML encontrou um bloco de fonte na referência interna de modelos e
nenhum na pública; a busca em todas as páginas HTML públicas também não
encontrou blocos `mkdocstrings-source`. Diretórios/páginas restritos e
manifestos JSONL estavam ausentes do artefato público. O PDF continua com
os avisos registrados acima.

Abas e serviços de QA foram encerrados; scripts temporários de smoke e a
fixture foram removidos. Relatórios, manifestos, bundles de smoke e capturas
desse QA permanecem no workspace externo temporário. A campanha científica
posterior tem armazenamento durável sob `/home`, separado desses smokes,
conforme o fechamento abaixo.

## PR isolada e retomada autenticada

A PR #104 foi preparada sobre `origin/main` em `acc2791`, com 46 caminhos
da entrega e sem os trabalhos históricos de LP/desempenho. A fonte congelada
da campanha é `03f91770ec92dec934d794cbad50ea3224f4cb8a`. A worktree de revisão
foi movida para `/home/joaopedro/.cache/fraus/worktrees/docs-modelo-20261026`:
o tmpfs de `/tmp` atingiu sua quota ao preparar dependências e payloads.
Nenhum peso ou artefato científico antigo foi apagado para liberar espaço.

Na base integrada passaram 352 testes focados, os builds estritos interno
e público e a geração do PDF; os diagramas geral/Transformer foram conferidos
por rasterização. O HTML público não contém fontes de funções, páginas
restritas ou JSONL. No GitHub, os checks de SQLite, PostgreSQL e dashboard
passaram. A Vercel criou automaticamente um ambiente **Preview**, com
`production_environment: false`; o ambiente conferido era Preview, não produção.

O explorador integrado foi operado com dublê explícito: as três frases
responderam 200, com um POST por classificação e texto preservado; selecionar
etapa não disparou inferência. Desktop 1440px e celular 390px foram observados;
no celular, movimento reduzido ativo e sem overflow horizontal. A aba e os
serviços desse QA foram encerrados. As métricas Torch reais continuam sendo
evidência separada dessa interação sintética.

## Fechamento científico e operacional — 26–27/10/2026

### Fonte, ambiente e recuperação

A fonte científica congelada é
`03f91770ec92dec934d794cbad50ea3224f4cb8a`, não a revisão documental posterior.
O upload não continha `.git`: os notebooks registraram `commit_fraus: null`.
Os três `codigo_manifesto.json` foram comparados integralmente com os bytes de
`git archive` dessa fonte. O vínculo fica em **manifesto externo**, sem alterar
receitas para fingir um commit interno disponível:

- `manifesto-bundles.json`: código enviado, hashes dos dados e bundles,
  proveniência externa e artefatos do fusor; hash do tar de código
  `8f36fe926f0e611a2c71f8fbbd1d10f048cd5eca63b476190f3da4d137bd945c`.
- `completude-bundles.json`: nove bundles de semente completos, cada um com
  pesos, tokenizador, receita, histórico, manifesto da divisão, avaliação final
  e marcador de rodada concluída; os bundles agregados das três tarefas e seus
  hashes também foram recuperados. Não confundir nove treinos com doze treinos
  por haver arquivos agregados adicionais.

Execução pela **Google Colab CLI 0.7.5**, OAuth2 na conta autorizada, na mesma
sessão própria `fraus-generalizacao-20261026`. Não houve compra nem conta
alternativa. `gpu-prova.json` e as nove entradas de `gpu-treinos.jsonl`
registram **Tesla T4, Torch 2.13.0+cu130, CUDA runtime 13.0**; as nove entradas
registram parâmetros do modelo em `cuda:0`, uma por tarefa/semente.
Dependências vieram do lock. As ocorrências de recuperação foram operacionais,
não alterações oportunistas da receita:

1. O tmpfs de `/tmp` atingiu quota preparando dependências/payloads. A worktree
   e a campanha migraram para armazenamento em `/home`, com cerca de 72 GB
   disponíveis naquela observação, sem apagar artefatos antigos.
2. O upload único de dados de cerca de 1,83 GB recebeu HTTP 400. O pacote de
   treino de cerca de 70,6 MB foi transferido em nove partes de 8 MiB.
   ConsumerBR foi obtido pela fonte pública canônica no runtime, com SHA-256
   igual ao corpus local; foi usado somente para transferência, não no treino.
3. Instalar as versões fixadas no kernel já carregado causou `ImportError`
   de NumPy (`_slice`); reiniciar o kernel resolveu esse estado. A importação
   do Trainer encontrou depois `torchvision::nms`: o Torchvision pré-instalado
   `0.26.0+cu130`, fora do lock, era incompatível. Removeu-se **somente esse
   Torchvision** e reiniciou-se o kernel, sem remover dependências fixadas.
4. Uma execução perdeu conexão antes de executar o código, no ajuste inicial
   de diretório da CLI, e expirou após 660 s. A causa raiz do transporte
   **não foi estabelecida**; não atribuí-la à quota. `colab status`
   ressincronizou a sessão, que estava IDLE; uma execução curta confirmou
   novamente CUDA/T4 no mesmo runtime, sem nova alocação.
5. Nenhuma semente havia começado nessas falhas. Depois, 13/42/77 foram
   executadas **uma vez por cabeça**, sem repetir sementes concluídas ou mudar
   a receita. Bundles, hashes, exportação da sessão e provas GPU foram
   recuperados antes de `colab stop`. `estado.json` registra nove treinos,
   nove bundles, etapas com saída zero e `sessao_encerrada: true`.
   `gpu_alocada: false` é o estado final após o stop, não negação da GPU usada.
6. O fusor candidato foi extraído, treinado e avaliado **localmente em CPU após
   o stop**, com os candidatos escolhidos na validação; sua etapa terminou com
   saída zero. As ablações 39/4/7 são experimentos, não substitutos do runtime.

A saída terminal do HTTP 400 estampou uma URL temporária assinada.
**Não copiar logs brutos para PR, site ou esta nota.** O registro
`higiene-logs.json` informa 23 arquivos examinados, nenhum marcador de
credencial encontrado nos logs persistidos redigidos; isso não autoriza
publicação automática desses arquivos.

### Evidência científica preservada e limites

A [página pública](../generalizacao.md) concentra a matriz
artefato/dataset/divisão/data, as nove avaliações, médias e desvios amostrais,
ECE bruto/calibrado, todas as épocas das curvas comparáveis e as ablações.
Não duplicamos essas tabelas nesta nota.

- **Seleção:** satisfação 42, emoção 13, ironia 42, medianas da **validação**.
  A mediana calculada depois no teste não foi usada para trocar candidatos.
- **Sobreajuste novo:** séries comparáveis mostram treino melhorando e perda
  de validação piorando em intervalos persistentes. A perda de validação e
  o F1 não precisam atingir seus ótimos na mesma época. Esses padrões valem
  para a reprodução datada, não identificam causa única e não diagnosticam
  os pesos antigos ou publicados, ainda inconclusivos.
- **Sistema:** `independencia-sistema.json` confronta os fingerprints dos
  treinos efetivamente executados com os holdouts B2W reservados. Os seis
  cruzamentos textuais normalizados dão zero; há isolamento por produto B2W.
  O relatório original `fusor-candidato/metricas.json` conserva
  `teste_independente_sistema: false` e a ressalva de emoção baseada apenas
  em fingerprints agregados; **não foi reescrito**. A prova complementar
  estabelece independência observável pelos identificadores comparados, não
  ausência universal de vazamento. Grupos entre fontes não são comparáveis;
  paráfrases, tradução e proveniência sem identificador continuam limitações.
- **Transferência:** `transferencia-sobreposicoes.json` registra zero colisões
  textuais da amostra ConsumerBR de 5.000 com o treino B2W e seis colisões
  do XED integral de 4.286 com o treino GoEmotions, duas conflitantes.
  Holdouts não foram alterados. São benchmarks já consultados, não testes
  virgens; no XED, F1-macro de sete classes difere do das seis presentes.
- **Fusor:** 900/120/300 conversas sintéticas, scalers ajustados só no treino,
  quatro esperas em `log1p` e cache identificado por manifesto/checkpoints/
  contrato. Uma execução por variante não fornece desvio entre sementes.
  Não foram medidos conformal ou desempenho em atendimentos reais rotulados.
- **Histórico e produção:** auditoria/baselines de 26/10 e resultados de
  setembro mantêm suas datas e limites. Nenhum peso foi promovido ou copiado
  para diretório ativo. O agente não executou comandos de publicação nem merge.
  O Preview automático já registrado não identifica um checkpoint publicado.

### Armazenamento e retomada

Raiz durável da campanha:
`/home/joaopedro/.cache/fraus/campanhas/2026-10-26/`.
`bundles/` preserva os nove bundles individuais e três agregados;
`fusor-candidato/` preserva candidato, importâncias e ablações.
`resumo-cientifico.json`, `conclusoes-cientificas.json`,
`manifesto-bundles.json`, `completude-bundles.json`,
`independencia-sistema.json`, `transferencia-sobreposicoes.json`,
`estado.json` e as provas CUDA são as referências da campanha concluída.
`colab.ipynb` é a exportação privada da sessão, não uma página publicável.
O histórico de auditoria/baselines continua em
`/tmp/fraus-overfitting-20261026/`; não confundir esse workspace temporário
com a raiz durável dos candidatos.

“Durável” aqui significa fora do tmpfs, não prova de backup externo.
Pesos, corpora, logs e manifestos individuais não entram no Git nem no site.
Uma retomada deve partir dos artefatos exportados, sem reabrir GPU ou refazer
sementes já concluídas apenas para reconstruir evidência disponível.

### Conferência independente após a recuperação

O agente principal conferiu os bytes e SHA-256 de **19 arquivos**: os nove
bundles individuais, três agregados e sete artefatos do fusor.
`verificacao-integridade-pai.json`, fora do repositório, registra essa prova.
O candidato completo foi carregado pela API real `Fusor.carregar`, na escala
`log1p`; ele e as duas ablações reproduziram os F1 registrados nos 300 exemplos
sintéticos de teste. `Fusor.pontuar` também foi exercitado com features reais
desse cache, sem tocar no artefato ativo.

A revisão científica independente conferiu avaliações, médias/desvios
amostrais, seleção pela validação, nove históricos, vínculo externo de código,
provas CUDA e limites de independência, sem achado material nesse escopo.
A consulta final `colab --auth oauth2 sessions` não encontrou sessões ativas.
A régua operacional nova de ironia também foi preservada na página pública:
é a régua já consultada, não um novo corpus nem garantia de qualidade.

O vínculo de código foi conferido também contra o próprio Git: SHA-256 dos
116 arquivos do mapa externo iguais aos bytes de `git show 03f9177:caminho`;
os 106 arquivos de cada um dos três manifestos internos correspondem ao mesmo
mapa. `vinculo-codigo-pai.json` registra essa camada externa, sem alterar o
`commit_fraus: null` observado dentro dos notebooks.

### Resultados posteriores ao merge da base

A PR #104 foi mergeada fora desta execução em `2026-10-26T23:57:18Z`,
com head `e06d413` e merge `6d7278e`. Os resultados finais foram commitados
depois, em `51cb74b`: eles não fazem parte do diff mergeado naquela PR.
A entrega complementar usa a branch `docs/resultados-generalizacao-20261027`,
baseada na `main` já mergeada, e altera somente os seis documentos de resultados.
O código dos treinos permanece vinculado a `03f9177`; essa reorganização Git
não muda pesos, dados, receita ou avaliação e não exige refazer a campanha.

