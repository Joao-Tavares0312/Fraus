/** Produto iniciado: cinco cliques, jogo, indicadores intactos e modais aninhados. */
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { mkdir } from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright";

const BASE = process.env.DASHBOARD_URL ?? "http://127.0.0.1:3000";
const DESTINO = process.env.SEGREDO_EVIDENCIAS;
const navegador = await chromium.launch({ channel: "chrome", headless: true });
const erros = [];
const cenarios = [];
if (DESTINO) await mkdir(DESTINO, { recursive: true });

async function esperarMovimento(pagina) {
  await pagina.evaluate(() => Promise.all(document.getAnimations().map((animacao) => animacao.finished.catch(() => {}))));
  await pagina.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))));
}

try {
  for (const { largura, claro, reduce } of [
    { largura: 1440, claro: false, reduce: false },
    { largura: 390, claro: false, reduce: true },
    { largura: 320, claro: true, reduce: true },
  ]) {
    const contexto = await navegador.newContext({ viewport: { width: largura, height: 900 }, deviceScaleFactor: 1, reducedMotion: reduce ? "reduce" : "no-preference" });
    const pagina = await contexto.newPage();
    pagina.on("pageerror", (erro) => erros.push(erro.message));
    await pagina.goto(`${BASE}/dashboard?de=2026-08-01&ate=2026-08-22`, { waitUntil: "networkidle" });
    await pagina.getByRole("heading", { name: "Visão geral", exact: true }).waitFor();
    await pagina.evaluate(() => document.fonts.ready);
    const indicadores = pagina.locator('[data-slot="indicador"]');
    assert.equal(await indicadores.count(), 4, "requer snapshot de QA com os quatro indicadores");
    const antes = await indicadores.allTextContents();
    if (largura < 768) await pagina.getByRole("button", { name: "Abrir navegação", exact: true }).click();
    if (claro) await pagina.getByRole("button", { name: "Tema: Escuro. Trocar para Claro.", exact: true }).click();
    const marca = pagina.getByRole("button", { name: "Fraus — revelar o segredo com cinco cliques", exact: true });
    const jogo = pagina.getByRole("dialog", { name: "Encaixe secreto", exact: true });
    for (let i = 0; i < 4; i++) await marca.click({ delay: 60 });
    assert.equal(await jogo.count(), 0, "quatro cliques não abrem o segredo");
    await marca.click();
    await jogo.waitFor();
    await pagina.waitForFunction(() => document.activeElement?.getAttribute("aria-label") === "Fechar segredo");
    assert.deepEqual(await indicadores.allTextContents(), antes, "abrir o segredo não altera indicadores");
    await esperarMovimento(pagina);
    if (DESTINO) await pagina.screenshot({ path: path.join(DESTINO, `segredo-${largura}-aberto.png`) });
    const arteAntes = createHash("sha256").update(await jogo.locator("svg[role=img]").screenshot()).digest("hex");

    // Teclado nativo do range: extremo esquerdo e quatro passos até o encaixe.
    for (const nome of ["Topo", "Centro", "Base"]) {
      const peca = jogo.getByRole("slider", { name: nome, exact: true });
      await peca.focus();
      await peca.press("Home");
      for (let passo = 0; passo < 4; passo++) await peca.press("ArrowRight");
    }
    await jogo.getByRole("status").filter({ hasText: "Contexto reconstruído." }).waitFor();
    await esperarMovimento(pagina);
    const arteDepois = createHash("sha256").update(await jogo.locator("svg[role=img]").screenshot()).digest("hex");
    assert.notEqual(arteDepois, arteAntes, "resolver altera os pixels da marca, não só o placar");
    assert.deepEqual(await indicadores.allTextContents(), antes, "vencer não altera indicadores");
    assert.equal(await jogo.evaluate((elemento) => elemento.scrollWidth <= elemento.clientWidth), true, "painel sem overflow horizontal");
    assert.equal(await pagina.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
    if (reduce) assert.equal(await jogo.locator("svg image").evaluateAll((imagens) => imagens.every((imagem) => getComputedStyle(imagem).transitionProperty === "none")), true, "reduce não anima fragmentos");
    if (DESTINO) await pagina.screenshot({ path: path.join(DESTINO, `segredo-${largura}-resolvido.png`) });

    await jogo.getByRole("button", { name: "Embaralhar", exact: true }).click();
    assert.doesNotMatch(await jogo.getByRole("status").innerText(), /Contexto reconstruído/);
    assert.deepEqual(await indicadores.allTextContents(), antes, "novo desafio não altera indicadores");
    await jogo.getByRole("button", { name: "Fechar segredo", exact: true }).focus();
    await pagina.keyboard.press("Shift+Tab");
    await pagina.waitForFunction(() => [...document.querySelectorAll('[role="dialog"]')].find((dialogo) => dialogo.querySelector('input[type="range"]'))?.contains(document.activeElement));
    await pagina.keyboard.press("Escape");
    await jogo.waitFor({ state: "hidden" });
    await pagina.waitForFunction(() => document.activeElement?.getAttribute("aria-label") === "Fraus — revelar o segredo com cinco cliques");
    if (largura < 768) assert.equal(await pagina.getByRole("dialog", { name: "Navegação do Fraus" }).isVisible(), true, "Escape fecha só o segredo, não a gaveta que o abriu");
    assert.deepEqual(await indicadores.allTextContents(), antes, "fechar não altera indicadores");

    await marca.click();
    assert.equal(await jogo.count(), 0, "fechar reinicia a contagem");
    for (let i = 0; i < 4; i++) await marca.click({ delay: 60 });
    await jogo.waitFor();
    await pagina.waitForFunction(() => document.activeElement?.getAttribute("aria-label") === "Fechar segredo");
    assert.doesNotMatch(await jogo.getByRole("status").innerText(), /Contexto reconstruído/, "reabrir não conserva vitória anterior");
    if (largura === 320) await pagina.mouse.click(2, 2);
    else await jogo.getByRole("button", { name: "Voltar à dashboard", exact: true }).click();
    await jogo.waitFor({ state: "hidden" });
    await pagina.waitForFunction(() => document.activeElement?.getAttribute("aria-label") === "Fraus — revelar o segredo com cinco cliques");
    if (largura < 768) assert.equal(await pagina.getByRole("dialog", { name: "Navegação do Fraus" }).isVisible(), true, "fechar o segredo preserva a navegação móvel");
    assert.deepEqual(await indicadores.allTextContents(), antes);
    if (largura < 768) {
      const gaveta = pagina.getByRole("dialog", { name: "Navegação do Fraus" });
      await gaveta.getByRole("link", { name: "Atendimentos", exact: true }).click();
      await pagina.waitForURL(new URL("/dashboard/atendimentos?de=2026-08-01&ate=2026-08-22", BASE).href);
      await gaveta.waitFor({ state: "hidden" });
      await pagina.getByRole("button", { name: "Abrir navegação", exact: true }).click();
      assert.equal(await pagina.getByRole("dialog", { name: "Navegação do Fraus" }).getByRole("link", { name: "Atendimentos", exact: true }).getAttribute("aria-current"), "page");
      await pagina.keyboard.press("Escape");
      await pagina.waitForFunction(() => document.activeElement?.getAttribute("aria-label") === "Abrir navegação");
    }
    cenarios.push({ largura, tema: claro ? "claro" : "escuro", reduce, jogo: "resolvido por teclado; arte alterada; embaralhar/reabrir; foco contido e devolvido; indicadores intactos; navegação móvel após o segredo" });
    await contexto.close();
  }
  assert.deepEqual(erros, []);
} finally {
  await navegador.close();
}
console.log(JSON.stringify({ ok: true, cenarios }, null, 2));
