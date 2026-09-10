# Fraus

Ferramenta que lê atendimento por chatbot e **estima satisfação sem perguntar
nada ao cliente**.

A tese é o caso que uma pesquisa de NPS declarada não captura: o cliente que
escreve *"ok, obrigado 🙂"* e sai insatisfeito. Ele não responde pesquisa — e é
justamente ele que o sistema precisa enxergar.

!!! warning "Todo número aqui é inferido"
    O NPS do Fraus **não é perguntado**: ele é derivado do texto do
    atendimento. Toda exibição carrega a etiqueta de estimativa, e apresentá-lo
    como NPS declarado seria falso. Ver [Limitações](limitacoes.md) e
    [Conformidade](conformidade.md).

## O que ler primeiro

| Se você quer | Leia |
|---|---|
| entender a aposta do projeto | [A tese](tese.md) |
| **mexer no código** | [As invariantes](invariantes.md) — comece por aqui, sem exceção |
| saber como as peças se ligam | [Arquitetura](arquitetura.md) |
| saber como os modelos foram treinados | [Treinamento](treinamento.md) |
| entender a interface | [Design](design.md) |
| saber o que o sistema **não** sabe | [Limitações](limitacoes.md) |

## Sem LLM em runtime

Três BERTimbau fine-tunados (satisfação, emoção, ironia) e um fusor
`LogisticRegression` sobre 39 features de sete famílias de sinal. Inferência
local, em CPU, sem nenhuma chamada de rede no caminho de predição.

Isso é **requisito**, não otimização: o trabalho existe para demonstrar que dá
para medir isso com modelos pequenos e interpretáveis — coeficiente de regressão
logística responde *por que* um atendimento recebeu a nota, e floresta densa
não.

## Baixar

<!-- Link em HTML cru de proposito: o PDF e gerado SO no build de publicacao
     (`mkdocs-pdf.yml`, que roda no Linux do CI), entao ele nao existe entre os
     arquivos de documentacao que o MkDocs valida. Em Markdown, o modo estrito
     abortaria o build local com "target is not found" -- e a previa local
     precisa funcionar. -->
O PDF com o site inteiro está em <a href="pdf/fraus.pdf">pdf/fraus.pdf</a>,
gerado no mesmo build que publica estas páginas — então ele nunca está mais
velho que o site.
