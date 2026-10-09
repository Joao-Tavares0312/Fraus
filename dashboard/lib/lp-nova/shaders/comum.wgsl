// O vocabulario compartilhado da cena: a particula, o quadro e as cores com dono.
//
// Espaco da cena: y em [-1, 1] (de baixo para cima) e x em [-aspecto, aspecto].
// As cores sao as da vitrine (`lib/vitrine/motor.ts`): ambar e o DITO, azul e o
// MEDIDO, magenta so no halo do orbe. Familia nao ganha cor propria.

export struct Particula {
  pos: vec2f,
  vel: vec2f,
  origem: vec2f,
  familia: u32,
  semente: f32,
  tinta: f32,
  vida: f32,
}

export struct Cena {
  tempo: f32,
  dt: f32,
  aspecto: f32,
  total: u32,
  // pesos de destino: frase, disperso, enxame, orbe
  destino: vec4f,
  // leitura, brilho, respira, humor (-1 detrator .. 1 promotor)
  leitura: vec4f,
  // foco do orbe (xy), raio do orbe (z), cinza da leitura sem sinal (w)
  foco: vec4f,
  // tamanho do ponto em unidades de cena (x), escala dos enxames (y)
  ponto: vec4f,
  centros: array<vec4f, 7>,
}

export const DITO: vec3f = vec3f(1.0, 0.6, 0.16);
export const MEDIDO: vec3f = vec3f(0.22, 0.5, 1.0);
export const HALO: vec3f = vec3f(0.8, 0.18, 0.75);
export const FUNDO: vec3f = vec3f(0.04, 0.04, 0.047);
