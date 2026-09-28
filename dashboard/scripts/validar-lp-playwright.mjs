import { chromium } from "playwright";
import { mkdir } from "node:fs/promises";
import { join } from "node:path";
import { tmpdir } from "node:os";

const saida = join(tmpdir(), "fraus-playwright");
await mkdir(saida, { recursive: true });
// Valores medidos na build de producao, com uma pequena margem para hashes e
// metadados do compilador. A cena leve nunca pode baixar o pacote 3D (~1,95 MB).
const ORCAMENTOS = { desktop: { inicial: 725_000, total: 2_700_000 }, leve: { inicial: 725_000, total: 725_000 } };
const navegador = await chromium.launch({ channel: "chrome", headless: true });
const resultados = [];

async function validar(nome, viewport, opcoes = {}) {
  const pagina = await navegador.newPage({ viewport, deviceScaleFactor: 1 });
  if (opcoes.movimentoReduzido) await pagina.emulateMedia({ reducedMotion: "reduce" });
  if (opcoes.economizarDados) await pagina.addInitScript(() => {
    Object.defineProperty(navigator, "connection", { configurable: true, value: { saveData: true, addEventListener() {}, removeEventListener() {} } });
  });
  await pagina.addInitScript(() => {
    window.__metricasFraus = { cls: 0, lcp: 0 };
    new PerformanceObserver((lista) => {
      for (const entrada of lista.getEntries()) if (!entrada.hadRecentInput) window.__metricasFraus.cls += entrada.value;
    }).observe({ type: "layout-shift", buffered: true });
    new PerformanceObserver((lista) => {
      window.__metricasFraus.lcp = lista.getEntries().at(-1)?.startTime ?? 0;
    }).observe({ type: "largest-contentful-paint", buffered: true });
  });
  const erros = [];
  pagina.on("console", (mensagem) => { if (mensagem.type() === "error") erros.push(`console: ${mensagem.text()}`); });
  pagina.on("pageerror", (erro) => erros.push(`pageerror: ${erro.message}`));
  const resposta = await pagina.goto("http://localhost:3000", { waitUntil: "networkidle", timeout: 60_000 });
  const medirRecursos = () => pagina.evaluate(() => {
    const recursos = performance.getEntriesByType("resource");
    return {
      recursos: recursos.length,
      bytes: recursos.reduce((total, recurso) => total + (recurso.transferSize || recurso.encodedBodySize || 0), 0),
      hdriCarregado: recursos.some((recurso) => recurso.name.includes("studio_small_06_1k.hdr")),
    };
  });
  const metricasIniciais = await medirRecursos();
  await pagina.screenshot({ path: join(saida, `${nome}-hero.png`), fullPage: false });
  const secao = pagina.locator("#sistema");
  await secao.scrollIntoViewIfNeeded();
  const canvas3d = pagina.getByLabel(/Sete sinais convergindo/).locator("canvas");
  if (opcoes.espera3d) await canvas3d.waitFor({ state: "visible", timeout: 30_000 });
  else await secao.locator('[data-cena="leve"]').waitFor({ state: "visible", timeout: 10_000 });
  await pagina.waitForTimeout(500);
  const metricasCom3D = await medirRecursos();
  const geometria = await secao.evaluate((elemento) => {
    const caixa = elemento.getBoundingClientRect();
    return { topo: caixa.top + window.scrollY, altura: caixa.height };
  });
  const etapas = [];
  for (const [indice, progresso] of (opcoes.espera3d ? [0.08, 0.49, 0.86] : [0]).entries()) {
    await pagina.evaluate(({ y }) => window.scrollTo({ top: y, behavior: "instant" }), { y: geometria.topo + Math.max(0, geometria.altura - viewport.height) * progresso });
    await pagina.waitForTimeout(opcoes.espera3d ? 900 : 100);
    const visiveis = await secao.locator("article").evaluateAll((artigos) => artigos.map((artigo) => ({
      texto: artigo.querySelector("h3")?.textContent?.trim(), opacidade: Number.parseFloat(getComputedStyle(artigo).opacity), visibilidade: getComputedStyle(artigo).visibility,
    })).filter((item) => item.opacidade > 0.25 && item.visibilidade === "visible"));
    etapas.push({ indice: indice + 1, visiveis });
    await pagina.screenshot({ path: join(saida, `${nome}-etapa-${indice + 1}.png`), fullPage: false });
  }
  resultados.push({
    nome, status: resposta?.status(), canvas3d: await canvas3d.count(), metricasIniciais, metricasCom3D,
    vitais: await pagina.evaluate(() => ({ ...window.__metricasFraus, fcp: performance.getEntriesByName("first-contentful-paint")[0]?.startTime ?? 0 })),
    etapas, erros,
  });
  await pagina.close();
}

await validar("desktop", { width: 1440, height: 1000 }, { espera3d: true });
await validar("mobile", { width: 390, height: 844 });
await validar("movimento-reduzido", { width: 1440, height: 1000 }, { movimentoReduzido: true });
await validar("economia-de-dados", { width: 1440, height: 1000 }, { economizarDados: true });
await navegador.close();
console.log(JSON.stringify({ saida, orcamentos: ORCAMENTOS, resultados }, null, 2));

const regressao = resultados.some((resultado) => {
  const completo = resultado.nome === "desktop";
  const orcamento = completo ? ORCAMENTOS.desktop : ORCAMENTOS.leve;
  return resultado.status !== 200 || resultado.erros.length > 0
    || resultado.metricasIniciais.bytes > orcamento.inicial || resultado.metricasCom3D.bytes > orcamento.total
    || resultado.vitais.cls > 0.1
    || (completo && resultado.etapas.some((etapa) => etapa.visiveis.length !== 1))
    || (!completo && (resultado.canvas3d !== 0 || resultado.metricasCom3D.hdriCarregado || resultado.etapas[0]?.visiveis.length !== 3));
});
if (regressao) process.exitCode = 1;
