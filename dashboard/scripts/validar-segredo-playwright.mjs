/** Produto iniciado: aparicao da Fraus-chan, indicadores intactos e modais aninhados. */
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { mkdir } from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright";

const BASE = process.env.DASHBOARD_URL ?? "http://127.0.0.1:3000";
assert.ok(["localhost", "127.0.0.1", "[::1]"].includes(new URL(BASE).hostname), "QA somente local");
const DESTINO = process.env.SEGREDO_EVIDENCIAS;
const navegador = await chromium.launch({ channel: "chrome", headless: true });
const erros = [];
const cenarios = [];
if (DESTINO) await mkdir(DESTINO, { recursive: true });

async function esperarMovimento(pagina) {
  await pagina.evaluate(() => Promise.all(document.getAnimations().map((animacao) => animacao.finished.catch(() => {}))));
}

async function esperarPersonagem(pagina) {
  await pagina.waitForFunction(() => document.querySelector('[role="dialog"] button[aria-label="Interagir com Fraus-chan"]')?.disabled === false);
  await esperarMovimento(pagina);
}

async function arte(personagem) {
  // Captura os pixels visiveis sem rolar o dialogo nem alterar a viewport.
  const clip = await personagem.evaluate((elemento) => {
    const caixa = elemento.getBoundingClientRect();
    const dialogo = elemento.closest('[role="dialog"]').getBoundingClientRect();
    const x = Math.max(0, caixa.left, dialogo.left);
    const y = Math.max(0, caixa.top, dialogo.top);
    return {
      x, y,
      width: Math.min(innerWidth, caixa.right, dialogo.right) - x,
      height: Math.min(innerHeight, caixa.bottom, dialogo.bottom) - y,
    };
  });
  return createHash("sha256").update(await personagem.page().screenshot({ clip })).digest("hex");
}

try {
  for (const { largura, altura, claro, reduce } of [
    { largura: 1440, altura: 960, claro: false, reduce: false },
    { largura: 1280, altura: 900, claro: true, reduce: false },
    { largura: 390, altura: 844, claro: false, reduce: false },
    { largura: 320, altura: 740, claro: true, reduce: true },
    { largura: 844, altura: 390, claro: false, reduce: true },
  ]) {
    const contexto = await navegador.newContext({ viewport: { width: largura, height: altura }, deviceScaleFactor: 1, reducedMotion: reduce ? "reduce" : "no-preference" });
    if (claro) await contexto.addInitScript(() => localStorage.setItem("fraus-tema", "claro"));
    const pagina = await contexto.newPage();
    pagina.on("pageerror", (erro) => erros.push(erro.message));
    const posesBaixadas = [];
    pagina.on("response", (resposta) => {
      if (resposta.url().includes("/fraus-chan/")) posesBaixadas.push({ url: resposta.url(), status: resposta.status() });
    });
    await pagina.goto(`${BASE}/dashboard?de=2026-08-01&ate=2026-08-22`, { waitUntil: "networkidle" });
    await pagina.getByRole("heading", { name: "Visão geral", exact: true }).waitFor();
    await pagina.evaluate(() => document.fonts.ready);
    const indicadores = pagina.locator('[data-slot="indicador"]');
    assert.equal(await indicadores.count(), 4, "requer snapshot de QA com os quatro indicadores");
    const antes = await indicadores.allTextContents();
    assert.equal(posesBaixadas.length, 0, "as poses nao carregam antes de descobrir o segredo");
    if (largura < 768) await pagina.getByRole("button", { name: "Abrir navegação", exact: true }).click();
    const marca = pagina.getByRole("button", { name: "Fraus — revelar o segredo com cinco cliques", exact: true });
    const segredo = pagina.getByRole("dialog", { name: "Fraus-chan", exact: true });
    for (let i = 0; i < 4; i++) await marca.click({ delay: 60 });
    assert.equal(await segredo.count(), 0, "quatro cliques nao abrem o segredo");
    await marca.click();
    await segredo.waitFor();
    await pagina.waitForFunction(() => document.activeElement?.getAttribute("aria-label") === "Fechar segredo");
    await segredo.getByRole("button", { name: "Dar um oi", exact: true }).waitFor();
    await esperarPersonagem(pagina);
    assert.deepEqual(await indicadores.allTextContents(), antes, "a aparicao nao altera indicadores");
    assert.ok(posesBaixadas.every((resposta) => resposta.status === 200), "artes reais servidas sem erro");
    assert.equal(await segredo.locator("img").evaluateAll((imagens) => imagens.every((imagem) => imagem.complete && imagem.naturalWidth > 0)), true);
    if (reduce) assert.equal(await segredo.evaluate((elemento) => elemento.getAnimations({ subtree: true }).length), 0, "reduce sem animacao espacial");
    assert.equal(await segredo.evaluate((elemento) => elemento.scrollWidth <= elemento.clientWidth), true, "painel sem overflow horizontal");
    assert.equal(await pagina.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
    if (DESTINO) await pagina.screenshot({ path: path.join(DESTINO, `segredo-${largura}-aberto.png`) });
    const personagem = segredo.getByRole("button", { name: "Interagir com Fraus-chan", exact: true });
    const falaInicial = await segredo.getByRole("status").innerText();
    const saudacao = await arte(personagem);

    // A mesma interacao funciona pelo teclado e diretamente na personagem.
    const oi = segredo.getByRole("button", { name: "Dar um oi", exact: true });
    await oi.focus();
    await oi.press("Enter");
    await segredo.getByRole("button", { name: "Fechar segredo", exact: true }).focus();
    await esperarMovimento(pagina);
    const falaCumplice = await segredo.getByRole("status").innerText();
    assert.notEqual(falaCumplice, falaInicial, "cumprimentar recebe uma resposta");
    const piscadinha = await arte(personagem);
    assert.notEqual(piscadinha, saudacao, "a resposta tambem muda a arte visivel");
    if (DESTINO) await pagina.screenshot({ path: path.join(DESTINO, `segredo-${largura}-piscadinha.png`) });
    await personagem.click();
    await segredo.getByRole("button", { name: "Fechar segredo", exact: true }).focus();
    await esperarMovimento(pagina);
    assert.notEqual(await segredo.getByRole("status").innerText(), falaCumplice);
    assert.notEqual(await arte(personagem), piscadinha, "o toque tambem muda a expressao visivel");
    assert.deepEqual(await indicadores.allTextContents(), antes, "reagir nao altera indicadores");

    // Replay na mesma fase remonta a coreografia; reduce no meio nao a prende.
    await segredo.getByRole("button", { name: "Rever entrada", exact: true }).click();
    if (!reduce) assert.equal(await personagem.isEnabled(), false, "a entrada reserva a interacao ate a chegada");
    await segredo.getByRole("button", { name: "Rever entrada", exact: true }).click();
    if (largura === 1440) {
      await pagina.emulateMedia({ reducedMotion: "reduce" });
      await esperarPersonagem(pagina);
      assert.equal(await segredo.evaluate((elemento) => elemento.getAnimations({ subtree: true }).length), 0, "mudar para reduce conclui a entrada sem movimento");
      await pagina.emulateMedia({ reducedMotion: "no-preference" });
    }
    await esperarPersonagem(pagina);
    await segredo.getByRole("button", { name: "Fechar segredo", exact: true }).focus();
    await pagina.keyboard.press("Shift+Tab");
    await pagina.waitForFunction(() => document.querySelector('button[aria-label="Interagir com Fraus-chan"]')?.closest('[role="dialog"]')?.contains(document.activeElement));
    await pagina.keyboard.press("Escape");
    await segredo.waitFor({ state: "hidden" });
    await pagina.waitForFunction(() => document.activeElement?.getAttribute("aria-label") === "Fraus — revelar o segredo com cinco cliques");
    if (largura < 768) assert.equal(await pagina.getByRole("dialog", { name: "Navegação do Fraus" }).isVisible(), true, "Escape preserva a gaveta");

    await marca.click();
    assert.equal(await segredo.count(), 0, "fechar reinicia a contagem");
    for (let i = 0; i < 4; i++) await marca.click({ delay: 60 });
    await segredo.waitFor();
    await esperarPersonagem(pagina);
    assert.equal(await segredo.getByRole("status").innerText(), falaInicial, "reabrir volta a saudacao");
    if (largura === 320) await pagina.mouse.click(2, 2);
    else await segredo.getByRole("button", { name: "Voltar à dashboard", exact: true }).click();
    await segredo.waitFor({ state: "hidden" });
    await pagina.waitForFunction(() => document.activeElement?.getAttribute("aria-label") === "Fraus — revelar o segredo com cinco cliques");
    assert.deepEqual(await indicadores.allTextContents(), antes, "fechar nao altera indicadores");
    if (largura < 768) {
      const gaveta = pagina.getByRole("dialog", { name: "Navegação do Fraus" });
      assert.equal(await gaveta.isVisible(), true, "fechar o segredo preserva a navegacao movel");
      await gaveta.getByRole("link", { name: "Atendimentos", exact: true }).click();
      await pagina.waitForURL(new URL("/dashboard/atendimentos?de=2026-08-01&ate=2026-08-22", BASE).href);
      await gaveta.waitFor({ state: "hidden" });
    } else {
      assert.deepEqual(await indicadores.allTextContents(), antes, "fechar nao altera indicadores");
    }
    cenarios.push({ largura, altura, tema: claro ? "claro" : "escuro", reduce, resultado: "entrada, teclado, piscadinha, toque, replay interrompido, reabertura, foco e indicadores intactos" });
    await contexto.close();
  }
  assert.deepEqual(erros, []);
} finally {
  await navegador.close();
}
console.log(JSON.stringify({ ok: true, cenarios }, null, 2));
