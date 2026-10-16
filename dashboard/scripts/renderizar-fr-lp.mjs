/** Pre-renderiza a arte real da LP; execute com o produto local aberto em LP_URL. */
import { chromium } from "playwright";
import { mkdir } from "node:fs/promises";
import { execFileSync } from "node:child_process";
import path from "node:path";

const base = process.env.LP_URL ?? "http://127.0.0.1:3000";
const destino = path.resolve("public/identidade");
const permitirSoftware = process.env.LP_GL_SOFTWARE === "1";
if (permitirSoftware) console.warn("CAPTURA OFFLINE: WebGL em software permitido explicitamente. Nao representa desempenho do caminho padrao de producao.");
const navegador = await chromium.launch({ channel: "chrome", headless: true });
try {
  await mkdir(destino, { recursive: true });
  const pagina = await navegador.newPage({ viewport: { width: 1920, height: 900 }, deviceScaleFactor: 2, reducedMotion: "no-preference" });
  if (permitirSoftware) await pagina.addInitScript(() => {
    const original = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function (tipo, ...args) {
      return tipo === "webgl" || tipo === "webgl2"
        ? original.call(this, tipo, { ...args[0], failIfMajorPerformanceCaveat: false })
        : original.call(this, tipo, ...args);
    };
  });
  await pagina.goto(base, { waitUntil: "networkidle" });
  const arte = pagina.locator(".objeto-desktop [data-fr-estado]");
  await arte.waitFor();
  if (await arte.getAttribute("data-fr-estado") !== "pronto") {
    throw new Error("A exportacao exige GL real inicializado. Para captura offline controlada em backend de software, autorize explicitamente LP_GL_SOFTWARE=1; isso nao mede desempenho de producao.");
  }
  // Recorte transparente e constante; geometria, poses e materiais continuam
  // vindo do componente do produto, sem uma segunda representacao da marca.
  await pagina.addStyleTag({ content: `
    html, body, .lp { background: transparent !important; }
    .lp::before { display: none !important; }
    .lp .palco { height: 700px !important; }
    .lp .objeto-desktop { position: relative; flex: none; width: 800px; height: 640px; min-height: 0; }
  ` });
  const pedidas = process.argv.slice(2).map(Number);
  for (const etapa of pedidas.length ? pedidas : [0, 1, 2, 3]) {
    await pagina.locator(`[data-cena="${etapa}"]`).evaluate((elemento) => window.scrollTo({ top: window.scrollY + elemento.getBoundingClientRect().top - 40, behavior: "instant" }));
    await pagina.waitForFunction((valor) => {
      const arte = document.querySelector(".objeto-desktop [data-fr-etapa]");
      return arte?.dataset.frEtapa === String(valor) && arte.dataset.frAssentada === String(valor) && arte.dataset.frEstado === "pronto" && arte.dataset.frMovimento === "parado";
    }, etapa);
    // Transicoes nativas nao aparecem em getAnimations(); captura so apos draw final.
    await pagina.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))));
    const png = await pagina.locator(".objeto-desktop").screenshot({ omitBackground: true });
    for (const [sufixo, largura, altura] of [["", 1280, 1024], ["-compacto", 800, 640]]) {
      const arquivo = path.join(destino, `fr-lp-${etapa}${sufixo}.webp`);
      execFileSync("ffmpeg", ["-y", "-v", "error", "-f", "image2pipe", "-i", "pipe:0", "-frames:v", "1", "-vf", `scale=${largura}:${altura}`, "-c:v", "libwebp", "-quality", "82", "-compression_level", "6", arquivo], { input: png });
      console.log(`FR ${etapa}: ${arquivo}`);
    }
  }
} finally {
  await navegador.close();
}
