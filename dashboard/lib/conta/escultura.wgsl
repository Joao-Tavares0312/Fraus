// Geometria e iluminacao usadas apenas no exportador Node/Dawn.
// O cache de superficies evita repetir raymarch em cada quadro do filme.
struct Quadro { tamanho: vec2f, tempo: f32, somente_fundo: f32 }
struct Superficie { ponto: vec4f, normal: vec4f, material: vec4f }
@group(0) @binding(0) var<storage, read> distancias: array<vec2f>;
@group(0) @binding(1) var<storage, read_write> superficies: array<Superficie>;
@group(0) @binding(2) var<uniform> quadro: Quadro;

fn amostra(uv: vec2f) -> vec2f {
  let q = clamp(uv * 1023.0, vec2f(0.0), vec2f(1023.0));
  let i = vec2u(q);
  let j = min(i + vec2u(1u), vec2u(1023u));
  let f = fract(q);
  let a = mix(distancias[i.y * 1024u + i.x], distancias[i.y * 1024u + j.x], f.x);
  let b = mix(distancias[j.y * 1024u + i.x], distancias[j.y * 1024u + j.x], f.x);
  return mix(a, b, f.y) + vec2f(length(max(abs(uv - 0.5) - 0.5, vec2f(0.0))) * 4.2);
}
fn pecas(p: vec3f) -> vec2f {
  let d = amostra(vec2f(p.x / 4.2 + 0.5, 0.5 - p.y / 4.2));
  let z = abs(p.z) - 0.19;
  let a = vec2f(d.x + 0.035, z);
  let b = vec2f(d.y + 0.035, z);
  return vec2f(length(max(a, vec2f(0.0))) + min(max(a.x, a.y), 0.0),
               length(max(b, vec2f(0.0))) + min(max(b.x, b.y), 0.0)) - 0.035;
}
fn objeto(p: vec3f) -> f32 {
  if (quadro.somente_fundo > 0.5) { return 1000.0; }
  let d = pecas(p);
  return min(d.x, d.y);
}
// Ciclorama de grafite: dobras diagonais acompanham o corte da marca.
fn parede(p: vec3f) -> f32 {
  let eixo = dot(p.xy, normalize(vec2f(-0.54, 0.84)));
  let relevo = 0.22 * cos(eixo * 3.2) + 0.035 * cos(eixo * 6.4);
  return (p.z + 1.2 - relevo) * 0.82;
}
fn cena(p: vec3f) -> f32 {
  let chao = p.y + 1.25;
  let fundo = parede(p);
  let h = clamp(0.5 + 0.5 * (chao - fundo) / 0.4, 0.0, 1.0);
  let estudio = mix(chao, fundo, h) - 0.4 * h * (1.0 - h);
  return min(objeto(p), estudio);
}
fn normal(p: vec3f) -> vec3f {
  let e = vec2f(0.018, 0.0);
  return normalize(vec3f(cena(p + e.xyy) - cena(p - e.xyy), cena(p + e.yxy) - cena(p - e.yxy), cena(p + e.yyx) - cena(p - e.yyx)));
}
fn sombra(p: vec3f, l: vec3f) -> f32 {
  if (quadro.somente_fundo > 0.5) { return 1.0; }
  var s = 1.0;
  var t = 0.025;
  for (var i = 0; i < 48; i++) {
    let d = objeto(p + l * t);
    s = min(s, 9.0 * d / t);
    t += clamp(d, 0.025, 0.15);
    if (d < 0.001 || t > 5.0) { break; }
  }
  return clamp(s, 0.0, 1.0);
}
fn ruido(p: vec2f) -> f32 { return fract(sin(dot(p, vec2f(127.1, 311.7))) * 43758.5453); }
fn raio(uv: vec2f) -> vec3f {
  let frente = normalize(vec3f(0.0, -0.05, 0.0) - vec3f(2.5, 1.15, 6.3));
  let direita = normalize(cross(frente, vec3f(0.0, 1.0, 0.0)));
  let cima = cross(direita, frente);
  let aspecto = select(0.94, quadro.tamanho.x / quadro.tamanho.y, quadro.somente_fundo > 0.5);
  let tela = (uv - 0.5) * vec2f(aspecto, -1.0);
  return normalize(frente * 1.75 + direita * tela.x + cima * tela.y);
}
@compute @workgroup_size(8, 8)
fn preparar(@builtin(global_invocation_id) id: vec3u) {
  let tamanho = vec2u(quadro.tamanho);
  if (any(id.xy >= tamanho)) { return; }
  let indice = id.y * tamanho.x + id.x;
  let rd = raio((vec2f(id.xy) + 0.5) / quadro.tamanho);
  var t = 0.0;
  var p = vec3f(0.0);
  var atingiu = false;
  for (var i = 0; i < 200; i++) {
    p = vec3f(2.5, 1.15, 6.3) + rd * t;
    let d = cena(p);
    if (d < 0.0008) { atingiu = true; break; }
    t += max(d * 0.7, 0.0004);
    if (t > 22.0) { break; }
  }
  if (!atingiu) {
    superficies[indice] = Superficie(vec4f(0.0), vec4f(0.0), vec4f(0.0));
    return;
  }
  let n = normal(p);
  var metal = 0.0;
  var tipo = 1.0;
  if (quadro.somente_fundo < 0.5) {
    let d = pecas(p);
    metal = select(0.0, 1.0, d.y < d.x);
    tipo = select(1.0, 0.0, abs(min(d.x, d.y)) < 0.01);
  }
  var oclusao = 1.0;
  for (var j = 1; j <= 5; j++) {
    let r = f32(j) * 0.045;
    oclusao -= max(0.0, r - cena(p + n * r)) * 0.9;
  }
  let sh = sombra(p + n * 0.006, normalize(vec3f(-3.0, 5.0, 4.0)));
  superficies[indice] = Superficie(vec4f(p, 1.0), vec4f(n, clamp(oclusao, 0.0, 1.0)),
    vec4f(metal, tipo, sh, t));
}
fn fresnel(cosseno: f32, f0: vec3f) -> vec3f { return f0 + (1.0 - f0) * pow(1.0 - cosseno, 5.0); }
fn luz(n: vec3f, v: vec3f, l: vec3f, base: vec3f, metal: f32, rugosidade: f32) -> vec3f {
  let h = normalize(v + l);
  let nv = max(dot(n, v), 0.001);
  let nl = max(dot(n, l), 0.0);
  let nh = max(dot(n, h), 0.0);
  let a = rugosidade * rugosidade;
  let a2 = a * a;
  let denominador = nh * nh * (a2 - 1.0) + 1.0;
  let distribuicao = a2 / max(3.14159 * denominador * denominador, 0.0001);
  let k = (rugosidade + 1.0) * (rugosidade + 1.0) / 8.0;
  let geometria = nv / (nv * (1.0 - k) + k) * nl / (nl * (1.0 - k) + k);
  let f = fresnel(max(dot(h, v), 0.0), mix(vec3f(0.04), base, metal));
  let especular = distribuicao * geometria * f / max(4.0 * nv * nl, 0.001);
  return ((1.0 - f) * (1.0 - metal) * base / 3.14159 + especular) * nl;
}
@fragment fn main(@builtin(position) pixel: vec4f, @location(0) uv: vec2f) -> @location(0) vec4f {
  let indice = u32(pixel.y) * u32(quadro.tamanho.x) + u32(pixel.x);
  let s = superficies[indice];
  let fundo = vec3f(0.0035, 0.0035, 0.0037);
  var cor = fundo;
  if (s.ponto.w > 0.5) {
    let p = s.ponto.xyz;
    let n = s.normal.xyz;
    let v = -raio(uv);
    let metal = s.material.x;
    let estudio = s.material.y > 0.5;
    if (estudio) {
      let grafite = vec3f(0.024, 0.025, 0.027);
      let l = normalize(vec3f(-3.0, 5.0, 4.0));
      let rasante = normalize(vec3f(-4.0, 1.0, 0.4));
      let distanciaLuz = length(p.xy - vec2f(-1.4, 1.4));
      let banho = exp(-distanciaLuz * 0.32);
      cor = fundo + grafite * 0.11 * s.normal.w;
      cor += luz(n, v, l, grafite, 0.0, 0.62) * vec3f(2.4, 2.35, 2.2) * s.material.z;
      cor += grafite * max(dot(n, rasante), 0.0) * vec3f(0.9, 0.76, 0.53) * banho;
      cor *= 0.98 + ruido(floor(p.xy * 650.0)) * 0.02;
    } else {
    let escovado = sin(p.y * 1350.0 + sin(p.x * 37.0) * 2.0) * 0.5 + 0.5;
    let micro = ruido(floor(p.xy * 1800.0));
    let base = mix(vec3f(0.72, 0.73, 0.72), vec3f(0.76, 0.57, 0.29), metal);
    let rugosidade = mix(0.34, 0.22 + escovado * 0.04, metal);
    let f0 = mix(vec3f(0.04), base, metal);
    let refletido = reflect(-v, n);
    let l = normalize(vec3f(-3.0, 5.0, 4.0));
    let janela = pow(max(dot(refletido, normalize(vec3f(-1.5, 2.0, 4.0))), 0.0), 18.0);
    let recorte = pow(max(dot(refletido, normalize(vec3f(3.0, 1.5, -2.0))), 0.0), 24.0);
    cor = base * mix(0.11, 0.015, metal) * s.normal.w;
    cor += luz(n, v, l, base, metal, rugosidade) * vec3f(3.4, 3.25, 3.0) * s.material.z;
    cor += fresnel(max(dot(n, v), 0.0), f0) * (vec3f(1.6, 1.55, 1.45) * janela + vec3f(0.7, 0.75, 0.83) * recorte);
    cor += base * (0.025 + 0.045 * max(n.y, 0.0)) * s.normal.w;
    cor *= 0.988 + micro * 0.012;
    // Uma fonte de luz percorre a fenda real do SVG, nao uma faixa sobre a imagem.
    let andamento = smoothstep(0.08, 0.9, quadro.tempo);
    let direcao = normalize(vec2f(450.0, 290.0));
    let perpendicular = vec2f(-direcao.y, direcao.x);
    let centro = vec2f(-1.1, -0.91) + direcao * andamento * 3.25;
    let relativo = p.xy - centro;
    let transversal = dot(relativo, perpendicular) / 0.15;
    let longitudinal = dot(relativo, direcao) / 0.48;
    let largura = exp(-transversal * transversal);
    let comprimento = exp(-longitudinal * longitudinal);
    let seno = sin(clamp(quadro.tempo, 0.0, 1.0) * 3.14159265);
    let pulso = seno * seno;
    let fonte = normalize(vec3f(centro + vec2f(-0.2, 0.4), 2.3) - p);
    let faixa = largura * comprimento * pulso;
    cor += luz(n, v, fonte, base, metal, 0.28) * vec3f(9.0, 7.8, 5.4) * faixa;
    cor += base * faixa * 0.65;
    }
    let nevoa = 1.0 - exp(-pow(max(s.material.w - 6.5, 0.0) * 0.24, 2.0));
    cor = mix(cor, fundo, nevoa);
  }
  // ACES aproximado e grao estatico: mesma textura no poster e em todos os quadros.
  cor = clamp((cor * (2.51 * cor + 0.03)) / (cor * (2.43 * cor + 0.59) + 0.14), vec3f(0.0), vec3f(1.0));
  cor = pow(cor, vec3f(1.0 / 2.2));
  cor += vec3f((ruido(pixel.xy) - 0.5) / 600.0);
  return vec4f(cor, 1.0);
}
