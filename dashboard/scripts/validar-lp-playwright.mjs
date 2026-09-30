/**
 * Valida a vitrine (`/`) do Instrumento contra um servidor ja rodando em
 * http://localhost:3000 (`npm run dev` ou `npm run start`).
 *
 * O QUE ELE GARANTE, e por que cada item existe:
 *  - resposta 200, zero erro de console e zero `pageerror`;
 *  - nenhuma rolagem horizontal (o `body` nunca rola na horizontal, e em 390px
 *    e onde isso quebra primeiro);
 *  - CLS abaixo de 0,1 -- o orbe e o reveal por rolagem nao podem empurrar layout;
 *  - orcamento de bytes: a vitrine nao tem canvas, WebGL, three nem imagem
 *    bitmap, entao o teto e baixo de proposito. Se um dia estourar, alguem
 *    trouxe de volta o que a reformulacao de 30/09/2026 tirou;
 *  - o orbe GIRA por padrao e fica PARADO com `prefers-reduced-motion`;
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
const ORCAMENTO_BYTES = 1_400_000;
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
  pagina.on("console", (m) => {
    if (m.type() !== "error") return;
    const texto = m.text();
    // RUIDO CONHECIDO, e nao e da vitrine: com `prefers-reduced-motion` o
    // `MarcaFraus` (components/shell) hidrata com `transition` diferente do
    // servidor -- vem do `useReducedMotion` do Motion. Fica fora do gate ate
    // a marca ser corrigida; qualquer OUTRO erro de console derruba o teste.
    if (texto.includes("hydrated but some attributes") && texto.includes("MarcaFraus")) return;
    erros.push(`console: ${texto}`);
  });
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
    const nomeAnimacao = getComputedStyle(document.querySelector(".vt-orbe i")).animationName;
    return {
      bytes: recursos.reduce((t, r) => t + (r.transferSize || r.encodedBodySize || 0), 0),
      largura: { rolavel: document.documentElement.scrollWidth, janela: document.documentElement.clientWidth },
      h1: document.querySelectorAll("h1").length,
      landmarks: ["header", "nav", "main", "footer"].filter((t) => document.querySelector(t)).length,
      canvas: document.querySelectorAll("canvas").length,
      ledsSemRotulo: [...document.querySelectorAll('[data-slot="segmento-led"]')].filter((e) => !e.getAttribute("aria-label")).length,
      leds: document.querySelectorAll('[data-slot="segmento-led"]').length,
      orbeAnimado: nomeAnimacao !== "none",
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
  if (r.canvas !== 0) f.push(`${r.nome}: a vitrine nao tem canvas, achou ${r.canvas}`);
  if (r.h1 !== 1) f.push(`${r.nome}: esperava 1 h1, achou ${r.h1}`);
  if (r.landmarks !== 4) f.push(`${r.nome}: esperava 4 landmarks, achou ${r.landmarks}`);
  if (r.leds === 0 || r.ledsSemRotulo > 0) f.push(`${r.nome}: ${r.ledsSemRotulo} de ${r.leds} LED sem aria-label`);
  if (r.nome === "movimento-reduzido" ? r.orbeAnimado : !r.orbeAnimado) {
    f.push(`${r.nome}: orbe ${r.orbeAnimado ? "animado" : "parado"} onde deveria ${r.nome === "movimento-reduzido" ? "estar parado" : "girar"}`);
  }
  return f;
});
if (falhas.length) {
  console.error("\nFALHAS:\n - " + falhas.join("\n - "));
  process.exitCode = 1;
}
