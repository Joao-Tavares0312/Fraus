/** Smoke real da LP; LP_URL aponta para build em execucao. Capturas opcionais em LP_EVIDENCIAS. */
import { chromium } from "playwright";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

const BASE = process.env.LP_URL ?? "http://localhost:3000";
const DESTINO = process.env.LP_EVIDENCIAS;
const ARGS = ["--enable-unsafe-webgpu", "--enable-features=Vulkan,WebGPU", "--use-angle=vulkan", "--ignore-gpu-blocklist"];
let navegador;
const falhas = [];
const evidencias = [];
if (DESTINO) await mkdir(DESTINO, { recursive: true });
function exigir(nome, condicao, detalhe) { if (!condicao) falhas.push(`${nome}: ${detalhe}`); }

async function abrir(viewport, { reduzido = false, semGpu = false, chuva = false, javaScriptEnabled = true } = {}) {
  // Cada caso recebe um processo/Instance proprio. Contextos isolam o DOM,
  // mas ainda compartilham o backend nativo WebGPU do processo anterior.
  await navegador?.close();
  navegador = await chromium.launch({ channel: "chrome", headless: true, args: ARGS });
  const contexto = await navegador.newContext({ viewport, deviceScaleFactor: 1, reducedMotion: reduzido ? "reduce" : "no-preference", javaScriptEnabled });
  await contexto.addInitScript(({ semGpu, chuva }) => {
    window.__lpSmoke = { submits: 0, destroys: 0, storage: [] };
    if (chuva) new MutationObserver(() => document.documentElement.classList.add("tema-chuva")).observe(document, { childList: true });
    if (semGpu) {
      let objeto = navigator;
      while (objeto) { if (Object.prototype.hasOwnProperty.call(objeto, "gpu")) delete objeto.gpu; objeto = Object.getPrototypeOf(objeto); }
    }
    if (typeof GPUAdapter !== "undefined") {
      const original = GPUAdapter.prototype.requestDevice;
      GPUAdapter.prototype.requestDevice = async function (...args) {
        const device = await original.apply(this, args);
        window.__deviceDaCena = device;
        const submit = device.queue.submit.bind(device.queue);
        device.queue.submit = (...a) => { window.__lpSmoke.submits++; return submit(...a); };
        const destroy = device.destroy.bind(device);
        device.destroy = () => { window.__lpSmoke.destroys++; return destroy(); };
        const createBuffer = device.createBuffer.bind(device);
        device.createBuffer = (descritor) => {
          if (descritor.usage & GPUBufferUsage.STORAGE) window.__lpSmoke.storage.push(descritor.size);
          return createBuffer(descritor);
        };
        return device;
      };
    }
  }, { semGpu, chuva });
  const pagina = await contexto.newPage();
  const erros = [];
  pagina.on("console", m => { if (m.type() === "error") erros.push(`console: ${m.text()} em ${pagina.url()} ${JSON.stringify(m.location())}`); });
  pagina.on("pageerror", e => erros.push(`pageerror: ${e.stack ?? e.message} em ${pagina.url()}`));
  const resposta = await pagina.goto(`${BASE}/`, { waitUntil: "networkidle", timeout: 90_000 });
  await pagina.evaluate(() => document.fonts.ready);
  if (javaScriptEnabled) await pagina.waitForFunction(() => document.querySelector(".ln")?.dataset.regime !== "carregando", null, { timeout: 30_000 });
  await pagina.waitForTimeout(300);
  return { contexto, pagina, erros, status: resposta?.status() };
}

async function registrar(nome, pagina, dados) {
  const arquivo = `${nome}.png`;
  if (DESTINO) await pagina.screenshot({ path: path.join(DESTINO, arquivo) });
  evidencias.push({ nome, captura: DESTINO ? arquivo : null, ...dados });
}
async function medidas(pagina) {
  return pagina.evaluate(() => {
    const raiz = document.querySelector(".ln");
    const botoes = [...document.querySelectorAll(".ln-hero .ln-botao")].map(b => ({ texto: b.textContent.trim(), href: b.getAttribute("href"), top: b.getBoundingClientRect().top, bottom: b.getBoundingClientRect().bottom, right: b.getBoundingClientRect().right }));
    window.scrollTo(10_000, 0);
    const diagnostico = document.querySelector(".ln-diagnostico details");
    const metodo = document.querySelector(".ln-metodo");
    const fecho = [...document.querySelectorAll(".ln-fecho .ln-botao")].map(b => b.getAttribute("href"));
    const ausencia = document.querySelector(".ln-leituras--ausentes");
    const navegacao = [...document.querySelectorAll(".ln-topo__acoes a")].map(a => {
      const r = a.getBoundingClientRect();
      return { href: a.getAttribute("href"), top: r.top, bottom: r.bottom, left: r.left, right: r.right, altura: r.height };
    });
    const materia = document.querySelector(".ln-limites__materia");
    const estiloDaMateria = materia && getComputedStyle(materia);
    const resumoDosLimites = document.querySelector(".ln-limites details summary");
    return {
      regime: raiz?.dataset.regime,
      rotulo: document.querySelector(".ln-regime")?.textContent,
      h1: document.querySelectorAll("h1").length,
      canvas: document.querySelectorAll("canvas").length,
      scrollX: window.scrollX,
      altura: innerHeight,
      largura: innerWidth,
      botoes,
      fecho,
      navegacao,
      materia: materia && {
        fundo: estiloDaMateria.backgroundImage,
        largura: materia.getBoundingClientRect().width,
        altura: materia.getBoundingClientRect().height,
        opacidade: estiloDaMateria.opacity,
        carregada: performance.getEntriesByType("resource").some(r => new URL(r.name).pathname === "/estudio-grafite.webp"),
      },
      resumoDosLimites: resumoDosLimites && { altura: resumoDosLimites.getBoundingClientRect().height },
      diagnosticoRecolhido: diagnostico && !diagnostico.open && getComputedStyle(diagnostico).position !== "fixed",
      metodoRecolhido: metodo && !metodo.open,
      casoNatural: getComputedStyle(document.querySelector(".ln-fusor__preso")).position !== "sticky",
      ausenciaCompacta: !ausencia || (ausencia.tagName === "ASIDE" && !ausencia.querySelector("h2,[role=tab]")),
      posteres: performance.getEntriesByType("resource").filter(r => /\/lp-nova\/.*\.(webp|png)/.test(r.name)).map(r => ({ url: r.name, bytes: r.encodedBodySize })),
      gpu: window.__lpSmoke,
    };
  });
}

try {
  for (const viewport of [{ width: 1280, height: 720 }, { width: 1568, height: 882 }, { width: 390, height: 844 }]) {
    for (const chuva of [false, true]) for (const semGpu of [false, true]) {
      const nome = `${viewport.width}x${viewport.height}-${chuva ? "chuva" : "instrumento"}-${semGpu ? "poster" : "vivo"}`;
      const { contexto, pagina, erros, status } = await abrir(viewport, { chuva, semGpu });
      const m = await medidas(pagina);
      exigir(nome, status === 200 && m.h1 === 1 && m.canvas === 1, `status/h1/canvas ${status}/${m.h1}/${m.canvas}`);
      exigir(nome, semGpu ? m.regime === "poster" : m.regime?.startsWith("vivo"), `regime ${m.regime}`);
      exigir(nome, m.scrollX === 0, `scrollX ${m.scrollX}`);
      exigir(nome, m.botoes.length === 2 && m.botoes.every(b => b.top >= 0 && b.bottom <= m.altura && b.right <= m.largura), `CTAs ausentes/fora da dobra: ${JSON.stringify(m.botoes)}`);
      exigir(nome, semGpu || m.posteres.length === 0, `vivo baixou poster: ${JSON.stringify(m.posteres)}`);
      exigir(nome, m.diagnosticoRecolhido && m.metodoRecolhido && m.casoNatural && m.ausenciaCompacta, `estrutura produto primeiro: ${JSON.stringify(m)}`);
      exigir(nome, m.fecho.join(",") === "/entrar,/cadastrar", `fecho sem acesso real: ${m.fecho}`);
      exigir(nome, m.navegacao.map(a => a.href).join(",") === "#metodo,/entrar" && m.navegacao.every(a => a.altura >= 44 && a.left >= 0 && a.right <= m.largura && a.top >= 0 && a.bottom <= m.altura), `navegacao cortada ou sem destino: ${JSON.stringify(m.navegacao)}`);
      exigir(nome, m.materia?.fundo.includes("/estudio-grafite.webp") && m.materia.carregada && m.materia.opacidade === "1" && m.materia.largura >= 250 && m.materia.altura >= 150, `materia ausente ou reduzida a detalhe: ${JSON.stringify(m.materia)}`);
      exigir(nome, m.resumoDosLimites?.altura >= 44, `resumo sem alvo de toque: ${JSON.stringify(m.resumoDosLimites)}`);
      await registrar(nome + "-hero", pagina, m);
      await pagina.locator(".ln-hero .ln-botao").first().click();
      const destino = m.botoes[0].href;
      exigir(nome, destino?.startsWith("#") && await pagina.locator(destino).isVisible(), `acao sem destino ${destino}`);
      await pagina.waitForTimeout(700);
      await registrar(nome + "-destino", pagina, { destino, erros });
      const metodo = pagina.locator(".ln-metodo");
      await metodo.locator("summary").focus();
      await pagina.keyboard.press("Enter");
      exigir(nome, await metodo.evaluate(e => e.open), "metodo nao abriu por teclado");
      for (const id of ["metodo", "leituras", "limites"]) {
        const ancora = pagina.locator(`#${id}`);
        exigir(nome, await ancora.count() === 1, `ancora inexistente/duplicada #${id}`);
      }
      await pagina.locator("#leituras").scrollIntoViewIfNeeded();
      await registrar(nome + "-metodo-aberto", pagina, { altura: await pagina.evaluate(() => document.documentElement.scrollHeight) });
      await metodo.locator("summary").focus();
      await pagina.keyboard.press("Enter");
      exigir(nome, !(await metodo.evaluate(e => e.open)), "metodo nao fechou por teclado");
      await pagina.locator(".ln-topo__metodo").focus();
      await pagina.keyboard.press("Enter");
      exigir(nome, new URL(pagina.url()).hash === "#metodo", "Como funciona nao chegou ao metodo");
      await pagina.locator("#limites").scrollIntoViewIfNeeded();
      await registrar(nome + "-limites-materia", pagina, { materia: m.materia });
      const limites = pagina.locator(".ln-limites details");
      await limites.locator("summary").focus();
      await pagina.keyboard.press("Enter");
      exigir(nome, await limites.evaluate(e => e.open), "limites nao abriram por teclado");
      await registrar(nome + "-limites-abertos", pagina, {});
      await pagina.keyboard.press("Enter");
      exigir(nome, !(await limites.evaluate(e => e.open)), "limites nao fecharam por teclado");
      await pagina.locator(".ln-fecho a[href='/cadastrar']").click();
      await pagina.waitForURL(url => url.pathname === "/cadastrar");
      exigir(nome, new URL(pagina.url()).pathname === "/cadastrar", "Criar conta nao chegou ao cadastro");
      await pagina.goto(`${BASE}/`, { waitUntil: "networkidle" });
      await pagina.locator(".ln-fecho a[href='/entrar']").click();
      await pagina.waitForURL(url => url.pathname === "/entrar");
      exigir(nome, new URL(pagina.url()).pathname === "/entrar", "Entrar nao chegou ao acesso");
      exigir(nome, erros.length === 0, erros.join(" | "));
      await contexto.close();
    }
  }
  {
    const { contexto, pagina, erros } = await abrir({ width: 1280, height: 720 });
    const antes = await pagina.evaluate(() => ({ ...window.__lpSmoke }));
    await pagina.emulateMedia({ reducedMotion: "reduce" });
    await pagina.waitForFunction(() => document.querySelector(".ln")?.dataset.regime === "poster");
    await pagina.waitForTimeout(300);
    const parada = await pagina.evaluate(() => ({ ...window.__lpSmoke }));
    await pagina.waitForTimeout(700);
    const depois = await pagina.evaluate(() => ({ ...window.__lpSmoke }));
    exigir("motion dinamico", parada.destroys > antes.destroys && depois.submits === parada.submits, JSON.stringify({ antes, parada, depois }));
    await registrar("motion-dinamico", pagina, { antes, parada, depois, erros });
    exigir("motion dinamico", erros.length === 0, erros.join(" | "));
    await contexto.close();
  }
  {
    const { contexto, pagina, erros } = await abrir({ width: 899, height: 900 });
    const inicial = await pagina.evaluate(() => ({ ...window.__lpSmoke }));
    await pagina.setViewportSize({ width: 900, height: 900 });
    await pagina.waitForFunction(() => window.__lpSmoke.destroys >= 1 && document.querySelector(".ln")?.dataset.regime?.startsWith("vivo"));
    await pagina.waitForTimeout(500);
    const largo = await pagina.evaluate(() => ({ ...window.__lpSmoke }));
    await pagina.setViewportSize({ width: 899, height: 900 });
    await pagina.waitForFunction(() => window.__lpSmoke.destroys >= 2 && document.querySelector(".ln")?.dataset.regime?.startsWith("vivo"));
    await pagina.waitForTimeout(500);
    const estreito = await pagina.evaluate(() => ({ ...window.__lpSmoke }));
    exigir("breakpoint", inicial.storage.at(-1) === 896000 && largo.storage.at(-1) === 6720000 && estreito.storage.at(-1) === 896000, JSON.stringify({ inicial, largo, estreito }));
    await registrar("breakpoint", pagina, { inicial, largo, estreito, erros });
    exigir("breakpoint", erros.length === 0, erros.join(" | "));
    await contexto.close();
  }
  {
    const { contexto, pagina, erros } = await abrir({ width: 1280, height: 720 });
    await pagina.waitForTimeout(8500);
    const repouso = await pagina.evaluate(() => ({ ...window.__lpSmoke }));
    await pagina.waitForTimeout(800);
    const parada = await pagina.evaluate(() => ({ ...window.__lpSmoke }));
    exigir("repouso", parada.submits === repouso.submits, JSON.stringify({ repouso, parada }));
    await pagina.mouse.wheel(0, 400);
    await pagina.waitForTimeout(500);
    const retorno = await pagina.evaluate(() => ({ ...window.__lpSmoke }));
    exigir("repouso", retorno.submits > parada.submits, "rolagem nao retomou render");
    await registrar("repouso-retorno", pagina, { repouso, parada, retorno, erros });
    await pagina.evaluate(() => window.__deviceDaCena.destroy());
    await pagina.waitForFunction(() => document.querySelector(".ln")?.dataset.regime === "poster");
    const cor = await pagina.locator(".ln-fala__texto").evaluate(e => getComputedStyle(e).color);
    exigir("device perdido", !/rgba\(0, 0, 0, 0\)/.test(cor), "frase transparente");
    exigir("repouso/device", erros.length === 0, erros.join(" | "));
    await contexto.close();
  }
  for (const largura of [320, 390, 1280]) {
    const { contexto, pagina, erros } = await abrir({ width: largura, height: 844 }, { reduzido: true });
    const m = await medidas(pagina);
    exigir("reduce/reflow", m.regime === "poster" && m.scrollX === 0, JSON.stringify(m));
    exigir("reduce/reflow", m.navegacao.every(a => a.altura >= 44 && a.left >= 0 && a.right <= m.largura), `navegacao fora da tela: ${JSON.stringify(m.navegacao)}`);
    await registrar(`${largura}-reduce`, pagina, m);
    exigir("reduce/reflow", erros.length === 0, erros.join(" | "));
    await contexto.close();
  }
  for (const largura of [320, 390, 1280]) {
    const { contexto, pagina } = await abrir({ width: largura, height: 844 }, { javaScriptEnabled: false });
    const m = await medidas(pagina);
    exigir("sem JS", m.botoes.length === 2 && m.posteres.length > 0 && m.scrollX === 0, JSON.stringify(m));
    exigir("sem JS", m.metodoRecolhido && m.casoNatural && m.fecho.join(",") === "/entrar,/cadastrar", JSON.stringify(m));
    exigir("sem JS", m.materia?.carregada && m.materia.largura >= 250 && m.materia.altura >= 150, `materia sem JS: ${JSON.stringify(m.materia)}`);
    exigir("sem JS", m.navegacao.every(a => a.altura >= 44 && a.left >= 0 && a.right <= m.largura), `navegacao sem JS: ${JSON.stringify(m.navegacao)}`);
    const metodo = pagina.locator(".ln-metodo");
    await metodo.locator("summary").focus();
    await pagina.keyboard.press("Enter");
    exigir("sem JS", await metodo.evaluate(e => e.open), "details nativo nao abriu");
    await registrar(`${largura}-sem-js`, pagina, m);
    await contexto.close();
  }
  {
    const { contexto, pagina } = await abrir({ width: 1280, height: 720 });
    const resposta = await pagina.goto(`${BASE}/leitura`, { waitUntil: "domcontentloaded" });
    exigir("redirect", new URL(pagina.url()).pathname === "/" && resposta?.status() === 200, pagina.url());
    await contexto.close();
  }
} finally {
  await navegador?.close();
  if (DESTINO) await writeFile(path.join(DESTINO, "resultados.json"), JSON.stringify({ base: BASE, data: new Date().toISOString(), falhas, evidencias }, null, 2));
}
if (falhas.length) { console.error(`FALHOU\n- ${falhas.join("\n- ")}`); process.exit(1); }
console.log("ok /: produto primeiro, aprofundamento por teclado, ancoras e acesso real, materia estatica visivel, navegacao com alvos de toque, dobras desktop/mobile, dois temas, vivo sem poster, fallback, motion dinamico, breakpoint, repouso/retorno, device perdido, reflow, sem JS e redirect");
