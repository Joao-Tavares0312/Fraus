---
hide:
  - navigation
  - toc
---

<div class="fx-hero" markdown>
<div class="fx-orbe" aria-hidden="true"><i></i><i></i><i></i></div>

<p class="fx-hero__rotulo">Fraus — documentação</p>

# O cliente <em>diz</em> uma coisa. O texto <span>mede</span> outra.

<p class="fx-hero__sub">Ferramenta que lê atendimento por chatbot e estima satisfação
<strong>sem perguntar nada ao cliente</strong>. O caso que uma pesquisa de NPS
declarada não captura: quem escreve <em>"ok, obrigado 🙂"</em> e sai
insatisfeito não responde pesquisa — e é ele que o sistema precisa enxergar.</p>

<div class="fx-hero__acoes" markdown>
[Ler as invariantes](invariantes.md){ .md-button .md-button--primary }
[A tese](tese.md){ .md-button }
[Arquitetura](arquitetura.md){ .md-button }
</div>
</div>

<div class="fx-fatos">
<div class="fx-fato"><small>Famílias de sinal</small><svg viewBox="0 0 146 108" role="img" aria-label="07 famílias de sinal"><polygon transform="translate(0 0)" points="14,4 54,4 60,10 54,16 14,16 8,10" fill="currentColor" opacity="1"/><polygon transform="translate(0 0)" points="62,12 68,18 68,44 62,50 56,44 56,18" fill="currentColor" opacity="1"/><polygon transform="translate(0 0)" points="62,58 68,64 68,90 62,96 56,90 56,64" fill="currentColor" opacity="1"/><polygon transform="translate(0 0)" points="14,92 54,92 60,98 54,104 14,104 8,98" fill="currentColor" opacity="1"/><polygon transform="translate(0 0)" points="6,58 12,64 12,90 6,96 0,90 0,64" fill="currentColor" opacity="1"/><polygon transform="translate(0 0)" points="6,12 12,18 12,44 6,50 0,44 0,18" fill="currentColor" opacity="1"/><polygon transform="translate(0 0)" points="14,48 54,48 60,54 54,60 14,60 8,54" fill="currentColor" opacity="0.1"/><polygon transform="translate(78 0)" points="14,4 54,4 60,10 54,16 14,16 8,10" fill="currentColor" opacity="1"/><polygon transform="translate(78 0)" points="62,12 68,18 68,44 62,50 56,44 56,18" fill="currentColor" opacity="1"/><polygon transform="translate(78 0)" points="62,58 68,64 68,90 62,96 56,90 56,64" fill="currentColor" opacity="1"/><polygon transform="translate(78 0)" points="14,92 54,92 60,98 54,104 14,104 8,98" fill="currentColor" opacity="0.1"/><polygon transform="translate(78 0)" points="6,58 12,64 12,90 6,96 0,90 0,64" fill="currentColor" opacity="0.1"/><polygon transform="translate(78 0)" points="6,12 12,18 12,44 6,50 0,44 0,18" fill="currentColor" opacity="0.1"/><polygon transform="translate(78 0)" points="14,48 54,48 60,54 54,60 14,60 8,54" fill="currentColor" opacity="0.1"/></svg></div>
<div class="fx-fato"><small>Features no fusor</small><svg viewBox="0 0 146 108" role="img" aria-label="39 features no fusor"><polygon transform="translate(0 0)" points="14,4 54,4 60,10 54,16 14,16 8,10" fill="currentColor" opacity="1"/><polygon transform="translate(0 0)" points="62,12 68,18 68,44 62,50 56,44 56,18" fill="currentColor" opacity="1"/><polygon transform="translate(0 0)" points="62,58 68,64 68,90 62,96 56,90 56,64" fill="currentColor" opacity="1"/><polygon transform="translate(0 0)" points="14,92 54,92 60,98 54,104 14,104 8,98" fill="currentColor" opacity="1"/><polygon transform="translate(0 0)" points="6,58 12,64 12,90 6,96 0,90 0,64" fill="currentColor" opacity="0.1"/><polygon transform="translate(0 0)" points="6,12 12,18 12,44 6,50 0,44 0,18" fill="currentColor" opacity="0.1"/><polygon transform="translate(0 0)" points="14,48 54,48 60,54 54,60 14,60 8,54" fill="currentColor" opacity="1"/><polygon transform="translate(78 0)" points="14,4 54,4 60,10 54,16 14,16 8,10" fill="currentColor" opacity="1"/><polygon transform="translate(78 0)" points="62,12 68,18 68,44 62,50 56,44 56,18" fill="currentColor" opacity="1"/><polygon transform="translate(78 0)" points="62,58 68,64 68,90 62,96 56,90 56,64" fill="currentColor" opacity="1"/><polygon transform="translate(78 0)" points="14,92 54,92 60,98 54,104 14,104 8,98" fill="currentColor" opacity="1"/><polygon transform="translate(78 0)" points="6,58 12,64 12,90 6,96 0,90 0,64" fill="currentColor" opacity="0.1"/><polygon transform="translate(78 0)" points="6,12 12,18 12,44 6,50 0,44 0,18" fill="currentColor" opacity="1"/><polygon transform="translate(78 0)" points="14,48 54,48 60,54 54,60 14,60 8,54" fill="currentColor" opacity="1"/></svg></div>
<div class="fx-fato"><small>BERTimbau fine-tunados</small><svg viewBox="0 0 146 108" role="img" aria-label="3 BERTimbau"><polygon transform="translate(0 0)" points="14,4 54,4 60,10 54,16 14,16 8,10" fill="currentColor" opacity="1"/><polygon transform="translate(0 0)" points="62,12 68,18 68,44 62,50 56,44 56,18" fill="currentColor" opacity="1"/><polygon transform="translate(0 0)" points="62,58 68,64 68,90 62,96 56,90 56,64" fill="currentColor" opacity="1"/><polygon transform="translate(0 0)" points="14,92 54,92 60,98 54,104 14,104 8,98" fill="currentColor" opacity="1"/><polygon transform="translate(0 0)" points="6,58 12,64 12,90 6,96 0,90 0,64" fill="currentColor" opacity="1"/><polygon transform="translate(0 0)" points="6,12 12,18 12,44 6,50 0,44 0,18" fill="currentColor" opacity="1"/><polygon transform="translate(0 0)" points="14,48 54,48 60,54 54,60 14,60 8,54" fill="currentColor" opacity="0.1"/><polygon transform="translate(78 0)" points="14,4 54,4 60,10 54,16 14,16 8,10" fill="currentColor" opacity="1"/><polygon transform="translate(78 0)" points="62,12 68,18 68,44 62,50 56,44 56,18" fill="currentColor" opacity="1"/><polygon transform="translate(78 0)" points="62,58 68,64 68,90 62,96 56,90 56,64" fill="currentColor" opacity="1"/><polygon transform="translate(78 0)" points="14,92 54,92 60,98 54,104 14,104 8,98" fill="currentColor" opacity="1"/><polygon transform="translate(78 0)" points="6,58 12,64 12,90 6,96 0,90 0,64" fill="currentColor" opacity="0.1"/><polygon transform="translate(78 0)" points="6,12 12,18 12,44 6,50 0,44 0,18" fill="currentColor" opacity="0.1"/><polygon transform="translate(78 0)" points="14,48 54,48 60,54 54,60 14,60 8,54" fill="currentColor" opacity="1"/></svg></div>
<div class="fx-fato"><small>LLMs na inferência</small><svg viewBox="0 0 146 108" role="img" aria-label="0 LLMs na inferência"><polygon transform="translate(0 0)" points="14,4 54,4 60,10 54,16 14,16 8,10" fill="currentColor" opacity="1"/><polygon transform="translate(0 0)" points="62,12 68,18 68,44 62,50 56,44 56,18" fill="currentColor" opacity="1"/><polygon transform="translate(0 0)" points="62,58 68,64 68,90 62,96 56,90 56,64" fill="currentColor" opacity="1"/><polygon transform="translate(0 0)" points="14,92 54,92 60,98 54,104 14,104 8,98" fill="currentColor" opacity="1"/><polygon transform="translate(0 0)" points="6,58 12,64 12,90 6,96 0,90 0,64" fill="currentColor" opacity="1"/><polygon transform="translate(0 0)" points="6,12 12,18 12,44 6,50 0,44 0,18" fill="currentColor" opacity="1"/><polygon transform="translate(0 0)" points="14,48 54,48 60,54 54,60 14,60 8,54" fill="currentColor" opacity="0.1"/><polygon transform="translate(78 0)" points="14,4 54,4 60,10 54,16 14,16 8,10" fill="currentColor" opacity="1"/><polygon transform="translate(78 0)" points="62,12 68,18 68,44 62,50 56,44 56,18" fill="currentColor" opacity="1"/><polygon transform="translate(78 0)" points="62,58 68,64 68,90 62,96 56,90 56,64" fill="currentColor" opacity="1"/><polygon transform="translate(78 0)" points="14,92 54,92 60,98 54,104 14,104 8,98" fill="currentColor" opacity="1"/><polygon transform="translate(78 0)" points="6,58 12,64 12,90 6,96 0,90 0,64" fill="currentColor" opacity="1"/><polygon transform="translate(78 0)" points="6,12 12,18 12,44 6,50 0,44 0,18" fill="currentColor" opacity="1"/><polygon transform="translate(78 0)" points="14,48 54,48 60,54 54,60 14,60 8,54" fill="currentColor" opacity="0.1"/></svg></div>
</div>

!!! warning "Todo número aqui é inferido"
    O NPS do Fraus **não é perguntado**: ele é derivado do texto do
    atendimento. Toda exibição carrega a etiqueta de estimativa, e apresentá-lo
    como NPS declarado seria falso. Ver [Limitações](limitacoes.md) e
    [Conformidade](conformidade.md).

## O que ler primeiro

<div class="fx-cards" markdown>

-   **[A tese](tese.md)**

    A aposta do projeto e o caso que ela cobre.

-   **[As invariantes](invariantes.md)**

    Para mexer no código: comece por aqui, sem exceção.

-   **[Arquitetura](arquitetura.md)**

    Como as peças se ligam, do adaptador de ingestão ao dashboard.

-   **[Treinamento](treinamento.md)**

    Como os modelos foram treinados e o que foi medido.

-   **[Design da interface](design.md)**

    O sistema visual: LED, régua dito/medido e as regras.

-   **[Limitações](limitacoes.md)**

    O que o sistema **não** sabe, dito sem rodeio.

-   **[Conformidade](conformidade.md)**

    O que o produto lê e o que ele se recusa a fazer.

-   **[Encolher os modelos](encolhimento.md)**

    Como o runtime ficou pequeno sem trocar o modelo, medido.

-   **[Cartão do modelo](cartao-do-modelo.md)**

    Desempenho por fatia, sem esconder a fatia ruim.

</div>

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
