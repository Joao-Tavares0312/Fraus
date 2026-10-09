import { nosDasFeatures, pontoDaMascara } from "./constelacao";
import { distribuirEnxames } from "./enxames";
import { pesosDasFases } from "./fases";
import { estadoDoOrbe } from "./orbe";

/**
 * A PARTE PURA DA CENA: o que vai para a GPU, sem DOM e sem GPU.
 *
 * Mora aqui para a cena do navegador (`cena.ts`) e o script dos posteres
 * (`scripts/renderizar-posteres.ts`) montarem o MESMO quadro: o poster de
 * quem nao tem WebGPU sai do mesmo WGSL e dos mesmos uniforms da cena viva.
 */
export const BYTES_POR_PARTICULA = 56; // Particula em comum.wgsl: 5 x vec2f + u32 + 3 x f32

/** mulberry32: aleatorio reproduzivel, para o poster sair igual toda vez. */
export function aleatorioComSemente(semente: number): () => number {
  let a = semente >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const ORDEM_FAMILIAS = distribuirEnxames(7).map((e) => e.chave);

const NOS = nosDasFeatures();

/**
 * O estado inicial de cada particula. Alem da origem (o glifo da frase), cada
 * uma ja nasce sabendo o seu ponto na MASCARA e o seu NO -- um no da propria
 * familia, distribuido em rodizio, para os nos de uma familia grande ficarem
 * tao cheios quanto os de uma pequena. A geometria da constelacao e y-para-
 * baixo (tela); a cena e y-para-cima, entao o y e invertido aqui, uma vez.
 */
export function sementeDasParticulas(total: number, origens: Float32Array, aleatorio: () => number): ArrayBuffer {
  const bruto = new ArrayBuffer(total * BYTES_POR_PARTICULA);
  const f32 = new Float32Array(bruto);
  const u32 = new Uint32Array(bruto);
  for (const enxame of distribuirEnxames(total)) {
    const familia = ORDEM_FAMILIAS.indexOf(enxame.chave);
    const nosDaFamilia = NOS.filter((n) => n.familia === enxame.chave);
    for (let i = enxame.inicio; i < enxame.inicio + enxame.particulas; i++) {
      const b = (i * BYTES_POR_PARTICULA) / 4;
      const [mx, my] = pontoDaMascara(aleatorio);
      const no = nosDaFamilia[(i - enxame.inicio) % nosDaFamilia.length];
      f32[b] = origens[i * 2];
      f32[b + 1] = origens[i * 2 + 1];
      f32[b + 4] = origens[i * 2];
      f32[b + 5] = origens[i * 2 + 1];
      f32[b + 6] = mx;
      f32[b + 7] = -my;
      f32[b + 8] = no.x;
      f32[b + 9] = -no.y;
      u32[b + 10] = familia;
      f32[b + 11] = aleatorio();
    }
  }
  return bruto;
}

export type EntradaQuadro = {
  aspecto: number;
  alturaPx: number;
  total: number;
  celular: boolean;
  progresso: number;
  humor: number;
  cinza: number;
  tempo: number;
  dt: number;
  /** Quanto a pagina rolou: a frase do hero sobe junto com o texto. */
  rolagemPx: number;
};

export function uniformesDoQuadro(e: EntradaQuadro) {
  const p = pesosDasFases(e.progresso);
  // Desktop: o orbe mora no terco direito, ao lado do texto. Celular: no alto.
  const foco = e.celular ? [0, 0.42] : [e.aspecto * 0.42, 0];
  const raio = e.celular ? 0.24 : 0.3;
  const escala = e.celular ? 0.8 : 1;
  // Raio da mascara em unidades de cena: ela ocupa o palco ao lado do texto.
  const mascara = e.celular ? 0.42 : 0.66;
  // O orbe da vitrine antiga: o mesmo foco, mas raio e canto proprios.
  const o = estadoDoOrbe(p, e.cinza);
  const canto = e.celular ? [e.aspecto * 0.72, 0.82] : [e.aspecto * 0.84, 0.72];
  const raioDoHero = e.celular ? 0.32 : 0.56;
  return {
    tempo: e.tempo,
    dt: e.dt,
    aspecto: e.aspecto,
    total: e.total,
    destino: [p.frase, p.disperso, p.mascara, p.nos],
    // extra.y: a rolagem em unidades de cena (a tela inteira mede 2).
    extra: [p.orbe, (e.rolagemPx / Math.max(1, e.alturaPx)) * 2, 0, 0],
    leitura: [p.leitura, p.brilho, p.respira, e.humor],
    foco: [foco[0], foco[1], raio, e.cinza],
    // Ganho de alfa: a luz somada do campo fica parecida com 4 mil ou 120 mil.
    ponto: [((e.celular ? 2.2 : 1.6) / Math.max(1, e.alturaPx)) * 2, escala, Math.min(1, 6000 / e.total), mascara],
    // Desktop: metade direita, o texto mora na esquerda. Celular: faixa de cima.
    campo: e.celular ? [0, 0.55, e.aspecto * 0.95, 0.4] : [e.aspecto * 0.5, 0, e.aspecto * 0.5, 0.9],
    // Tela em pixels CSS, intensidade dos tracos e o apagar do traco do dito.
    fosforo: [e.aspecto * e.alturaPx, e.alturaPx, o.tracos * p.brilho, o.apagaDito],
    // Centro do orbe (xy), raio (z) e saturacao (w).
    orbe: [
      foco[0] + (canto[0] - foco[0]) * o.noCanto,
      foco[1] + (canto[1] - foco[1]) * o.noCanto,
      raioDoHero * o.escala,
      o.saturacao,
    ],
    // Peso das manchas: ambar (dito), azul (medido), magenta (halo); afastamento (w).
    paleta: [o.dito, o.medido, o.halo, o.afastamento],
  };
}
