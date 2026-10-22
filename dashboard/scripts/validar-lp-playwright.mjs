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
  if (GPU) await contexto.addInitScript(() => {
    // Invariante de recursos: perder/restaurar nao pode acumular listeners.
    window.__qaRedimensionadores = new Set();
    const adicionar = window.addEventListener.bind(window);
    const remover = window.removeEventListener.bind(window);
    window.addEventListener = function (tipo, fn, opcoes) {
      if (tipo === "resize") window.__qaRedimensionadores.add(fn);
      return adicionar(tipo, fn, opcoes);
    };
    window.removeEventListener = function (tipo, fn, opcoes) {
      if (tipo === "resize") window.__qaRedimensionadores.delete(fn);
      return remover(tipo, fn, opcoes);
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
    // Placas sao pseudo-elementos: o embaralhar reescreve o texto e elas ficam.
    {
      const botao = pagina.locator(".lp .btn.placas").first();
      const original = (await botao.textContent()) ?? "";
      await botao.hover();
      await pagina.waitForTimeout(1000);
      const depois = await botao.evaluate((el) => ({
        texto: el.textContent,
        rotulo: el.getAttribute("aria-label"),
        face: getComputedStyle(el, "::before").content,
        filtro: getComputedStyle(el).filter,
        opacidade: getComputedStyle(el).opacity,
      }));
      exigir("botao: texto apos embaralhar", depois.texto === original, JSON.stringify(depois.texto));
      exigir("botao: placas", depois.face !== "none" && depois.filtro.includes("drop-shadow"), JSON.stringify(depois));
      exigir("botao: nome acessivel", depois.rotulo === original, JSON.stringify(depois.rotulo));
      // Transicao de opacity nas placas fazia o GSAP gravar 0 como valor final do .rv.
      exigir("botao: visivel apos a entrada", depois.opacidade === "1", depois.opacidade);
      await capturar(pagina, "lp-hero");
      await pagina.mouse.move(0, 0);
    }
    exigir("contadores", JSON.stringify(await contadores(pagina)) === JSON.stringify(FATOS), JSON.stringify(await contadores(pagina)));
    exigir("pin", await pagina.locator(".pin-spacer").count() === 1, "faixa nao foi fixada");
    const estado = await pagina.evaluate(() => ({ fr: document.querySelector(".lp")?.dataset.frEstado, backend: document.querySelector(".lp-gl")?.dataset.frBackend }));
    evidencias.push({ nome: "palco", ...estado });
    exigir("palco", estado.fr === "pronto" || estado.fr === "estatico", JSON.stringify(estado));
    if (GPU) exigir("palco com GPU", estado.fr === "pronto", JSON.stringify(estado));
    if (GPU && estado.fr === "pronto") {
      const contagens = [await pagina.evaluate(() => window.__qaRedimensionadores.size)];
      for (let ciclo = 0; ciclo < 2; ciclo++) {
        await pagina.evaluate(() => {
          window.__qaPerda = document.querySelector(".lp-gl").getContext("webgl").getExtension("WEBGL_lose_context");
          window.__qaPerda.loseContext();
        });
        await pagina.waitForFunction(() => document.querySelector(".lp").dataset.frEstado === "estatico");
        await pagina.evaluate(() => window.__qaPerda.restoreContext());
        await pagina.waitForFunction(() => document.querySelector(".lp").dataset.frEstado === "pronto");
        contagens.push(await pagina.evaluate(() => window.__qaRedimensionadores.size));
      }
      exigir("contexto: sem recursos acumulados", contagens.every((n) => n === contagens[0]), JSON.stringify(contagens));
      evidencias.push({ nome: "recuperacao-contexto", contagens });
    }
    await capturar(pagina, "inicio");
    await pagina.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight));
    await pagina.waitForTimeout(2500);
    exigir("fecho: inversao", await pagina.locator(".lp.inv").count() === 1, "o mundo nao virou ouro");
    await pagina.waitForTimeout(800); // a opacidade dos pontos transiciona em 0,6 s
    const opacidadePonto = await pagina.locator(".lp-ceu .lp-ponto").first().evaluate((el) => getComputedStyle(el).opacity);
    exigir("ceu: pontos somem no fecho", opacidadePonto === "0", opacidadePonto);
    exigir("indice", (await pagina.locator(".lp-indice").innerText()) === "07 / 07", await pagina.locator(".lp-indice").innerText());
    await capturar(pagina, "fecho");
    // A primeira visita ao letreiro pode ser na volta do fecho, em reverso.
    await pagina.evaluate(() => {
      const mq = document.querySelector(".mq");
      window.scrollTo(0, mq.getBoundingClientRect().top + scrollY - innerHeight / 3);
    });
    await pagina.waitForTimeout(1200);
    const letreiro = pagina.locator("[data-letreiro]");
    const retorno = await letreiro.evaluate((el) => getComputedStyle(el).transform);
    await pagina.waitForTimeout(400);
    exigir("letreiro: retorno em reverso", await letreiro.evaluate((el) => getComputedStyle(el).transform) !== retorno, "letreiro parado ao entrar vindo de baixo");
    await pagina.evaluate(() => window.scrollTo(0, 0));
    await pagina.waitForTimeout(1200);
    const foraDaTela = await letreiro.evaluate((el) => getComputedStyle(el).transform);
    await pagina.waitForTimeout(400);
    exigir("letreiro: pausa fora da tela", await letreiro.evaluate((el) => getComputedStyle(el).transform) === foraDaTela, "letreiro continua escrevendo transform fora da tela");
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
