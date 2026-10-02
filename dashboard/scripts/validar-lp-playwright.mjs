/**
 * Valida a vitrine (`/`) do Instrumento contra um servidor ja rodando em
 * http://localhost:3000 (`npm run dev` ou `npm run start`).
 *
 * O QUE ELE GARANTE, e por que cada item existe:
 *  - resposta 200, zero erro de console e zero `pageerror`;
 *  - nenhuma rolagem horizontal (o `body` nunca rola na horizontal, e em 390px
 *    e onde isso quebra primeiro);
 *  - CLS abaixo de 0,1 -- o orbe e o reveal por rolagem nao podem empurrar layout;
 *  - orcamento de bytes: a cena e UM canvas WebGL escrito a mao (sem three,
 *    sem GSAP; so o Lenis entra de dependencia), entao o teto continua baixo
 *    de proposito. Se estourar, alguem trouxe uma biblioteca de cena;
 *  - exatamente UM canvas, e o regime certo: `vt-vivo` por padrao,
 *    `vt-estatico` com `prefers-reduced-motion` (congela, nao desacelera);
 *  - o hero tem um unico `h1`, os quatro landmarks e todo `SegmentoLED` com
 *    `aria-label` (um SVG de poligonos sem rotulo nao diz nada a leitor de tela).
 *
 * As capturas vao para uma pasta temporaria e o caminho e impresso.
 */
import { chromium } from "playwright";
import { mkdir } from "node:fs/promises";
import { join } from "node:path";
import { tmpdir } from "node:os";

const saida = join(tmpdir(), "fraus-playwright");
await mkdir(saida, { recursive: true });

// Medidos na build de producao com folga para hash e metadados. Fontes entram
// (Bricolage, Martian Mono, Inter), e por isso o teto nao e menor.
const ORCAMENTO_BYTES = 700_000; // medido em build de producao: ~485 KB, com folga para hash e fonte
const navegador = await chromium.launch({ channel: "chrome", headless: true });
const resultados = [];

async function validar(nome, viewport, { movimentoReduzido = false } = {}) {
  const pagina = await navegador.newPage({ viewport, deviceScaleFactor: 1 });
  if (movimentoReduzido) await pagina.emulateMedia({ reducedMotion: "reduce" });
  await pagina.addInitScript(() => {
    window.__vitais = { cls: 0 };
    new PerformanceObserver((lista) => {
      for (const entrada of lista.getEntries()) if (!entrada.hadRecentInput) window.__vitais.cls += entrada.value;
    }).observe({ type: "layout-shift", buffered: true });
  });
  const erros = [];
  pagina.on("console", (m) => { if (m.type() === "error") erros.push(`console: ${m.text()}`); });
  pagina.on("pageerror", (e) => erros.push(`pageerror: ${e.message}`));

  const resposta = await pagina.goto("http://localhost:3000", { waitUntil: "networkidle", timeout: 60_000 });
  await pagina.screenshot({ path: join(saida, `${nome}-hero.png`) });

  // Rola a pagina inteira: dispara os reveals e mede o CLS de verdade.
  const altura = await pagina.evaluate(() => document.documentElement.scrollHeight);
  for (let y = 0; y < altura; y += 500) {
    await pagina.evaluate((yy) => window.scrollTo(0, yy), y);
    await pagina.waitForTimeout(80);
  }
  await pagina.evaluate(() => window.scrollTo(0, 0));
  await pagina.screenshot({ path: join(saida, `${nome}-pagina.png`), fullPage: true });

  const medidas = await pagina.evaluate(() => {
    const recursos = performance.getEntriesByType("resource");
    return {
      bytes: recursos.reduce((t, r) => t + (r.transferSize || r.encodedBodySize || 0), 0),
      largura: { rolavel: document.documentElement.scrollWidth, janela: document.documentElement.clientWidth },
      h1: document.querySelectorAll("h1").length,
      landmarks: ["header", "nav", "main", "footer"].filter((t) => document.querySelector(t)).length,
      canvas: document.querySelectorAll("canvas").length,
      ledsSemRotulo: [...document.querySelectorAll('[data-slot="segmento-led"]')].filter((e) => !e.getAttribute("aria-label")).length,
      leds: document.querySelectorAll('[data-slot="segmento-led"]').length,
      regime: document.querySelector(".vt")?.classList.contains("vt-estatico") ? "estatico" : "vivo",
      cls: window.__vitais.cls,
    };
  });
  resultados.push({ nome, status: resposta?.status(), altura, ...medidas, erros });
  await pagina.close();
}

await validar("desktop", { width: 1440, height: 900 });
await validar("mobile", { width: 390, height: 844 });
await validar("movimento-reduzido", { width: 1440, height: 900 }, { movimentoReduzido: true });
await navegador.close();
console.log(JSON.stringify({ saida, resultados }, null, 2));

const falhas = resultados.flatMap((r) => {
  const f = [];
  if (r.status !== 200) f.push(`${r.nome}: status ${r.status}`);
  if (r.erros.length) f.push(`${r.nome}: ${r.erros.length} erro(s) de console`);
  if (r.largura.rolavel > r.largura.janela) f.push(`${r.nome}: rolagem horizontal (${r.largura.rolavel} > ${r.largura.janela})`);
  if (r.cls > 0.1) f.push(`${r.nome}: CLS ${r.cls.toFixed(3)} > 0,1`);
  if (r.bytes > ORCAMENTO_BYTES) f.push(`${r.nome}: ${r.bytes} bytes > ${ORCAMENTO_BYTES}`);
  if (r.canvas !== 1) f.push(`${r.nome}: a vitrine tem um canvas so, achou ${r.canvas}`);
  if (r.h1 !== 1) f.push(`${r.nome}: esperava 1 h1, achou ${r.h1}`);
  if (r.landmarks !== 4) f.push(`${r.nome}: esperava 4 landmarks, achou ${r.landmarks}`);
  if (r.leds === 0 || r.ledsSemRotulo > 0) f.push(`${r.nome}: ${r.ledsSemRotulo} de ${r.leds} LED sem aria-label`);
  const regimeEsperado = r.nome === "movimento-reduzido" ? "estatico" : "vivo";
  if (r.regime !== regimeEsperado) f.push(`${r.nome}: regime ${r.regime}, esperava ${regimeEsperado}`);
  return f;
});
if (falhas.length) {
  console.error("\nFALHAS:\n - " + falhas.join("\n - "));
  process.exitCode = 1;
}
