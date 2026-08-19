# Grafo da memória — design

**Data:** 2026-08-19
**Escopo:** uma rota nova na API (`GET /grafo`), um módulo puro novo
(`fraus/grafo.py`) e uma página nova na dashboard (`/grafo`).

---

## 1. O problema

A dashboard mostra o Fraus por **agregado** (indicadores, série temporal,
léxico por classe) e por **item** (a ficha de um atendimento). Não há nenhuma
tela que mostre a **estrutura**: o que está ligado a quê, e por onde um número
chegou onde chegou.

Para o usuário final e para a banca, a pergunta que hoje não tem tela é
*"o que esse sistema sabe, e como esse conhecimento se conecta?"*. A resposta
natural para isso é um grafo — a mesma leitura que o graph view do Obsidian
entrega sobre um vault.

**Cuidado de nomenclatura:** o Fraus não tem LLM em runtime e não tem memória
conversacional. "Memória" aqui significa o conjunto de coisas que o sistema
guarda e usa: o léxico que ele ativou, as conversas que ingeriu, o que o fusor
aprendeu, e de onde cada dado veio.

## 2. As três camadas

| Camada | Tipos de nó | Arestas |
|---|---|---|
| **Léxico** (o que o modelo sabe) | `termo`, `emoji`, `feature` | `conversa→termo`, `conversa→emoji`, `feature→categoria` |
| **Domínio** (o que foi atendido) | `conversa`, `categoria`, `canal`, `desfecho` | `conversa→categoria`, `conversa→canal`, `conversa→desfecho` |
| **Proveniência** (de onde veio) | `fonte`, `importacao`, `configuracao` | `fonte→canal` — e nada mais (ver §2.0) |

O nó `conversa` é a **espinha**: ele é o único tipo que aparece nas três
camadas, e é por isso que o grafo unificado se sustenta. Sem ele seriam três
nuvens desconectadas, e aí três abas separadas seriam a escolha certa.

### 2.0 O limite da proveniência, e por que ele fica visível

O schema **não permite** ligar uma importação às conversas que ela criou:
`importacoes` guarda `(ocorrida_em, arquivo, aceitas, rejeitadas, motivos)` e
nenhuma coluna aponta para `conversas`. `fontes_integracao` também não tem
vínculo direto — só o campo `canal` em comum.

Então a proveniência liga **só pelo que existe**: `fonte→canal`, por igualdade
de canal — `fontes_integracao` tem a coluna `canal`, então a aresta é
derivável. Ela é honesta sobre a força do vínculo (`tipo: "alimenta_canal"`) e
não finge granularidade por conversa que o banco não tem.

**A importação não liga em nada.** `importacoes` não tem coluna `canal`, e um
arquivo CSV não declara origem: não há igualdade a fazer. Uma versão anterior
desta spec afirmava `importacao→canal` "por igualdade de canal", e a
implementação que a seguiu ligou cada importação a **todos** os canais do
recorte — arestas inventadas, em produto cartesiano, afirmando que um arquivo
alimentou um canal que ninguém disse que ele alimentou. O erro foi pego na
revisão final e o texto está corrigido aqui para não reincidir.

O nó `importacao` existe e fica **solto** na camada. Isso é deliberado: num
graph view, um nó desconectado **é** a informação — ele mostra, sem legenda,
que a proveniência por importação não é rastreável no schema de hoje. Um fio
falso esconderia essa lacuna; o vazio a declara.

**Isto não vira migração de schema neste escopo.** Adicionar
`conversas.importacao_id` é uma mudança de modelo de dados com backfill, e
misturá-la numa entrega de visualização é como se perde o controle das duas.
Fica registrado aqui como consequência descoberta, para virar decisão própria
depois.

### 2.0.1 Nada de `emocao` no grafo

Emoção por conversa sai do `ClassificadorEmocao` — é **inferência**, e a rota
não toca no `Motor` (§3.3.3). Um nó `emocao` exigiria rodar o modelo por
conversa dentro de uma requisição de página, o mesmo erro de §2.1.

Termo e emoji ficam porque são extração **textual pura**
(`contar_palavras`, `emojis_com_posicao`) — nenhum modelo carregado.

Pelo mesmo motivo não existe nó `modelo` ligado a conversa: não há registro de
qual versão de modelo pontuou qual conversa. Um nó `modelo` desconectado seria
decoração.

### 2.1 Por que `feature` liga em `categoria` e não em `conversa`

`contribuicoes` **não é persistida**. `Banco.todas()` devolve
`(conversa, score)`; `GET /conversas/{id}` recalcula a atribuição via `Motor`
na leitura. Uma aresta `feature→conversa` por conversa do recorte exigiria
rodar o BERTimbau N vezes dentro de uma requisição de página.

Então a aresta é `feature→categoria`, com peso derivado dos **coeficientes do
fusor** — globais, já em disco, custo zero. Semanticamente isso é o certo: o
grafo responde *"o que o modelo aprendeu que caracteriza um detrator"*, e a
atribuição por conversa continua sendo a `PainelContribuicoes` no detalhe do
atendimento. Duas perguntas diferentes, duas telas.

Se o fusor não estiver treinado, `contribuicoes` volta zerada por construção
(`fraus/fusor.py`) — nesse caso a camada omite as arestas `feature→categoria`
em vez de desenhar dezesseis fios de peso 0.

### 2.2 O teto do léxico

O SentiLex tem **79.190 termos**. O grafo mostra apenas os termos
**efetivamente ativados** nas conversas do recorte, ordenados por frequência,
cortados em `teto_termos` (default 120).

O corte é **declarado**, nunca silencioso: `meta` devolve
`{ termos_totais, termos_exibidos, truncado }` e a página exibe isso na régua
inferior. Um grafo que trunca calado afirma visualmente que aquilo é tudo o
que o sistema sabe — o que é falso.

A extração usa `contar_palavras` e `emojis_com_posicao`, as mesmas funções do
`lexico_por_classe` e do sinal de emoji, para a contagem não divergir do
motor. Só a fala do **cliente** conta; o texto do bot é roteiro.

## 3. Backend

### 3.1 `fraus/grafo.py` — módulo puro

Irmão de `fraus/indicadores.py`: nenhum import de FastAPI. Assinatura:

```python
def montar_grafo(
    registros: list[tuple[Conversa, float | None]],
    faixas: dict,
    *,
    camadas: frozenset[str] = TODAS_AS_CAMADAS,
    teto_termos: int = 120,
    coeficientes: dict[str, float] | None = None,
    proveniencia: dict | None = None,
) -> dict:
```

Devolve `{"nos": [...], "arestas": [...], "meta": {...}}`.

**Nó:**
```json
{
  "id": "conversa:42",
  "tipo": "conversa",
  "camada": "dominio",
  "rotulo": "Atendimento #42",
  "grau": 7,
  "score": 63.0,
  "nota": 6,
  "categoria": "detrator",
  "sem_sinal": false
}
```
`score`/`nota`/`categoria` só existem em nós `conversa`. Nós de outros tipos
não carregam campo de veredito nenhum.

**Aresta:**
```json
{ "de": "conversa:42", "para": "termo:demora", "tipo": "ativou", "peso": 3 }
```

**Complexidade:** uma passada sobre `registros` + `Counter` para os termos.
Mesma ordem do `/lexico` que já existe. Nenhuma chamada ao `Motor`, nenhuma
inferência — a rota não carrega modelo.

### 3.2 `fraus/api/rotas/grafo.py`

```
GET /grafo?de=&ate=&camadas=lexico,dominio,proveniencia&teto_termos=120
```

Mesmo padrão dos outros routers: `APIRouter`, `Depends(obter_contexto)`,
`ctx.registros_do_recorte(de, ate)` (recorte com as duas pontas inclusivas,
validado por `recorte_ou_400`). Registrado em `fraus/api/main.py` junto dos
demais.

- `camadas` ausente = todas. Valor desconhecido na lista → **400**, não
  ignorado em silêncio (ignorar devolveria um grafo diferente do pedido sem
  avisar).
- `teto_termos` limitado a `TETO_TERMOS_GRAFO = 500`. Acima disso → 400. O
  teto existe para o cliente não conseguir pedir uma resposta de 80k nós.
- Sem conversas no recorte: **200** com `nos: []` — vazio não é erro.

A rota herda o middleware de acesso já existente; não introduz autenticação
própria.

### 3.3 Invariantes que este código carrega

1. **Ausência de dado não é insatisfação.** `score: None` → o nó vai com
   `score: null` e `sem_sinal: true`. Nunca 0 — não no valor, não no raio, não
   no peso de aresta, não no agregado do `meta`.
2. **Score, nota e categoria são derivados no servidor.** O nó já chega com
   `nota` e `categoria` prontas; o cliente não conhece faixa de NPS. Duplicar
   a regra em TypeScript já divergiu nas fronteiras 6/7 e 8/9.
3. **Sem LLM, sem rede, sem inferência.** A rota lê o banco e conta. Se ela
   algum dia precisar do `Motor`, o desenho está errado.

## 4. Frontend

### 4.1 Biblioteca

**`react-force-graph-2d`** (canvas 2D, MIT, 59 KB gzip medido).

Alternativas avaliadas e por que caíram:

| Lib | gzip | Motivo da recusa |
|---|---|---|
| sigma.js + graphology | 40 KB | menor e escala mais (WebGL), mas formas fora do padrão exigem escrever render program — e a cabeça vazada é requisito, não enfeite |
| d3-force puro | 22 KB | mais leve; custo é reimplementar zoom/drag/hit-testing à mão |
| @xyflow/react | 58 KB | renderiza em DOM: 5k nós = 5k elementos |
| cytoscape | 134 KB | peso sem ganho para este caso |
| reagraph / @antv/g6 | 383 / 416 KB | obesos; reagraph arrasta three.js |
| @cosmograph/cosmos | 200 KB | licença **CC-BY-NC-4.0** e arrasta `@supabase/supabase-js` |

O decisor foi `nodeCanvasObject`: ele entrega o `CanvasRenderingContext2D`
cru, que é o que permite desenhar a notação do `DESIGN.md` em vez de aceitar
a bolinha padrão da lib.

Referência de implementação (leitura, não dependência):
`quartz-community/graph` (MIT, 808 linhas) — a lógica de vizinhança e os
parâmetros de força de lá são bons; o PixiJS que ele usa (246 KB) não entra.

### 4.2 Estrutura da página

```
dashboard/app/grafo/page.tsx          Server Component: busca e trata erro
dashboard/components/grafo/
  GrafoDaMemoria.tsx                  'use client' — dynamic(ssr:false)
  ReguaDeCamadas.tsx                  foco de camada + aviso de truncamento
  FichaDoNo.tsx                       painel lateral do nó selecionado
  desenho.ts                          nodeCanvasObject e paleta por tipo
```

`dynamic(..., { ssr: false })` **não é permitido** em Server Component no App
Router — daí a separação obrigatória entre `page.tsx` e o componente cliente.

A página segue o shell existente: `CabecalhoPagina`, `FiltroPeriodo`,
`export const dynamic = "force-dynamic"`, e entra na `NavegacaoLateral`.

### 4.3 Notação (o mundo *Pauta* aplicado ao canvas)

- **Cabeça vazada = `sem_sinal`.** Nó com `score: null` desenha só o contorno,
  oco. É a mesma forma que a `CabecasDeLeitura` já usa na linha do tempo: a
  regra de produto vira notação, não nota de rodapé.
- **Âmbar acima, azul abaixo.** Nós do *dito* (`termo`, `emoji`,
  `conversa`) em âmbar; nós do *medido* (`feature`, `categoria`, `desfecho`,
  `fonte`, `importacao`, `configuracao`) em azul. Paleta herdada dos
  tokens OKLCH existentes — o grafo não introduz cor nova.
- **Raio por grau, nunca por score.** Score vira preenchimento; tamanho é
  conectividade. Mapear score→tamanho faria o nó "sem sinal" encolher até
  sumir, que é violar a invariante por via visual.
- **Label só com zoom > 1.5.** Em milhares de nós, label sempre visível é
  mancha ilegível.

### 4.4 Interação

- **Hover** → acende a vizinhança; o resto cai para 15% de opacidade.
  Adjacência pré-computada num `Map<string, Set<string>>` (O(1) por hover).
- **Click** → centraliza, dá zoom e abre a `FichaDoNo`. Nó `conversa` traz
  link para `/atendimentos/{id}`: o grafo é porta de entrada, não beco.
- **Foco de camada** → `Todas | Léxico | Domínio | Proveniência`. Não troca de
  grafo nem re-simula: apaga as outras camadas para 8% de opacidade e
  re-enquadra. As pontes entre camadas continuam visíveis.
- **Período** → o `FiltroPeriodo` existente; muda a query, refaz o fetch.

### 4.5 Performance

- `cooldownTicks`: 60 acima de 1500 nós, 200 abaixo. `warmupTicks: 20`.
- `onEngineStop` → `zoomToFit(400, 40)`. A simulação **para** depois de
  assentar; nada de laço de física queimando CPU indefinidamente.
- `d3VelocityDecay: 0.3`, `charge.strength(-120).distanceMax(400)` — ajustado
  após a montagem via `useEffect`, porque `d3Force` só existe depois dela.

### 4.6 Acessibilidade e estados

- **Fallback DOM:** `<ul className="sr-only">` com cada nó como `<button>`
  navegável por teclado, disparando a mesma seleção. Canvas é opaco para
  leitor de tela; sem isso a tela é inacessível por construção.
- **Vazio:** o banco hoje tem 0 conversas. `EstadoVazio` com texto acionável
  ("nenhuma conversa analisada ainda — importe em /analisar"), não um canvas
  preto que parece defeito.
- **API fora:** o `AvisoApiFora` já existente cobre; a página não inventa
  tratamento próprio.
- **Truncado:** a régua inferior mostra `N termos ativados · M exibidos` com
  marcação de aviso quando `truncado`.

## 5. Testes

**Python (`tests/test_grafo.py`)** — módulo puro, sem subir servidor:
- conversa com `score: None` produz nó com `sem_sinal: true` e `score: null`,
  e não aparece como 0 em nenhum campo do `meta`;
- `teto_termos` corta por frequência e o `meta` reporta `truncado: true` com
  os totais corretos;
- `camadas` restrito não emite nó nem aresta das camadas excluídas;
- nenhuma aresta órfã: todo `de`/`para` existe em `nos`;
- fusor não treinado → nenhuma aresta `feature→categoria`;
- a camada de proveniência liga em `canal`, nunca em `conversa` (§2.0) — o
  teste falha se alguém "melhorar" isso inventando vínculo.

**Contrato da rota (`tests/test_api_grafo.py`)**, junto dos demais testes de
API: recorte inclusivo nas duas pontas, `camadas` inválida → 400,
`teto_termos` acima do limite → 400, recorte vazio → 200 com `nos: []`.

**Fora de escopo:** teste de render do canvas. O que é testável na tela é a
transformação de dados (adjacência, filtro de camada), não o pixel.

## 6. Fora de escopo

- Edição do grafo pela tela (é visualização, não editor).
- Persistir o grafo: ele é derivado do banco a cada requisição, como todos os
  agregados do Fraus.
- Mostrar o SentiLex completo (ver §2.2).
- Layout 3D / WebGL.
- Migração de schema para rastrear origem por conversa (§2.0) — decisão
  própria, não carona nesta entrega.
- Atribuição por conversa dentro do grafo (ver §2.1 — já existe no detalhe do
  atendimento).
