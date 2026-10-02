/**
 * A COREOGRAFIA DA VITRINE, na parte pura: o que o orbe e a constelacao
 * fazem em cada ponto da rolagem. O motor (`motor.ts`) mede o DOM e desenha;
 * aqui so ha conta, testavel sem navegador.
 *
 * O ORBE E UM OBJETO SO que atravessa a pagina: grande no hero, pequeno no
 * canto enquanto as palavras se juntam, no centro do palco quando vira o
 * fusor, cinza e parado no "sem sinal", de volta no fecho. Cada estado e um
 * ponto num espaco de canais, e a rolagem interpola entre eles.
 *
 * A COR TAMBEM E CANAL, e com dono (pedido do Joao, 01/10/2026): o peso de
 * cada mancha muda por secao. Ambar e o DITO, azul e o MEDIDO -- o encoding
 * de sempre. Na entrada da conversa o ambar domina, no fusor o azul, no fecho
 * ("o cliente mente") o ambar volta. O magenta e cenografia e so oscila. No
 * "sem sinal" a saturacao vai a zero: ausencia e cinza, fora da escala.
 */

export type EstadoDoOrbe = {
  /** Centro, em fracao da viewport (0..1, y para baixo). */
  x: number;
  y: number;
  /** Raio, em fracao do menor lado da viewport. */
  r: number;
  /** Saturacao: 1 colorido, 0 cinza (sem sinal). */
  sat: number;
  /** Afastamento das tres manchas. */
  sp: number;
  /** Velocidade do giro: 0 para o orbe. */
  vel: number;
  /** Intensidade dos tracos de fosforo no fundo. */
  tr: number;
  /** 1 apaga o canal do dito no fosforo (o cliente nao escreveu). */
  A: number;
  /** Peso de cada mancha: ambar (dito), azul (medido), magenta (cenografia). */
  dito: number;
  medido: number;
  halo: number;
};

const CANAIS: readonly (keyof EstadoDoOrbe)[] = [
  "x", "y", "r", "sat", "sp", "vel", "tr", "A", "dito", "medido", "halo",
];

/** Prende em [0, 1]. NaN vai ao extremo seguro (0), nunca propaga. */
export function grampear01(t: number): number {
  if (Number.isNaN(t)) return 0;
  return Math.max(0, Math.min(1, t));
}

/** Curva suave (smoothstep) para as transicoes nao terem quina. */
export function suave(t: number): number {
  const u = grampear01(t);
  return u * u * (3 - 2 * u);
}

export function misturar(a: EstadoDoOrbe, b: EstadoDoOrbe, t: number): EstadoDoOrbe {
  const saida = { ...a };
  for (const c of CANAIS) saida[c] = a[c] + (b[c] - a[c]) * t;
  return saida;
}

type Paleta = Pick<EstadoDoOrbe, "dito" | "medido" | "halo">;
const EQUILIBRIO: Paleta = { dito: 1, medido: 1, halo: 1 };
const DITO: Paleta = { dito: 1.3, medido: 0.5, halo: 0.55 };
const MEDIDO: Paleta = { dito: 0.45, medido: 1.4, halo: 0.55 };
const SISTEMA: Paleta = { dito: 0.75, medido: 1.15, halo: 0.85 };
const FECHO: Paleta = { dito: 1.35, medido: 0.7, halo: 0.7 };

/**
 * Os estados nomeados, por largura. `nucleo`, `fusor` e `vazio` tem x/y
 * provisorios: o motor os sobrescreve com o centro medido do palco e da
 * ancora do "sem sinal".
 */
export const ESTADOS_DO_ORBE = {
  largo: {
    hero: { x: 0.72, y: 0.46, r: 0.34, sat: 1, sp: 1, vel: 1, tr: 1, A: 0, ...EQUILIBRIO },
    canto: { x: 0.92, y: 0.15, r: 0.05, sat: 1, sp: 0.6, vel: 1, tr: 0.3, A: 0, ...DITO },
    nucleo: { x: 0.7, y: 0.5, r: 0.07, sat: 1, sp: 0.45, vel: 1, tr: 0.25, A: 0, ...MEDIDO },
    fusor: { x: 0.7, y: 0.5, r: 0.15, sat: 1, sp: 1.35, vel: 1, tr: 0.25, A: 0, ...MEDIDO },
    vazio: { x: 0.75, y: 0.5, r: 0.12, sat: 0, sp: 0, vel: 0, tr: 0.55, A: 1, ...EQUILIBRIO },
    sistema: { x: 0.95, y: 0.12, r: 0.045, sat: 1, sp: 0.8, vel: 1, tr: 0.5, A: 0, ...SISTEMA },
    fecho: { x: 0.76, y: 0.52, r: 0.3, sat: 1, sp: 1, vel: 1, tr: 0.8, A: 0, ...FECHO },
  },
  estreito: {
    hero: { x: 0.5, y: 0.19, r: 0.3, sat: 1, sp: 1, vel: 1, tr: 1, A: 0, ...EQUILIBRIO },
    canto: { x: 0.88, y: 0.1, r: 0.06, sat: 1, sp: 0.6, vel: 1, tr: 0.3, A: 0, ...DITO },
    nucleo: { x: 0.5, y: 0.3, r: 0.08, sat: 1, sp: 0.45, vel: 1, tr: 0.25, A: 0, ...MEDIDO },
    fusor: { x: 0.5, y: 0.3, r: 0.17, sat: 1, sp: 1.35, vel: 1, tr: 0.25, A: 0, ...MEDIDO },
    vazio: { x: 0.5, y: 0.3, r: 0.13, sat: 0, sp: 0, vel: 0, tr: 0.55, A: 1, ...EQUILIBRIO },
    sistema: { x: 0.9, y: 0.1, r: 0.05, sat: 1, sp: 0.8, vel: 1, tr: 0.5, A: 0, ...SISTEMA },
    fecho: { x: 0.7, y: 0.28, r: 0.3, sat: 1, sp: 1, vel: 1, tr: 0.8, A: 0, ...FECHO },
  },
} satisfies Record<"largo" | "estreito", Record<string, EstadoDoOrbe>>;

/**
 * Trechos da secao fixada: [inicio, fim, estagio no inicio, estagio no fim].
 * Estagio 1 = palavras, 2 = mascara, 3 = 39 nos, 4 = dentro do fusor. Os
 * platos (estagio igual nas duas pontas) seguram cada forma para ser lida.
 */
const TRECHOS: readonly (readonly [number, number, number, number])[] = [
  [0, 0.12, 1, 1],
  [0.12, 0.32, 1, 2],
  [0.32, 0.42, 2, 2],
  [0.42, 0.6, 2, 3],
  [0.6, 0.72, 3, 3],
  [0.72, 0.86, 3, 4],
  [0.86, 1, 4, 4],
];

/** Progresso dentro da secao fixada (0..1) -> estagio continuo (1..4). */
export function estagioDaConstelacao(progresso: number): number {
  const p = grampear01(progresso);
  for (const [a, b, ka, kb] of TRECHOS) {
    if (p <= b) return ka + (kb - ka) * suave((p - a) / (b - a));
  }
  return 4;
}

export type Quadro = { y: number; estado: () => EstadoDoOrbe };

/** Estado do orbe na rolagem `y`, interpolando entre os quadros vizinhos. */
export function orbeEntreQuadros(quadros: readonly Quadro[], y: number): EstadoDoOrbe {
  if (y <= quadros[0].y) return quadros[0].estado();
  for (let i = 0; i < quadros.length - 1; i++) {
    const a = quadros[i];
    const b = quadros[i + 1];
    if (y <= b.y) return misturar(a.estado(), b.estado(), suave((y - a.y) / (b.y - a.y)));
  }
  return quadros[quadros.length - 1].estado();
}

/** Garante quadros em ordem estrita: um quadro nunca vem antes do anterior. */
export function monotonizar(ys: readonly number[]): number[] {
  const saida = [...ys];
  for (let i = 1; i < saida.length; i++) saida[i] = Math.max(saida[i], saida[i - 1] + 1);
  return saida;
}
