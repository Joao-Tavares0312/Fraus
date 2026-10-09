import { Cena, Particula, DITO, MEDIDO } from "./comum.wgsl";

@group(0) @binding(0) var<uniform> cena: Cena;
@group(0) @binding(1) var<storage, read> particulas: array<Particula>;

struct Saida {
  @builtin(position) posicao: vec4f,
  @location(0) canto: vec2f,
  @location(1) cor: vec3f,
  @location(2) alfa: f32,
}

fn canto(v: u32) -> vec2f {
  let c = array<vec2f, 6>(
    vec2f(-1.0, -1.0), vec2f(1.0, -1.0), vec2f(-1.0, 1.0),
    vec2f(-1.0, 1.0), vec2f(1.0, -1.0), vec2f(1.0, 1.0),
  );
  return c[v % 6u];
}

@vertex fn vs_main(@builtin(vertex_index) v: u32, @builtin(instance_index) i: u32) -> Saida {
  let p = particulas[i];
  let k = canto(v);
  let tamanho = cena.ponto.x * (0.7 + 0.6 * fract(p.semente * 53.1));
  let centro = vec2f(p.pos.x / cena.aspecto, p.pos.y);
  var s: Saida;
  s.posicao = vec4f(centro + k * vec2f(tamanho / cena.aspecto, tamanho), 0.0, 1.0);
  s.canto = k;
  let cinza = vec3f(0.62, 0.63, 0.68);
  let cor = mix(DITO, MEDIDO, clamp(p.tinta, 0.0, 1.0));
  s.cor = mix(cor, cinza, cena.foco.w * cena.leitura.x);
  s.alfa = cena.leitura.y * (0.35 + 0.4 * fract(p.semente * 17.9));
  return s;
}

@fragment fn fs_main(e: Saida) -> @location(0) vec4f {
  let d = dot(e.canto, e.canto);
  if (d > 1.0) { discard; }
  let a = e.alfa * (1.0 - d) * (1.0 - d);
  return vec4f(e.cor * a, a);
}
