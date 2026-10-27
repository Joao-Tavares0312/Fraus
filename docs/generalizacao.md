# Generalização e evidências

## Estado da investigação — 27/10/2026

!!! warning "Campanha concluída; candidatos novos, não modelos publicados"
    A reprodução de 26–27/10 concluiu **nove treinos em T4**, exportou os nove
    bundles e avaliou o candidato do fusor e suas ablações. As curvas comparáveis
    sustentam **sobreajuste nesta reprodução**, com padrões detalhados abaixo.
    O diagnóstico dos pesos antigos e dos publicados continua **inconclusivo**:
    suas curvas e proveniência não foram recuperadas. Não houve promoção de
    modelo nem publicação em produção; a sessão própria foi encerrada pela CLI.

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

A campanha nova usa a fonte congelada
`03f91770ec92dec934d794cbad50ea3224f4cb8a`, vinculada por
`manifesto-bundles.json`. O upload não continha `.git`: o campo de commit
interno dos notebooks ficou nulo. A ligação externa com o commit resulta da
comparação integral dos três `codigo_manifesto.json` com os bytes de
`git archive` dessa fonte, não de um commit interno inventado. Pesos, logs e
manifestos individuais permanecem fora do Git e do site.

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
| `resumo-cientifico.json` + nove bundles / satisfação, emoção e ironia novas | B2W, GoEmotions-PT e MultiPICo PT; splits congelados e sementes 13/42/77 | 26–27/10/2026 | nove avaliações finais, ECE bruto/calibrado e curvas por época; tabelas abaixo | reprodução nova, não recuperação do histórico nem identificação de produção |
| `fusor-candidato/metricas.json` / completo e ablações | B2W agrupado + 900/120/300 conversas sintéticas de treino/validação/teste | 26–27/10/2026 | extração real com cabeças candidatas e avaliação de 39/4/7 features concluídas | uma execução por variante, não atendimento real rotulado |
| `independencia-sistema.json` / prova complementar | validação/teste B2W contra treinos reais das três cabeças novas | 27/10/2026 | fingerprints correspondem às receitas; zero colisões textuais normalizadas nos seis cruzamentos | não detecta paráfrases; grupos entre fontes não são comparáveis |
| `transferencia-sobreposicoes.json` + `resumo-cientifico.json` / candidatos selecionados | ConsumerBR amostrado (5.000) e XED integral (4.286) contra os treinos reais correspondentes | 27/10/2026 | zero colisões ConsumerBR × treino B2W; seis XED × treino GoEmotions, dois conflitos | benchmarks já consultados, não testes virgens; XED não é textualmente independente |
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
As métricas das três cabeças nas linhas de 26/10 acima são **baselines dos
artefatos locais anteriores**, não resultados das nove rodadas novas.
As quedas B2W → ConsumerBR e GoEmotions → XED mostram limites de transferência
sob essas condições, sem
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

## Resultados da reprodução — 26–27/10/2026

Fonte: `resumo-cientifico.json`, derivado das receitas, históricos e avaliações
finais preservados nos bundles. Os valores abaixo são arredondados, não
substituem os registros completos. Precisão/recall/F1/suporte por classe,
matrizes de confusão, temperaturas e hashes estão nesses artefatos externos;
não publicamos exemplos individuais.

### Três sementes por cabeça

O desvio é **amostral** (`n − 1`, três sementes), não intervalo de confiança.
Os tamanhos são os efetivamente usados, após limpeza e divisão agrupada.
A semente escolhida é a mediana **da validação**, congelada antes do teste.

| cabeça / corpus | treino / validação / teste | F1-macro validação, média ± desvio | F1-macro teste, média ± desvio | semente escolhida na validação |
|---|---:|---:|---:|---:|
| satisfação / B2W | 95.722 / 12.058 / 18.895 | 0,757917 ± 0,002995 | **0,755156 ± 0,005943** | **42** |
| emoção / GoEmotions-PT | 36.806 / 4.874 / 7.328 | 0,578719 ± 0,001800 | **0,592371 ± 0,005218** | **13** |
| ironia / MultiPICo PT | 1.126 / 292 / 462 | 0,688503 ± 0,015942 | **0,647941 ± 0,023741** | **42** |

Detalhamento dos nove treinos. “Época” é a do checkpoint escolhido por
F1-macro de validação, não necessariamente a de menor perda.

| cabeça / semente | época | F1 validação | F1 teste | acurácia teste |
|---|---:|---:|---:|---:|
| satisfação / 13 | 1 | 0,760614 | 0,754337 | 0,830590 |
| satisfação / **42** | 4 | 0,758444 | 0,761466 | 0,847208 |
| satisfação / 77 | 1 | 0,754693 | 0,749664 | 0,817253 |
| emoção / **13** | 3 | 0,578321 | 0,597280 | 0,657751 |
| emoção / 42 | 5 | 0,577151 | 0,586892 | 0,659934 |
| emoção / 77 | 4 | 0,580685 | 0,592943 | 0,666075 |
| ironia / 13 | 4 | 0,675866 | 0,665176 | 0,681818 |
| ironia / **42** | 2 | 0,683228 | 0,620862 | 0,670996 |
| ironia / 77 | 4 | 0,706413 | 0,657787 | 0,686147 |

ECE top-1 no mesmo teste: **bruto, sem temperatura**, e **com temperatura
ajustada somente na validação**.

| cabeça / semente | ECE bruto | ECE com temperatura |
|---|---:|---:|
| satisfação / 13 | 0,023847 | 0,024383 |
| satisfação / **42** | 0,075406 | 0,020136 |
| satisfação / 77 | 0,030691 | 0,022800 |
| emoção / **13** | 0,106976 | 0,037097 |
| emoção / 42 | 0,158665 | 0,036317 |
| emoção / 77 | 0,129541 | 0,026192 |
| ironia / 13 | 0,056899 | 0,033080 |
| ironia / **42** | 0,047387 | 0,066038 |
| ironia / 77 | 0,135616 | 0,057866 |

A mediana retrospectiva do **teste** seria 13/77/77, respectivamente; ela
**não** substituiu 42/13/42. Temperatura não garante melhora de ECE em todo
teste: piorou na satisfação 13 e na ironia 42. Não escolher outra temperatura
ou semente por esse resultado final.

### Curvas comparáveis: evidência de sobreajuste

São medições por época em modo **eval**, sem dropout, no diagnóstico fixo
estratificado de treino (até 2.000 exemplos, semente 42) e na validação, com
a mesma função de perda ponderada. Não são médias de minibatches do treino.
As séries completas observadas estão abaixo; o treino diagnóstico não é uma
estimativa em dados independentes.

| cabeça / semente | época | perda treino eval | perda validação | F1 treino eval | F1 validação |
|---|---:|---:|---:|---:|---:|
| satisfação / 13 | 1 | 0,4540 | 0,5316 | 0,8015 | 0,7606 |
| satisfação / 13 | 2 | 0,3661 | 0,5393 | 0,8063 | 0,7474 |
| satisfação / 13 | 3 | 0,2742 | 0,5789 | 0,8581 | 0,7545 |
| satisfação / 42 | 1 | 0,4754 | 0,5455 | 0,7538 | 0,7195 |
| satisfação / 42 | 2 | 0,3681 | 0,5231 | 0,8314 | 0,7567 |
| satisfação / 42 | 3 | 0,2823 | 0,5619 | 0,8349 | 0,7424 |
| satisfação / 42 | 4 | 0,2231 | 0,7633 | 0,9054 | 0,7584 |
| satisfação / 42 | 5 | 0,1816 | 0,8071 | 0,9165 | 0,7560 |
| satisfação / 77 | 1 | 0,4444 | 0,5172 | 0,7930 | 0,7547 |
| satisfação / 77 | 2 | 0,3507 | 0,5359 | 0,8343 | 0,7513 |
| satisfação / 77 | 3 | 0,2565 | 0,6102 | 0,8620 | 0,7488 |
| emoção / 13 | 1 | 0,8665 | 1,1082 | 0,5909 | 0,5518 |
| emoção / 13 | 2 | 0,6800 | 1,1377 | 0,6426 | 0,5593 |
| emoção / 13 | 3 | 0,4778 | 1,3006 | 0,7625 | 0,5783 |
| emoção / 13 | 4 | 0,3429 | 1,3887 | 0,7960 | 0,5729 |
| emoção / 13 | 5 | 0,3100 | 1,4869 | 0,8175 | 0,5769 |
| emoção / 42 | 1 | 0,8804 | 1,0785 | 0,5890 | 0,5567 |
| emoção / 42 | 2 | 0,6518 | 1,0771 | 0,6619 | 0,5691 |
| emoção / 42 | 3 | 0,4384 | 1,2388 | 0,7589 | 0,5729 |
| emoção / 42 | 4 | 0,3380 | 1,3445 | 0,8057 | 0,5709 |
| emoção / 42 | 5 | 0,2917 | 1,4710 | 0,8454 | 0,5772 |
| emoção / 77 | 1 | 0,8492 | 1,0976 | 0,5838 | 0,5311 |
| emoção / 77 | 2 | 0,6131 | 1,0670 | 0,6961 | 0,5805 |
| emoção / 77 | 3 | 0,4550 | 1,1954 | 0,7433 | 0,5741 |
| emoção / 77 | 4 | 0,3308 | 1,3682 | 0,8109 | 0,5807 |
| emoção / 77 | 5 | 0,2968 | 1,4625 | 0,8246 | 0,5760 |
| ironia / 13 | 1 | 0,6619 | 0,6637 | 0,5546 | 0,4816 |
| ironia / 13 | 2 | 0,5648 | 0,6067 | 0,7101 | 0,6546 |
| ironia / 13 | 3 | 0,4430 | 0,5903 | 0,7829 | 0,6638 |
| ironia / 13 | 4 | 0,3703 | 0,6040 | 0,8391 | 0,6759 |
| ironia / 13 | 5 | 0,3441 | 0,6132 | 0,8608 | 0,6746 |
| ironia / 42 | 1 | 0,6415 | 0,6541 | 0,6574 | 0,5798 |
| ironia / 42 | 2 | 0,5308 | 0,6095 | 0,7471 | 0,6832 |
| ironia / 42 | 3 | 0,3764 | 0,6069 | 0,8175 | 0,6430 |
| ironia / 42 | 4 | 0,2986 | 0,6320 | 0,8714 | 0,6520 |
| ironia / 77 | 1 | 0,6073 | 0,6280 | 0,6501 | 0,6199 |
| ironia / 77 | 2 | 0,4684 | 0,5897 | 0,7915 | 0,6826 |
| ironia / 77 | 3 | 0,3241 | 0,5940 | 0,8615 | 0,6925 |
| ironia / 77 | 4 | 0,2517 | 0,6364 | 0,9152 | 0,7064 |
| ironia / 77 | 5 | 0,2337 | 0,6524 | 0,9220 | 0,7029 |

- **Satisfação:** perda de treino cai enquanto a de validação sobe nas épocas
  1–3 de 13/77 e 2–5 de 42. O F1 de validação não acompanha o ganho do treino.
- **Emoção:** o padrão de perdas persiste em 1–5 de 13 e 2–5 de 42/77.
  O F1 de validação ainda melhora em algumas épocas, mas muito menos que o
  de treino; seleção por F1 e seleção por perda não são a mesma decisão.
- **Ironia:** perda de validação sobe em 3–5 de 13 e 2–5 de 77 enquanto o
  treino melhora. Na 42, o F1 perde o pico da época 2; a perda só aumenta de
  3 para 4, não desde a época 2. Não atribuímos uma subida monotônica inexistente.

Esses padrões sustentam **sobreajuste nas fases indicadas desta reprodução**,
não uma causa única, um limiar universal de gap ou um diagnóstico dos pesos
publicados. O checkpoint continuou selecionado somente pela validação.

### Transferência e régua operacional dos candidatos escolhidos

| candidato / benchmark | n | F1-macro | acurácia | ECE com temperatura |
|---|---:|---:|---:|---:|
| satisfação 42 / ConsumerBR amostrado | 5.000 | 0,573398 | 0,756600 | 0,063823 |
| emoção 13 / XED-pt integral | 4.286 | **sete classes 0,233188; seis presentes 0,272053** | 0,278115 | 0,371403 |
| ironia 42 / régua de atendimento já consultada | 20 | 0,520000 | não registrada | não registrado |

O notebook 04 também registrou a régua operacional em
`ironia-generalizacao-20261026/metricas.json`, campo `regua_20`: dois falsos
positivos e sete falsos negativos. Não é um corpus novo de atendimento;
acurácia e ECE dessa régua não constam nesse relatório, por isso ficam ausentes.
ConsumerBR amostrado não colide textualmente com os 95.722 exemplos de treino B2W;
isso não o torna teste virgem nem prova independência por empresa/autor.
XED tem seis colisões textuais com os 36.806 exemplos de treino GoEmotions,
duas com conflito de rótulo; o benchmark integral foi preservado, sem limpar
retrospectivamente o holdout para melhorar a comparação. Grupos entre fontes
não são comparáveis. Não há ECE bruto de transferência no resumo: não inferir
uma melhora de calibração sem essa medição.

As quedas fora do corpus-fonte descrevem transferência sob mudança de domínio,
distribuição e alvo; não isolam causalmente sobreajuste. XED ainda usa rótulos
projetados entre línguas e não contém neutro. Nenhum dos dois é um corpus novo
de atendimentos reais rotulados.

### Candidato do fusor e ablações

São **900/120/300 conversas sintéticas** de treino/validação/teste, equilibradas
por classe em cada lado, com textos dos grupos correspondentes do manifesto
B2W reservado antes do treino de satisfação. Usaram os candidatos escolhidos
pela validação; não os baselines locais antigos. Features excluídas foram
removidas da matriz, cada scaler foi ajustado somente no treino, e as quatro
esperas mantêm `log1p`. O cache vincula manifesto, checkpoints e contrato.

| variante experimental | features | F1 validação | F1 teste | acurácia teste | ECE teste |
|---|---:|---:|---:|---:|---:|
| completo | 39 | 0,932486 | **0,931557** | 0,933333 | 0,030091 |
| somente texto | 4 | 0,836454 | **0,883318** | 0,886667 | 0,044542 |
| somente tempo | 7 | 0,509600 | **0,558372** | 0,573333 | 0,048255 |

Há uma execução por variante: **não há média/desvio de três sementes do
fusor**. O ECE é das probabilidades do candidato; não houve nova temperatura
do fusor nem avaliação conformal nesta campanha. Essas ablações não substituem
o runtime nem medem causalidade dos sinais.

O relatório original do instrumento conservou a ressalva de independência
não verificável da emoção, pois só examina fingerprints agregados de outro
corpus. Ele **não foi sobrescrito**. A prova complementar
`independencia-sistema.json` confirma os fingerprints dos treinos reais das
três cabeças e encontra zero colisões textuais normalizadas com validação e
teste B2W. Em satisfação, há também isolamento por produto no manifesto.
Isso estabelece independência **observável por esses identificadores nesta
reprodução**; não cobre paráfrases, traduções, proveniência ausente ou grupos
incomparáveis entre fontes. Não altera a insuficiência histórica dos pesos
antigos, nem converte o teste sintético em generalização comprovada em suporte.

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
dos três notebooks foram compiladas; esse smoke local não executou o caminho de GPU.
Isso verifica contratos do código, **não** mede satisfação, emoção, ironia ou
generalização do Fraus. A campanha T4 posterior é evidência separada, acima.

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

O experimento concluído preserva o relatório conservador original e o
complementa com a comparação textual dos treinos reais, conforme a seção de
resultados. Conversas sintéticas continuam não sendo atendimentos reais
rotulados, ainda que os identificadores observados sejam disjuntos.

## Como interpretar as conclusões

1. **Vazamento/dependência observada:** os 41 produtos atravessam os pools da
   receita posicional reconstruída. Os atalhos históricos de latência e de
   marcadores de ironia estão documentados no diário; não são diagnóstico
   automático dos pesos publicados hoje.
2. **Sobreajuste:** as curvas novas mostram treino melhorando e perda de
   validação piorando persistentemente nos intervalos explicitados acima.
   A conclusão vale para **esta reprodução de 26–27/10**, sem limiar universal
   de gap e sem diagnóstico causal. Para pesos antigos/publicados, faltam
   curvas e proveniência: o diagnóstico continua **inconclusivo**, não
   “sem sobreajuste”.
3. **Transferência:** ConsumerBR, XED e as réguas de ironia já foram consultados.
   Medem desempenho em outro domínio sob essas condições, não teste virgem.
   Para XED, distinguir **F1-macro nas sete classes** de F1-macro somente nas
   classes presentes; não comparar os dois como se fossem a mesma métrica.
   MultiPICo anota ironia vendo o post; o modelo lê só a resposta, uma limitação
   contextual adicional.
4. **Insuficiência:** faltam curvas e proveniência completa dos treinos
   **históricos**, checkpoint publicado identificado e corpus novo de
   atendimento rotulado. Nem o baseline isolado de uma cabeça nem o teste
   sintético novo autorizam promessa de acurácia operacional em suporte real.

Para os limites de uso, veja [Limitações](limitacoes.md) e
[Conformidade](conformidade.md). O método e a hipótese estão em [A tese](tese.md).
