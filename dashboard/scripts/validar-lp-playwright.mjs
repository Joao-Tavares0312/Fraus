/** LP_URL aponta para o produto em execucao; LP_EVIDENCIAS guarda capturas opcionais. */
import { chromium } from "playwright";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { createHash } from "node:crypto";

const BASE = process.env.LP_URL ?? "http://127.0.0.1:3000";
const DESTINO = process.env.LP_EVIDENCIAS;
const permitirSoftware = process.env.LP_GL_SOFTWARE === "1";
if (permitirSoftware) console.warn("QA FORCADO: WebGL em software permitido explicitamente. Nao e benchmark do caminho padrao de producao.");
const falhas = [];
const evidencias = [];
const navegador = await chromium.launch({ channel: "chrome", headless: true });
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
  else if (permitirSoftware) await contexto.addInitScript(() => {
    const original = HTMLCanvasElement.prototype.getContext;
    HTMLCanvasElement.prototype.getContext = function (tipo, ...args) {
      return tipo === "webgl" || tipo === "webgl2"
        ? original.call(this, tipo, { ...args[0], failIfMajorPerformanceCaveat: false })
        : original.call(this, tipo, ...args);
    };
  });
  const pagina = await contexto.newPage();
  const erros = [];
  pagina.on("pageerror", (erro) => erros.push(erro.stack ?? erro.message));
  const resposta = await pagina.goto(`${BASE}/`, { waitUntil: "networkidle" });
  await pagina.evaluate(() => document.fonts.ready);
  return { contexto, pagina, erros, status: resposta?.status() };
}

async function registrar(nome, pagina, dados = {}) {
  await pagina.locator(".arte-estatica").evaluateAll((imagens) => Promise.all(imagens.filter((imagem) => {
    const r = imagem.getBoundingClientRect();
    return r.width > 0 && r.bottom > 0 && r.top < innerHeight;
  }).map((imagem) => imagem.decode())));
  const arquivo = `${nome}.png`;
  if (DESTINO) await pagina.screenshot({ path: path.join(DESTINO, arquivo) });
  evidencias.push({ nome, captura: DESTINO ? arquivo : null, ...dados });
}

async function irParaEtapa(pagina, etapa) {
  await pagina.locator(`[data-cena="${etapa}"]`).evaluate((elemento) => elemento.scrollIntoView({ block: "center", behavior: "instant" }));
}

async function assentarArte(pagina, etapa) {
  await pagina.locator(".objeto-desktop [data-fr-estado]").waitFor();
  if (await pagina.locator(".objeto-desktop [data-fr-estado]").getAttribute("data-fr-estado") === "estatico") {
    await pagina.waitForFunction((valor) => document.querySelector(".objeto-desktop [data-fr-etapa]")?.dataset.frEtapa === String(valor), etapa);
    await pagina.locator(".objeto-desktop .arte-estatica").evaluate((imagem) => imagem.decode());
    return false;
  }
  await pagina.waitForFunction((valor) => {
    const arte = document.querySelector(".objeto-desktop [data-fr-etapa]");
    return arte?.dataset.frEtapa === String(valor) && arte.dataset.frAssentada === String(valor) && arte.dataset.frEstado === "pronto" && arte.dataset.frMovimento === "parado";
  }, etapa);
  await pagina.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  return true;
}

async function arteVisivel(pagina, compacta = false) {
  const png = await pagina.locator(compacta ? ".hero .arte-compacta" : ".objeto-desktop").screenshot();
  const cores = await pagina.evaluate(async (bytes) => {
    const imagem = await createImageBitmap(new Blob([new Uint8Array(bytes)], { type: "image/png" }));
    const tela = document.createElement("canvas");
    tela.width = imagem.width; tela.height = imagem.height;
    const ctx = tela.getContext("2d");
    ctx.drawImage(imagem, 0, 0);
    imagem.close();
    const pixels = ctx.getImageData(0, 0, tela.width, tela.height).data;
    let claro = 0, ouro = 0;
    for (let i = 0; i < pixels.length; i += 4) {
      const r = pixels[i], g = pixels[i + 1], b = pixels[i + 2];
      if (r > 150 && g > 150 && b > 130 && Math.max(r, g, b) - Math.min(r, g, b) < 50) claro++;
      if (r > 90 && r > g * 1.03 && g > b * 1.05) ouro++;
    }
    return { claro, ouro };
  }, [...png]);
  return { hash: createHash("sha256").update(png).digest("hex"), ...cores };
}

async function pose(pagina) {
  const estado = await pagina.locator(".objeto-desktop [data-fr-etapa]").evaluate((elemento) => ({
    etapa: Number(elemento.dataset.frEtapa),
    movimento: elemento.dataset.frMovimento,
    scroll: window.scrollY,
  }));
  return { ...estado, ...await arteVisivel(pagina) };
}

try {
  for (const viewport of [{ width: 1280, height: 720 }, { width: 1440, height: 900 }, { width: 390, height: 844 }, { width: 320, height: 844 }]) {
    for (const opcoes of [{}, { reduzido: true }, { javaScriptEnabled: false }]) {
      const nome = `${viewport.width}x${viewport.height}-${opcoes.reduzido ? "reduce" : opcoes.javaScriptEnabled === false ? "sem-js" : "normal"}`;
      const { contexto, pagina, erros, status } = await abrir(viewport, opcoes);
      const habilitada = viewport.width >= 900 && !opcoes.reduzido && opcoes.javaScriptEnabled !== false;
      const animada = habilitada ? await assentarArte(pagina, 0) : false;
      if (habilitada) {
        const capacidade = await pagina.locator(".fr-canvas").evaluate((canvas) => ({
          contexto: !!canvas.getContext("webgl", { failIfMajorPerformanceCaveat: true }),
          backend: canvas.dataset.frBackend,
        }));
        const contextoDisponivel = capacidade.contexto && (capacidade.backend !== "software" || permitirSoftware);
        exigir(nome, animada === contextoDisponivel && (!permitirSoftware || animada), `Renderizador nao corresponde a capacidade grafica real: ${JSON.stringify(capacidade)}`);
        evidencias.push({ nome: `${nome}-caminho`, caminho: animada ? "webgl" : "webp-sem-contexto-performatico", backend: capacidade.backend, softwarePermitido: permitirSoftware });
      }
      const medidas = await pagina.evaluate(() => {
        const hero = document.querySelector(".hero .acao-lp").getBoundingClientRect();
        const raiz = document.querySelector(".lp");
        const pincel = getComputedStyle(raiz, "::before");
        return {
          h1: document.querySelectorAll("h1").length,
          overflow: document.documentElement.scrollWidth > innerWidth,
          escultura: document.querySelector(".objeto-desktop [data-fr-etapa]")?.dataset.frEstado ?? "estatico",
          fundo: { altura: parseFloat(pincel.height), pagina: raiz.getBoundingClientRect().height, imagem: pincel.backgroundImage },
          hero: { left: hero.left, right: hero.right, top: hero.top, bottom: hero.bottom },
          nav: [...document.querySelectorAll(".lp-cabecalho nav a")].map((link) => {
            const r = link.getBoundingClientRect();
            return { href: link.getAttribute("href"), left: r.left, right: r.right, altura: r.height };
          }),
          acoes: [...document.querySelectorAll(".fecho a")].map((link) => link.getAttribute("href")),
        };
      });
      exigir(nome, status === 200 && medidas.h1 === 1, JSON.stringify({ status, medidas }));
      exigir(nome, !medidas.overflow, "overflow horizontal");
      exigir(nome, medidas.escultura === (animada ? "pronto" : "estatico"), `arte no modo errado: ${JSON.stringify(medidas)}`);
      exigir(nome, Math.abs(medidas.fundo.altura - medidas.fundo.pagina) <= 1 && medidas.fundo.imagem.includes("/identidade/fundo-pincel.svg"), `pincel nao cobre toda a LP: ${JSON.stringify(medidas.fundo)}`);
      exigir(nome, medidas.hero.left >= 0 && medidas.hero.right <= viewport.width && medidas.hero.top >= 0, "acao do hero cortada");
      if (viewport.width >= 900) exigir(nome, medidas.hero.bottom <= viewport.height, "acao do hero fora da primeira dobra desktop");
      exigir(nome, medidas.nav.every((link) => link.left >= 0 && link.right <= viewport.width && link.altura >= 44), "navegacao cortada ou sem alvo de toque");
      exigir(nome, medidas.acoes.includes("/entrar") && medidas.acoes.includes("/cadastrar"), "acesso sem destinos reais");
      exigir(nome, await pagina.locator("a[href='/dashboard']").count() > 0, "percurso sem destino na ferramenta");
      for (const ancora of ["inicio", "como-funciona", "sinais", "na-pratica", "leituras", "limites"]) {
        exigir(nome, await pagina.locator(`#${ancora}`).count() === 1, `ancora ausente/duplicada: ${ancora}`);
      }
      await registrar(`${nome}-hero`, pagina, medidas);
      const heroArte = await arteVisivel(pagina, viewport.width < 900);
      exigir(nome, heroArte.claro > 500 && heroArte.ouro > 500, `FR nao visivel: ${JSON.stringify(heroArte)}`);
      await pagina.locator(".hero .acao-lp").focus();
      await pagina.keyboard.press("Enter");
      exigir(nome, new URL(pagina.url()).hash === "#como-funciona", "acao do hero nao navegou");
      const detalhes = pagina.locator(".contexto-detalhes");
      await detalhes.locator("summary").focus();
      await pagina.keyboard.press("Enter");
      exigir(nome, !(await detalhes.evaluate((elemento) => elemento.open)), "detalhes nao fecharam por teclado");
      await pagina.keyboard.press("Enter");
      exigir(nome, await detalhes.evaluate((elemento) => elemento.open), "detalhes nao abriram por teclado");
      await registrar(`${nome}-contexto`, pagina);

      const gravadas = pagina.locator(".leituras-gravadas");
      if (await gravadas.count()) {
        await gravadas.locator("summary").focus();
        await pagina.keyboard.press("Enter");
        exigir(nome, await pagina.locator("[role='tabpanel']").isVisible(), "snapshot validado sem transcricao visivel");
        if (opcoes.javaScriptEnabled !== false) {
          const abas = pagina.getByRole("tab");
          await abas.first().focus();
          await pagina.keyboard.press("End");
          exigir(nome, await abas.last().getAttribute("aria-selected") === "true", "End nao selecionou ultima leitura");
          const nota = await pagina.locator("[role='tabpanel'] [aria-label^='nota estimada:']").getAttribute("aria-label");
          exigir(nome, nota && !/\d/.test(nota), `ausencia virou numero: ${nota}`);
          await pagina.keyboard.press("ArrowRight");
          exigir(nome, await abas.first().getAttribute("aria-selected") === "true", "seta nao circulou entre leituras");
        }
        await registrar(`${nome}-snapshot`, pagina);
        await gravadas.locator("summary").click();
      } else {
        exigir(nome, await pagina.locator(".leituras-ausentes [role='status']").count() === 1 && await pagina.getByRole("tab").count() === 0, "ausencia sem explicacao ou com escolhas ficticias");
      }
      for (const etapa of [2, 3]) {
        await irParaEtapa(pagina, etapa);
        if (viewport.width >= 900 && !opcoes.reduzido && opcoes.javaScriptEnabled !== false) await assentarArte(pagina, etapa);
        await registrar(`${nome}-etapa-${etapa}`, pagina);
      }
      if (viewport.width < 900 || opcoes.reduzido || opcoes.javaScriptEnabled === false) {
        exigir(nome, !(await pagina.locator(".legenda-arte button").isVisible()), "replay aparece onde a arte deve ser estatica");
      }
      await pagina.locator("#limites").scrollIntoViewIfNeeded();
      const limite = pagina.locator(".limite-detalhe").nth(1);
      await limite.locator("summary").focus();
      await pagina.keyboard.press("Enter");
      exigir(nome, await limite.evaluate((elemento) => elemento.open), "limites nao abriram por teclado");
      exigir(nome, !(await pagina.evaluate(() => document.documentElement.scrollWidth > innerWidth)), "overflow apos abrir detalhes");
      await registrar(`${nome}-limites`, pagina);
      exigir(nome, erros.length === 0, erros.join(" | "));
      await contexto.close();
    }
  }

  {
    const { contexto, pagina, erros } = await abrir({ width: 1440, height: 900 });
    const animada = await assentarArte(pagina, 0);
    if (animada) {
    await irParaEtapa(pagina, 1);
    await pagina.waitForFunction(() => document.querySelector(".objeto-desktop [data-fr-etapa]")?.dataset.frEtapa === "1");
    await pagina.waitForTimeout(100);
    await irParaEtapa(pagina, 3);
    await assentarArte(pagina, 3);
    const final = await pose(pagina);
    await pagina.waitForTimeout(150);
    const assentada = await pose(pagina);
    exigir("retarget rapido", final.etapa === 3 && final.hash === assentada.hash && final.claro > 500 && final.ouro > 500, JSON.stringify({ final, assentada }));
    await irParaEtapa(pagina, 1);
    await assentarArte(pagina, 1);
    const retorno = await pose(pagina);
    exigir("retorno", retorno.etapa === 1, JSON.stringify(retorno));
    // Screenshot de elemento pode esperar a composicao e chegar so apos o fim
    // da animacao em software. Captura pixels no draw real, antes do descarte
    // do drawing buffer, em vez de confundir estado anterior com imagem tardia.
    await pagina.evaluate(() => {
      const original = WebGLRenderingContext.prototype.drawArrays;
      const imagens = [];
      window.replayFraus = { imagens, restaurar: () => { WebGLRenderingContext.prototype.drawArrays = original; } };
      WebGLRenderingContext.prototype.drawArrays = function (...args) {
        original.apply(this, args);
        if (this.canvas.matches(".fr-canvas") && imagens.length < 3) imagens.push(this.canvas.toDataURL());
      };
    });
    await pagina.locator(".legenda-arte button").click();
    await pagina.waitForFunction(() => window.replayFraus.imagens.length > 0);
    const durante = await pagina.locator(".objeto-desktop [data-fr-etapa]").evaluate((elemento) => ({
      etapa: Number(elemento.dataset.frEtapa), movimento: elemento.dataset.frMovimento, scroll: window.scrollY,
    }));
    await assentarArte(pagina, 1);
    const quadrosReplay = await pagina.evaluate(() => {
      const { imagens, restaurar } = window.replayFraus;
      restaurar();
      delete window.replayFraus;
      return { capturados: imagens.length, distintos: new Set(imagens).size };
    });
    const repetida = await pose(pagina);
    exigir("replay", quadrosReplay.distintos > 1 && repetida.hash === retorno.hash && repetida.scroll === retorno.scroll, JSON.stringify({ retorno, durante, repetida, quadrosReplay }));
    await registrar("replay-retorno", pagina, { retorno, durante, repetida, quadrosReplay });
    await pagina.emulateMedia({ reducedMotion: "reduce" });
    await pagina.locator(".objeto-desktop [data-fr-etapa]").waitFor({ state: "detached" });
    exigir("reduce dinamico", !(await pagina.locator(".legenda-arte button").count()), "replay persistiu");
    await irParaEtapa(pagina, 2);
    const poster = pagina.locator(".objeto-desktop .arte-estatica");
    exigir("reduce dinamico", await poster.isVisible() && await poster.evaluate((imagem) => imagem.complete && imagem.naturalWidth > 0), "FR estatico nao carregou");
    await pagina.setViewportSize({ width: 899, height: 900 });
    exigir("breakpoint", !(await pagina.locator(".palco").isVisible()) && await pagina.locator(".arte-compacta").first().isVisible(), "arte mobile/desktop nao alternou");
    await pagina.setViewportSize({ width: 900, height: 900 });
    exigir("breakpoint", await pagina.locator(".palco").isVisible() && !(await pagina.locator(".arte-compacta").first().isVisible()), "arte desktop nao voltou");
    await pagina.emulateMedia({ reducedMotion: "no-preference" });
    await pagina.locator('.objeto-desktop [data-fr-estado="pronto"]').waitFor();
    await assentarArte(pagina, 2);
    const restaurada = await arteVisivel(pagina);
    exigir("retorno ao 3D", restaurada.claro > 500 && restaurada.ouro > 500, `FR nao visivel: ${JSON.stringify(restaurada)}`);
    exigir("narrativa", erros.length === 0, erros.join(" | "));
    } else {
      evidencias.push({ nome: "retarget/replay/media dinamica GL", exercitado: false, motivo: "Contexto recusado pela politica padrao; executar LP_GL_SOFTWARE=1 para QA forcado, nao para benchmark" });
    }
    await contexto.close();
  }

  {
    const { contexto, pagina, erros } = await abrir({ width: 1440, height: 900 }, { semGL: true });
    await pagina.locator('.objeto-desktop [data-fr-estado="estatico"]').waitFor();
    await pagina.locator(".objeto-desktop .arte-estatica").evaluate((imagem) => imagem.decode());
    const estatica = await arteVisivel(pagina);
    exigir("sem WebGL", estatica.claro > 500 && estatica.ouro > 500 && !(await pagina.locator(".legenda-arte button").count()), `fallback sem marca: ${JSON.stringify(estatica)}`);
    await irParaEtapa(pagina, 3);
    await pagina.waitForFunction(() => document.querySelector(".objeto-desktop [data-fr-etapa]")?.dataset.frEtapa === "3");
    await pagina.locator(".objeto-desktop .arte-estatica").evaluate((imagem) => imagem.decode());
    const final = await arteVisivel(pagina);
    exigir("sem WebGL", final.hash !== estatica.hash && final.claro > 500 && final.ouro > 500, `fallback nao segue a narrativa: ${JSON.stringify(final)}`);
    exigir("sem WebGL", erros.length === 0, erros.join(" | "));
    await registrar("sem-webgl", pagina, final);
    await contexto.close();
  }

  {
    const { contexto, pagina, erros } = await abrir({ width: 1440, height: 900 });
    const animada = await assentarArte(pagina, 0);
    if (animada) {
    await pagina.evaluate(() => {
      const desenhar = WebGLRenderingContext.prototype.drawArrays;
      window.quadrosArteFraus = 0;
      WebGLRenderingContext.prototype.drawArrays = function (...args) {
        window.quadrosArteFraus++;
        return desenhar.apply(this, args);
      };
    });
    await pagina.locator(".legenda-arte button").click();
    await pagina.waitForFunction(() => document.querySelector(".objeto-desktop [data-fr-etapa]")?.dataset.frMovimento === "animando");
    await assentarArte(pagina, 0);
    const quadros = await pagina.evaluate(() => window.quadrosArteFraus);
    await pagina.waitForTimeout(250);
    exigir("sem loop ocioso", quadros > 0 && quadros === await pagina.evaluate(() => window.quadrosArteFraus), "drawArrays continuou apos transicao");
    const extensao = await pagina.locator(".fr-canvas").evaluateHandle((canvas) => canvas.getContext("webgl").getExtension("WEBGL_lose_context"));
    if (await extensao.evaluate((valor) => !!valor)) {
      await extensao.evaluate((valor) => valor.loseContext());
      await pagina.locator('.objeto-desktop [data-fr-estado="estatico"]').waitFor();
      await pagina.locator(".objeto-desktop .arte-estatica").evaluate((imagem) => imagem.decode());
      const perdida = await arteVisivel(pagina);
      exigir("contexto perdido", perdida.claro > 500 && perdida.ouro > 500 && !(await pagina.locator(".legenda-arte button").count()), `marca desapareceu: ${JSON.stringify(perdida)}`);
      await registrar("contexto-perdido", pagina, perdida);
      await extensao.evaluate((valor) => valor.restoreContext());
      await assentarArte(pagina, 0);
      const restaurada = await arteVisivel(pagina);
      exigir("contexto restaurado", restaurada.claro > 500 && restaurada.ouro > 500 && await pagina.locator(".legenda-arte button").isVisible(), `marca nao voltou: ${JSON.stringify(restaurada)}`);
    } else {
      evidencias.push({ nome: "contexto perdido/restaurado", exercitado: false, motivo: "WEBGL_lose_context indisponivel neste navegador" });
    }
    await extensao.dispose();
    exigir("ciclo WebGL", erros.length === 0, erros.join(" | "));
    } else {
      evidencias.push({ nome: "loop ocioso/perda/restauracao GL", exercitado: false, motivo: "Contexto recusado pela politica padrao; arte WebP exercitada nas demais etapas" });
    }
    await contexto.close();
  }

  {
    const { contexto, pagina } = await abrir({ width: 1280, height: 720 });
    await pagina.locator(".fecho a[href='/cadastrar']").click();
    await pagina.waitForURL((url) => url.pathname === "/cadastrar");
    await pagina.goto(`${BASE}/`, { waitUntil: "networkidle" });
    await pagina.locator(".fecho a[href='/entrar']").click();
    await pagina.waitForURL((url) => url.pathname === "/entrar");
    const resposta = await pagina.goto(`${BASE}/leitura`, { waitUntil: "networkidle" });
    exigir("redirect", resposta?.status() === 200 && new URL(pagina.url()).pathname === "/", pagina.url());
    await contexto.close();
  }
} finally {
  await navegador.close();
  if (DESTINO) await writeFile(path.join(DESTINO, "resultados.json"), JSON.stringify({ base: BASE, data: new Date().toISOString(), softwarePermitido: permitirSoftware, falhas, evidencias }, null, 2));
}
for (const evento of evidencias.filter((item) => item.exercitado === false)) console.warn(`NAO EXERCITADO ${evento.nome}: ${evento.motivo}`);
console.log("Caminhos exercitados:", JSON.stringify(evidencias.filter((item) => item.caminho)));
if (falhas.length) { console.error(`FALHOU\n- ${falhas.join("\n- ")}`); process.exit(1); }
console.log("ok LP: navegacao, teclado, dados/ausencia e arte visivel; consultar evidencias para caminho WebGL/WebP e cenarios GL nao exercitados");
