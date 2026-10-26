---
hide:
  - navigation
  - toc
---

<div class="fx-hero" markdown>
<div class="fx-orbe" aria-hidden="true"><i></i><i></i><i></i></div>

<p class="fx-hero__rotulo">Fraus — documentação</p>

# O cliente <em>diz</em>. O Fraus <span>estima</span>.

<p class="fx-hero__sub">Ferramenta que lê atendimento por chatbot e estima satisfação
<strong>sem perguntar nada ao cliente</strong>. Um encerramento como
<em>"ok, obrigado 🙂"</em> não prova satisfação nem insatisfação: o contexto
traz sinais, não acesso ao estado real de quem escreveu.</p>

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

!!! warning "NPS inferido, não declarado"
    O NPS do Fraus **não é perguntado**: ele é derivado do texto do
    atendimento. Toda exibição carrega a etiqueta de estimativa, e apresentá-lo
    como NPS declarado seria falso. Ver [Limitações](limitacoes.md) e
    [Conformidade](conformidade.md).

## Escolha seu percurso

<div class="fx-cards" markdown>

-   **[Banca e metodologia — a tese](tese.md)**

    Entenda a pergunta, as unidades de análise e o que sustenta as conclusões.
    Siga por [arquitetura](arquitetura.md), [treinamento](treinamento.md),
    [generalização e evidências](generalizacao.md) e
    [cartão do modelo](cartao-do-modelo.md). Leia os limites antes de
    interpretar uma métrica como prova em atendimentos reais.

-   **[Usuários — guia de uso](guia-de-uso.md)**

    Leve um arquivo à análise, confira a gravação e encontre os atendimentos
    no período certo. Aprenda a distinguir estimativa, ausência de sinal e
    indisponibilidade. Para receber conversas automaticamente, siga a
    [integração com o Tars](integracao-tars.md).

-   **[Desenvolvedores — desenvolvimento local](desenvolvimento.md)**

    Prepare os extras e artefatos, execute API e dashboard e encontre os
    comandos de testes e documentação. Comece pelas
    [invariantes](invariantes.md); consulte o [design](design.md) e a
    [referência de código](referencia/modelos.md) antes de alterar contratos.

</div>

## Sem LLM em runtime

Três BERTimbau fine-tunados (satisfação, emoção, ironia) e um fusor
`LogisticRegression` sobre 39 features de sete famílias de sinal. Inferência
local, em CPU, sem nenhuma chamada de rede no caminho de predição.

Isso é **requisito**, não otimização. As probabilidades por mensagem e a
decomposição do fusor permitem inspecionar a leitura do sistema; não são
ativações internas do Transformer nem prova causal sobre palavras.

## Baixar

<!-- Link em HTML cru de proposito: o PDF e gerado SO no build de publicacao
     (`mkdocs-pdf.yml`, que roda no Linux do CI), entao ele nao existe entre os
     arquivos de documentacao que o MkDocs valida. Em Markdown, o modo estrito
     abortaria o build local com "target is not found" -- e a previa local
     precisa funcionar. -->
O PDF com o site inteiro está em <a href="pdf/fraus.pdf">pdf/fraus.pdf</a>,
gerado no mesmo build que publica estas páginas — então ele nunca está mais
velho que o site.
