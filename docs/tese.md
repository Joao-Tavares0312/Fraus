# A tese

## Pergunta de pesquisa

**Como combinar sinais observáveis de uma conversa de chatbot para estimar a
satisfação do cliente, sem pesquisa obrigatória e sem LLM em runtime?**

Pesquisas declaradas de NPS e CSAT dependem da participação do cliente e podem
sofrer viés de não resposta. Já a contenção informa se houve transferência para
um humano, mas não distingue, sozinha, resolução de desistência. São medidas
complementares; o Fraus não propõe substituir uma pela outra nem tratar quem
não respondeu à pesquisa como insatisfeito.

## Hipótese e alcance

A hipótese de trabalho é que **texto, emoji e estrutura temporal contêm pistas
complementares** para uma estimativa de satisfação. Essas pistas podem apoiar
a revisão humana e a identificação de tendências, inclusive em atendimentos
sem resposta a uma pesquisa.

Uma frase motivadora é:

> *"que atendimento maravilhoso, só esperei 3 horas"*

Ela ilustra a possível divergência entre elogio literal e situação relatada.
Não é prova de que o sistema reconheça ironia, nem de que uma espera relatada
no texto tenha sido medida pelos timestamps. O comportamento nesse caso
depende dos classificadores e das features; falhas são declaradas em
[Limitações](limitacoes.md).

## Unidade de análise e método

- **Mensagem:** as três cabeças neurais estimam satisfação textual, emoção e
  ironia. Emoção tem sete classes treinadas; desprezo é derivado de raiva e
  nojo, não uma oitava classe aprendida.
- **Conversa:** os sinais das mensagens e da estrutura são agregados em
  **39 features de sete famílias**. O fusor aplica `StandardScaler` e
  `LogisticRegression` e produz um score de 0 a 100. Ironia é a oitava família
  observada, exibida por mensagem, mas não participa desse vetor.
- **Recorte de conversas:** o servidor deriva nota, categoria e indicadores.
  O **NPS é inferido**, não a resposta declarada de clientes. Conversa sem
  evidência suficiente, incluindo cortesia isolada, é “sem sinal”, não zero.

O método usa classificadores BERTimbau fine-tunados e sinais determinísticos,
com inferência local em CPU e **nenhuma chamada a LLM em runtime**.
A [Arquitetura](arquitetura.md) detalha o processamento; o
[Treinamento](treinamento.md) separa a receita vigente do diário histórico.

## Origem dos dados e avaliação

O texto de satisfação vem de resenhas B2W; emoção usa GoEmotions traduzido para
português; a campanha diagnóstica de ironia usa MultiPICo em português.
ConsumerBR e XED são referências de transferência **já consultadas**, não testes
virgens. As fontes, divisões, artefatos e resultados efetivamente obtidos estão
centralizados em [Generalização e evidências](generalizacao.md), sem repetir
suas tabelas nesta página.

O fusor é avaliado em conversas sintéticas: texto real é combinado com tempo,
emoji e estrutura gerados. Isso mede comportamento nesse domínio, não acurácia
em atendimentos reais rotulados. A recomendação e as estrelas de uma resenha
também não são o mesmo alvo, nem equivalem automaticamente a NPS declarado.

## Interpretação e ameaças à validade

O **falso containment** cruza ausência de transferência com classificação
detratora inferida. É um sinal para investigar, não comprovação de que o
cliente desistiu ou de que o bot causou insatisfação. Esse cruzamento pode ser
feito por outras abordagens; não se reivindica exclusividade metodológica.

As principais ameaças são mudança de domínio (resenha e rede social não são
suporte), tradução e ruído dos rótulos, dependência entre produtos/autores,
atalhos do simulador, seleção histórica com consulta ao teste e proveniência
incompleta dos pesos antigos. Sem curvas comparáveis e manifestos históricos
não se conclui presença nem ausência de overfitting atual. A campanha de três
sementes por cabeça está **pendente de autenticação do Colab**, não concluída.

## O que a tese não promete

- Não mede diretamente o estado interno do cliente nem produz diagnóstico.
- Não atribui causalidade a palavras, tempo de espera ou contribuições do fusor.
- Não decide automaticamente sobre clientes e **não pontua atendentes** —
  ver [Conformidade](conformidade.md).
- Não transforma contenção em qualidade, nem ausência de dado em insatisfação.
- Não apresenta resultados históricos ou testes sintéticos como validação de
  produção. O [Cartão do modelo](cartao-do-modelo.md) preserva as medições
  históricas e explicita seus limites.
