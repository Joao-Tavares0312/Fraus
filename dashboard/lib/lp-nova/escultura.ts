/** Contornos do SVG oficial, normalizados para 400×302. Curvas subdivididas
 * com desvio maximo de 0,16 no original; fenda de 18 unidades ja subtraida.
 * As cinco placas sao arte da marca, nunca familias ou features do modelo. */
type Ponto = readonly [number, number];
type Contorno = { readonly direcao: -1 | 1; readonly pontos: readonly Ponto[] };

export const CONTORNOS_FR: readonly Contorno[] = [
  { direcao: -1, pontos: [[67.349,258.076],[67.349,301.056],[20.033,301.056],[20.033,288.569]] },
  { direcao: -1, pontos: [[0,0.747],[260.908,0.747],[221.307,43.554],[67.349,43.554],[67.349,124.081],[172.102,124.066],[134.113,166.873],[67.349,166.85],[67.349,238.53],[20.033,269.022],[20.033,36.322],[19.841,32.495],[19.27,28.735],[18.332,25.069],[17.038,21.521],[15.399,18.119],[13.427,14.889],[11.132,11.858],[8.525,9.051]] },
  { direcao: 1, pontos: [[310.864,124.013],[314.89,123.809],[318.8,123.212],[322.575,122.24],[326.193,120.914],[329.637,119.255],[332.885,117.28],[335.919,115.011],[338.717,112.468],[341.261,109.67],[343.529,106.636],[345.504,103.388],[347.164,99.944],[348.489,96.325],[349.461,92.551],[350.058,88.641],[350.262,84.615],[350.058,80.574],[349.461,76.618],[349.385,76.32],[387.411,51.814],[387.511,52.025],[390.31,59.757],[392.362,67.798],[393.623,76.099],[394.053,84.615],[393.623,93.116],[392.362,101.372],[390.31,109.342],[387.511,116.983],[384.006,124.254],[379.838,131.113],[375.047,137.518],[369.676,143.427],[363.767,148.798],[357.362,153.589],[350.503,157.757],[343.232,161.262],[335.591,164.061],[327.621,166.113],[319.365,167.374],[310.864,167.804],[277.582,167.804],[400,301.59],[337.398,301.365],[214.383,163.321],[275.379,124.013]] },
  // O recorte atravessa o R duas vezes: arco superior e pe da haste sao ilhas
  // separadas. Uma ponte de largura zero entre elas nao e um poligono simples;
  // arredonda-la ainda cria auto-intersecoes. Cada fronteira e extrudada so uma vez.
  { direcao: 1, pontos: [[342.746,61.052],[341.261,58.981],[338.717,56.05],[335.919,53.373],[332.885,50.975],[329.637,48.88],[326.193,47.112],[322.575,45.696],[318.8,44.654],[314.89,44.011],[310.864,43.791],[296.043,43.791],[238.056,43.84],[277.904,0],[310.864,0],[315.143,0.112],[319.365,0.446],[327.621,1.753],[335.591,3.874],[343.232,6.765],[350.503,10.378],[357.362,14.667],[363.767,19.587],[369.676,25.09],[375.047,31.132],[379.58,37.314]] },
  { direcao: 1, pontos: [[203.319,150.905],[179.355,124.013],[245.048,124.013]] },
];

// x/y/z da camera, distancia, abertura, escala, deslocamento x, desvio das placas.
export const POSES_FR = [
  [-8, -18, -8, 21, 0, 1.22, 8, 0],
  [-14, -35, -8, 58, 12, 1.04, 4, 0],
  [8, -48, -16, 48, 24, 1.28, 18, 4],
  [-8, -20, -5, 38, 8, 1.10, 0, 2],
] as const;

function produto(a: Ponto, b: Ponto, c: Ponto) {
  return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]);
}

/** Ear clipping: respeita concavidades e a fenda, sem leque cruzando o vazio do R. */
function triangular(pontos: readonly Ponto[]) {
  const indices = pontos.map((_, i) => i);
  const area = pontos.reduce((soma, p, i) => {
    const q = pontos[(i + 1) % pontos.length];
    return soma + p[0] * q[1] - q[0] * p[1];
  }, 0);
  if (area < 0) indices.reverse();
  const triangulos: number[] = [];
  while (indices.length > 3) {
    let cortou = false;
    for (let i = 0; i < indices.length; i++) {
      const a = indices[(i + indices.length - 1) % indices.length];
      const b = indices[i];
      const c = indices[(i + 1) % indices.length];
      if (produto(pontos[a], pontos[b], pontos[c]) <= 1e-8) continue;
      if (indices.some((j) => j !== a && j !== b && j !== c &&
        produto(pontos[a], pontos[b], pontos[j]) >= -1e-8 &&
        produto(pontos[b], pontos[c], pontos[j]) >= -1e-8 &&
        produto(pontos[c], pontos[a], pontos[j]) >= -1e-8)) continue;
      triangulos.push(a, b, c);
      indices.splice(i, 1);
      cortou = true;
      break;
    }
    if (!cortou) throw new Error("Contorno FR nao pode ser triangulado sem cruzar sua silhueta.");
  }
  triangulos.push(...indices);
  return { triangulos, borda: area < 0 ? [...pontos].reverse() : pontos };
}

/** Um unico buffer intercalado: posicao xyz + placa/letra/superficie/luz.
 * Tipo de superficie: corpo=0, F=1, R=2, dorso=3; arestas usam tipo+4. */
export function criarVerticesFR() {
  const vertices: number[] = [];
  const contornos = CONTORNOS_FR.map(({ pontos, direcao }) => ({ pontos, direcao, ...triangular(pontos) }));
  // Todas as poses olham o mesmo hemisferio: placas proximas primeiro permitem
  // rejeitar fragmentos ocultos pelo depth test antes de executar o material.
  for (let placa = 4; placa >= 0; placa--) {
    for (const { pontos, direcao, triangulos, borda } of contornos) {
      const material = placa === 1 || placa === 4 ? (direcao === -1 ? 1 : 2) : 0;
      const adicionar = (p: Ponto, z: number, superficie: number, luz = 1) => {
        vertices.push(p[0], p[1], z, placa - 2, direcao, superficie, luz);
      };
      for (const i of triangulos) adicionar(pontos[i], 9, material);
      for (let i = 0; i < triangulos.length; i += 3) {
        adicionar(pontos[triangulos[i]], -9, 3);
        adicionar(pontos[triangulos[i + 2]], -9, 3);
        adicionar(pontos[triangulos[i + 1]], -9, 3);
      }
      for (let i = 0; i < borda.length; i++) {
        const a = borda[i], b = borda[(i + 1) % borda.length];
        const angulo = Math.atan2(b[1] - a[1], b[0] - a[0]);
        const luz = 0.7 + 0.27 * Math.sin(angulo - Math.PI / 4);
        adicionar(a, -9, material + 4, luz); adicionar(b, -9, material + 4, luz); adicionar(b, 9, material + 4, luz);
        adicionar(a, -9, material + 4, luz); adicionar(b, 9, material + 4, luz); adicionar(a, 9, material + 4, luz);
      }
    }
  }
  return new Float32Array(vertices);
}
