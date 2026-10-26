# Generalização e evidências

## Estado da investigação — 26/10/2026

!!! warning "Diagnóstico de overfitting atual: inconclusivo"
    Há atalhos históricos documentados e sobreposição de produtos na receita
    posicional reconstruída. Isso não recupera as curvas dos pesos antigos nem
    identifica o checkpoint de produção. A campanha fechada no Colab e o novo
    experimento independente do fusor **ainda não têm resultados**. A CLI oficial
    está instalada e o login OAuth2 na conta autorizada foi concluído na retomada;
    alocação T4, quota e exportação dos candidatos ainda precisam ser observadas.
    Não houve promoção de modelo ou deploy nesta investigação.

Esta página distingue quatro perguntas: **vazamento**, **sobreajuste**,
**transferência de domínio** e **insuficiência de evidência**. Uma métrica alta
não responde às quatro; uma queda entre corpora tampouco prova overfitting.
As medições históricas continuam no [Cartão do modelo](cartao-do-modelo.md)
e no [diário de treinamento](treinamento.md), com suas datas.

## Matriz de evidências

Os identificadores abaixo nomeiam saídas de pesquisa preservadas fora do site
público. Não são links para manifestos individuais, dados brutos ou pesos.
Base do inventário: commit `836d440bbe246018fb8808a4ede4c6f84d6a0ef9`.
A data é a da observação, não uma alegação sobre quando o modelo foi treinado.

| artefato / componente | dataset e divisão | data | o que foi observado | limite |
|---|---|---|---|---|
| `inventario.json` / três cabeças Torch locais | arquivos, configurações e hashes; sem inferência | 26/10/2026 | checkpoints locais identificados por bytes | não identifica produção nem recupera manifestos históricos |
| `auditoria.json` / corpora locais completos | leitores canônicos e splits 42, sem inferência | 26/10/2026 | auditoria integral concluída; duplicatas, conflitos e interseções normalizadas registrados | a reconstrução não prova a origem supervisionada dos pesos antigos |
| `historico.json` / receita antiga do fusor | pools posicionais B2W, 900 linhas de treino e 300 de teste | 26/10/2026 | zero textos normalizados comuns; **41 produtos comuns**, envolvendo 63 linhas de treino e 52 de teste | reconstrução da receita atual, não prova de quais exemplos treinaram pesos antigos |
| `satisfacao-atual.json` / cabeça local de satisfação | B2W, amostra estratificada de 5.000 dos 18.895 exemplos do teste reconstruído | 26/10/2026 | F1-macro **0,764556**, acurácia **0,820000**, ECE **0,018971** | pesos anteriores à divisão podem ter visto exemplos; independência histórica não verificável |
| `satisfacao-atual.json` / mesma cabeça | ConsumerBR, amostra estratificada de 5.000 dos 143.717 exemplos do teste reconstruído | 26/10/2026 | F1-macro **0,538760**, acurácia **0,690600**, ECE **0,090972** | transferência já consultada; independência depende de treino somente em B2W, sem manifesto histórico que a comprove |
| `ironia-atual.json` / cabeça local de ironia | teste reconstruído MultiPICo-PT, 462 exemplos | 26/10/2026 | F1-macro **0,660294**, acurácia **0,683983**, ECE **0,055439** | benchmark já consultado; independência histórica do sistema não verificável |
| `ironia-atual.json` / mesma cabeça | régua de 20 frases de atendimento | 26/10/2026 | F1-macro **0,520000**, acurácia **0,550000**, ECE **0,242688** | conjunto pequeno e já consultado; não estima qualidade em produção |
| `emocao-atual.json` / cabeça local de emoção | teste GoEmotions-PT reconstruído, 7.328 exemplos | 26/10/2026 | F1-macro **0,691023**, acurácia **0,720524**, ECE **0,056790** | pesos anteriores à nova divisão podem ter visto parte dos exemplos; independência histórica não verificável |
| `emocao-atual.json` / mesma cabeça | XED-pt, 4.286 exemplos, seis classes presentes (sem neutro) | 26/10/2026 | F1-macro **sete classes 0,240398**; **seis presentes 0,280465**; acurácia **0,285814**, ECE **0,451814** | transferência já consultada; rótulos projetados de outras línguas, não validação de suporte real |
| satisfação e emoção locais / curvas antigas | treino supervisionado histórico | 26/10/2026 | curvas e manifestos individuais antigos não recuperados | não permite medir gap treino–validação dos pesos atuais |
| nova campanha das três cabeças | B2W, GoEmotions-PT e MultiPICo PT; três sementes por cabeça | 26/10/2026 | **OAuth2 concluído; execução e quota T4 ainda pendentes** | sem nove rodadas, curvas novas ou média/desvio a reportar |
| candidato independente do fusor | B2W agrupado + conversas sintéticas | 26/10/2026 | **pendente da campanha e dos manifestos das cabeças** | sem avaliação nova de sistema independente |
| produção | checkpoint não identificado | 26/10/2026 | nenhuma inferência autenticada ou proveniência de pesos demonstrada nesta investigação | saúde da API não comprova inferência nem igualdade com artefatos locais |

Os pesos locais de ironia medidos têm SHA-256
`512841782d167327b21e1c2c98e602c28dbdf30d6fdafa9733b9f078f4d09388`.
O conjunto MultiPICo medido tem fingerprint textual
`4eee9c62e8c9a11fb5e39d1609238b7175420ca171e8352a3516e4785693595e`;
a régua de 20 frases,
`90f3ab25892bef90b09167120808ae9357919384667fdd74ec4132d4ef27e668`.
Os pesos locais de emoção têm SHA-256
`e9735f12ef459ba93102d868be7455d9a0d453099530597f3855269b5ab83cd9`;
os fingerprints textuais de GoEmotions-PT e XED-pt são, respectivamente,
`8b48cefed8df6595e35c6aee7b24fc33fae1237bede03b4436e51c7e51e182ec` e
`a1d2cd6db52ca19183d9a4cbaa7d1f59aae74e1f1add01d7251ef9e5ecf4c49a`.
Os pesos locais de satisfação têm SHA-256
`9f9448aed6c655ce0fab2d3e32db485d0b8de986c6d907eb82336f69c62edad2`;
os fingerprints textuais das amostras B2W e ConsumerBR são, respectivamente,
`481da017399ae008fa610886c740b5e7b64dfa1f076b6a85e5a0473f7b38040a` e
`99a53fd45904ac297d5cf62d4936945b413e8fc3b4f7720246d016e15309d237`.
Essas impressões identificam conjuntos observados agora, não comprovam que
ficaram fora de todo ajuste supervisionado ou de decisões históricas.

No XED, o campo `f1_macro` do JSON representa as sete classes do contrato,
enquanto `f1_macro_classes_presentes` representa as seis observadas. A leitura
de console pode destacar o segundo; não é intercambiável com o primeiro.
As métricas das três cabeças acima são **baselines dos artefatos locais**,
não resultados das nove rodadas propostas. As quedas B2W → ConsumerBR e
GoEmotions → XED mostram limites de transferência sob essas condições, sem
identificar isoladamente a causa (domínio, variedade, projeção dos rótulos
ou sobreajuste).

### O que a reconstrução do fusor mostra

A divisão por posição não isolava produtos, apesar de não repetir textos
normalizados entre os dois pools. Logo, **disjunção textual não é independência
por produto**. Não se mede aqui o efeito dessa dependência sobre a acurácia.

Estrelas (alvo da cabeça de satisfação) e recomendação com precedência do
neutro de três estrelas (alvo do fusor) discordam em **16 linhas do pool de
treino e 5 do pool de teste**. São alvos diferentes: a discordância não deve
ser apagada nem tratada automaticamente como erro de anotação. Os pools não
são as conversas efetivamente sorteadas pelo simulador e não demonstram
independência do treino supervisionado das cabeças.

## Auditoria integral dos corpora

Contagens aceitas pelos leitores, antes de qualquer amostragem. “Conflito”
conta **linhas** removidas porque o mesmo texto normalizado recebeu rótulos
diferentes dentro daquele corpus; não escolhe uma das respostas.

| corpus | aceitos | duplicatas excedentes excluídas | linhas conflitantes excluídas | após limpeza |
|---|---:|---:|---:|---:|
| B2W | 129.098 | 2.373 | 50 | 126.675 |
| ConsumerBR | 1.063.112 | 32.414 | 72.587 | 958.111 |
| GoEmotions-PT | 49.469 | 321 | 140 | 49.008 |
| MultiPICo PT | 1.891 | 8 | 3 | 1.880 |
| XED-pt | 4.286 | 9 | 2 | 4.275 |

O benchmark XED acima preserva seus **4.286 exemplos integrais**; a coluna
“após limpeza” é uma contagem de auditoria, não uma mudança silenciosa
desse benchmark. A divisão reconstruída de treino GoEmotions compartilha
**seis textos normalizados** com XED, dois deles com rótulos conflitantes.
Logo, nem separação por nome de corpus comprova disjunção textual.

B2W e ConsumerBR aceitos compartilham nove textos normalizados, quatro com
conflitos de rótulo. A demonstração de isolamento do auxiliar ConsumerBR
removeu duas linhas conflitantes e quatro duplicatas do treino principal;
**não foi aplicada a um treino** desta campanha.

O pool posicional antigo de teste do fusor compartilha **215 textos** com
o treino B2W da divisão 42 reconstruída. Misturar esse pool antigo com uma
cabeça treinada nessa divisão nova contaminaria a avaliação do sistema.
O manifesto prospectivo compartilhado entre cabeça e fusor evita essa
mistura; não comprova retroativamente a independência dos modelos antigos.

## Protocolo de auditoria

`scripts/auditar_generalizacao.py` reutiliza os leitores canônicos de corpora
e gera JSON agregado versão 1, com corpora, artefatos, divisões,
sobreposições e limitações, além de manifesto privado adjacente. Ele não
treina, não infere e não desserializa pickle/joblib desconhecido.

A auditoria registra contagens aceitas pelos leitores, classes, grupos,
duplicatas, conflitos e hashes. Texto é normalizado antes da comparação;
o fingerprint forte também incorpora rótulos e grupos. Índices do manifesto
são posições **aceitas pelo leitor**, não números de linhas brutas.

- Congelar validação e teste antes de anexar dados auxiliares. Textos ou grupos
  auxiliares que colidam com holdouts saem do treino auxiliar; os holdouts não
  são movidos para acomodá-los. Conflitos de rótulo são registrados, não
  resolvidos escolhendo silenciosamente uma fonte.
- Colisão entre validação e teste bloqueia o novo treino.
- Dividir por produto, autor ou post quando o leitor oferece essa identidade.
  Sem grupo, usar identidade textual e declarar que autores/produtos
  desconhecidos podem atravessar os lados.
- ConsumerBR não demonstra independência por empresa: o benchmark não usa esse
  agrupamento, dada a concentração dos exemplos em grandes empresas.
- Hash calculado hoje não substitui manifesto histórico. Sem cadeia de
  proveniência, escrever **independência não verificável**, não “sem vazamento”.

## Protocolo da campanha fechada

A [receita vigente](treinamento.md#receita-vigente-de-pesquisa-26102026) fixa
sementes **13, 42 e 77**, no máximo cinco épocas e os mesmos hiperparâmetros
nas três rodadas de cada cabeça. Não há busca oportunista de encoders,
regularizadores ou novos corpora. É uma **nova reprodução datada**, não
recuperação do histórico perdido.

Satisfação usa B2W completo após split, sem ConsumerBR auxiliar; emoção usa
GoEmotions-PT; ironia usa MultiPICo em português **sem IDPT auxiliar**.
A divisão usa semente 42, com 75/10/15 para B2W e GoEmotions e 60/15/25 para
MultiPICo, respeitando os grupos disponíveis.

Checkpoint e temperatura usam validação. A semente mediana é escolhida por
F1-macro de validação; configuração e seleção são gravadas antes da avaliação
final das três sementes no teste congelado. O fingerprint divergente bloqueia
a avaliação. Não selecionar retrospectivamente outra semente pelo teste.

Por época, preservar perda e F1 de validação e de um subconjunto diagnóstico
fixo de treino (até 2.000 exemplos, seed 42, modo eval e mesma perda ponderada).
Relatar melhor época, argumentos efetivos, F1-macro, acurácia, precisão,
recall, F1 e suporte por classe, matriz de confusão e ECE antes/depois da
temperatura. As três sementes fornecem média e **desvio amostral**.
Não existe um limiar universal de gap que diagnostique sobreajuste.

### Verificação de implementação não é resultado científico

Em 26/10/2026, a verificação integrada da receita registrou 77 testes focados
aprovados e um smoke real com BERT **aleatório e minúsculo**, treinado por duas
épocas em dados construídos. O smoke salvou/recarregou o modelo, executou a
avaliação final separada e recusou manifesto divergente. As 18 células Python
dos três notebooks foram compiladas; o caminho de GPU não foi executado.
Isso verifica contratos do código, **não** mede satisfação, emoção, ironia ou
generalização do Fraus e não substitui as nove rodadas pendentes.

### Teste do sistema e ablações do fusor

Reservar os grupos do teste B2W **antes** de treinar a cabeça de satisfação.
O manifesto explícito compartilhado entre notebook 01 e treino do fusor
registra origem, índices aceitos, hashes de texto/grupo e rótulos de satisfação
por lado. `--manifesto` é obrigatório no script local; caches são vinculados
a esse manifesto, bytes dos checkpoints, features/`log1p`, simulador e léxicos.
Cache antigo sem essa identidade não é comparável por nome de arquivo.

O fusor continua usando recomendação e neutro de três estrelas; o rótulo de
satisfação do manifesto identifica a divisão da cabeça, não troca o alvo do
fusor. Treino, validação e teste do fusor só usam seus respectivos grupos.
Comparar completo, somente texto e somente tempo removendo colunas e ajustando
cada scaler **só no treino**. Nenhuma ablação é artefato de runtime.

Mesmo com B2W isolado, se os manifestos de emoção e ironia não comprovarem
independência supervisionada, não chamar o teste de independente do sistema
inteiro. E conversas sintéticas continuam não sendo atendimentos reais
rotulados, ainda que os grupos de texto sejam disjuntos.

## Como interpretar as conclusões

1. **Vazamento/dependência observada:** os 41 produtos atravessam os pools da
   receita posicional reconstruída. Os atalhos históricos de latência e de
   marcadores de ironia estão documentados no diário; não são diagnóstico
   automático dos pesos publicados hoje.
2. **Overfitting:** exige curvas comparáveis em que treino melhora e validação
   piora persistentemente, junto de contexto de seleção e incerteza. Essas
   curvas antigas não estão disponíveis, e as novas rodadas não ocorreram.
   O diagnóstico atual permanece **inconclusivo**; ausência de evidência não é
   ausência de sobreajuste.
3. **Transferência:** ConsumerBR, XED e as réguas de ironia já foram consultados.
   Medem desempenho em outro domínio sob essas condições, não teste virgem.
   Para XED, distinguir **F1-macro nas sete classes** de F1-macro somente nas
   classes presentes; não comparar os dois como se fossem a mesma métrica.
   MultiPICo anota ironia vendo o post; o modelo lê só a resposta, uma limitação
   contextual adicional.
4. **Insuficiência:** faltam curvas históricas, proveniência completa dos
   treinos, checkpoint publicado identificado e corpus novo de atendimento
   rotulado. Nenhum baseline de uma cabeça, sozinho, valida a satisfação
   inferida de ponta a ponta nem autoriza promessa de acurácia operacional.

Para os limites de uso, veja [Limitações](limitacoes.md) e
[Conformidade](conformidade.md). O método e a hipótese estão em [A tese](tese.md).
