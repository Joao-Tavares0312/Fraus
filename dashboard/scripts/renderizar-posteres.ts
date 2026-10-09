/**
 * Os POSTERES da LP nova: o que aparece para quem nao tem WebGPU ou pediu
 * movimento reduzido.
 *
 * Saem do MESMO WGSL e dos MESMOS uniforms da cena viva (`lib/lp-nova/quadro.ts`),
 * renderizados no Node pelo vgpu (Dawn). A simulacao corre com semente fixa ate
 * o momento de cada poster, e o script renderiza tudo DUAS vezes e compara os
 * bytes: se a segunda leitura diferir da primeira, o poster nao e reproduzivel
 * e o script falha em vez de gravar.
 *
 *     npx jiti scripts/renderizar-posteres.ts
 */
import { mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";
import { PNG } from "pngjs";
import { resolveShader } from "@vgpu/wgsl/runtime";
import { compute, draw, effect, frame, init, storage, target } from "vgpu/node";
import { MARCOS } from "../lib/lp-nova/fases";
import { BYTES_POR_PARTICULA, aleatorioComSemente, sementeDasParticulas, uniformesDoQuadro } from "../lib/lp-nova/quadro";

const LARGURA = 1600;
const ALTURA = 1000;
const TOTAL = 60_000;
const SEMENTE = 20261009;
const PASSOS_POR_MOMENTO = 420;
const DT = 1 / 60;

// O hero sem WebGPU mostra a frase no DOM; o poster dele e o campo ambar do lado.
const MOMENTOS = [
  { nome: "hero", progresso: MARCOS.disperso },
  { nome: "mascara", progresso: MARCOS.mascara },
  { nome: "fecho", progresso: MARCOS.fecho },
] as const;

const PASTA_SHADERS = path.resolve("lib/lp-nova/shaders");
const DESTINO = path.resolve("public/lp-nova");

async function fonte(nome: string) {
  return (await resolveShader({ entry: path.join(PASTA_SHADERS, nome), validate: "require" })).wgsl;
}

async function renderizarTudo(): Promise<Map<string, Uint8Array>> {
  // O Dawn do Node sobe em modo de compatibilidade (zero storage buffer no
  // vertice); o adaptador suporta, entao o limite e pedido explicitamente.
  const gpu = await init({ requiredLimits: { maxStorageBuffersInVertexStage: 1 } });
  const [simularWgsl, particulasWgsl, orbeWgsl] = await Promise.all([
    fonte("simular.wgsl"),
    fonte("particulas.wgsl"),
    fonte("orbe.wgsl"),
  ]);
  const aleatorio = aleatorioComSemente(SEMENTE);
  const origens = new Float32Array(TOTAL * 2);
  for (let i = 0; i < origens.length; i++) origens[i] = (aleatorio() - 0.5) * 0.4;

  const particulas = storage(gpu, TOTAL * BYTES_POR_PARTICULA, "read-write");
  particulas.write(sementeDasParticulas(TOTAL, origens, aleatorio));
  const simular = compute(gpu, simularWgsl, { label: "simular" });
  const campo = draw(gpu, {
    shader: particulasWgsl,
    vertices: 6,
    instances: TOTAL,
    blend: { color: { src: "one", dst: "one" }, alpha: { src: "one", dst: "one" } },
  });
  const orbe = effect(gpu, orbeWgsl);
  const alvo = target(gpu, { size: [LARGURA, ALTURA] });

  const quadros = new Map<string, Uint8Array>();
  let tempo = 0;
  let progresso = 0;
  for (const momento of MOMENTOS) {
    for (let passo = 0; passo < PASSOS_POR_MOMENTO; passo++) {
      // Caminha ate o marco em vez de saltar: as particulas chegam como chegariam rolando.
      progresso += (momento.progresso - progresso) * 0.02;
      tempo += DT;
      const u = uniformesDoQuadro({
        aspecto: LARGURA / ALTURA,
        alturaPx: ALTURA,
        total: TOTAL,
        celular: false,
        progresso,
        humor: 0,
        cinza: 0,
        tempo,
        dt: DT,
      });
      simular.set({ cena: u, particulas }).dispatch(Math.ceil(TOTAL / 64));
      campo.set({ cena: u, particulas });
      orbe.set({ cena: u });
      if (passo === PASSOS_POR_MOMENTO - 1) {
        frame(gpu, (f) =>
          f.pass(alvo, (pass) => {
            pass.draw(orbe);
            pass.draw(campo);
          }),
        );
      }
    }
    // Na 0.5.0 quem le e a textura de cor do alvo (`npx vgpu docs` e a doc
    // desta versao; o site ja mostra `target.read()` de uma versao adiante).
    type Legivel = { read(o: { mipLevel: number; region: "all" }): Promise<Uint8Array> };
    const cor = (alvo as unknown as { color: Legivel }).color;
    quadros.set(momento.nome, new Uint8Array(await cor.read({ mipLevel: 0, region: "all" })));
  }
  gpu.dispose();
  return quadros;
}

function maiorDiferenca(a: Uint8Array, b: Uint8Array): number {
  if (a.length !== b.length) return 255;
  let maior = 0;
  for (let i = 0; i < a.length; i++) maior = Math.max(maior, Math.abs(a[i] - b[i]));
  return maior;
}

const primeira = await renderizarTudo();
const segunda = await renderizarTudo();
mkdirSync(DESTINO, { recursive: true });
for (const { nome } of MOMENTOS) {
  const a = primeira.get(nome)!;
  const diferenca = maiorDiferenca(a, segunda.get(nome)!);
  // <= 2 e arredondamento de driver (a mesma regua do pixelDiff do vgpu).
  if (diferenca > 2) {
    console.error(`${nome}: duas renderizacoes diferem (maxByte ${diferenca}); poster nao reproduzivel`);
    process.exit(1);
  }
  const png = new PNG({ width: LARGURA, height: ALTURA });
  png.data.set(a);
  writeFileSync(path.join(DESTINO, `${nome}.png`), PNG.sync.write(png));
  console.log(`ok ${nome}.png (maxByte entre as duas: ${diferenca})`);
}
