import { celulasDoValor, type Celula, type Segmento } from "../../lib/segmentos";

/**
 * O DISPLAY DE SETE SEGMENTOS -- o numero como instrumento.
 *
 * O Fraus mede, e um numero medido merece a forma de um instrumento. Mas a
 * razao de o LED existir e outra, e e a que sustenta o desenho inteiro: num
 * display de sete segmentos **o segmento apagado tambem e desenhado**. A
 * celula sem luz continua la, a 10% de opacidade, ocupando o lugar do digito.
 * E exatamente a invariante 2 do CLAUDE.md ("ausencia de dado nao e
 * insatisfacao") virada objeto: `valor: null` NAO renderiza `0`, renderiza
 * celulas apagadas -- o medidor existe, esta ligado, e nao leu nada.
 *
 * REGRAS QUE ESTE COMPONENTE NAO QUEBRA
 *  - Nao calcula, nao arredonda, nao converte. Recebe a string JA formatada em
 *    pt-BR pelo chamador (uma fonte so de formatacao, invariante 3).
 *  - `rotulo` e OBRIGATORIO. Um SVG de poligonos nao diz nada a um leitor de
 *    tela, e um numero sem nome ("2,9" de que?) tambem nao diz nada a quem ve.
 *    Com `valor: null` o `aria-label` vira `${rotulo}: sem sinal` -- a palavra
 *    que a cor sozinha nao carregaria.
 *  - Caractere fora do alfabeto nao some: entra como texto cru em mono. Um
 *    display que engole um caractere muda o numero em silencio.
 *  - Sem estado e sem hook, entao serve em Server Component e em cliente.
 *
 * Cor: `medido` (azul -- e a cor do que foi MEDIDO, encoding de sempre),
 * `marca` (o dourado, para fatos da marca) e `tinta` (o foreground, para o que
 * e observado e nao inferido). O dourado nunca codifica valor de dado.
 */

/** Geometria de UMA celula larga (viewBox 68x108). Os mesmos poligonos do mockup. */
const POLIGONOS: Readonly<Record<Segmento, string>> = {
  a: "14,4 54,4 60,10 54,16 14,16 8,10",
  b: "62,12 68,18 68,44 62,50 56,44 56,18",
  c: "62,58 68,64 68,90 62,96 56,90 56,64",
  d: "14,92 54,92 60,98 54,104 14,104 8,98",
  e: "6,58 12,64 12,90 6,96 0,90 0,64",
  f: "6,12 12,18 12,44 6,50 0,44 0,18",
  g: "14,48 54,48 60,54 54,60 14,60 8,54",
};

/**
 * O TRACO FINO, da vitrine (01/10/2026): a mesma celula 68x108 com segmento de
 * 4 unidades em vez de 12 e sem brilho. O Joao pediu o numero mais leve ao
 * lado de cartoes minimalistas; o que nao muda e a gramatica -- o apagado
 * continua desenhado (a 8%), `null` continua sem nenhum segmento aceso.
 */
const POLIGONOS_FINOS: Readonly<Record<Segmento, string>> = {
  a: "6,2 8,0 60,0 62,2 60,4 8,4",
  b: "66,6 68,8 68,48 66,50 64,48 64,8",
  c: "66,58 68,60 68,100 66,102 64,100 64,60",
  d: "6,106 8,104 60,104 62,106 60,108 8,108",
  e: "2,58 4,60 4,100 2,102 0,100 0,60",
  f: "2,6 4,8 4,48 2,50 0,48 0,8",
  g: "6,54 8,52 60,52 62,54 60,56 8,56",
};

export type TracoDoLED = "cheio" | "fino";

/** O brilho e UM filtro no grupo aceso; o traco fino nao tem brilho nenhum. */
const brilho = (traco: TracoDoLED) =>
  traco === "fino" ? undefined : { filter: "drop-shadow(0 0 3px currentColor)" };

const ORDEM: readonly Segmento[] = ["a", "b", "c", "d", "e", "f", "g"];

const LARGURA = 68;
const LARGURA_ESTREITA = 20;
const ALTURA = 108;

/**
 * `medido` e a cor de sempre. `erro` existe para um unico caso: o easter egg
 * da marca, que faz o numero MENTIR com o selo de aviso na tela (lib/mentira),
 * e o numero falso vai para o vermelho de erro -- quem nao le o selo percebe
 * que a tela mudou de regime.
 */
export type CorDoLED = "medido" | "marca" | "tinta" | "erro";

const COR: Record<CorDoLED, string> = {
  medido: "var(--medido)",
  marca: "var(--primary)",
  tinta: "var(--foreground)",
  erro: "var(--destructive)",
};

/** Um digito: os sete poligonos, apagados sempre, acesos por cima quando for o caso. */
function Digito({
  acesos,
  altura,
  espaco,
  traco,
}: {
  acesos: readonly Segmento[];
  altura: number;
  espaco: number;
  traco: TracoDoLED;
}) {
  const poligonos = traco === "fino" ? POLIGONOS_FINOS : POLIGONOS;
  const apagados = ORDEM.filter((s) => !acesos.includes(s));
  return (
    <svg
      aria-hidden
      focusable="false"
      viewBox={`0 0 ${LARGURA} ${ALTURA}`}
      height={altura}
      width={(altura * LARGURA) / ALTURA}
      style={{ marginRight: espaco, flex: "none", overflow: "visible" }}
      data-celula="digito"
    >
      <g fill="currentColor" opacity={traco === "fino" ? 0.08 : 0.1}>
        {apagados.map((s) => (
          <polygon key={s} points={poligonos[s]} />
        ))}
      </g>
      {/* O brilho e UM filtro no grupo aceso, e nao um por poligono: sete
          `drop-shadow` por digito, em vinte digitos, e custo sem retorno. */}
      <g fill="currentColor" style={brilho(traco)}>
        {acesos.map((s) => (
          <polygon key={s} points={poligonos[s]} data-aceso={s} />
        ))}
      </g>
    </svg>
  );
}

function Estreita({
  altura,
  espaco,
  children,
  nome,
  traco,
}: {
  altura: number;
  espaco: number;
  children: React.ReactNode;
  nome: string;
  traco: TracoDoLED;
}) {
  return (
    <svg
      aria-hidden
      focusable="false"
      viewBox={`0 0 ${LARGURA_ESTREITA} ${ALTURA}`}
      height={altura}
      width={(altura * LARGURA_ESTREITA) / ALTURA}
      style={{ marginRight: espaco, flex: "none", overflow: "visible" }}
      data-celula={nome}
    >
      <g fill="currentColor" style={brilho(traco)}>
        {children}
      </g>
    </svg>
  );
}

function Peca({
  celula,
  altura,
  espaco,
  traco,
}: {
  celula: Celula;
  altura: number;
  espaco: number;
  traco: TracoDoLED;
}) {
  const fino = traco === "fino";
  switch (celula.tipo) {
    case "digito":
      return <Digito acesos={celula.acesos} altura={altura} espaco={espaco} traco={traco} />;
    case "mais":
      return (
        <svg
          aria-hidden
          focusable="false"
          viewBox={`0 0 ${LARGURA} ${ALTURA}`}
          height={altura}
          width={(altura * LARGURA) / ALTURA}
          style={{ marginRight: espaco, flex: "none", overflow: "visible" }}
          data-celula="mais"
        >
          <g fill="currentColor" style={brilho(traco)}>
            <polygon points={(fino ? POLIGONOS_FINOS : POLIGONOS).g} />
            <polygon
              points={fino ? "34,26 36,28 36,80 34,82 32,80 32,28" : "28,26 34,20 40,26 40,82 34,88 28,82"}
            />
          </g>
        </svg>
      );
    case "virgula":
      // A virgula do pt-BR: o ponto com uma CAUDA que desce para a esquerda. E
      // o que separa `66,1` de `66.1` -- milhar, em pt-BR.
      return (
        <Estreita altura={altura} espaco={espaco} nome="virgula" traco={traco}>
          <circle cx={11} cy={fino ? 102 : 94} r={fino ? 4 : 7.5} />
          <polygon
            data-cauda
            points={fino ? "13,103 15,104 9,117 7,116" : "12,98 19,94 16,108 6,120 2,115 9,106"}
          />
        </Estreita>
      );
    case "ponto":
      return (
        <Estreita altura={altura} espaco={espaco} nome="ponto" traco={traco}>
          <circle cx={10} cy={fino ? 102 : 98} r={fino ? 4 : 7} />
        </Estreita>
      );
    case "doispontos":
      return (
        <Estreita altura={altura} espaco={espaco} nome="doispontos" traco={traco}>
          <circle cx={10} cy={36} r={fino ? 4 : 7} />
          <circle cx={10} cy={72} r={fino ? 4 : 7} />
        </Estreita>
      );
    case "espaco":
      return (
        <span
          aria-hidden
          data-celula="espaco"
          style={{ display: "inline-block", width: altura * 0.25, flex: "none" }}
        />
      );
    case "cru":
      return (
        <span
          aria-hidden
          data-celula="cru"
          className="font-mono"
          style={{
            fontSize: altura * 0.55,
            lineHeight: 1,
            marginRight: espaco,
            alignSelf: "flex-end",
          }}
        >
          {celula.texto}
        </span>
      );
  }
}

export function SegmentoLED({
  valor,
  rotulo,
  altura = 40,
  cor = "medido",
  celulas = 3,
  traco = "cheio",
  className,
}: {
  /** String JA formatada em pt-BR pelo chamador. `null` = sem sinal (nunca zero). */
  valor: string | null;
  /** Texto acessivel por extenso: "nota estimada", "latência mediana". Obrigatorio. */
  rotulo: string;
  /** Altura do display em px. */
  altura?: number;
  cor?: CorDoLED;
  /** Quantas celulas apagadas mostrar quando `valor` e `null`. */
  celulas?: number;
  /** `fino` so na vitrine: segmento delgado e sem brilho. */
  traco?: TracoDoLED;
  className?: string;
}) {
  const pecas = celulasDoValor(valor, celulas);
  const espaco = altura * 0.09;
  const legenda = valor === null ? `${rotulo}: sem sinal` : `${rotulo} ${valor}`;

  return (
    <span
      role="img"
      aria-label={legenda}
      data-slot="segmento-led"
      data-apagado={valor === null ? "true" : undefined}
      data-traco={traco}
      className={`inline-flex items-end ${className ?? ""}`.trim()}
      style={{ color: COR[cor], height: altura }}
    >
      {pecas.map((c, i) => (
        <Peca key={i} celula={c} altura={altura} espaco={espaco} traco={traco} />
      ))}
    </span>
  );
}
