import type { Pesos } from "./fases";

/**
 * O ORBE DA VITRINE ANTIGA na LP nova, parte pura: dado o peso de cada
 * momento da historia, como o orbe esta. O shader (`shaders/orbe.wgsl`) so
 * desenha estes canais; a coreografia mora aqui, testavel sem GPU.
 *
 * O orbe e um objeto so que atravessa a pagina: grande no hero, pequeno no
 * canto enquanto a mascara se forma (o rosto precisa ler), de volta ao centro
 * quando os nos caem no fusor, cinza e parado na leitura sem sinal, grande de
 * novo no fecho. A cor e canal com dono: ambar e o DITO, azul e o MEDIDO; o
 * magenta e cenografia. Tabela herdada da vitrine antiga (`lib/vitrine/coreografia.ts`, removida
 * em 09/10/2026 quando esta LP virou a raiz).
 */
export type EstadoDoOrbe = {
  /** Raio relativo ao do hero (1). */
  escala: number;
  /** 0 no foco do palco, 1 no canto de cima. */
  noCanto: number;
  /** 1 colorido, 0 cinza. */
  saturacao: number;
  /** Afastamento das tres manchas; 0 as junta paradas no centro. */
  afastamento: number;
  /** Intensidade dos tracos de fosforo no fundo. */
  tracos: number;
  /** 1 apaga o traco do dito: o cliente nao escreveu. */
  apagaDito: number;
  /** Peso de cada mancha. */
  dito: number;
  medido: number;
  halo: number;
};

type Paleta = Pick<EstadoDoOrbe, "dito" | "medido" | "halo">;
const EQUILIBRIO: Paleta = { dito: 1, medido: 1, halo: 1 };
const DITO: Paleta = { dito: 1.3, medido: 0.5, halo: 0.55 };
const MEDIDO: Paleta = { dito: 0.45, medido: 1.4, halo: 0.55 };
const SISTEMA: Paleta = { dito: 0.75, medido: 1.15, halo: 0.85 };
const FECHO: Paleta = { dito: 1.35, medido: 0.7, halo: 0.7 };

const vivo = { saturacao: 1, apagaDito: 0 };

const ESTADOS: Record<"frase" | "disperso" | "mascara" | "nos" | "orbe" | "leitura", EstadoDoOrbe> = {
  frase: { escala: 1, noCanto: 0, afastamento: 1, tracos: 1, ...vivo, ...EQUILIBRIO },
  // A conversa entra: o ambar do que foi dito domina.
  disperso: { escala: 0.85, noCanto: 0, afastamento: 1, tracos: 0.9, ...vivo, ...DITO },
  mascara: { escala: 0.18, noCanto: 1, afastamento: 0.6, tracos: 0.3, ...vivo, ...DITO },
  nos: { escala: 0.22, noCanto: 0, afastamento: 0.45, tracos: 0.25, ...vivo, ...MEDIDO },
  orbe: { escala: 0.45, noCanto: 0, afastamento: 1.35, tracos: 0.25, ...vivo, ...MEDIDO },
  leitura: { escala: 0.4, noCanto: 0, afastamento: 1, tracos: 0.55, ...vivo, ...SISTEMA },
};
const NO_FECHO: EstadoDoOrbe = { escala: 1, noCanto: 0, afastamento: 1, tracos: 0.8, ...vivo, ...FECHO };

const CANAIS = Object.keys(NO_FECHO) as (keyof EstadoDoOrbe)[];

/**
 * Sem `humor` de proposito: a cor do humor e das particulas; o orbe so
 * distingue COM sinal de SEM sinal (`cinza`), porque ausencia nao e um humor.
 */
export function estadoDoOrbe(p: Pesos, cinza: number): EstadoDoOrbe {
  const saida = Object.fromEntries(CANAIS.map((c) => [c, 0])) as EstadoDoOrbe;
  for (const fase of Object.keys(ESTADOS) as (keyof typeof ESTADOS)[]) {
    for (const c of CANAIS) saida[c] += ESTADOS[fase][c] * p[fase];
  }
  for (const c of CANAIS) saida[c] += (NO_FECHO[c] - saida[c]) * p.respira;
  const ausente = Math.min(1, Math.max(0, cinza)) * p.leitura;
  saida.saturacao *= 1 - ausente;
  saida.afastamento *= 1 - ausente;
  saida.apagaDito = Math.max(saida.apagaDito, ausente);
  return saida;
}
