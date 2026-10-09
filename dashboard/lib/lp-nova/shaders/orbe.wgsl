import { Cena, DITO, MEDIDO, HALO, FUNDO } from "./comum.wgsl";

@group(0) @binding(0) var<uniform> cena: Cena;

// O FUNDO DA VITRINE ANTIGA, portado de GLSL (`FS_FUNDO` do antigo lib/vitrine/motor.ts):
// o fosforo de um osciloscopio -- reticula, dois tracos (ambar do dito, azul do
// medido), varredura, curvatura de CRT, vinheta, scanline e grao -- e por cima
// o orbe de tres manchas. Os canais que a rolagem move vem de `lib/lp-nova/orbe.ts`.

fn h(p: vec2f) -> f32 { return fract(sin(dot(p, vec2f(127.1, 311.7))) * 43758.5453); }

fn ruido(p: vec2f) -> f32 {
  let i = floor(p);
  var f = fract(p);
  f = f * f * (3.0 - 2.0 * f);
  return mix(mix(h(i), h(i + vec2f(1.0, 0.0)), f.x), mix(h(i + vec2f(0.0, 1.0)), h(i + vec2f(1.0, 1.0)), f.x), f.y);
}

fn fbm(p0: vec2f) -> f32 {
  var v = 0.0;
  var a = 0.5;
  var p = p0;
  for (var i = 0; i < 5; i++) {
    v += a * ruido(p);
    p *= 2.03;
    a *= 0.5;
  }
  return v;
}

fn hs(x: f32) -> f32 { return fract(sin(x) * 43758.5453); }

fn vn(x: f32) -> f32 {
  let i = floor(x);
  var f = fract(x);
  f = f * f * (3.0 - 2.0 * f);
  return mix(hs(i), hs(i + 1.0), f) * 2.0 - 1.0;
}

// O sinal do dito: rajadas, como fala. O do medido: uma onda calma.
fn sinal_dito(x: f32, t: f32) -> f32 {
  let e = pow(max(0.0, sin(x * 9.42478 + 0.6)), 4.0);
  return e * (sin(x * 150.0 + t * 1.3) * 0.55 + vn(x * 70.0 + t * 0.8) * 0.45);
}

fn sinal_medido(x: f32, t: f32) -> f32 {
  return 0.18 * sin(x * 14.0 + t * 0.7) + 0.09 * vn(x * 35.0 + t * 0.9) + 0.06 * sin(x * 61.0 - t * 1.7);
}

fn traco(y: f32, v: f32, dv: f32, r: vec2f) -> f32 {
  let dpx = (y - v) * r.y;
  let inclinacao = dv * r.y / r.x;
  let d = abs(dpx) / sqrt(1.0 + inclinacao * inclinacao);
  return exp(-d * d / 1.8) + 0.38 * exp(-d / 6.5) + 0.09 * exp(-d / 34.0);
}

fn tela(a: vec3f, b: vec3f) -> vec3f { return 1.0 - (1.0 - a) * (1.0 - b); }

@fragment fn fs_main(@location(0) uv: vec2f) -> @location(0) vec4f {
  let r = max(cena.fosforo.xy, vec2f(1.0));
  let t = cena.tempo;
  // Pixel com y para cima, como o gl_FragCoord do original.
  let fc = vec2f(uv.x, 1.0 - uv.y) * r;

  // Curvatura de CRT: fora da tela curva fica o vidro escuro.
  var cc = (fc / r) * 2.0 - 1.0;
  cc *= 1.0 + 0.025 * dot(cc, cc);
  let u = cc * 0.5 + 0.5;
  var cor = FUNDO * 0.6;
  if (u.x >= 0.0 && u.x <= 1.0 && u.y >= 0.0 && u.y <= 1.0) {
    cor = FUNDO;
    let gx = abs(fract(u.x * 10.0 + 0.5) - 0.5) / 10.0 * r.x;
    let gy = abs(fract(u.y * 8.0 + 0.5) - 0.5) / 8.0 * r.y;
    let grade = max(step(gx, 0.6), step(gy, 0.6));
    let marcas = step(abs(u.y - 0.5) * r.y, 4.0) * step(abs(fract(u.x * 50.0 + 0.5) - 0.5) / 50.0 * r.x, 0.6)
      + step(abs(u.x - 0.5) * r.x, 4.0) * step(abs(fract(u.y * 40.0 + 0.5) - 0.5) / 40.0 * r.y, 0.6);
    cor += vec3f(0.93, 0.93, 0.96) * (grade * 0.05 + min(marcas, 1.0) * 0.07);

    // Varredura: o traco acende onde o feixe acabou de passar.
    let x = u.x;
    let e = 1.0 / r.x;
    let feixe = fract(t * 0.11);
    let atras = fract(feixe - x);
    let persiste = 0.25 + 0.75 * exp(-atras * 5.0);
    let y_dito = 0.64;
    let y_medido = 0.36;
    let v1 = y_dito + 0.05 * sinal_dito(x, t);
    let d1 = 0.05 * (sinal_dito(x + e, t) - sinal_dito(x - e, t)) / (2.0 * e);
    let v2 = y_medido + 0.04 * sinal_medido(x, t);
    let d2 = 0.04 * (sinal_medido(x + e, t) - sinal_medido(x - e, t)) / (2.0 * e);
    let apaga = cena.fosforo.w;
    let i1 = traco(u.y, v1, d1, r) * persiste * (1.0 - apaga);
    let i2 = traco(u.y, v2, d2, r) * persiste;
    // Sem fala do cliente o canal do dito vira linha de base tracejada.
    let tracejado = step(0.5, fract(fc.x / 14.0));
    let base = exp(-pow((u.y - y_dito) * r.y, 2.0) / 1.2) * tracejado * apaga;
    let tracos = DITO * i1 + MEDIDO * i2 + vec3f(0.62, 0.63, 0.68) * base * 0.55;
    cor += tracos * cena.fosforo.z * 0.55;

    let vinheta = smoothstep(1.25, 0.35, length(cc * vec2f(0.92, 1.0)));
    cor *= 0.55 + 0.45 * vinheta;
    cor *= 0.965 + 0.035 * sin(fc.y * 3.14159);
  }

  // O orbe, em unidades de cena (y para cima, x em [-aspecto, aspecto]).
  let q = vec2f((uv.x * 2.0 - 1.0) * cena.aspecto, 1.0 - uv.y * 2.0);
  let raio = max(cena.orbe.z, 1e-4);
  let q0 = (q - cena.orbe.xy) / raio;
  let d = length(q0);
  if (d < 1.8) {
    let sat = cena.orbe.w;
    let s = cena.paleta.w * 0.5;
    let w = cena.paleta.xyz;
    let qq = q0 + 0.22 * vec2f(fbm(q0 * 1.8 + t * 0.07), fbm(q0 * 1.8 - t * 0.09 + 3.1)) - 0.11;
    let tau = 6.28318;
    let a1 = s * vec2f(cos(t * tau / 14.0), sin(t * tau / 14.0));
    let a2 = s * vec2f(cos(t * tau / 18.0 + 2.1), sin(t * tau / 18.0 + 2.1));
    let a3 = s * vec2f(cos(-t * tau / 22.0 + 4.2), sin(-t * tau / 22.0 + 4.2));
    var o = vec3f(0.02, 0.02, 0.03);
    o = tela(o, DITO * w.x * exp(-dot(qq - a1, qq - a1) * 2.6));
    o = tela(o, MEDIDO * w.y * exp(-dot(qq - a2, qq - a2) * 2.4));
    o = tela(o, HALO * 0.85 * w.z * exp(-dot(qq - a3, qq - a3) * 3.2));
    o = clamp(o, vec3f(0.0), vec3f(1.0));
    o *= mix(0.3, 1.0, smoothstep(1.0, 0.35, d));
    o += 0.08 * smoothstep(0.75, 1.0, d) * smoothstep(1.02, 0.98, d);
    let g = dot(o, vec3f(0.299, 0.587, 0.114));
    o = mix(vec3f(g * 0.55), o, sat);
    // A secao do analista abaixa a luz da cena; o orbe acompanha.
    o *= mix(0.55, 1.0, cena.leitura.y);
    let dentro = smoothstep(1.0, 0.985, d);
    let halo = (1.0 - dentro) * exp(-(d - 1.0) * 5.0) * 0.16 * sat * w.z;
    cor = mix(cor, o, dentro) + vec3f(0.55, 0.16, 0.55) * halo;
  }

  cor += (h(fc + fract(t)) - 0.5) * 0.02;
  return vec4f(cor, 1.0);
}
