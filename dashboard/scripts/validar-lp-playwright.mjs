import { chromium } from "playwright";
import { mkdir } from "node:fs/promises";
import { join } from "node:path";
import { tmpdir } from "node:os";

const saida = join(tmpdir(), "fraus-playwright");
await mkdir(saida, { recursive: true });

const navegador = await chromium.launch({ channel: "chrome", headless: true });
const resultados = [];

async function validar(nome, viewport) {
  const pagina = await navegador.newPage({ viewport, deviceScaleFactor: 1 });
  const erros = [];
  pagina.on("console", (mensagem) => {
    if (mensagem.type() === "error") erros.push(`console: ${mensagem.text()}`);
  });
  pagina.on("pageerror", (erro) => erros.push(`pageerror: ${erro.message}`));

  const resposta = await pagina.goto("http://localhost:3000", { waitUntil: "networkidle", timeout: 60_000 });
  const metricasIniciais = await pagina.evaluate(() => {
    const recursos = performance.getEntriesByType("resource");
    return {
      recursos: recursos.length,
      bytes: recursos.reduce((total, recurso) => total + (recurso.transferSize || recurso.encodedBodySize || 0), 0),
      hdriCarregado: recursos.some((recurso) => recurso.name.includes("studio_small_06_1k.hdr")),
    };
  });
  await pagina.screenshot({ path: join(saida, `${nome}-hero.png`), fullPage: false });

  const secao = pagina.locator("#sistema");
  await secao.scrollIntoViewIfNeeded();
  const canvas3d = pagina.getByLabel("Sete sinais convergindo em um núcleo conforme a rolagem").locator("canvas");
  await canvas3d.waitFor({ state: "visible", timeout: 30_000 });
  await pagina.waitForTimeout(500);
  const metricasCom3D = await pagina.evaluate(() => {
    const recursos = performance.getEntriesByType("resource");
    return {
      recursos: recursos.length,
      bytes: recursos.reduce((total, recurso) => total + (recurso.transferSize || recurso.encodedBodySize || 0), 0),
      hdriCarregado: recursos.some((recurso) => recurso.name.includes("studio_small_06_1k.hdr")),
    };
  });
  const geometria = await secao.evaluate((elemento) => {
    const caixa = elemento.getBoundingClientRect();
    return { topo: caixa.top + window.scrollY, altura: caixa.height };
  });

  const etapas = [];
  for (const [indice, progresso] of [0.08, 0.49, 0.86].entries()) {
    await pagina.evaluate(({ y }) => window.scrollTo({ top: y, behavior: "instant" }), {
      y: geometria.topo + (geometria.altura - viewport.height) * progresso,
    });
    await pagina.waitForTimeout(900);
    const visiveis = await secao.locator("article").evaluateAll((artigos) => artigos.map((artigo) => ({
      texto: artigo.querySelector("h3")?.textContent?.trim(),
      opacidade: Number.parseFloat(getComputedStyle(artigo).opacity),
      filtro: getComputedStyle(artigo).filter,
      visibilidade: getComputedStyle(artigo).visibility,
    })).filter((item) => item.opacidade > 0.25 && item.visibilidade === "visible"));
    etapas.push({ indice: indice + 1, visiveis });
    await pagina.screenshot({ path: join(saida, `${nome}-etapa-${indice + 1}.png`), fullPage: false });
  }

  resultados.push({
    nome,
    status: resposta?.status(),
    canvas3d: await canvas3d.count(),
    metricasIniciais,
    metricasCom3D,
    etapas,
    erros,
  });
  await pagina.close();
}

await validar("desktop", { width: 1440, height: 1000 });
await validar("mobile", { width: 390, height: 844 });
await navegador.close();

console.log(JSON.stringify({ saida, resultados }, null, 2));

if (resultados.some((resultado) => resultado.status !== 200 || resultado.erros.length > 0 || resultado.etapas.some((etapa) => etapa.visiveis.length !== 1))) {
  process.exitCode = 1;
}
