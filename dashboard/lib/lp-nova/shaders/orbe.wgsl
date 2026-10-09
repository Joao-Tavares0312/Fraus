import { Cena, DITO, MEDIDO, HALO, FUNDO } from "./comum.wgsl";
import { fbmSimplex3d } from "@vgpu/wgsl-std/noise/simplex";

@group(0) @binding(0) var<uniform> cena: Cena;

// O fundo e o orbe-fusor numa passada de tela cheia. O orbe ganha forca quando
// as particulas caem nele e respira no fecho; o halo magenta e so cenografia.
@fragment fn fs_main(@location(0) uv: vec2f) -> @location(0) vec4f {
  let q = vec2f((uv.x * 2.0 - 1.0) * cena.aspecto, 1.0 - uv.y * 2.0);
  let foco = cena.foco.xy;
  let raio = cena.foco.z;
  let d = distance(q, foco);

  // O orbe some atras da mascara e acende quando os nos caem nele.
  // Atras da mascara o orbe quase apaga: o rosto e os vazios precisam ler.
  let forca = clamp(cena.extra.x + 0.35 * cena.destino.w + 0.25 - 0.5 * cena.destino.z, 0.0, 1.0) * cena.leitura.y;
  let n = fbmSimplex3d(vec3f((q - foco) * 2.2, cena.tempo * 0.12), 4, 2.0, 0.5);
  let corpo = smoothstep(raio * 1.05, raio * 0.2, d + n * 0.06 * raio);
  let halo = exp(-pow(max(d - raio * 0.6, 0.0) / (raio * 0.9), 2.0));

  let medida = clamp(cena.extra.x + cena.leitura.z, 0.0, 1.0);
  let miolo = mix(DITO, MEDIDO, medida) * (0.55 + 0.45 * n);
  var cor = FUNDO;
  cor = cor + HALO * halo * 0.22 * forca;
  cor = mix(cor, miolo, corpo * 0.85 * forca);

  // Vinheta: as bordas descansam no quase-preto do Instrumento.
  let vinheta = smoothstep(1.6, 0.4, length(q / vec2f(cena.aspecto, 1.0)));
  return vec4f(cor * mix(0.6, 1.0, vinheta), 1.0);
}
