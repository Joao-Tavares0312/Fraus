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
}: {
  acesos: readonly Segmento[];
  altura: number;
  espaco: number;
}) {
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
      <g fill="currentColor" opacity={0.1}>
        {apagados.map((s) => (
          <polygon key={s} points={POLIGONOS[s]} />
        ))}
      </g>
      {/* O brilho e UM filtro no grupo aceso, e nao um por poligono: sete
          `drop-shadow` por digito, em vinte digitos, e custo sem retorno. */}
      <g fill="currentColor" style={{ filter: "drop-shadow(0 0 3px currentColor)" }}>
        {acesos.map((s) => (
          <polygon key={s} points={POLIGONOS[s]} data-aceso={s} />
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
}: {
  altura: number;
  espaco: number;
  children: React.ReactNode;
  nome: string;
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
      <g fill="currentColor" style={{ filter: "drop-shadow(0 0 3px currentColor)" }}>
        {children}
      </g>
    </svg>
  );
}

function Peca({
  celula,
  altura,
  espaco,
}: {
  celula: Celula;
  altura: number;
  espaco: number;
}) {
  switch (celula.tipo) {
    case "digito":
      return <Digito acesos={celula.acesos} altura={altura} espaco={espaco} />;
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
          <g fill="currentColor" style={{ filter: "drop-shadow(0 0 3px currentColor)" }}>
            <polygon points={POLIGONOS.g} />
            <polygon points="28,26 34,20 40,26 40,82 34,88 28,82" />
          </g>
        </svg>
      );
    case "virgula":
      return (
        <Estreita altura={altura} espaco={espaco} nome="virgula">
          <circle cx={10} cy={98} r={7} />
        </Estreita>
      );
    case "doispontos":
      return (
        <Estreita altura={altura} espaco={espaco} nome="doispontos">
          <circle cx={10} cy={36} r={7} />
          <circle cx={10} cy={72} r={7} />
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
      className={`inline-flex items-end ${className ?? ""}`.trim()}
      style={{ color: COR[cor], height: altura }}
    >
      {pecas.map((c, i) => (
        <Peca key={i} celula={c} altura={altura} espaco={espaco} />
      ))}
    </span>
  );
}
