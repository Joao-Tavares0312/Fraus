/**
 * Poster WebP responsivo da mesma cena WGSL. Node/Dawn renderiza duas vezes;
 * o Chrome ja usado pelo smoke codifica WebP, sem novo pacote ou binario.
 * npm run posteres (requer o Chrome do Playwright, como npm run test:lp).
 */
import { mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";
import { PNG } from "pngjs";
import { chromium } from "playwright";
import { resolveShader } from "@vgpu/wgsl/runtime";
import { compute, draw, effect, frame, init, storage, target } from "vgpu/node";
import { MARCOS } from "../lib/lp-nova/fases";
import { BYTES_POR_PARTICULA, aleatorioComSemente, sementeDasParticulas, uniformesDoQuadro } from "../lib/lp-nova/quadro";

const SEMENTE = 20261009;
const PASSOS_POR_MOMENTO = 420;
const DT = 1 / 60;
const FORMATOS = [
  { sufixo: "", largura: 1280, altura: 800, total: 30_000, celular: false },
  { sufixo: "-celular", largura: 390, altura: 844, total: 8_000, celular: true },
] as const;
const MOMENTOS = [
  { nome: "hero", progresso: MARCOS.frase },
  { nome: "mascara", progresso: MARCOS.mascara },
  { nome: "fecho", progresso: MARCOS.fecho },
] as const;
const PASTA_SHADERS = path.resolve("lib/lp-nova/shaders");
const DESTINO = path.resolve("public/lp-nova");

async function fonte(nome: string) {
  return (await resolveShader({ entry: path.join(PASTA_SHADERS, nome), validate: "require" })).wgsl;
}

async function renderizarTudo(formato: (typeof FORMATOS)[number]): Promise<Record<string, Uint8Array>> {
  const { largura, altura, total, celular } = formato;
  const gpu = await init({ requiredLimits: { maxStorageBuffersInVertexStage: 1 } });
  try {
    const [simularWgsl, particulasWgsl, orbeWgsl] = await Promise.all([
      fonte("simular.wgsl"), fonte("particulas.wgsl"), fonte("orbe.wgsl"),
    ]);
    const aleatorio = aleatorioComSemente(SEMENTE);
    const origens = new Float32Array(total * 2);
    for (let i = 0; i < origens.length; i++) origens[i] = (aleatorio() - 0.5) * 0.4;
    const particulas = storage(gpu, total * BYTES_POR_PARTICULA, "read-write");
    particulas.write(sementeDasParticulas(total, origens, aleatorio));
    const simular = compute(gpu, simularWgsl, { label: "simular" });
    const campo = draw(gpu, {
      shader: particulasWgsl, vertices: 6, instances: total,
      blend: { color: { src: "one", dst: "one" }, alpha: { src: "one", dst: "one" } },
    });
    const orbe = effect(gpu, orbeWgsl);
    const alvo = target(gpu, { size: [largura, altura] });
    const quadros: Record<string, Uint8Array> = {};
    let tempo = 0;
    let progresso = 0;
    for (const momento of MOMENTOS) {
      for (let passo = 0; passo < PASSOS_POR_MOMENTO; passo++) {
        progresso += (momento.progresso - progresso) * 0.02;
        tempo += DT;
        const u = uniformesDoQuadro({
          aspecto: largura / altura, alturaPx: altura, total, celular, progresso,
          rolagemPx: 0, humor: 0, cinza: 0, tempo, dt: DT,
        });
        simular.set({ cena: u, particulas }).dispatch(Math.ceil(total / 64));
        campo.set({ cena: u, particulas });
        orbe.set({ cena: u });
        if (passo === PASSOS_POR_MOMENTO - 1) {
          frame(gpu, (f) => f.pass(alvo, (pass) => {
            pass.draw(orbe);
            // A frase do hero e texto DOM, nao uma nuvem sem glifos no poster.
            if (momento.nome !== "hero") pass.draw(campo);
          }));
        }
      }
      quadros[momento.nome] = new Uint8Array(await alvo.color.read({ mipLevel: 0, region: "all" }));
    }
    return quadros;
  } finally {
    gpu.dispose();
  }
}

function maiorDiferenca(a: Uint8Array, b: Uint8Array): number {
  if (a.length !== b.length) return 255;
  let maior = 0;
  for (let i = 0; i < a.length; i++) maior = Math.max(maior, Math.abs(a[i] - b[i]));
  return maior;
}

const navegador = await chromium.launch({ channel: "chrome", headless: true });
try {
  const pagina = await navegador.newPage();
  mkdirSync(DESTINO, { recursive: true });
  for (const formato of FORMATOS) {
    const primeira = await renderizarTudo(formato);
    const segunda = await renderizarTudo(formato);
    for (const { nome } of MOMENTOS) {
      const pixels = primeira[nome];
      const diferenca = maiorDiferenca(pixels, segunda[nome]);
      if (diferenca > 2) throw new Error(`${nome}${formato.sufixo}: poster nao reproduzivel (maxByte ${diferenca})`);
      const png = new PNG({ width: formato.largura, height: formato.altura });
      png.data.set(pixels);
      const dados = `data:image/png;base64,${PNG.sync.write(png).toString("base64")}`;
      const base64 = await pagina.evaluate(async (url) => {
        const imagem = await createImageBitmap(await (await fetch(url)).blob());
        const canvas = new OffscreenCanvas(imagem.width, imagem.height);
        const contexto = canvas.getContext("2d");
        if (!contexto) throw new Error("Chrome sem canvas 2D para codificar poster");
        contexto.drawImage(imagem, 0, 0);
        imagem.close();
        const blob = await canvas.convertToBlob({ type: "image/webp", quality: 0.82 });
        if (blob.type !== "image/webp") throw new Error("Chrome nao codificou WebP");
        const bytes = new Uint8Array(await blob.arrayBuffer());
        let binario = "";
        for (let i = 0; i < bytes.length; i += 8192) binario += String.fromCharCode(...bytes.subarray(i, i + 8192));
        return btoa(binario);
      }, dados);
      const arquivo = `${nome}${formato.sufixo}.webp`;
      const webp = Buffer.from(base64, "base64");
      writeFileSync(path.join(DESTINO, arquivo), webp);
      console.log(`ok ${arquivo}: ${webp.length} bytes (maxByte ${diferenca})`);
    }
  }
} finally {
  await navegador.close();
}
