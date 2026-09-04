# Hierarquia na ferramenta e cena na vitrine — plano de implementação

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dar à ferramenta uma hierarquia legível de longe e à vitrine uma cena
que acompanha a rolagem, sem trocar o mundo *Pauta* nem encostar na camada de
dado.

**Architecture:** Três camadas com dependência em um sentido só — vocabulário em
`lib/` (funções puras, testáveis em vitest), componentes de composição
(`Painel`, `Aparato`, `CabecaVazada`, `Atelier`) que consomem esse vocabulário
por parâmetro, e as telas, que não ganham regra própria de hierarquia. Quem
decide peso é o componente, pelo mesmo motivo que cor mora em token.

**Tech Stack:** Next.js 16 (Turbopack), React, TypeScript, Tailwind v4, tokens
OKLCH em `app/globals.css`, Motion, vitest (`environment: node`), pytest na raiz
para as guardas que atravessam a fronteira de linguagem.

**Spec:** `docs/superpowers/specs/2026-09-04-hierarquia-e-vitrine-design.md`

## Global Constraints

- **Identificadores e docstrings em português, sem acento nos nomes de símbolo**
  (`nivelDoPainel`, `cabeca_vazada`). Texto de interface leva acento normal.
- **Commits em português, sem acento**, no estilo `tipo(escopo): resumo`.
- **TDD**: teste que falha primeiro, implementação mínima, teste verde, commit.
- **Nada de dependência nova sem motivo declarado.** O vitest da dashboard roda
  `environment: node` e inclui só `lib/**/*.test.ts`. Montar componente exigiria
  jsdom e testing-library — **não faça isso neste plano**. Lógica que precisa de
  teste mora em `lib/`; o resto é verificado pelos gates e pelo olho.
- **Ausência de dado não é insatisfação.** `score: None` aparece como "sem
  sinal", nunca 0, em lugar nenhum. Procure `?? 0` e `|| 0` antes de commitar.
- **Score, nota e categoria são derivados no SERVIDOR.** Nenhum componente novo
  recalcula, arredonda ou reclassifica.
- **Categoria nunca é comunicada só por cor** — e a mesma disciplina vale para
  forma: a cabeça vazada sempre acompanha rótulo textual.
- **Nada que carrega dado é translúcido.** Gráfico, tabela, transcrição e régua
  desenham em superfície opaca.
- **`--primary` (o dourado da marca) nunca codifica valor.** Só ação primária,
  foco de teclado e o cursor de leitura.
- **Todo par de cor que carrega texto cruza AA (4,5:1)** por cálculo, nos dois
  temas. `npm run contraste` é o juiz; a espessura do vidro cede, o portão não.
- **Ciclo de verificação de cada tarefa que toca UI:** `npx tsc --noEmit`,
  `npm run lint`, `npm run build`, e — quando a tarefa tocar cor, opacidade ou
  o `Atelier` — `npm run pisos` e `npm run contraste`. **Nenhum dos cinco vê a
  tela**: conferir olhando, nos dois temas, numa tela cheia e numa vazia.

### Como levantar a tela para conferir

A API real não sobe hoje (contrato em 39 features, artefato em 38). Para
trabalho visual, use o motor dublê — os números são sintéticos e servem só para
forma e densidade:

```bash
# terminal 1 -- a porta 8000 pode estar ocupada; 8001 e o padrao deste plano
FRAUS_DEMO_DUBLE=1 uv run uvicorn --host 127.0.0.1 --port 8001 \
  --app-dir scripts api_demo:app

# terminal 2
cd dashboard && FRAUS_API_URL=http://127.0.0.1:8001 npm run dev
```

**Abra em `http://localhost:3000`, nunca em `http://127.0.0.1:3000`.** O Next 16
dev devolve 403 nos chunks para a origem `127.0.0.1`, e sem os chunks não há
hidratação: a página renderiza no servidor e nenhum `whileInView` dispara. O
sintoma é tela em branco, idêntico ao de um bug de animação.

---

## File Structure

| Caminho | Responsabilidade | Estado |
|---|---|---|
| `dashboard/lib/hierarquia.ts` | vocabulário de nível: nomes, classes e o mapa de dominante por tela | criar |
| `dashboard/lib/hierarquia.test.ts` | guarda do vocabulário e do mapa | criar |
| `dashboard/lib/cena.ts` | progresso de rolagem → intensidade de cada camada do ateliê | criar |
| `dashboard/lib/cena.test.ts` | guarda da curva e do teto de intensidade | criar |
| `dashboard/components/Painel.tsx` | ganha `nivel`; deixa de hospedar o aparato | modificar |
| `dashboard/components/Aparato.tsx` | ganha o modo "um por tela" | modificar |
| `dashboard/components/AparatoDaTela.tsx` | contexto que recolhe as ressalvas e as rende uma vez no pé | criar |
| `dashboard/components/CabecaVazada.tsx` | a notação de "sem sinal" da §1.1 | criar |
| `dashboard/components/FaixaIndicadores.tsx` | vira armadura: perde superfície própria | modificar |
| `dashboard/components/shell/Atelier.tsx` | camadas passam a ler o progresso da cena | modificar |
| `dashboard/app/dashboard/*/page.tsx` | declaram nível e montam o aparato da tela | modificar |
| `dashboard/app/page.tsx` | seções da LP recebem âncora visual própria | modificar |
| `dashboard/scripts/pisos.mjs` | pior caso vira trajetória, não ponto | modificar |
| `tests/test_derivacoes_dashboard.py` | guardas que atravessam a fronteira de linguagem | modificar |
| `dashboard/DESIGN.md` | as cinco emendas da §8 da spec | modificar |

---

## Ordem e dependências

```
Task 1 (vocabulario) ──> Task 2 (Painel) ──> Task 3 (aparato por tela)
                                          ├─> Task 5 (regua)
                                          ├─> Task 6 (telas declaram nivel)
                                          └─> Task 6b (estados do dominante)
Task 4 (cabeca vazada) ── independente
Task 7 (veredito do Modelo) ── depende de 2, 3 e 6b
Task 8 (lib/cena) ──> Task 9 (Atelier) ──> Task 10 (LP) ──> Task 11 (pisos)
Task 12 (DESIGN.md) ── por ultimo
```

As tarefas 4 e 8 não dependem de nada e podem ser feitas a qualquer momento.

**Task 6b depois da Task 5**: as duas mexem no mesmo bloco de render do
`Painel`, e a 6b envolve o que a 5 introduz. Fora de ordem, uma desfaz a outra.

**Task 11 obrigatoriamente depois da 9 e da 10**: medir piso antes de a cena
existir mede um ateliê que não é mais o vigente.

---

### Task 1: O vocabulário de hierarquia

**Files:**
- Create: `dashboard/lib/hierarquia.ts`
- Test: `dashboard/lib/hierarquia.test.ts`

**Interfaces:**
- Consumes: nada.
- Produces: `type Nivel = "dominante" | "apoio"`; `classesDoNivel(nivel: Nivel): string`; `const DOMINANTE_POR_TELA: Record<string, string>`; `dominanteDaTela(rota: string): string | null`.

- [ ] **Step 1: Write the failing test**

```ts
// dashboard/lib/hierarquia.test.ts
import { describe, expect, it } from "vitest";
import {
  DOMINANTE_POR_TELA,
  classesDoNivel,
  dominanteDaTela,
} from "./hierarquia";

describe("classesDoNivel", () => {
  it("da ao dominante uma superficie mais densa que a do apoio", () => {
    expect(classesDoNivel("dominante")).toContain("vidro");
    expect(classesDoNivel("apoio")).toContain("vidro-fino");
  });

  it("nao devolve a mesma coisa para os dois niveis", () => {
    expect(classesDoNivel("dominante")).not.toBe(classesDoNivel("apoio"));
  });
});

describe("dominanteDaTela", () => {
  it("nomeia um dominante para cada tela da ferramenta", () => {
    const rotas = [
      "/dashboard",
      "/dashboard/atendimentos",
      "/dashboard/modelo",
      "/dashboard/grafo",
      "/dashboard/integracoes",
      "/dashboard/configuracoes",
    ];
    for (const rota of rotas) {
      expect(dominanteDaTela(rota), rota).toBeTruthy();
    }
  });

  it("da UM dominante por tela, nunca dois", () => {
    // A tese da hierarquia: um sistema por tela responde a pergunta que
    // levou o analista ali. Dois dominantes e nenhum.
    const valores = Object.values(DOMINANTE_POR_TELA);
    expect(new Set(valores).size).toBe(valores.length);
  });

  it("devolve null para rota que nao e tela da ferramenta", () => {
    expect(dominanteDaTela("/")).toBeNull();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd dashboard && npx vitest run lib/hierarquia.test.ts`
Expected: FAIL — `Failed to resolve import "./hierarquia"`.

- [ ] **Step 3: Write minimal implementation**

```ts
// dashboard/lib/hierarquia.ts
/**
 * O VOCABULARIO DE HIERARQUIA.
 *
 * Ate 04/09/2026 todo painel usava a mesma superficie, o mesmo raio e o mesmo
 * espacamento: a pagina era uma pilha de blocos equivalentes, sem primario e
 * secundario legiveis de longe. A §2.2 do DESIGN.md ja pedia ritmo vertical
 * ("um sistema denso ganha o direito de um respiro depois") e a interface nao
 * executava.
 *
 * O peso mora AQUI, e nao na tela, pelo mesmo motivo que cor mora em token:
 * regra digitada de novo em outro lugar diverge. E a mesma disciplina da
 * invariante 4 do CLAUDE.md, que existe porque isso ja aconteceu neste
 * projeto -- duplicar a regra de faixa de NPS no TypeScript causou divergencia
 * de arredondamento nas fronteiras 6/7 e 8/9.
 *
 * NAO decide cor. Nivel e escala, superficie e espaco; cor continua sendo
 * dito/medido e categoria, que sao encoding e nao hierarquia.
 */

export type Nivel = "dominante" | "apoio";

/**
 * As tres espessuras de vidro ja existem desde 21/08/2026 (DESIGN.md §7) e
 * estavam sendo consumidas quase indistintamente. O denso NAO entra aqui: ele
 * existe para o conteudo atras SUMIR num menu suspenso, e usar isso como
 * hierarquia de pagina gastaria a espessura mais cara de CSS em decoracao.
 */
const CLASSES: Record<Nivel, string> = {
  dominante: "vidro p-4 sm:p-6",
  apoio: "vidro-fino p-4 sm:p-5",
};

export function classesDoNivel(nivel: Nivel): string {
  return CLASSES[nivel];
}

/**
 * QUAL sistema responde a pergunta que levou o analista a cada tela.
 *
 * O valor e um IDENTIFICADOR ESTAVEL, nao o titulo exibido. Guardar o titulo
 * seria fragil por construcao: varios paineis montam o titulo em tempo de
 * render porque ele carrega periodo ou contagem (`Atendimentos de ${rotulo}`,
 * `${n} nos, ${m} arestas`), e nenhuma string estatica casa com isso -- um
 * consumidor que comparasse titulo falharia em silencio em metade das telas.
 *
 * Quem MARCA o dominante e a propria tela, com `nivel="dominante"` no Painel.
 * Esta tabela documenta a intencao e da a guarda de "um por tela" algo para
 * conferir; ela nao e chave de busca.
 */
export const DOMINANTE_POR_TELA: Record<string, string> = {
  "/dashboard": "nps-x-latencia",
  "/dashboard/atendimentos": "tabela-de-atendimentos",
  // A tela Modelo abria pelo simulador e enterrava no meio o que o avaliador
  // precisa ler primeiro. O veredito sobe para dominante -- ver Task 7.
  "/dashboard/modelo": "veredito-do-modelo",
  "/dashboard/grafo": "canvas-do-grafo",
  "/dashboard/integracoes": "fontes",
  "/dashboard/configuracoes": "faixas-de-nps",
};

export function dominanteDaTela(rota: string): string | null {
  return DOMINANTE_POR_TELA[rota] ?? null;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd dashboard && npx vitest run lib/hierarquia.test.ts`
Expected: PASS, 4 testes.

- [ ] **Step 5: Commit**

```bash
git add dashboard/lib/hierarquia.ts dashboard/lib/hierarquia.test.ts
git commit -m "feat(dashboard): o vocabulario de hierarquia ganha um dono"
```

---

### Task 2: `Painel` passa a ter nível

**Files:**
- Modify: `dashboard/components/Painel.tsx`
- Test: `dashboard/lib/hierarquia.test.ts` (acréscimo)

**Interfaces:**
- Consumes: `classesDoNivel`, `Nivel` da Task 1.
- Produces: `Painel` aceita `nivel?: Nivel` (padrão `"apoio"`).

**Por que o padrão é `apoio` e não `dominante`:** painel que não declara nível
não pode virar o dominante por omissão — a tela passaria a ter dois. O padrão
seguro é o rebaixado.

- [ ] **Step 1: Write the failing test**

Acrescente a `dashboard/lib/hierarquia.test.ts`:

```ts
import { readFileSync } from "node:fs";

describe("Painel", () => {
  it("consome o vocabulario em vez de digitar a superficie de novo", () => {
    // Guarda de duplicacao: se alguem cravar `vidro-fino` no Painel, a regra
    // passa a existir em dois lugares e diverge no dia em que um dos dois for
    // corrigido -- que e exatamente como o Aparato nasceu (ver o cabecalho
    // dele).
    const fonte = readFileSync("components/Painel.tsx", "utf8");
    expect(fonte).toContain("classesDoNivel");
    expect(fonte).not.toMatch(/"[^"]*\bvidro(-fino)?\b[^"]*"/);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd dashboard && npx vitest run lib/hierarquia.test.ts`
Expected: FAIL — o `Painel` de hoje tem `"vidro especular chanfro …"` cravado e
não menciona `classesDoNivel`.

- [ ] **Step 3: Write minimal implementation**

Em `dashboard/components/Painel.tsx`, acrescente o import e o parâmetro, e troque
a montagem de classes. O resto do componente não muda nesta tarefa.

```tsx
import { classesDoNivel, type Nivel } from "@/lib/hierarquia";

export function Painel({
  titulo,
  legenda,
  acessorio,
  rodape,
  semPadding,
  /**
   * Peso do sistema na tela. O padrao e `apoio` de proposito: painel que nao
   * declara nivel nao pode virar dominante por omissao, senao a tela passa a
   * ter dois -- e duas respostas principais e nenhuma.
   */
  nivel = "apoio",
  className,
  children,
}: {
  titulo: string;
  legenda?: ReactNode;
  acessorio?: ReactNode;
  rodape?: ReactNode;
  semPadding?: boolean;
  nivel?: Nivel;
  className?: string;
  children: ReactNode;
}) {
```

E, na `className` do `motion.section`:

```tsx
      className={cn(
        "especular chanfro quebra-evitar min-w-0 overflow-hidden rounded-lg",
        classesDoNivel(nivel),
        className,
      )}
```

O título acompanha o nível:

```tsx
        <h2
          className={cn(
            "font-semibold tracking-tight text-foreground",
            nivel === "dominante" ? "text-base" : "text-sm",
          )}
        >
          {titulo}
        </h2>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd dashboard && npx vitest run lib/hierarquia.test.ts && npx tsc --noEmit && npm run lint && npm run build`
Expected: vitest PASS, tsc sem saída, lint limpo, build concluído.

- [ ] **Step 5: Conferir olhando**

Suba a dashboard (ver "Como levantar a tela") e abra `/dashboard` nos dois temas.
Nesta tarefa **nenhuma tela declara nível ainda**, então tudo deve aparecer como
`apoio`: mais leve que hoje, e uniformemente. Se algum painel sumir ou perder a
quina iluminada, a montagem de classes perdeu `especular` ou `chanfro`.

- [ ] **Step 6: Commit**

```bash
git add dashboard/components/Painel.tsx dashboard/lib/hierarquia.test.ts
git commit -m "feat(dashboard): o painel passa a ter nivel"
```

---

### Task 3: Um aparato por tela

**Files:**
- Create: `dashboard/components/AparatoDaTela.tsx`
- Modify: `dashboard/components/Painel.tsx`, `dashboard/components/FaixaIndicadores.tsx`

**Interfaces:**
- Consumes: `Aparato` (inalterado).
- Produces: `<ProvedorDeAparato>`, `<AparatoDaTela />`, `useRegistrarRessalva(titulo: string, conteudo: ReactNode)`.

**A regra que não pode ser quebrada:** os rótulos curtos `estimativa`,
`observado` e `sem sinal` **não são aparato** (DESIGN.md §4.1) e continuam
colados ao número, sempre visíveis. O que se consolida é a prosa de método.

- [ ] **Step 1: Write the failing test**

Acrescente a `dashboard/lib/hierarquia.test.ts`:

```ts
describe("aparato", () => {
  it("o Painel nao hospeda mais um Aparato proprio", () => {
    // Seis aparatos identicos por tela viram ruido: a honestidade fica com
    // forma de repeticao, e nao de rigor. A prosa se consolida num so, no pe
    // da tela; os rotulos curtos continuam colados ao numero.
    const fonte = readFileSync("components/Painel.tsx", "utf8");
    expect(fonte).not.toContain("<Aparato");
    expect(fonte).toContain("useRegistrarRessalva");
  });

  it("nenhuma tela da ferramenta perdeu a prosa metodologica", () => {
    // Recolher e permitido; remover nao.
    const telas = [
      "app/dashboard/page.tsx",
      "app/dashboard/atendimentos/page.tsx",
      "app/dashboard/modelo/page.tsx",
    ];
    for (const tela of telas) {
      expect(readFileSync(tela, "utf8"), tela).toContain("AparatoDaTela");
    }
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd dashboard && npx vitest run lib/hierarquia.test.ts`
Expected: FAIL — `Painel.tsx` ainda contém `<Aparato`.

- [ ] **Step 3: Write minimal implementation**

```tsx
// dashboard/components/AparatoDaTela.tsx
"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { Aparato } from "./Aparato";

/**
 * O APARATO DA TELA -- um, no pe, e nao um por painel.
 *
 * O QUE MUDOU E POR QUE. A §4.1 do DESIGN.md tirou a prosa metodologica de
 * cima do dado e a mandou para o rodape do sistema, e isso funcionou. O que
 * ela nao resolveu: com seis paineis por tela, "Método e ressalvas" passou a
 * aparecer seis vezes, identico, e repeticao le como ruido em vez de rigor.
 *
 * O QUE NAO MUDA: nenhum texto de honestidade sai da tela -- recolher e
 * permitido, remover nao. E os rotulos curtos (`estimativa`, `observado`,
 * `sem sinal`) NAO sao aparato: continuam colados ao numero, sempre visiveis,
 * como a propria §4.1 diz.
 *
 * POR QUE CONTEXTO, e nao a tela juntando a prosa na mao: a ressalva pertence
 * ao painel que a produz. Se a tela a digitasse, ela envelheceria separada do
 * painel -- o mesmo defeito que o `Aparato` foi extraido para resolver.
 */

type Ressalva = { titulo: string; conteudo: ReactNode };

const Contexto = createContext<{
  registrar: (r: Ressalva) => void;
  remover: (titulo: string) => void;
} | null>(null);

/**
 * A lista viaja num contexto SEPARADO do de escrita: quem so registra
 * (`Painel`) nao precisa re-renderizar quando a lista muda, e quem so le
 * (`AparatoDaTela`) nao precisa das funcoes. Um contexto unico faria cada
 * painel da tela re-renderizar a cada inscricao dos vizinhos.
 */
const ListaContexto = createContext<Ressalva[]>([]);

export function ProvedorDeAparato({ children }: { children: ReactNode }) {
  const [ressalvas, setRessalvas] = useState<Ressalva[]>([]);

  const registrar = useCallback((nova: Ressalva) => {
    setRessalvas((atuais) => {
      const semAAntiga = atuais.filter((r) => r.titulo !== nova.titulo);
      return [...semAAntiga, nova];
    });
  }, []);

  const remover = useCallback((titulo: string) => {
    setRessalvas((atuais) => atuais.filter((r) => r.titulo !== titulo));
  }, []);

  const valor = useMemo(() => ({ registrar, remover }), [registrar, remover]);

  return (
    <Contexto.Provider value={valor}>
      <ListaContexto.Provider value={ressalvas}>
        {children}
      </ListaContexto.Provider>
    </Contexto.Provider>
  );
}

/**
 * Chamado pelo painel que PRODUZ a ressalva. Fora do provedor vira no-op de
 * proposito: um painel usado solto nao deve quebrar a pagina.
 */
export function useRegistrarRessalva(titulo: string, conteudo: ReactNode) {
  const ctx = useContext(Contexto);
  const temConteudo = Boolean(conteudo);

  useEffect(() => {
    if (!ctx || !temConteudo) return;
    ctx.registrar({ titulo, conteudo });
    return () => ctx.remover(titulo);
    // `conteudo` fica FORA das dependencias: ele e JSX, recriado a cada render,
    // e incluir isso reinscreveria a ressalva em laco infinito. O titulo e a
    // identidade da entrada.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ctx, titulo, temConteudo]);
}

export function AparatoDaTela({ className }: { className?: string }) {
  const ressalvas = useContext(ListaContexto);
  if (ressalvas.length === 0) return null;

  return (
    <Aparato className={className}>
      <div className="mt-2 flex max-w-[72ch] flex-col gap-4 text-xs leading-relaxed text-muted-foreground">
        {ressalvas.map((r) => (
          <section key={r.titulo}>
            <h3 className="mb-1 font-semibold text-foreground">{r.titulo}</h3>
            {r.conteudo}
          </section>
        ))}
      </div>
    </Aparato>
  );
}
```

Em `Painel.tsx`, troque o bloco do aparato pela inscrição:

```tsx
import { useRegistrarRessalva } from "./AparatoDaTela";

  // A ressalva sobe para o aparato da tela, identificada pelo titulo do
  // painel. Os rotulos curtos ficam onde estao.
  useRegistrarRessalva(
    titulo,
    legenda || rodape ? (
      <>
        {legenda}
        {rodape}
      </>
    ) : null,
  );
```

E apague o `{temAparato ? (…) : null}` do final, junto com a variável
`temAparato` e o import de `Aparato`.

- [ ] **Step 4: A `FaixaIndicadores` também solta o aparato dela**

Ela tem um `Aparato` próprio (`FaixaIndicadores.tsx:201`) além do vidro
(`:126`). Troque o bloco `<Aparato>…</Aparato>` por uma chamada de
`useRegistrarRessalva("Indicadores", …)` com o mesmo conteúdo, e apague o
import de `Aparato`. **O vidro fica por enquanto** — quem o remove é a Task 6,
que trata a armadura inteira; separar as duas mudanças mantém cada uma
revisável sozinha.

- [ ] **Step 5: Montar o provedor e o rodapé em cada tela**

Em `dashboard/app/dashboard/layout.tsx`, envolva o conteúdo com
`<ProvedorDeAparato>` e ponha `<AparatoDaTela className="mt-8" />` logo antes da
`NotaMetodologica`. O provedor no layout, e não em cada página, é o que garante
que toda tela ganhe o rodapé sem repetir a montagem.

- [ ] **Step 5: Run tests**

Run: `cd dashboard && npx vitest run && npx tsc --noEmit && npm run lint && npm run build`
Expected: tudo verde.

- [ ] **Step 6: Conferir olhando**

Abra as seis telas nos dois temas. Em cada uma deve haver **um** "Método e
ressalvas", no pé, e ao abrir devem estar lá **todas** as ressalvas que antes
estavam espalhadas — com o título do painel de origem. Confira nominalmente que
nenhuma sumiu: compare com as capturas de antes. Este é o ponto do plano onde
texto de honestidade pode se perder em silêncio.

- [ ] **Step 7: Commit**

```bash
git add dashboard/components/AparatoDaTela.tsx dashboard/components/Painel.tsx \
        dashboard/app/dashboard/layout.tsx dashboard/lib/hierarquia.test.ts
git commit -m "feat(dashboard): um aparato por tela no lugar de um por painel"
```

---

### Task 4: A cabeça vazada

**Files:**
- Create: `dashboard/components/CabecaVazada.tsx`
- Modify: `dashboard/components/TabelaConversas.tsx`, `dashboard/components/DistribuicaoScores.tsx`, `dashboard/components/PioresAtendimentos.tsx`
- Test: `tests/test_derivacoes_dashboard.py` (acréscimo)

**Interfaces:**
- Consumes: nada.
- Produces: `<CabecaVazada rotulo?: string />`.

**A dívida que esta tarefa paga:** a §1.1 do `DESIGN.md` promete desde sempre
que atendimento sem sinal é **cabeça vazada** — "o marcador existe, ocupa a
posição temporal, e é oco" — e chama isso de "a peça mais importante desta
lista". A interface imprime a string "sem sinal". `CabecasDeLeitura.tsx` é outra
coisa (emoção e ironia por frase); a notação nunca existiu.

- [ ] **Step 1: Write the failing test**

Acrescente a `tests/test_derivacoes_dashboard.py`:

```python
def test_sem_sinal_e_notacao_e_nao_so_texto():
    """A §1.1 do DESIGN.md promete cabeca vazada para o sem sinal.

    Guarda que atravessa a fronteira de linguagem, no mesmo molde de
    `test_a_vitrine_anuncia_o_numero_real_de_features`: o pytest le o TSX
    como texto. O que ela impede e a regressao silenciosa de alguem trocar a
    notacao de volta por uma string, que nenhum gate de front pegaria.
    """
    componentes = RAIZ / "dashboard" / "components"
    assert (componentes / "CabecaVazada.tsx").is_file()

    for arquivo in ("TabelaConversas.tsx", "DistribuicaoScores.tsx"):
        fonte = (componentes / arquivo).read_text(encoding="utf-8")
        assert "CabecaVazada" in fonte, f"{arquivo} ainda imprime sem sinal cru"


def test_a_cabeca_vazada_carrega_rotulo_textual():
    """Categoria nunca e comunicada so por cor -- nem so por forma.

    Um anel oco sem rotulo obrigaria o leitor a saber a convencao, e o
    PRODUCT.md exige o rotulo textual junto.
    """
    caminho = RAIZ / "dashboard" / "components" / "CabecaVazada.tsx"
    fonte = caminho.read_text(encoding="utf-8")
    assert "sem sinal" in fonte
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_derivacoes_dashboard.py -k cabeca -q`
Expected: FAIL — `CabecaVazada.tsx` não existe.

- [ ] **Step 3: Write minimal implementation**

```tsx
// dashboard/components/CabecaVazada.tsx
import { cn } from "@/lib/utils";

/**
 * A CABECA VAZADA: "sem sinal" como NOTACAO, nao como string.
 *
 * A §1.1 do DESIGN.md promete esta peca desde o comeco e a chama de a mais
 * importante da lista: "o marcador existe, ocupa a posicao temporal, e e oco".
 * O principio de produto 3 -- ausencia de dado nao e insatisfacao -- deixa de
 * ser nota de rodape e vira forma.
 *
 * POR QUE OCO E NAO CINZA: cinza dentro da escala leria como um valor baixo.
 * Oco nao esta na escala; ele ocupa o tempo e nao soa.
 *
 * O ROTULO E OBRIGATORIO. O PRODUCT.md exige que categoria nunca seja
 * comunicada so por cor, e forma tem a mesma fraqueza: um anel sozinho obriga
 * o leitor a conhecer a convencao. Quem quiser esconder o rotulo do desenho
 * (numa celula estreita, por exemplo) usa `rotuloVisivel={false}` -- que o
 * mantem para o leitor de tela, e nunca o remove.
 */
export function CabecaVazada({
  rotulo = "sem sinal",
  rotuloVisivel = true,
  className,
}: {
  rotulo?: string;
  rotuloVisivel?: boolean;
  className?: string;
}) {
  return (
    <span className={cn("inline-flex items-center gap-1.5", className)}>
      <span
        aria-hidden
        className="inline-block size-2.5 shrink-0 rounded-full border border-muted-foreground bg-transparent"
      />
      <span className={cn("text-xs", rotuloVisivel ? "text-muted-foreground" : "sr-only")}>
        {rotulo}
      </span>
    </span>
  );
}
```

Nos três componentes de consumo, troque a impressão de `"sem sinal"` por
`<CabecaVazada />`. **Não mexa na lógica que decide quando é sem sinal** — ela
já está certa e é a invariante 2.

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_derivacoes_dashboard.py -q && cd dashboard && npx tsc --noEmit && npm run lint && npm run build`
Expected: tudo verde.

- [ ] **Step 5: Conferir olhando**

`/dashboard` e `/dashboard/atendimentos` nos dois temas. As duas conversas
`demo-dia-mudo-*` são os casos de teste vivos. Confira: o anel é visível contra
o vidro nos dois temas, **não** entra na escala de cor de categoria, e a
distribuição continua mostrando "4 sem sinal" fora da escala.

- [ ] **Step 6: Commit**

```bash
git add dashboard/components/CabecaVazada.tsx dashboard/components/TabelaConversas.tsx \
        dashboard/components/DistribuicaoScores.tsx dashboard/components/PioresAtendimentos.tsx \
        tests/test_derivacoes_dashboard.py
git commit -m "feat(dashboard): o sem sinal vira cabeca vazada, como a §1.1 promete"
```

---

### Task 5: A régua ancora o dominante

**Files:**
- Modify: `dashboard/components/Painel.tsx`

**Interfaces:**
- Consumes: `Nivel` da Task 1.
- Produces: `Painel` aceita `regua?: { dito: ReactNode; medido: ReactNode }`.

**O limite desta tarefa, e ele é a parte importante:** a régua entra **só onde o
dado de fato se divide** em dito e medido. O gráfico de NPS × latência **não**
recebe régua: as duas séries são medidas. A transcrição recebe. Forçar a
metáfora onde ela não cabe é decorar com notação, que a §1.1 proíbe
explicitamente — "se em algum momento ler esta interface exigir saber solfejo, a
regra foi aplicada errado".

- [ ] **Step 1: Write the failing test**

Acrescente a `dashboard/lib/hierarquia.test.ts`:

```ts
describe("regua", () => {
  it("o Painel sabe montar a regua com os dois lados", () => {
    const fonte = readFileSync("components/Painel.tsx", "utf8");
    expect(fonte).toContain("regua");
    expect(fonte).toContain("border-linha");
  });

  it("o grafico de NPS x latencia NAO usa regua", () => {
    // As duas series sao MEDIDAS. Regua ali seria notacao decorativa.
    const fonte = readFileSync("components/GraficoNpsLatencia.tsx", "utf8");
    expect(fonte).not.toContain("regua=");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd dashboard && npx vitest run lib/hierarquia.test.ts`
Expected: FAIL — `Painel.tsx` não menciona `regua`.

- [ ] **Step 3: Write minimal implementation**

Em `Painel.tsx`, acrescente o parâmetro e o bloco:

```tsx
  /**
   * A regua do sistema: dito ACIMA, medido ABAIXO (DESIGN.md §1).
   *
   * So passe isto quando o dado REALMENTE se divide nos dois lados. Onde as
   * duas series sao medidas -- o grafico de NPS x latencia e o caso -- a
   * regua nao entra: seria notacao decorativa, e a §1.1 proibe.
   */
  regua,
```

E, dentro do corpo, no lugar de `{children}` quando `regua` existir:

```tsx
        {regua ? (
          <div className="flex flex-col">
            <div className="pb-3">{regua.dito}</div>
            <div className="border-t border-linha" />
            <div className="pt-3">{regua.medido}</div>
          </div>
        ) : (
          children
        )}
```

- [ ] **Step 4: Run tests**

Run: `cd dashboard && npx vitest run && npx tsc --noEmit && npm run lint && npm run build`
Expected: tudo verde.

- [ ] **Step 5: Commit**

```bash
git add dashboard/components/Painel.tsx dashboard/lib/hierarquia.test.ts
git commit -m "feat(dashboard): a regua ancora o sistema dominante onde o dado se divide"
```

---

### Task 6: As telas declaram nível, e os dois buracos fecham

**Files:**
- Modify: `dashboard/app/dashboard/page.tsx`, `dashboard/app/dashboard/atendimentos/page.tsx`, `dashboard/app/dashboard/grafo/page.tsx`, `dashboard/app/dashboard/integracoes/page.tsx`, `dashboard/app/dashboard/configuracoes/page.tsx`, `dashboard/components/FaixaIndicadores.tsx`, `dashboard/app/dashboard/layout.tsx`

**Interfaces:**
- Consumes: `Painel` com `nivel` (Task 2), `DOMINANTE_POR_TELA` (Task 1).
- Produces: nada consumido por tarefas seguintes.

- [ ] **Step 1: Write the failing test**

Acrescente a `dashboard/lib/hierarquia.test.ts`:

```ts
describe("as telas declaram nivel", () => {
  const TELAS = [
    ["app/dashboard/page.tsx", "/dashboard"],
    ["app/dashboard/atendimentos/page.tsx", "/dashboard/atendimentos"],
    ["app/dashboard/integracoes/page.tsx", "/dashboard/integracoes"],
    ["app/dashboard/configuracoes/page.tsx", "/dashboard/configuracoes"],
  ] as const;

  it("cada tela marca exatamente um painel como dominante", () => {
    for (const [arquivo] of TELAS) {
      const fonte = readFileSync(arquivo, "utf8");
      const ocorrencias = fonte.match(/nivel="dominante"/g) ?? [];
      expect(ocorrencias.length, arquivo).toBe(1);
    }
  });

  it("toda tela que declara dominante esta no vocabulario", () => {
    // NAO compare titulo: varios paineis montam o titulo em tempo de render
    // (`Atendimentos de ${rotulo}`), e string estatica nunca casa com isso.
    // O vocabulario guarda identificador; quem marca o dominante e a tela.
    for (const [, rota] of TELAS) {
      expect(DOMINANTE_POR_TELA, rota).toHaveProperty(rota);
    }
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd dashboard && npx vitest run lib/hierarquia.test.ts`
Expected: FAIL — nenhuma tela tem `nivel="dominante"`.

- [ ] **Step 3: Declarar o nível em cada tela**

Em cada `page.tsx`, ponha `nivel="dominante"` no painel que o
`DOMINANTE_POR_TELA` nomeia, e deixe os demais sem a propriedade (o padrão já é
`apoio`). Confira que o `titulo` do painel bate **exatamente** com a string do
vocabulário — é isso que o segundo teste verifica.

- [ ] **Step 4: A armadura perde a superfície**

Em `FaixaIndicadores.tsx`, remova as classes de vidro, borda e chanfro do
contêiner externo. A §2.2 do `DESIGN.md` sempre disse que os indicadores são
"rótulo mais número tabular, sem barra de progresso decorativa e sem cartão";
esta é a linha sendo cumprida. Os separadores entre indicadores viram `--linha`.

- [ ] **Step 5: Fechar os dois buracos**

No `layout.tsx` da dashboard:

- a barra lateral encosta no rodapé (a classe de altura passa a acompanhar o
  contêiner, em vez de parar em altura fixa);
- o miolo deixa de ter altura mínima que empurrava a `NotaMetodologica` para
  600px abaixo do conteúdo. Meça de novo depois de aplicar: o vazio some porque
  o dominante ocupa o que sobrava, não porque alguém cravou uma altura.

- [ ] **Step 6: Run tests**

Run: `cd dashboard && npx vitest run && npx tsc --noEmit && npm run lint && npm run build`
Expected: tudo verde.

- [ ] **Step 7: Conferir olhando — este é o passo que julga a tarefa**

Nos dois temas, nas seis telas. O que precisa ser verdade:

1. de longe, **um** bloco domina cada tela, e dá para dizer qual sem ler;
2. a Visão geral não tem mais o vazio de ~600px;
3. a barra lateral vai até o rodapé em página alta (`/dashboard/modelo` é a mais
   alta e é o melhor caso de teste);
4. a armadura lê como armadura — empilhada e compacta — e não como cartão.

- [ ] **Step 8: Commit**

```bash
git add dashboard/app/dashboard dashboard/components/FaixaIndicadores.tsx \
        dashboard/lib/hierarquia.test.ts
git commit -m "feat(dashboard): cada tela elege o seu sistema dominante"
```

---

### Task 6b: Os estados do dominante

**Files:**
- Modify: `dashboard/components/Painel.tsx`, `dashboard/components/EstadoVazio.tsx`, `dashboard/components/shell/AvisoApiFora.tsx`

**Interfaces:**
- Consumes: `Nivel` (Task 1), `Painel` com nível (Task 2).
- Produces: `Painel` aceita `erro?: ReactNode` e `vazio?: ReactNode`.

**O caso novo que a hierarquia cria:** falha isolada já era regra (§5 do
`DESIGN.md` — "um sistema que não carrega mostra o próprio erro no lugar dele, e
os vizinhos continuam de pé"). O que muda é que **um dominante quebrado deixa um
buraco muito maior que um apoio quebrado**, e um aviso pequeno dentro de uma
caixa grande lê como se nada tivesse acontecido.

- [ ] **Step 1: Write the failing test**

Acrescente a `dashboard/lib/hierarquia.test.ts`:

```ts
describe("estados do dominante", () => {
  it("o Painel sabe render erro e vazio no lugar do conteudo", () => {
    const fonte = readFileSync("components/Painel.tsx", "utf8");
    expect(fonte).toContain("erro");
    expect(fonte).toContain("vazio");
  });

  it("erro e vazio nao viram string vazia nem zero", () => {
    // Ausencia de dado nao e insatisfacao, e a invariante 2 do CLAUDE.md
    // manda procurar `?? 0` e `|| 0` antes de commitar.
    const fonte = readFileSync("components/Painel.tsx", "utf8");
    expect(fonte).not.toMatch(/\?\?\s*0\b/);
    expect(fonte).not.toMatch(/\|\|\s*0\b/);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd dashboard && npx vitest run lib/hierarquia.test.ts`
Expected: FAIL — `Painel.tsx` não menciona `erro` nem `vazio`.

- [ ] **Step 3: Write minimal implementation**

Em `Painel.tsx`, acrescente os dois parâmetros e a precedência de render:

```tsx
  /**
   * Falha isolada (DESIGN.md §5): o sistema que nao carrega mostra o proprio
   * erro NO LUGAR DELE, com o peso dele, e os vizinhos continuam de pe. Num
   * dominante isso importa mais: um aviso pequeno numa caixa grande le como
   * se nada tivesse acontecido.
   */
  erro,
  /**
   * Estado vazio nomeia O QUE FALTA e qual etapa ou endpoint resolveria.
   * Nunca preencher com numero simulado -- numa ferramenta batizada com o nome
   * do daemon do engano, dado plausivel inventado seria a pior falha possivel.
   */
  vazio,
```

E, no corpo, antes da régua e do `children`:

```tsx
        {erro ?? vazio ?? (regua ? (
          <div className="flex flex-col">
            <div className="pb-3">{regua.dito}</div>
            <div className="border-t border-linha" />
            <div className="pt-3">{regua.medido}</div>
          </div>
        ) : (
          children
        ))}
```

O `??` e não `||`: string vazia e `0` são conteúdo legítimo, e `||` os
descartaria — que é exatamente o padrão que a invariante 2 manda procurar.

- [ ] **Step 4: `AvisoApiFora` sobe de nível**

Quando a API está fora, o aviso passa a ser o dominante da tela enquanto durar,
em vez de uma tarja acima de painéis vazios. Ele já existe; o que muda é o peso.

- [ ] **Step 5: Run tests**

Run: `cd dashboard && npx vitest run && npx tsc --noEmit && npm run lint && npm run build`
Expected: tudo verde.

- [ ] **Step 6: Conferir olhando — os três estados, de propósito**

Este passo exige **provocar** as falhas, não esperar por elas:

1. **API fora**: derrube o `uvicorn` e recarregue `/dashboard`. O aviso domina;
   nenhum painel mostra zero.
2. **Vazio**: filtre um período sem atendimento (uma data futura serve). Cada
   sistema nomeia o que falta; a distribuição não vira barra de altura zero.
3. **Dominante falha, apoio carrega**: não há como provocar isso pela interface;
   force temporariamente um `throw` no componente do dominante, confira que os
   apoios continuam de pé, e **desfaça antes de commitar**.

- [ ] **Step 7: Commit**

```bash
git add dashboard/components/Painel.tsx dashboard/components/shell/AvisoApiFora.tsx \
        dashboard/lib/hierarquia.test.ts
git commit -m "feat(dashboard): erro e vazio ocupam o lugar do dominante, com o peso dele"
```

---

### Task 7: O veredito sobe ao topo da tela Modelo

**Files:**
- Create: `dashboard/components/modelo/EstadoDoModelo.tsx`
- Modify: `dashboard/app/dashboard/modelo/page.tsx`

**Interfaces:**
- Consumes: `Painel` com `nivel` (Task 2); os dados de métrica que a tela já lê.
- Produces: `<EstadoDoModelo />`.

**O defeito que esta tarefa conserta:** a tela Modelo abre pelo simulador e
enterra no meio, em corpo de texto com o mesmo peso do lexicon de emoji, os três
fatos que o avaliador precisa ler primeiro — as métricas de ironia estão
marcadas como suspeitas, a ironia saiu do vetor em 04/09/2026, e o corpus de
tempo é sintético. É a aplicação direta do princípio de produto 1: a tela nomeia
o que falta **antes** de mostrar número.

- [ ] **Step 1: Write the failing test**

Acrescente a `tests/test_derivacoes_dashboard.py`:

```python
def test_a_tela_modelo_abre_pelo_veredito():
    """O que o avaliador precisa ler primeiro nao pode estar no meio da pagina.

    As tres ressalvas estruturais do modelo -- ironia fora do vetor, metricas
    suspeitas e corpus de tempo sintetico -- sobem para um sistema dominante
    no topo.
    """
    painel = RAIZ / "dashboard"
    componente = painel / "components" / "modelo" / "EstadoDoModelo.tsx"
    assert componente.is_file()

    pagina = (painel / "app" / "dashboard" / "modelo" / "page.tsx").read_text(
        encoding="utf-8"
    )
    assert "EstadoDoModelo" in pagina
    # O veredito vem ANTES do simulador na ordem do arquivo.
    assert pagina.index("EstadoDoModelo") < pagina.index("Simulador")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_derivacoes_dashboard.py -k modelo -q`
Expected: FAIL — o componente não existe.

- [ ] **Step 3: Write minimal implementation**

Crie `EstadoDoModelo.tsx` como um `Painel nivel="dominante"` cujo conteúdo são
as três ressalvas estruturais, cada uma com o rótulo curto colado
(`suspeito`, `sintético`, `fora do vetor`) e a prosa longa indo para o aparato
da tela via `legenda`. **Não invente número**: o componente exibe o que a API
já entrega em `GET /modelo` e, onde não houver métrica, usa `EstadoVazio`, que
nomeia o que falta e qual etapa resolveria.

Texto vinculante, que não pode ser suavizado:

- a ironia continua carregada, obrigatória e lida por mensagem, e **não pontua**
  desde 04/09/2026 — medida no corpus de treino, ela funciona como detector de
  sentimento positivo;
- as métricas de ironia são de corpus **sintético** e o F1 de 100% é sinalizado
  como suspeito;
- o sinal de tempo é treinado em dados sintéticos calibrados por literatura.

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_derivacoes_dashboard.py -q && cd dashboard && npx vitest run && npx tsc --noEmit && npm run lint && npm run build`
Expected: tudo verde.

- [ ] **Step 5: Conferir olhando**

`/dashboard/modelo` nos dois temas. O veredito é a primeira coisa que se lê, e o
simulador vem depois. Confira que **nenhuma** das ressalvas que estavam no meio
da página sumiu — elas mudaram de lugar, não de existência.

- [ ] **Step 6: Commit**

```bash
git add dashboard/components/modelo/EstadoDoModelo.tsx \
        dashboard/app/dashboard/modelo/page.tsx tests/test_derivacoes_dashboard.py
git commit -m "feat(dashboard): a tela modelo abre pelo veredito, nao pelo simulador"
```

---

### Task 8: A curva da cena

**Files:**
- Create: `dashboard/lib/cena.ts`
- Test: `dashboard/lib/cena.test.ts`

**Interfaces:**
- Consumes: nada.
- Produces: `intensidadeDaCamada(camada: Camada, progresso: number): number`; `type Camada = "grade" | "planeta" | "estrelas"`; `const TETO_POR_CAMADA: Record<Camada, number>`.

**Por que isto é função pura e testada:** o teto de intensidade de cada camada é
o que a Task 11 vai usar para remedir os pisos. Se o teto for um número solto
dentro de um componente, o `pisos.mjs` mede uma superfície que não existe — que
é, literalmente, o defeito que a §8.6 do `DESIGN.md` registra ter acontecido
duas vezes neste projeto.

- [ ] **Step 1: Write the failing test**

```ts
// dashboard/lib/cena.test.ts
import { describe, expect, it } from "vitest";
import { TETO_POR_CAMADA, intensidadeDaCamada, type Camada } from "./cena";

const CAMADAS: Camada[] = ["grade", "planeta", "estrelas"];

describe("intensidadeDaCamada", () => {
  it("nunca passa do teto declarado, em nenhum ponto da rolagem", () => {
    // O teto e o que o pisos.mjs vai medir. Se a curva passar dele, o portao
    // mede uma superficie mais escura que a real e devolve verde com folga
    // que nao existe -- o defeito registrado na §8.6 do DESIGN.md.
    for (const camada of CAMADAS) {
      for (let p = 0; p <= 1.0001; p += 0.01) {
        expect(intensidadeDaCamada(camada, p), `${camada} @ ${p}`)
          .toBeLessThanOrEqual(TETO_POR_CAMADA[camada]);
      }
    }
  });

  it("nunca e negativa", () => {
    for (const camada of CAMADAS) {
      for (let p = 0; p <= 1.0001; p += 0.01) {
        expect(intensidadeDaCamada(camada, p)).toBeGreaterThanOrEqual(0);
      }
    }
  });

  it("trata progresso fora de 0..1 sem estourar", () => {
    for (const camada of CAMADAS) {
      expect(intensidadeDaCamada(camada, -5)).toBeGreaterThanOrEqual(0);
      expect(intensidadeDaCamada(camada, 99)).toBeLessThanOrEqual(
        TETO_POR_CAMADA[camada],
      );
    }
  });

  it("cada camada atinge o proprio teto em algum ponto", () => {
    // Teto que nunca e alcancado e pessimismo gratuito: faria o vidro
    // engrossar sem motivo, e a §8.6 diz que a espessura cede so quando
    // precisa.
    for (const camada of CAMADAS) {
      let maximo = 0;
      for (let p = 0; p <= 1.0001; p += 0.005) {
        maximo = Math.max(maximo, intensidadeDaCamada(camada, p));
      }
      expect(maximo).toBeCloseTo(TETO_POR_CAMADA[camada], 2);
    }
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd dashboard && npx vitest run lib/cena.test.ts`
Expected: FAIL — `Failed to resolve import "./cena"`.

- [ ] **Step 3: Write minimal implementation**

```ts
// dashboard/lib/cena.ts
/**
 * A CENA DA VITRINE: como cada camada do atelie responde a rolagem.
 *
 * O DEFEITO QUE ISTO CONSERTA: o atelie so existia no heroi. Grade, planeta e
 * campo de estrelas ocupavam a primeira tela e a LP virava preto chapado por
 * cerca de 5.600px -- a tese "espaco profundo" evaporava exatamente onde a
 * rolagem passa o tempo todo.
 *
 * POR QUE FUNCAO PURA, e nao numeros soltos no componente: o TETO de cada
 * camada e o que o `scripts/pisos.mjs` mede para saber a superficie mais clara
 * que o vidro pode compor. Teto escondido dentro de JSX e teto que o script
 * nao le -- e o portao passa a medir uma superficie que nao existe, que a
 * §8.6 do DESIGN.md registra ter acontecido duas vezes aqui.
 *
 * O QUE NAO MUDA: estas camadas moram no ATELIE, nao carregam dado, e passam
 * por baixo da luz e do vidro.
 */

export type Camada = "grade" | "planeta" | "estrelas";

/**
 * Opacidade maxima que cada camada assume em QUALQUER ponto da rolagem.
 * Espelhado em `scripts/pisos.mjs`; mudar aqui obriga a remedir la.
 */
export const TETO_POR_CAMADA: Record<Camada, number> = {
  grade: 0.1,
  planeta: 0.15,
  estrelas: 0.22,
};

function limitar(valor: number, minimo: number, maximo: number): number {
  return Math.min(maximo, Math.max(minimo, valor));
}

/**
 * `progresso` e 0 no topo da pagina e 1 no fim. Valores fora da faixa sao
 * grampeados: `scroll` elastico de trackpad entrega negativo e passa de 1, e
 * uma camada com opacidade negativa e um NaN esperando acontecer.
 */
export function intensidadeDaCamada(camada: Camada, progresso: number): number {
  const p = limitar(progresso, 0, 1);
  const teto = TETO_POR_CAMADA[camada];

  switch (camada) {
    // A grade e o piso do cenario: forte na entrada, cede conforme a leitura
    // comeca, e nao volta.
    case "grade":
      return teto * (1 - p);
    // O planeta cruza: nasce fora, atinge o proprio teto no meio da travessia
    // e sai. Meia onda de seno, que garante o teto exatamente uma vez.
    case "planeta":
      return teto * Math.sin(Math.PI * p);
    // O campo de estrelas e o oposto da grade: quase ausente no heroi, onde a
    // manchete manda, e assume o fundo conforme a pagina desce.
    case "estrelas":
      return teto * p;
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd dashboard && npx vitest run lib/cena.test.ts`
Expected: PASS, 4 testes.

- [ ] **Step 5: Commit**

```bash
git add dashboard/lib/cena.ts dashboard/lib/cena.test.ts
git commit -m "feat(dashboard): a curva da cena da vitrine ganha um dono testavel"
```

---

### Task 9: O ateliê lê o progresso

**Files:**
- Modify: `dashboard/components/shell/Atelier.tsx`
- Create: `dashboard/hooks/useProgressoDaCena.ts`

**Interfaces:**
- Consumes: `intensidadeDaCamada`, `TETO_POR_CAMADA` da Task 8.
- Produces: `useProgressoDaCena(): void` — escreve `--cena-grade`, `--cena-planeta` e `--cena-estrelas` no elemento raiz.

**A regra de implementação que não pode ser afrouxada:** escreva as variáveis
CSS **direto no nó, dentro de `requestAnimationFrame`**, sem `useState`. É o
mesmo desenho do `useEspecular`, e pelo mesmo motivo: um `setState` por evento
de rolagem re-renderiza a árvore inteira a cada quadro, atrás de tabela e
gráfico.

- [ ] **Step 1: Escrever o hook**

```ts
// dashboard/hooks/useProgressoDaCena.ts
"use client";

import { useEffect } from "react";
import { intensidadeDaCamada, type Camada } from "@/lib/cena";

const CAMADAS: Camada[] = ["grade", "planeta", "estrelas"];

/**
 * Liga a rolagem as variaveis da cena.
 *
 * SEM useState, de proposito: um setState por evento de rolagem re-renderiza a
 * arvore a cada quadro, atras de tabela e grafico. Escreve direto no no dentro
 * de rAF, como o `useEspecular` ja faz.
 *
 * DOIS DESLIGAMENTOS. `prefers-reduced-motion` e o obvio; o segundo e o
 * esquecido: quem pede menos movimento nao recebe uma versao lenta, recebe a
 * cena PARADA no estado inicial -- a mesma decisao da §8.7 sobre o campo de
 * particulas, que devolve `null` em vez de girar devagar.
 */
export function useProgressoDaCena(): void {
  useEffect(() => {
    const raiz = document.documentElement;
    const consulta = window.matchMedia("(prefers-reduced-motion: reduce)");

    function aplicar(progresso: number) {
      for (const camada of CAMADAS) {
        raiz.style.setProperty(
          `--cena-${camada}`,
          String(intensidadeDaCamada(camada, progresso)),
        );
      }
    }

    if (consulta.matches) {
      aplicar(0);
      return;
    }

    let pendente = false;
    function aoRolar() {
      if (pendente) return;
      pendente = true;
      requestAnimationFrame(() => {
        pendente = false;
        const rolavel = document.body.scrollHeight - window.innerHeight;
        aplicar(rolavel > 0 ? window.scrollY / rolavel : 0);
      });
    }

    aoRolar();
    window.addEventListener("scroll", aoRolar, { passive: true });
    return () => window.removeEventListener("scroll", aoRolar);
  }, []);
}
```

- [ ] **Step 2: Ligar no `Atelier`**

Em `Atelier.tsx`, chame `useProgressoDaCena()` e troque a opacidade fixa das três
camadas por `var(--cena-grade)`, `var(--cena-planeta)` e `var(--cena-estrelas)`,
**com fallback para o valor de hoje** — `var(--cena-grade, 0.1)` — para que a
primeira pintura, antes do JavaScript, não apague a cena.

- [ ] **Step 3: Verificar**

Run: `cd dashboard && npx vitest run && npx tsc --noEmit && npm run lint && npm run build`
Expected: tudo verde.

- [ ] **Step 4: Conferir olhando, e conferir o desligamento**

Abra a LP e role. Depois **force o movimento reduzido** e role de novo: a cena
tem que ficar parada no estado inicial, não lenta.

No Chrome: DevTools → Rendering → "Emulate CSS media feature
prefers-reduced-motion" → `reduce`.

- [ ] **Step 5: Commit**

```bash
git add dashboard/hooks/useProgressoDaCena.ts dashboard/components/shell/Atelier.tsx
git commit -m "feat(dashboard): o atelie acompanha a rolagem da vitrine"
```

---

### Task 10: As seções da LP ganham âncora

**Files:**
- Modify: `dashboard/app/page.tsx`

**Interfaces:**
- Consumes: a cena da Task 9.
- Produces: nada.

- [ ] **Step 1: Conferir o estado de partida**

A LP tem 8 seções e cerca de 6.600px. Depois do herói, todas repetem a mesma
caixa escura, com o mesmo alinhamento e a mesma escala de título. Capture antes
de mexer, para comparar depois.

- [ ] **Step 2: Dar contraste de escala e alinhamento**

Cada seção recebe uma âncora visual própria. Não é efeito novo: é usar o que já
existe — escala de título, largura de medida, alinhamento, e o momento em que a
cena da Task 9 está mais clara ou mais escura atrás dela.

A regra que governa: **uma seção não pode parecer a anterior**. Se duas seções
vizinhas têm o mesmo peso, uma delas está errada.

| # | Seção | Âncora | Por quê |
|---|---|---|---|
| 1 | herói | como está | já é a mais forte da página; a grade está no teto atrás dela |
| 2 | esteira de sinais | como está | é filete, e filete entre dois blocos é respiro |
| 3 | "Duas vozes, separadas por uma régua" | **a régua atravessa a largura inteira**, sangrando além da coluna de texto | é a única seção cuja tese *é* a régua; deixá-la contida dentro da coluna é enunciar sem mostrar |
| 4 | contadores 39 / 7 / 3 / 0 | **número em escala de display**, medida curta, muito espaço em volta | é a seção de menor densidade textual da página e a que mais ganha com vazio |
| 5 | "Sete sinais, um veredito" | **a constelação ocupa a tela toda**, a lista das sete famílias desce para medida estreita | é o momento de espetáculo da página; hoje ela divide espaço com a lista e as duas perdem |
| 6 | dito × medido | **duas colunas com pesos desiguais**, âmbar acima e azul abaixo da régua, e não lado a lado | duas colunas simétricas dizem "estes dois são equivalentes", e a tese é que a *distância* entre eles é a informação |
| 7 | "O número aponta as falas" | **a evidência manda**: as três falas em escala maior que a prosa | a prosa explica o que a evidência já mostra; hoje a hierarquia está invertida |
| 8 | "O que é medido, o que é estimado" | **medida larga, tipo menor, três colunas** | é a seção de leitura densa, e é honesta que ela pareça densa |
| 9 | fecho | **a cena no ponto mais claro** da trajetória, com a marca sangrando | é a última tela; o cenário fecha onde abriu |

O que **não** pode acontecer, e vale para todas as nove: nenhuma seção ganha
superfície translúcida sobre dado, nenhuma ganha cor de dado, e o contador de
features continua sendo lido do contrato.

O que **não** pode acontecer: nenhuma seção ganha superfície translúcida sobre
dado, nenhuma ganha cor de dado, e o contador de features continua sendo lido do
contrato (a guarda `test_a_vitrine_anuncia_o_numero_real_de_features` precisa
continuar passando).

- [ ] **Step 3: Verificar**

Run: `uv run pytest tests/test_derivacoes_dashboard.py -q && cd dashboard && npx tsc --noEmit && npm run lint && npm run build`
Expected: tudo verde, incluindo a guarda da vitrine.

- [ ] **Step 4: Conferir olhando, e este é o julgamento da tarefa**

Role a LP inteira, nos dois temas, e com movimento reduzido. O teste é simples:
**dá para dizer em que ponto da página você está sem ler o texto?** Se todas as
telas ainda parecem a mesma, a tarefa não foi feita.

- [ ] **Step 5: Commit**

```bash
git add dashboard/app/page.tsx
git commit -m "feat(dashboard): cada secao da vitrine ganha ancora propria"
```

---

### Task 11: Remedir os pisos para a trajetória

**Files:**
- Modify: `dashboard/scripts/pisos.mjs`, `dashboard/app/globals.css`

**Interfaces:**
- Consumes: `TETO_POR_CAMADA` da Task 8.
- Produces: pisos gravados no CSS que batem com o pior caso medido.

**O que muda conceitualmente:** até aqui o pior caso do ateliê era um **ponto**
— as camadas compostas nas suas opacidades fixas. Com a cena acompanhando a
rolagem, o pior caso vira uma **trajetória**, e o piso tem que ser medido no
estado mais claro que ela atinge em qualquer ponto.

**O par que vai reprovar primeiro:** a §8.6 registra `--detrator-texto` sobre o
piso do vidro fino em **4,54** na chuva, contra um limiar de 4,5. Duas ressalvas:
o segundo valor daquela seção é do tema **grafite, que foi descartado**, e o par
equivalente no **espaço profundo** — padrão de fábrica de hoje, vidro mais fino
dos três, a 56% — nunca foi registrado. Remeça antes de confiar em qualquer
número herdado.

- [ ] **Step 1: Ensinar o script a ler o teto**

Em `pisos.mjs`, troque a opacidade fixa das três camadas da cena pelo teto
declarado em `lib/cena.ts`. Leia do arquivo, não copie o número: teto duplicado
é teto que diverge, e é assim que o portão passa a medir uma superfície que não
existe.

- [ ] **Step 2: Rodar e obter os pisos novos**

Run: `cd dashboard && npm run pisos`
Anote os pisos que o script imprime para cada espessura, nos dois temas.

- [ ] **Step 3: Gravar os pisos no CSS e rodar o portão**

Atualize os `--vidro-<n>-piso` do `globals.css` com o que o script imprimiu.

Run: `cd dashboard && npm run contraste`

- [ ] **Step 4: Se algum par reprovar, a espessura cede**

A ordem é a de sempre e não se inverte: **a espessura ganha opacidade até
passar; o portão nunca é afrouxado, e a luz não é baixada para salvar o
contraste.** Suba de 1 em 1 ponto, remedindo o piso a cada passo — foi assim que
a §8.6 resolveu as três rodadas anteriores.

Se o par que reprovar for `--detrator-texto`, **pare e reporte**: ele é cor de
**dado** (categoria de NPS), e a §8.6 já declara que mexer nele é decisão de
outra ordem. Nesse caso a alavanca é baixar o teto da camada em `lib/cena.ts`,
que é cenário, e não a cor da categoria.

- [ ] **Step 5: Verificar**

Run: `cd dashboard && npm run pisos && npm run contraste && npm run build`
Expected: pisos batendo, contraste todo verde nos dois temas, build concluído.

- [ ] **Step 6: Commit**

```bash
git add dashboard/scripts/pisos.mjs dashboard/app/globals.css
git commit -m "fix(dashboard): o pior caso do atelie vira trajetoria, nao ponto"
```

---

### Task 12: As emendas ao `DESIGN.md`

**Files:**
- Modify: `dashboard/DESIGN.md`, `dashboard/PRODUCT.md`

**Interfaces:**
- Consumes: tudo que as tarefas anteriores decidiram.
- Produces: o contrato visual atualizado.

**Por que isto é tarefa e não nota de rodapé:** o `DESIGN.md` é o contrato, e
este projeto já pagou por documento que afirma o que o código não faz — a §8.6
registra uma emenda que alegava disjunção geométrica que não existia mais, e a
§8.2 registra uma regra atribuída ao `PRODUCT.md` que nunca esteve lá.

- [ ] **Step 1: Escrever as cinco emendas**

1. **§2.2** — a armadura deixa de ser painel (a seção já pedia); `Painel` ganha
   nível, e o vocabulário mora em `lib/hierarquia.ts`.
2. **§4.1** — o aparato passa a ser um por tela. **Deixe explícito** que os
   rótulos curtos continuam fora do aparato, colados ao número.
3. **§1.1** — a cabeça vazada saiu do papel e virou `CabecaVazada.tsx`. Registre
   que ela levou desde a redação da seção até 04/09/2026 para existir.
4. **§6** — a coreografia de rolagem da vitrine. O argumento registrado: a §6
   governa o modo **Operate**, a LP é vitrine declarada, e o precedente é a
   própria §8.7, que já abriu essa exceção para o WebGL. **A conta continua em
   dois na ferramenta.**
5. **§8.6** — o pior caso virou trajetória; os pisos foram remedidos; e registre
   o valor do par `--detrator-texto` no **espaço profundo**, que nunca esteve no
   documento.

- [ ] **Step 2: Corrigir a referência ao tema descartado**

A §8.6 cita pisos "no grafite" num documento cuja §8 diz que o grafite foi
descartado. Marque esses números como **históricos**, para que ninguém os use
como referência de um tema que não existe.

- [ ] **Step 3: Atualizar o `PRODUCT.md`**

Ele diz "Fusão de **38 features**" e "Cinco telas". O contrato está em **39**, e
as telas são **seis** (`grafo` e `analisar` além das cinco listadas). Corrija.

- [ ] **Step 4: Commit**

```bash
git add dashboard/DESIGN.md dashboard/PRODUCT.md
git commit -m "docs(design): as emendas de hierarquia e cena entram no contrato"
```

---

## Verificação final da branch

- [ ] `uv run pytest -q` — a suíte inteira da raiz
- [ ] `cd dashboard && npx vitest run`
- [ ] `cd dashboard && npx tsc --noEmit`
- [ ] `cd dashboard && npm run lint`
- [ ] `cd dashboard && npm run pisos`
- [ ] `cd dashboard && npm run contraste`
- [ ] `cd dashboard && npm run build`
- [ ] **Conferir olhando**: as seis telas e a LP, nos dois temas, com dado e em
      estado vazio, e com `prefers-reduced-motion: reduce`.

O último item não é formalidade. A §9 do `DESIGN.md` registra três defeitos que
passaram verdes por todos os outros: o papel pautado invisível a 5,5%, a grade a
laser colapsada numa faixa de 30px, e o portão medindo uma superfície que não
existia. **Nenhum dos gates vê a tela.**
