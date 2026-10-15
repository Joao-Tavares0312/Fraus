import { Cena, DITO, MEDIDO, HALO, FUNDO } from "./comum.wgsl";

@group(0) @binding(0) var<uniform> cena: Cena;

// O FUNDO DA VITRINE ANTIGA, portado de GLSL (`FS_FUNDO` do antigo lib/vitrine/motor.ts):
// o fosforo de um osciloscopio -- reticula, dois tracos (ambar do dito, azul do
// medido), varredura, curvatura de CRT, vinheta, scanline e grao -- e por cima
// uma esfera polida de fosforo. Os canais e a coreografia vem de `lib/lp-nova/orbe.ts`.

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
  let borda = 2.0 / max(raio * r.y, 1.0);
  let dentro = 1.0 - smoothstep(1.0 - borda, 1.0 + borda, d);
  let sat = cena.orbe.w;
  let w = cena.paleta.xyz;
  // O halo fica fora da silhueta; nao lava a superficie nem a tipografia.
  let halo = exp(-max(d - 1.0, 0.0) * 12.0) * (1.0 - dentro) * 0.075 * sat * w.z;
  cor += HALO * halo;
  if (d < 1.0 + borda) {
    // Intersecao analitica com a esfera: volume e reflexo sem ray marching.
    let z = sqrt(max(1.0 - dot(q0, q0), 0.0));
    let normal = normalize(vec3f(q0, max(z, 0.001)));
    // O dominio curva com a esfera. Sem sinal, fluxo e manchas param juntos.
    let tempo = t * 0.08 * sat * cena.paleta.w;
    let giro = tempo * 0.18;
    let superficie = vec2f(
      normal.x * cos(giro) + normal.z * sin(giro),
      normal.y + normal.z * 0.28
    );
    let fluxo = fbm(superficie * 3.2 + vec2f(tempo * 0.3, -tempo * 0.16));
    let camada = fbm(superficie * 6.0 + vec2f(fluxo * 1.5, tempo * 0.2));
    let fase = (superficie.y + fluxo * 0.65 + camada * 0.12) * 24.0 + superficie.x * 4.0;
    let faixa = 0.5 + 0.5 * sin(fase);
    let filamento = smoothstep(0.72, 0.98, faixa);
    let qq = superficie + (fluxo - 0.5) * vec2f(0.5, 0.7);
    let s = cena.paleta.w * 0.5;
    let a1 = s * vec2f(cos(tempo * 0.8), sin(tempo * 0.8));
    let a2 = s * vec2f(cos(tempo * 0.62 + 2.1), sin(tempo * 0.62 + 2.1));
    let a3 = s * vec2f(cos(-tempo * 0.5 + 4.2), sin(-tempo * 0.5 + 4.2));
    var pigmento = vec3f(0.025, 0.027, 0.035);
    pigmento = tela(pigmento, DITO * w.x * exp(-dot(qq - a1, qq - a1) * 2.1));
    pigmento = tela(pigmento, MEDIDO * w.y * exp(-dot(qq - a2, qq - a2) * 2.0));
    pigmento = tela(pigmento, HALO * w.z * 0.6 * exp(-dot(qq - a3, qq - a3) * 3.0));
    pigmento *= 0.48 + 0.32 * camada + 0.2 * filamento;
    let luz = normalize(vec3f(-0.55, 0.7, 0.8));
    let n = normalize(normal + vec3f(0.016 * cos(fase), 0.024 * sin(fase), 0.0));
    let difusa = max(dot(n, luz), 0.0);
    let meia = normalize(luz + vec3f(0.0, 0.0, 1.0));
    let reflexo = pow(max(dot(n, meia), 0.0), 110.0);
    let suave = pow(max(dot(normal, meia), 0.0), 12.0);
    let fresnel = pow(1.0 - z, 3.0);
    let recorte = fresnel * pow(max(dot(normal.xy, normalize(luz.xy)), 0.0), 3.0);
    var o = pigmento * (0.3 + 0.7 * z) * (0.55 + 0.45 * difusa);
    o += pigmento * filamento * 0.24 * z;
    o += vec3f(0.8, 0.86, 0.94) * (reflexo * 0.62 + suave * 0.1 + recorte * 0.48);
    o += mix(MEDIDO, DITO, difusa) * fresnel * 0.065 * sat;
    let g = dot(o, vec3f(0.299, 0.587, 0.114));
    o = mix(vec3f(g * 0.55), o, sat);
    // A secao do analista abaixa a luz da cena; o orbe acompanha.
    o *= mix(0.55, 1.0, cena.leitura.y);
    cor = mix(cor, o, dentro);
  }

  // Grao fixo no vidro: trocar a semente a cada quadro parecia cintilacao.
  cor += (h(fc) - 0.5) * 0.02;
  return vec4f(cor, 1.0);
}
