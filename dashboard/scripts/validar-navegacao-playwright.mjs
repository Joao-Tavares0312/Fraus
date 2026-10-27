/** Exercita a sidebar do produto já iniciado, sem subir serviço ou mudar dados. */
import assert from "node:assert/strict";
import { chromium } from "playwright";

const BASE = process.env.DASHBOARD_URL ?? "http://127.0.0.1:3000";
const navegador = await chromium.launch({ channel: "chrome", headless: true });
const periodo = "de=2026-08-01&ate=2026-08-22";
const erros = [];
const cenarios = [];

async function abrir(viewport) {
  const contexto = await navegador.newContext({ viewport, deviceScaleFactor: 1 });
  const pagina = await contexto.newPage();
  pagina.on("pageerror", (erro) => erros.push(erro.message));
  pagina.on("console", (mensagem) => {
    if (mensagem.type() === "error" && /hydrat|server rendered/i.test(mensagem.text())) erros.push(mensagem.text());
  });
  await pagina.goto(`${BASE}/dashboard?${periodo}&busca=nao-carregar`, { waitUntil: "networkidle" });
  await pagina.getByRole("heading", { level: 1 }).waitFor();
  assert.equal(new URL(pagina.url()).pathname, "/dashboard", "requer uma sessão válida ou o modo local aberto");
  return { contexto, pagina };
}

async function esperarEstado(pagina, estado) {
  await pagina.locator(`[data-slot="sidebar"][data-state="${estado}"]`).waitFor({ state: "visible" });
}

async function conferirLinks(pagina, escopo) {
  const links = escopo.locator('a[data-sidebar="menu-button"][href^="/dashboard"]');
  const destinos = await links.evaluateAll((elementos) => elementos.map((link) => ({
    href: link.getAttribute("href"), nome: link.getAttribute("aria-label"),
  })));
  assert.ok([5, 8].includes(destinos.length), "cinco destinos para usuario ou oito para dev");
  for (const { href, nome } of destinos) {
    assert.ok(nome?.trim(), `nome acessível ausente: ${href}`);
    const url = new URL(href, pagina.url());
    assert.equal(url.searchParams.toString(), periodo, `período/filtros incorretos em ${href}`);
  }
  const docs = escopo.locator('a[data-sidebar="menu-button"][target="_blank"]');
  if (await docs.count()) assert.ok(await docs.getAttribute("aria-label"), "documentação recolhida sem nome");
  return destinos;
}

try {
  const { contexto, pagina } = await abrir({ width: 1440, height: 900 });
  const barra = pagina.locator('[data-slot="sidebar"][data-state]');
  await esperarEstado(pagina, "expanded");
  const destinos = await conferirLinks(pagina, barra);
  for (const { href } of destinos) {
    await barra.locator(`a[data-sidebar="menu-button"][href="${href}"]`).click();
    await pagina.waitForURL(new URL(href, BASE).href);
    await pagina.getByRole("heading", { level: 1 }).waitFor();
    const atual = barra.locator('a[aria-current="page"]');
    assert.equal(await atual.count(), 1, "uma única folha atual");
    assert.equal(await atual.getAttribute("href"), href);
  }
  cenarios.push("destinos reais acessíveis, papel recebido, de/ate, folha atual");

  await barra.getByRole("button", { name: "Recolher navegação", exact: true }).click();
  await esperarEstado(pagina, "collapsed");
  await conferirLinks(pagina, barra);
  const atual = barra.locator('a[aria-current="page"]');
  await pagina.keyboard.press("Tab");
  await atual.focus();
  await pagina.locator('[data-slot="tooltip-content"][data-open]').filter({ hasText: "seção atual" }).waitFor();
  assert.equal((await contexto.cookies()).find((cookie) => cookie.name === "sidebar_state")?.value, "false");
  await pagina.reload({ waitUntil: "networkidle" });
  await esperarEstado(pagina, "collapsed");
  cenarios.push("rail com nomes e tooltip de foco; cookie false restaurado após reload");

  // O handler real da página recebe eventos de edição em controles nativos.
  await pagina.evaluate(() => {
    const formulario = document.createElement("form");
    formulario.id = "regressao-atalho-sidebar";
    formulario.innerHTML = '<input aria-label="Campo de regressão" /><textarea aria-label="Texto de regressão"></textarea><select aria-label="Seleção de regressão"><option>Um</option></select><div contenteditable="true" aria-label="Editor de regressão"><span>Texto editável</span></div>';
    document.querySelector("main").prepend(formulario);
  });
  for (const seletor of ["input", "textarea", "select", "[contenteditable]"]) {
    const campo = pagina.locator(`#regressao-atalho-sidebar ${seletor}`);
    await campo.focus();
    for (const tecla of ["Control+b", "Meta+b"]) {
      await campo.press(tecla);
      await esperarEstado(pagina, "collapsed");
    }
  }
  await pagina.locator("#regressao-atalho-sidebar").evaluate((elemento) => elemento.remove());
  await barra.getByRole("button", { name: "Expandir navegação", exact: true }).focus();
  await pagina.keyboard.press("Control+b");
  await esperarEstado(pagina, "expanded");
  await pagina.keyboard.press("Meta+b");
  await esperarEstado(pagina, "collapsed");
  cenarios.push("Ctrl/Meta+B só alternam fora de input, textarea, select e contenteditable");

  const tema = barra.locator('button[aria-label^="Tema:"]');
  const temaInicial = await tema.getAttribute("aria-label");
  await tema.click();
  await pagina.waitForFunction((anterior) => document.querySelector('button[aria-label^="Tema:"]')?.getAttribute("aria-label") !== anterior, temaInicial);
  await pagina.reload({ waitUntil: "networkidle" });
  await esperarEstado(pagina, "collapsed");
  assert.notEqual(await tema.getAttribute("aria-label"), temaInicial);
  await tema.click();
  cenarios.push("tema alterna e persiste sem perder recolhimento");

  await barra.getByRole("button", { name: "Expandir navegação", exact: true }).click();
  const marca = barra.getByRole("button", { name: "Fraus — revelar o segredo com cinco cliques", exact: true });
  const antesDoSegredo = pagina.url();
  for (let clique = 0; clique < 5; clique++) await marca.click({ delay: 70 });
  await pagina.waitForFunction(() => document.querySelector('button[aria-label="Fraus — revelar o segredo com cinco cliques"]')?.getAttribute("aria-expanded") === "true");
  // A cena e carregada sob demanda; estado expandido nao significa dialogo pronto.
  await pagina.getByRole("dialog", { name: "Fraus-chan", exact: true }).waitFor();
  await pagina.waitForFunction(() => document.activeElement?.getAttribute("aria-label") === "Fechar segredo");
  assert.equal(pagina.url(), antesDoSegredo, "segredo da marca não navega");
  await pagina.keyboard.press("Escape");
  await pagina.waitForFunction(() => document.querySelector('button[aria-label="Fraus — revelar o segredo com cinco cliques"]')?.getAttribute("aria-expanded") === "false");
  assert.equal(await marca.evaluate((elemento) => document.activeElement === elemento), true);
  cenarios.push("cinco cliques na marca sem navegar, Escape e foco devolvido");
  await contexto.close();

  const movel = await abrir({ width: 390, height: 844 });
  const abrirMenu = () => movel.pagina.getByRole("button", { name: "Abrir navegação", exact: true });
  await abrirMenu().focus();
  await movel.pagina.keyboard.press("Enter");
  const gaveta = movel.pagina.getByRole("dialog", { name: "Navegação do Fraus" });
  await gaveta.waitFor({ state: "visible" });
  await conferirLinks(movel.pagina, gaveta);
  assert.equal(await movel.pagina.evaluate(() => document.querySelector('[role="dialog"]')?.contains(document.activeElement)), true);
  for (const tecla of ["Shift+Tab", "Tab", "Tab"]) {
    await movel.pagina.keyboard.press(tecla);
    // Base UI passa pela sentinela externa e redireciona no proximo frame.
    // Esperar o destino evita ler a sentinela como fuga para o conteudo.
    await movel.pagina.waitForFunction(() => document.querySelector('[role="dialog"]')?.contains(document.activeElement));
  }
  await movel.pagina.keyboard.press("Escape");
  await gaveta.waitFor({ state: "hidden" });
  assert.equal(await abrirMenu().evaluate((elemento) => document.activeElement === elemento), true);

  await abrirMenu().click();
  await gaveta.getByRole("button", { name: "Fechar navegação", exact: true }).click();
  await gaveta.waitFor({ state: "hidden" });
  assert.equal(await abrirMenu().evaluate((elemento) => document.activeElement === elemento), true);
  cenarios.push("mobile: hidratação, abrir por teclado, Escape/fechar e retorno de foco");

  await abrirMenu().click();
  const atendimentos = gaveta.getByRole("link", { name: "Atendimentos", exact: true });
  const [novaAba] = await Promise.all([
    movel.contexto.waitForEvent("page"),
    atendimentos.click({ modifiers: ["Control"] }),
  ]);
  await novaAba.waitForURL(new URL(`/dashboard/atendimentos?${periodo}`, BASE).href);
  await novaAba.close();
  assert.equal(await gaveta.isVisible(), true, "clique modificado não fecha o menu original");
  await atendimentos.click();
  await movel.pagina.waitForURL(new URL(`/dashboard/atendimentos?${periodo}`, BASE).href);
  await gaveta.waitFor({ state: "hidden" });
  await abrirMenu().click();
  assert.equal(await gaveta.getByRole("link", { name: "Atendimentos", exact: true }).getAttribute("aria-current"), "page");
  await movel.pagina.keyboard.press("Escape");
  assert.equal(await movel.pagina.evaluate(() => document.documentElement.scrollWidth <= innerWidth), true);
  cenarios.push("mobile: nova aba preserva gaveta; navegação comum fecha e marca destino, sem overflow");
  await movel.contexto.close();
  assert.deepEqual(erros, [], "erros de página/hidratação");
} finally {
  await navegador.close();
}
console.log(JSON.stringify({ ok: true, cenarios }, null, 2));
