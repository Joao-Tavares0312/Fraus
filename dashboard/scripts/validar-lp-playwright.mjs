/** QA da LP coreografada. LP_URL aponta para o produto em execucao;
 * LP_EVIDENCIAS guarda capturas; LP_GPU=1 pede GPU real ao Chrome headless
 * (sem isso ele usa SwiftShader e o palco cai, de proposito, no WebP). */
import { chromium } from "playwright";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

const BASE = process.env.LP_URL ?? "http://127.0.0.1:3000";
const DESTINO = process.env.LP_EVIDENCIAS;
const GPU = process.env.LP_GPU === "1";
const FATOS = ["07", "39", "03", "00"];
const falhas = [];
const evidencias = [];
const navegador = await chromium.launch({
  channel: "chrome",
  headless: true,
  args: GPU ? ["--enable-gpu", "--use-angle=vulkan", "--ignore-gpu-blocklist"] : [],
});
if (DESTINO) await mkdir(DESTINO, { recursive: true });

function exigir(nome, condicao, detalhe) {
  if (!condicao) falhas.push(`${nome}: ${detalhe}`);
}

async function abrir(viewport, { reduzido = false, javaScriptEnabled = true, semGL = false } = {}) {
  const contexto = await navegador.newContext({ viewport, deviceScaleFactor: 1, reducedMotion: reduzido ? "reduce" : "no-preference", javaScriptEnabled });
  if (semGL) await contexto.addInitScript(() => {
    const original = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function (tipo, ...args) {
      return tipo === "webgl" || tipo === "webgl2" ? null : original.call(this, tipo, ...args);
    };
  });
  const pagina = await contexto.newPage();
  // O video do acesso derruba a GPU do Chrome headless+Vulkan: artefato do
  // ambiente de teste, nao da LP. Sem ele a volta mede so a remontagem.
  await pagina.route(/\.(mp4|webm)(\?.*)?$/, (rota) => rota.abort());
  const erros = [];
  pagina.on("pageerror", (erro) => erros.push(erro.stack ?? erro.message));
  pagina.on("console", (msg) => { if (msg.type() === "error" && !/ERR_FAILED/.test(msg.text())) erros.push(msg.text()); });
  const resposta = await pagina.goto(`${BASE}/`, { waitUntil: "networkidle" });
  exigir("status", resposta?.status() === 200, String(resposta?.status()));
  return { contexto, pagina, erros };
}

const capturar = async (pagina, nome) => {
  if (DESTINO) await pagina.screenshot({ path: path.join(DESTINO, `${nome}.png`) });
};
const contadores = (pagina) => pagina.locator("[data-n]").allTextContents();
const semRolagemLateral = (pagina) => pagina.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth);

try {
  // Sem JS: o servidor entrega a pagina inteira, numeros finais e sem preloader.
  {
    const { contexto, pagina } = await abrir({ width: 1440, height: 900 }, { javaScriptEnabled: false });
    exigir("sem JS: titulo", (await pagina.locator("h1").innerText()).includes("A análise começa."), "h1 incompleto");
    exigir("sem JS: preloader", !(await pagina.locator(".lp-pre").isVisible()), "preloader cobre a pagina sem script");
    exigir("sem JS: fatos", JSON.stringify(await contadores(pagina)) === JSON.stringify(FATOS), JSON.stringify(await contadores(pagina)));
    for (const destino of ["/entrar", "/cadastrar", "/dashboard"]) {
      exigir("sem JS: links", await pagina.locator(`a[href="${destino}"]`).count() > 0, `falta ${destino}`);
    }
    exigir("ceu: pontos sem JS", await pagina.locator(".lp-ceu .lp-ponto").count() === 140, "ceu sem os 140 pontos");
    await capturar(pagina, "sem-js");
    await contexto.close();
  }

  // Reduce: nada de preloader, pin ou rolagem suave; FR recua.
  {
    const { contexto, pagina, erros } = await abrir({ width: 1440, height: 900 }, { reduzido: true });
    await pagina.waitForTimeout(1200);
    exigir("reduce: preloader", !(await pagina.locator(".lp-pre").isVisible()), "preloader visivel");
    exigir("reduce: fatos", JSON.stringify(await contadores(pagina)) === JSON.stringify(FATOS), JSON.stringify(await contadores(pagina)));
    exigir("reduce: pin", await pagina.locator(".pin-spacer").count() === 0, "faixa fixada com reduce");
    exigir("reduce: lenis", !(await pagina.evaluate(() => document.documentElement.classList.contains("lenis"))), "rolagem suave com reduce");
    const risco = await pagina.locator(".lp-risco").first().evaluate((el) => ({ animacao: getComputedStyle(el).animationName, opacidade: getComputedStyle(el).opacity }));
    exigir("ceu: riscos parados e visiveis no reduce", risco.animacao === "none" && risco.opacidade === "1", JSON.stringify(risco));
    exigir("reduce: erros", erros.length === 0, erros.join(" | "));
    await capturar(pagina, "reduce");
    await contexto.close();
  }

  // Movimento: preloader na primeira visita, coreografia ativa, inversao no fecho.
  {
    const { contexto, pagina, erros } = await abrir({ width: 1440, height: 900 });
    exigir("ceu: pontos", await pagina.locator(".lp-ceu .lp-ponto").count() === 140, "ceu sem os 140 pontos");
    exigir("preloader: entrada", await pagina.locator(".lp-pre").isVisible(), "preloader nao tocou na primeira visita");
    await pagina.waitForTimeout(3500);
    exigir("preloader: saida", !(await pagina.locator(".lp-pre").isVisible()), "preloader preso");
    exigir("contadores", JSON.stringify(await contadores(pagina)) === JSON.stringify(FATOS), JSON.stringify(await contadores(pagina)));
    exigir("pin", await pagina.locator(".pin-spacer").count() === 1, "faixa nao foi fixada");
    const estado = await pagina.evaluate(() => ({ fr: document.querySelector(".lp")?.dataset.frEstado, backend: document.querySelector(".lp-gl")?.dataset.frBackend }));
    evidencias.push({ nome: "palco", ...estado });
    exigir("palco", estado.fr === "pronto" || estado.fr === "estatico", JSON.stringify(estado));
    if (GPU) exigir("palco com GPU", estado.fr === "pronto", JSON.stringify(estado));
    await capturar(pagina, "inicio");
    await pagina.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
    await pagina.waitForTimeout(2500);
    exigir("fecho: inversao", await pagina.locator(".lp.inv").count() === 1, "o mundo nao virou ouro");
    await pagina.waitForTimeout(800); // a opacidade dos pontos transiciona em 0,6 s
    const opacidadePonto = await pagina.locator(".lp-ceu .lp-ponto").first().evaluate((el) => getComputedStyle(el).opacity);
    exigir("ceu: pontos somem no fecho", opacidadePonto === "0", opacidadePonto);
    exigir("indice", (await pagina.locator(".lp-indice").innerText()) === "07 / 07", await pagina.locator(".lp-indice").innerText());
    await capturar(pagina, "fecho");
    await pagina.evaluate(() => window.scrollTo(0, 0));
    await pagina.waitForTimeout(1200);
    await pagina.reload({ waitUntil: "networkidle" });
    exigir("preloader: uma vez por sessao", !(await pagina.locator(".lp-pre").isVisible()), "tocou de novo apos reload");

    // Ida e volta pelo App Router: nada da coreografia sobra na outra rota.
    await pagina.waitForTimeout(1500);
    await pagina.locator(".lp-cabecalho a[href='/entrar']").click();
    await pagina.waitForURL((url) => url.pathname === "/entrar");
    await pagina.waitForTimeout(800);
    const sobra = await pagina.evaluate(() => ({ pin: document.querySelectorAll(".pin-spacer").length, lenis: document.documentElement.classList.contains("lenis"), lp: !!document.querySelector(".lp") }));
    exigir("desmontagem", !sobra.pin && !sobra.lenis && !sobra.lp, JSON.stringify(sobra));
    await pagina.goBack();
    await pagina.waitForTimeout(2500);
    const volta = await pagina.evaluate(() => ({ fr: document.querySelector(".lp")?.dataset.frEstado, pin: document.querySelectorAll(".pin-spacer").length }));
    exigir("volta", volta.pin === 1 && (!GPU || volta.fr === "pronto"), JSON.stringify(volta));
    exigir("movimento: erros", erros.length === 0, erros.join(" | "));
    await contexto.close();
  }

  // Sem WebGL: FR pre-renderizado no lugar do canvas, sem erro.
  {
    const { contexto, pagina, erros } = await abrir({ width: 1440, height: 900 }, { semGL: true });
    await pagina.waitForTimeout(3500);
    exigir("sem WebGL: estado", await pagina.locator('.lp[data-fr-estado="estatico"]').count() === 1, "palco nao caiu para o estatico");
    exigir("sem WebGL: arte", await pagina.locator(".lp-palco-estatico .arte-estatica").isVisible(), "FR estatico invisivel");
    exigir("sem WebGL: erros", erros.length === 0, erros.join(" | "));
    await contexto.close();
  }

  // Celular: sem rolagem lateral (a faixa de 300vw fica dentro do overflow).
  {
    const { contexto, pagina, erros } = await abrir({ width: 390, height: 844 });
    await pagina.waitForTimeout(3500);
    exigir("celular: largura", await semRolagemLateral(pagina), "rolagem horizontal");
    await pagina.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight / 2));
    await pagina.waitForTimeout(1200);
    exigir("celular: largura no meio", await semRolagemLateral(pagina), "rolagem horizontal durante a faixa");
    exigir("celular: erros", erros.length === 0, erros.join(" | "));
    await capturar(pagina, "celular");
    await contexto.close();
  }

  {
    const { contexto, pagina } = await abrir({ width: 1280, height: 720 }, { reduzido: true });
    const resposta = await pagina.goto(`${BASE}/leitura`, { waitUntil: "networkidle" });
    exigir("redirect", resposta?.status() === 200 && new URL(pagina.url()).pathname === "/", pagina.url());
    await contexto.close();
  }
} finally {
  await navegador.close();
  if (DESTINO) await writeFile(path.join(DESTINO, "resultados.json"), JSON.stringify({ base: BASE, data: new Date().toISOString(), gpu: GPU, falhas, evidencias }, null, 2));
}
console.log("Palco:", JSON.stringify(evidencias));
if (falhas.length) { console.error(`FALHOU\n- ${falhas.join("\n- ")}`); process.exit(1); }
console.log(`ok LP: sem JS, reduce, coreografia, sem WebGL, celular e redirect${GPU ? " (GPU real)" : " (palco no WebP: rode com LP_GPU=1 para o caminho WebGL)"}`);
