/** FR oficial: cache geometrico offline, materiais de estudio e luz de corte finita. */
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { spawn, type ChildProcess } from "node:child_process";
import { once } from "node:events";
import { chromium } from "playwright";
import { PNG } from "pngjs";
import { compute, effect, frame, init, storage, target } from "vgpu/node";

const navegador = await chromium.launch({ channel: "chrome", headless: true });
const pagina = await navegador.newPage();
try {
  const svg = readFileSync("public/fraus-logo.svg", "utf8");
  const mascaras = await pagina.evaluate(async (fonte) => {
    const imagem = new Image();
    imagem.src = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(fonte)}`;
    await imagem.decode();
    const canvas = new OffscreenCanvas(1024, 1024);
    const ctx = canvas.getContext("2d")!;
    ctx.drawImage(imagem, 0, 0, 1024, 1024);
    const pixels = ctx.getImageData(0, 0, 1024, 1024).data;
    const f: number[] = [], r: number[] = [];
    for (let i = 0; i < pixels.length; i += 4) {
      const claro = pixels[i] > 100;
      f.push(claro && Math.abs(pixels[i] - pixels[i + 2]) < 12 ? 1 : 0);
      r.push(claro && pixels[i] - pixels[i + 2] >= 12 ? 1 : 0);
    }
    return [f, r];
  }, svg);
  // Distancia euclidiana exata em duas dimensoes: evita facetas da chamfer.
  function distancia(mascara: number[], dentro: boolean) {
    const tamanho = 1024;
    const d = Float64Array.from(mascara, (v) => Boolean(v) === dentro ? 0 : 1e8);
    const entrada = new Float64Array(tamanho);
    const saida = new Float64Array(tamanho);
    const vertices = new Int32Array(tamanho);
    const fronteiras = new Float64Array(tamanho + 1);
    function transformar() {
      let k = 0;
      vertices[0] = 0;
      fronteiras[0] = -Infinity;
      fronteiras[1] = Infinity;
      for (let q = 1; q < tamanho; q++) {
        let s = 0;
        do {
          const v = vertices[k];
          s = ((entrada[q] + q * q) - (entrada[v] + v * v)) / (2 * (q - v));
          if (s > fronteiras[k]) break;
          k--;
        } while (k >= 0);
        k++;
        vertices[k] = q;
        fronteiras[k] = s;
        fronteiras[k + 1] = Infinity;
      }
      k = 0;
      for (let q = 0; q < tamanho; q++) {
        while (fronteiras[k + 1] < q) k++;
        saida[q] = (q - vertices[k]) ** 2 + entrada[vertices[k]];
      }
    }
    for (let y = 0; y < tamanho; y++) {
      entrada.set(d.subarray(y * tamanho, (y + 1) * tamanho));
      transformar();
      d.set(saida, y * tamanho);
    }
    for (let x = 0; x < tamanho; x++) {
      for (let y = 0; y < tamanho; y++) entrada[y] = d[y * tamanho + x];
      transformar();
      for (let y = 0; y < tamanho; y++) d[y * tamanho + x] = Math.sqrt(saida[y]);
    }
    return d;
  }
  const dados = new Float32Array(1024 * 1024 * 2);
  for (let canal = 0; canal < 2; canal++) {
    const fora = distancia(mascaras[canal], true);
    const dentro = distancia(mascaras[canal], false);
    for (let i = 0; i < fora.length; i++) dados[i * 2 + canal] = (fora[i] - dentro[i]) * 4.2 / 1024;
  }
  const somenteFundo = process.argv.includes("--fundo");
  const largura = somenteFundo ? 1280 : 960, altura = somenteFundo ? 800 : 1020;
  const fps = 24, quadros = somenteFundo ? 1 : 72;
  const gpu = await init();
  let codificador: ChildProcess | undefined;
  try {
    const campo = storage(gpu, dados.byteLength, "read");
    campo.write(dados);
    const superficies = storage(gpu, largura * altura * 48, "read-write");
    const shader = readFileSync("lib/conta/escultura.wgsl", "utf8");
    const u = (tempo: number) => ({ tamanho: [largura, altura], tempo, somente_fundo: somenteFundo ? 1 : 0 });
    const preparar = compute(gpu, shader, { entry: "preparar", set: { distancias: campo, superficies, quadro: u(0) } });
    preparar.dispatch(Math.ceil(largura / 8), Math.ceil(altura / 8));
    const escultura = effect(gpu, shader, { set: { distancias: campo, superficies, quadro: u(0) } });
    const alvo = target(gpu, { size: [largura, altura] });
    mkdirSync("public/conta", { recursive: true });
    let terminou = Promise.resolve();
    if (!somenteFundo) {
      codificador = spawn("ffmpeg", [
        "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgba",
        "-s", `${largura}x${altura}`, "-r", String(fps), "-i", "pipe:0",
        "-an", "-c:v", "libvpx-vp9", "-crf", "28", "-b:v", "0",
        "-row-mt", "1", "-threads", "2", "-pix_fmt", "yuv420p",
        "public/conta/fr-luz-de-corte.webm",
      ], { stdio: ["pipe", "inherit", "inherit"] });
      terminou = new Promise<void>((resolve, reject) => {
        codificador!.once("error", reject);
        codificador!.once("close", (codigo) => codigo === 0 ? resolve() : reject(new Error(`ffmpeg encerrou com ${codigo}`)));
      });
      void terminou.catch(() => {});
    }
    let pixels = new Uint8Array();
    let repouso: Uint8Array | undefined;
    for (let i = 0; i < quadros; i++) {
      escultura.set({ quadro: u(somenteFundo ? 0 : i / (quadros - 1)) });
      frame(gpu, (f) => f.pass(alvo, (pass) => pass.draw(escultura)));
      pixels = new Uint8Array(await alvo.color.read({ mipLevel: 0, region: "all" }));
      if (i === 0) repouso = pixels;
      const fluxo = codificador?.stdin;
      if (fluxo && !fluxo.write(pixels)) await once(fluxo, "drain");
    }
    codificador?.stdin?.end();
    await terminou;
    // O filme deve voltar ao mesmo repouso; NaN na luz pode apagar so o fim.
    let diferenca = 0;
    for (let i = 0; i < pixels.length; i++) diferenca = Math.max(diferenca, Math.abs(pixels[i] - repouso![i]));
    if (diferenca > 2) throw new Error(`Primeiro e ultimo quadros divergiram ${diferenca} niveis; poster recusado`);
    // Ultimo quadro e repouso: corresponde exatamente ao poster usado no fallback.
    const png = new PNG({ width: largura, height: altura });
    png.data.set(pixels);
    const url = `data:image/png;base64,${PNG.sync.write(png).toString("base64")}`;
    const base64 = await pagina.evaluate(async (fonte) => {
      const imagem = await createImageBitmap(await (await fetch(fonte)).blob());
      const canvas = new OffscreenCanvas(imagem.width, imagem.height);
      canvas.getContext("2d")!.drawImage(imagem, 0, 0);
      imagem.close();
      const blob = await canvas.convertToBlob({ type: "image/webp", quality: 0.9 });
      const bytes = new Uint8Array(await blob.arrayBuffer());
      let binario = "";
      for (let i = 0; i < bytes.length; i += 8192) binario += String.fromCharCode(...bytes.subarray(i, i + 8192));
      return btoa(binario);
    }, url);
    const webp = Buffer.from(base64, "base64");
    const destino = somenteFundo ? "public/estudio-grafite.webp" : "public/conta/fr-escultura.webp";
    writeFileSync(destino, webp);
    console.log(`${somenteFundo ? "Estudio sem monograma" : "Luz de corte"}: ${largura} × ${altura}, ${somenteFundo ? "estatico" : `${quadros / fps}s a ${fps}fps`}; WebP ${webp.byteLength} bytes`);
  } finally {
    if (codificador && codificador.exitCode === null) codificador.kill();
    gpu.dispose();
  }
} finally { await navegador.close(); }
