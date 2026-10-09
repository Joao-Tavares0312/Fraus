/**
 * A COREOGRAFIA DA LP NOVA, parte pura: dado o progresso da rolagem em [0, 1],
 * quanto cada momento da historia pesa no destino das particulas.
 *
 * O shader nao conhece secao nenhuma -- ele recebe estes pesos e mistura os
 * destinos. Assim a ordem da historia (frase, dispersao, enxames, fusor,
 * leitura, recuo, fecho) e testavel aqui, e trocar o ritmo da pagina nao
 * exige mexer em WGSL.
 */
export const MARCOS = {
  frase: 0,
  disperso: 0.14,
  enxame: 0.34,
  orbe: 0.5,
  leitura: 0.66,
  recuo: 0.8,
  fecho: 1,
} as const;

export type Pesos = {
  frase: number;
  disperso: number;
  enxame: number;
  orbe: number;
  leitura: number;
  /** Intensidade global do campo; cai na secao do analista. */
  brilho: number;
  /** Respiracao do orbe no fecho. */
  respira: number;
};

type Destino = "frase" | "disperso" | "enxame" | "orbe" | "leitura";

// A leitura segura o campo ate depois do recuo; o fecho devolve tudo ao orbe.
const CHAVES: ReadonlyArray<[number, Destino]> = [
  [MARCOS.frase, "frase"],
  [MARCOS.disperso, "disperso"],
  [MARCOS.enxame, "enxame"],
  [MARCOS.orbe, "orbe"],
  [MARCOS.leitura, "leitura"],
  [0.88, "leitura"],
  [MARCOS.fecho, "orbe"],
];

function suave(t: number): number {
  const x = Math.min(1, Math.max(0, t));
  return x * x * (3 - 2 * x);
}

function rampa(p: number, de: number, ate: number): number {
  return suave((p - de) / (ate - de));
}

export function pesosDasFases(progresso: number): Pesos {
  const p = Math.min(1, Math.max(0, progresso));
  const pesos: Pesos = { frase: 0, disperso: 0, enxame: 0, orbe: 0, leitura: 0, brilho: 1, respira: 0 };

  let i = 0;
  while (i < CHAVES.length - 2 && p > CHAVES[i + 1][0]) i++;
  const [inicio, de] = CHAVES[i];
  const [fim, para] = CHAVES[i + 1];
  const t = rampa(p, inicio, fim);
  pesos[de] += 1 - t;
  pesos[para] += t;

  pesos.brilho = 1 - 0.7 * rampa(p, 0.72, MARCOS.recuo) + 0.7 * rampa(p, 0.88, 0.96);
  pesos.respira = rampa(p, 0.9, MARCOS.fecho);
  return pesos;
}
