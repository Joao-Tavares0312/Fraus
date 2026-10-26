# Desenvolvimento local

Este percurso prepara **uma instalação de desenvolvimento**, não um deploy.
Leia as [invariantes](invariantes.md) antes de alterar regras e use a
[arquitetura](arquitetura.md) para localizar a responsabilidade de cada peça.
O Fraus estima satisfação sem LLM em runtime: a predição usa modelos locais,
em CPU, sem chamada de rede no caminho de inferência.

## Ambiente Python e extras

Use Python **3.11** e `uv`, na raiz do repositório. Para desenvolvimento com
Torch, testes e documentação:

```bash
uv sync --extra dev --extra torch --extra docs
```

Os extras são explícitos: um `uv sync` sem eles pode remover ferramentas que
você já estava usando. Preserve os extras necessários em cada sincronização.
O grupo `dev` instala pytest/httpx; `torch` instala o executor Torch; `docs`
instala MkDocs Material, mkdocstrings e a ferramenta de PDF.

Para trabalhar no treinamento instrumentado, acrescente `treino`:

```bash
uv sync --extra dev --extra torch --extra treino --extra docs
```

Esse extra inclui **accelerate**, exigido pelo `Trainer`, além das dependências
de treino/exportação. Não é dependência necessária à imagem de inferência.
As receitas, os notebooks e o protocolo de seleção/avaliação estão em
[Treinamento](treinamento.md) e [Generalização e evidências](generalizacao.md).
Ter os notebooks prontos não significa que uma campanha foi executada.

A alternativa de inferência sem Torch é ONNX:

```bash
uv sync --extra dev --extra onnx --extra docs
```

Declare `FRAUS_BACKEND=onnx` ao iniciar a API. Os grafos exportados são outros
artefatos, em `modelos-onnx/`; o backend não é escolhido pela presença de
arquivos e não recua silenciosamente para Torch. Conversão é uma tarefa
separada, com extra `conversao`: consulte [Encolher os modelos](encolhimento.md)
antes de exportar ou quantizar.

## Artefatos obrigatórios

Instalar dependências **não baixa os modelos treinados do Fraus**. O motor
padrão exige os três classificadores — satisfação, emoção e ironia — e um
fusor compatível. No backend Torch, os caminhos de fábrica são:

```text
modelos/
├── bertimbau-satisfacao/
├── bertimbau-emocao/
├── bertimbau-ironia/
└── fusor.joblib
```

Cada cabeça precisa de seus pesos, configuração e tokenizador. Com ONNX, as
três cabeças são lidas dos diretórios homônimos em `modelos-onnx/`; o fusor
continua em `modelos/fusor.joblib`. Use artefatos de origem autorizada e
rastreável; não carregue um pickle/joblib desconhecido para inspecioná-lo.

O fusor exige **39 features de sete famílias**, com as transformações vigentes
(incluindo `log1p` nas quatro features de espera). Um fusor antigo treinado em
segundos crus é recusado, mesmo que tenha 39 entradas. **Não contorne a recusa**
para fazer a UI funcionar. A ironia continua obrigatória na leitura por
mensagem, embora não pontue no vetor do fusor.

A aplicação cria banco e rotas antes de carregar o motor, que é preguiçoso.
Portanto, **a API subir ou responder à saúde não prova que consegue inferir**:
a primeira operação que exige modelos carrega os artefatos e falha
explicitamente se faltarem ou forem incompatíveis. Não há score parcial,
modelo dublê automático na API real nem valores zerados para preencher falta
de dados. Consulte [Cartão do modelo](cartao-do-modelo.md) para a procedência e
os limites das métricas; uma métrica histórica não identifica o checkpoint
que uma implantação serve hoje.

## Executar API e dashboard

Na **raiz**, inicie a API real em uma porta própria:

```bash
uv run python -m uvicorn fraus.api.main:app --host 127.0.0.1 --port 8001 --reload --reload-dir fraus
```

Ou, com os grafos ONNX preparados:

```bash
FRAUS_BACKEND=onnx uv run python -m uvicorn fraus.api.main:app --host 127.0.0.1 --port 8001 --reload --reload-dir fraus
```

Sem uma conexão PostgreSQL explicitamente configurada, o banco local é SQLite.
Use banco e dados descartáveis para experimentos; não a conexão de produção.
Configuração de credenciais pertence ao ambiente autorizado da instalação,
nunca ao Markdown, ao Git ou a variáveis públicas do navegador. Não desative
a autenticação nem publique um túnel para contornar um erro local.

Em **outro terminal**, entre em `dashboard/`:

```bash
cd dashboard
npm ci
FRAUS_API_URL=http://127.0.0.1:8001 npm run dev
```

A interface abre normalmente em `http://127.0.0.1:3000`. Não há `package.json`
na raiz. `FRAUS_API_URL` é configuração **do servidor Next**, que encaminha as
requisições e mantém a credencial fora do bundle do navegador. O padrão é
porta 8000; o exemplo acima muda explicitamente para a porta 8001 usada na
API real. Use o fluxo de acesso da instalação, sem copiar tokens para código
ou para esta documentação.

### Demonstração não é validação do motor

Para demonstração isolada existe, na raiz:

```bash
uv run python scripts/api_demo.py
```

O script usa banco temporário e conversas sintéticas na porta 8000; pode usar
motor real quando houver artefatos ou **dublê explicitamente identificado**.
Nunca é o comando de produção. Gravação analítica exige motor real; uma
interação bem-sucedida com dublê só exercita a interface. Mantenha essa instância
separada da API real e ajuste o destino da dashboard conscientemente.

## Verificar uma alteração

Os comandos abaixo são instruções para quem verifica a mudança; **não são
resultados de execução desta página**. Na raiz:

```bash
uv run pytest -q
```

A rodada padrão exclui testes marcados como lentos. Ao alterar o gerador de
corpus, execute também a seleção correspondente:

```bash
uv run pytest -q -m lento
```

Dentro de `dashboard/`:

```bash
npm test
npm run lint
npm run build
```

Teste os contratos relevantes, não só a compilação: ausência de sinal permanece
nula; score, nota e categoria vêm do servidor; leitura sem horário não grava;
controle administrativo não ganha permissão pela aparência da tela. Para
mudanças visuais, confira teclado, celular, temas e movimento reduzido seguindo
o [design da interface](design.md). Um teste com fixture precisa ser identificado
como tal e não substitui a verificação de inferência real.

## Trabalhar na documentação existente

O projeto usa **um site MkDocs Material**, com três percursos de leitura. Não
há uma segunda cópia dos textos para cada público. Mermaid, CSS e a referência
extraída de docstrings continuam na mesma infraestrutura.

Na raiz, preserve os extras e gere a cópia do design antes do build:

```bash
uv run python scripts/reunir_docs.py
uv run mkdocs serve -a localhost:8010
uv run mkdocs build --strict
uv run mkdocs build --strict --config-file mkdocs-publico.yml
```

`docs/design.md` é **gerado** a partir de `dashboard/DESIGN.md`: altere a fonte,
nunca a cópia. A comparação histórica permanece em
[Antes e depois da interface](redesign-2026-10-16.md).

O repositório é privado e o site é público. `mkdocs.yml` constrói a documentação
interna; `mkdocs-publico.yml` exclui notas, auditorias, handoff e roteiros
internos. **`not_in_nav` não impede publicação**. Preserve `exclude_docs` e
`show_source: false` no recorte público: docstrings podem ser apresentadas, mas
os corpos das funções não devem ser embutidos no HTML público. Manifestos
privados, relatórios brutos e corpora de experimentos ficam fora do site.

O PDF herda o recorte público e mantém essa mesma fronteira. Precisa das
bibliotecas nativas usadas pelo WeasyPrint (GTK/Pango/Cairo) e de Chromium
para desenhar Mermaid, por isso seu build é separado, no CI Linux.
`FRAUS_CHROME_PDF` seleciona o executável: o padrão local é `chromium`;
o workflow usa `google-chrome`.

```bash
uv run mkdocs build --config-file mkdocs-pdf.yml -d site-pdf
```

`pdf_event_hook.py` transforma os diagramas em imagens SVG antes do
WeasyPrint; diagrama ausente ou com erro interrompe o PDF. A biblioteca
Mermaid 11.17.2 tem SHA-256 fixado e é baixada no primeiro build para
`~/.cache/fraus/`. Isso ocorre na documentação, não na inferência do Fraus.
O site continua usando a integração Mermaid do Material.

Publicar dashboard, API ou documentação é outra operação. Estes comandos locais
não promovem pesos nem provam qual checkpoint está em produção.

## Contratos para consultar antes de editar

- [Invariantes](invariantes.md): classes, timestamps, ausência de sinal,
  derivação no servidor e contrato de features.
- [Arquitetura](arquitetura.md): mensagem, conversa, sinais, fusor e limites da
  explicação; [modelo canônico](referencia/modelos.md) e
  [sinais](referencia/sinais.md) detalham os componentes.
- [Fusor](referencia/fusor.md), [indicadores](referencia/indicadores.md) e
  [evidência e deriva](referencia/diagnostico.md): referência das regras no
  código, sem criar outra implementação no cliente.
- [Guia de uso](guia-de-uso.md) e [Integração com o Tars](integracao-tars.md):
  contratos visíveis a quem opera arquivos, períodos e fontes.
- [Treinamento](treinamento.md), [generalização](generalizacao.md) e
  [limitações](limitacoes.md): separar receita, medição, hipótese e evidência
  indisponível. Nenhum experimento candidato deve substituir o artefato ativo
  sem uma decisão de promoção separada.
