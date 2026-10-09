import { FAMILIAS_DO_VETOR } from "../../components/lp/fatos";

/**
 * A MASCARA E OS NOS: a geometria da constelacao da vitrine antiga
 * (`construirCeu`, no antigo `lib/vitrine/motor.ts`), portada para a cena vgpu.
 *
 * Tudo em unidades de MASCARA (raio vertical 1, centro 0): a cena escala e
 * posiciona no orbe. A mascara e um oval com olhos e boca VAZIOS -- o que a
 * cortesia esconde --, ambar a esquerda (o dito) e azul a direita (o medido).
 * Os nos sao um por feature, agrupados na contagem REAL de cada familia, com
 * folga entre familias: quem contar os nos le o vetor de verdade.
 */
export const MASCARA = {
  rx: 0.68,
  ry: 1,
  /** [centro x, centro y, semieixo x, semieixo y] dos dois olhos e da boca. */
  vazios: [
    [-0.36 * 0.68, -0.12, 0.2 * 0.68, 0.055],
    [0.36 * 0.68, -0.12, 0.2 * 0.68, 0.055],
    [0, 0.42, 0.26 * 0.68, 0.03],
  ] as ReadonlyArray<readonly [number, number, number, number]>,
};

function gauss(aleatorio: () => number): number {
  const u = Math.max(1e-9, aleatorio());
  return Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * aleatorio());
}

function noVazio(x: number, y: number): boolean {
  return MASCARA.vazios.some(([vx, vy, ax, ay]) => ((x - vx) / ax) ** 2 + ((y - vy) / ay) ** 2 < 1);
}

/** Um ponto da mascara: 20% no contorno, 10% contornando olhos e boca, o resto no rosto. */
export function pontoDaMascara(aleatorio: () => number): [number, number] {
  const { rx, ry, vazios } = MASCARA;
  const r = aleatorio();
  if (r < 0.2) {
    const t = aleatorio() * Math.PI * 2;
    const k = 1 - Math.abs(gauss(aleatorio)) * 0.02;
    return [Math.cos(t) * rx * k, Math.sin(t) * ry * k];
  }
  if (r < 0.3) {
    const [vx, vy, ax, ay] = vazios[Math.floor(aleatorio() * vazios.length)];
    const t = aleatorio() * Math.PI * 2;
    return [vx + Math.cos(t) * ax * 1.18, vy + Math.sin(t) * ay * 1.35];
  }
  for (let tentativa = 0; tentativa < 40; tentativa++) {
    const x = (aleatorio() * 2 - 1) * rx;
    const y = (aleatorio() * 2 - 1) * ry;
    if ((x / rx) ** 2 + (y / ry) ** 2 < 1 && !noVazio(x, y)) return [x, y];
  }
  return [0, ry * 0.8];
}

export type No = { x: number; y: number; familia: string };

/** Os nos: um por feature, num anel de raio ~0.85, com folga de 1.8 unidades entre familias. */
export function nosDasFeatures(): No[] {
  const total = FAMILIAS_DO_VETOR.reduce((t, f) => t + f.qtd, 0);
  const unidade = (Math.PI * 2) / (total + FAMILIAS_DO_VETOR.length * 1.8);
  const nos: No[] = [];
  let ang = -Math.PI / 2;
  for (const f of FAMILIAS_DO_VETOR) {
    for (let j = 0; j < f.qtd; j++) {
      const raio = 0.85 * (j % 2 ? 1.06 : 0.95);
      nos.push({ x: Math.cos(ang) * raio, y: Math.sin(ang) * raio * 0.92, familia: f.chave });
      ang += unidade;
    }
    ang += unidade * 1.8;
  }
  return nos;
}
