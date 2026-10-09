import { Cena, Particula } from "./comum.wgsl";
import { simplex3d } from "@vgpu/wgsl-std/noise/simplex";
import { hash2 } from "@vgpu/wgsl-std/hash";

@group(0) @binding(0) var<uniform> cena: Cena;
@group(0) @binding(1) var<storage, read_write> particulas: array<Particula>;

// Rotacional de um potencial de ruido: um campo sem divergencia, que mexe as
// particulas sem juntar nem esvaziar regioes -- o "ruido ambar" da dispersao.
fn curl(p: vec2f, t: f32) -> vec2f {
  let e = 0.01;
  let a = simplex3d(vec3f(p.x, p.y + e, t));
  let b = simplex3d(vec3f(p.x, p.y - e, t));
  let c = simplex3d(vec3f(p.x + e, p.y, t));
  let d = simplex3d(vec3f(p.x - e, p.y, t));
  return vec2f(a - b, -(c - d)) / (2.0 * e);
}

// Angulo e raio de hashes INDEPENDENTES: tirados da mesma semente por
// multiplicacao, eles se correlacionam e o disco vira braco de espiral.
fn em_volta(centro: vec2f, raio: f32, semente: f32, giro: f32, canal: f32) -> vec2f {
  let h = hash2(vec2f(semente, canal));
  let ang = h.x * 6.2831853 + cena.tempo * giro * (0.6 + 0.8 * h.y);
  let r = raio * sqrt(h.y);
  return centro + vec2f(cos(ang), sin(ang)) * r;
}

@compute @workgroup_size(64)
fn main(@builtin(global_invocation_id) id: vec3u) {
  let i = id.x;
  if (i >= cena.total) { return; }
  var p = particulas[i];

  let w = cena.destino;
  let leitura = cena.leitura.x;
  let humor = cena.leitura.w;
  let escala = cena.ponto.y;
  let foco = cena.foco.xy;

  // Destinos de cada momento da historia.
  // O campo espalhado mora do lado do orbe, nunca debaixo do texto.
  let espalhado = cena.campo.xy + (hash2(vec2f(p.semente, 3.0)) * 2.0 - 1.0) * cena.campo.zw;
  // A constelacao da vitrine antiga: a mascara e os nos, ao redor do orbe.
  let raio_mascara = cena.ponto.w;
  let respiro = 1.0 + 0.012 * sin(cena.tempo * 0.9 + p.semente * 6.0);
  let mascara = foco + p.mascara * raio_mascara * respiro;
  let no = em_volta(foco + p.no * raio_mascara, 0.022 * escala, p.semente, 0.6, 1.0);
  let orbe = em_volta(foco, cena.foco.z * (0.55 + 0.25 * cena.leitura.z * sin(cena.tempo * 1.4)), p.semente, 0.12, 2.0);

  let peso_orbe = cena.extra.x;
  // A origem e da pagina no topo; o canvas e fixo, entao ela sobe com a rolagem.
  let origem = p.origem + vec2f(0.0, cena.extra.y);
  let alvo = origem * w.x + espalhado * (w.y + leitura) + mascara * w.z + no * w.w + orbe * peso_orbe;

  // Agitacao: forte na dispersao; na leitura, o detrator agita e o promotor assenta.
  let agitado = clamp(-humor, 0.0, 1.0);
  let calma = clamp(humor, 0.0, 1.0);
  let amp = 0.35 * w.y + leitura * (0.08 + 0.55 * agitado - 0.05 * calma) * (1.0 - cena.foco.w) + 0.03 * (1.0 - w.x);
  let ruido = curl(p.pos * 1.3 + vec2f(p.semente), cena.tempo * 0.15) * amp;

  let mola = 6.0 * (1.0 - 0.6 * w.y);
  let forca = (alvo - p.pos) * mola + ruido;
  p.vel = p.vel * exp(-4.0 * cena.dt) + forca * cena.dt;
  p.pos = p.pos + p.vel * cena.dt;

  // Tinta: 0 e o dito (ambar), 1 e o medido (azul). Atravessar o orbe mede.
  let perto = 1.0 - smoothstep(cena.foco.z * 0.7, cena.foco.z * 1.2, distance(p.pos, foco));
  var tinta_alvo = p.tinta;
  if (w.x > 0.5) { tinta_alvo = 0.0; }
  // Na mascara a cor e o lado: ambar o que foi dito, azul o que da para medir.
  tinta_alvo = mix(tinta_alvo, step(0.0, p.mascara.x), w.z);
  tinta_alvo = mix(tinta_alvo, 0.55, w.w);
  tinta_alvo = max(tinta_alvo, perto * peso_orbe);
  tinta_alvo = mix(tinta_alvo, (humor + 1.0) * 0.5, leitura);
  p.tinta = mix(p.tinta, tinta_alvo, 1.0 - exp(-3.0 * cena.dt));
  p.vida = p.vida + cena.dt;

  particulas[i] = p;
}
