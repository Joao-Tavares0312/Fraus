/** Regressao das sondas do shell: visibilidade, concorrencia e recuperacao.
 * Usa somente um site local ja iniciado; falhas e visibilidade sao controladas
 * no navegador. Nao grava dados nem demonstra inferencia com modelo real. */
import assert from "node:assert/strict";
import { chromium } from "playwright";

const BASE = process.env.DASHBOARD_URL ?? "http://127.0.0.1:3000";
assert.ok(["localhost", "127.0.0.1", "[::1]"].includes(new URL(BASE).hostname), "este QA so aceita um site local");
const navegador = await chromium.launch({ channel: "chrome", headless: true });
try {
  const contexto = await navegador.newContext();
  const pagina = await contexto.newPage();
  let chamadas = 0;
  await pagina.route("**/api/fraus/saude", async (rota) => {
    chamadas++;
    // Estado em aquecimento mantem a cadencia curta, independente do modelo local.
    await rota.fulfill({ json: { status: "ok", motor: "real", estado_motor: "carregando" } });
  });
  await pagina.goto(`${BASE}/dashboard/analisar`, { waitUntil: "networkidle" });
  assert.equal(new URL(pagina.url()).pathname, "/dashboard/analisar", "requer uma sessao valida ou modo local aberto");
  await pagina.waitForFunction(() => document.readyState === "complete");
  const antesDeOcultar = chamadas;
  await pagina.evaluate(() => {
    Object.defineProperty(document, "visibilityState", { configurable: true, get: () => "hidden" });
    document.dispatchEvent(new Event("visibilitychange"));
  });
  await pagina.waitForTimeout(8500);
  assert.equal(chamadas, antesDeOcultar, "aba oculta nao deve continuar sondando a API");
  await pagina.evaluate(() => {
    Object.defineProperty(document, "visibilityState", { configurable: true, get: () => "visible" });
    document.dispatchEvent(new Event("visibilitychange"));
  });
  const limite = Date.now() + 1500;
  while (chamadas === antesDeOcultar && Date.now() < limite) await pagina.waitForTimeout(50);
  assert.equal(chamadas, antesDeOcultar + 1, "retorno a aba deve atualizar a disponibilidade imediatamente");
  await contexto.close();

  const disputa = await navegador.newContext();
  const painel = await disputa.newPage();
  let numero = 0, emCurso = 0, maximo = 0;
  let liberar;
  const respostaPendente = new Promise((resolver) => { liberar = resolver; });
  let avisar;
  const sondaIniciada = new Promise((resolver) => { avisar = resolver; });
  await painel.route("**/api/fraus/saude", async (rota) => {
    const atual = ++numero;
    maximo = Math.max(maximo, ++emCurso);
    if (atual >= 2) {
      avisar();
      await respostaPendente;
    }
    await rota.fulfill({ status: 503, json: { detail: "Indisponibilidade induzida no QA." } });
    emCurso--;
  });
  try {
    await painel.goto(`${BASE}/dashboard/analisar`, { waitUntil: "networkidle" });
    const tentar = painel.getByRole("button", { name: "Tentar de novo", exact: true });
    await tentar.waitFor();
    await sondaIniciada;
    await tentar.click();
    await painel.waitForTimeout(200);
    assert.equal(maximo, 1, "tentativa manual deve compartilhar a sonda periodica em curso");
    const respondeu = painel.waitForResponse((resposta) => resposta.url().endsWith("/api/fraus/saude") && resposta.status() === 503);
    liberar();
    await (await respondeu).finished();
    await painel.unroute("**/api/fraus/saude");
    await tentar.click();
    await painel.locator("main").getByText("API fora do ar", { exact: true }).waitFor({ state: "hidden" });
    assert.ok(painel.url().endsWith("/dashboard/analisar"), "recuperacao nao deve retirar o usuario da tela");
  } finally {
    liberar();
    await disputa.close();
  }
} finally {
  await navegador.close();
}
console.log("ok atividade: pausa oculta, retorno imediato, sonda unica concorrente e recuperacao real de disponibilidade");
