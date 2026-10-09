/**
 * Valida a LP (`/`) contra um servidor ja rodando
 * (`npm run dev` ou `npm run start`; base em LP_URL, padrao http://localhost:3000).
 *
 * O QUE ELE GARANTE, e por que cada item existe:
 *  - 200, zero `pageerror` e zero erro de console: a cena roda em WebGPU de
 *    verdade (Chrome com WebGPU ligado) e qualquer validacao de shader que
 *    falhe aparece aqui;
 *  - exatamente UM canvas e o rotulo do regime escrito: estado vazio nomeia o
 *    que falta, inclusive quando o que falta e a GPU;
 *  - regime vivo por padrao e `pôster` com `prefers-reduced-motion` (congela,
 *    nao desacelera);
 *  - nenhuma rolagem horizontal em 390 e 1440 (mede `scrollX` depois de pedir
 *    rolagem a direita: `scrollWidth` sozinho ja enganou este projeto);
 *  - um unico `h1` e os CTAs do hero dentro da dobra a 1280x720;
 *  - sair para /entrar no meio do laco nao derruba nada (device destruido com
 *    quadro em voo e o caso que o `dispose` existe para cobrir);
 *  - device PERDIDO no meio do laco cai no poster, com a frase legivel de novo;
 *  - `/leitura`, onde a LP nasceu, redireciona para `/`.
 */
import { chromium } from "playwright";

const BASE = process.env.LP_URL ?? "http://localhost:3000";
const ARGS = ["--enable-unsafe-webgpu", "--enable-features=Vulkan,WebGPU", "--use-angle=vulkan", "--ignore-gpu-blocklist"];
const navegador = await chromium.launch({ channel: "chrome", headless: true, args: ARGS });
const falhas = [];

async function abrir(viewport, { movimentoReduzido = false } = {}) {
  const pagina = await navegador.newPage({ viewport, deviceScaleFactor: 1 });
  if (movimentoReduzido) await pagina.emulateMedia({ reducedMotion: "reduce" });
  const erros = [];
  pagina.on("console", (m) => {
    if (m.type() === "error") erros.push(`console: ${m.text()}`);
  });
  pagina.on("pageerror", (e) => erros.push(`pageerror: ${e.message}`));
  const resposta = await pagina.goto(`${BASE}/`, { waitUntil: "networkidle", timeout: 90_000 });
  await pagina.waitForTimeout(2500);
  return { pagina, erros, status: resposta?.status() };
}

function exigir(nome, condicao, detalhe) {
  if (!condicao) falhas.push(`${nome}: ${detalhe}`);
}

for (const [nome, viewport] of [
  ["desktop", { width: 1440, height: 900 }],
  ["celular", { width: 390, height: 844 }],
]) {
  const { pagina, erros, status } = await abrir(viewport);
  exigir(nome, status === 200, `status ${status}`);
  const m = await pagina.evaluate(() => {
    window.scrollTo(10_000, 0);
    return {
      canvas: document.querySelectorAll("canvas").length,
      regime: document.querySelector(".ln")?.dataset.regime,
      rotulo: document.querySelector(".ln-regime")?.textContent ?? "",
      h1: document.querySelectorAll("h1").length,
      scrollX: window.scrollX,
    };
  });
  exigir(nome, m.canvas === 1, `${m.canvas} canvas`);
  exigir(nome, m.regime?.startsWith("vivo"), `regime ${m.regime} (esperado vivo com WebGPU)`);
  exigir(nome, m.rotulo.length > 0, "rotulo do regime ausente");
  exigir(nome, m.h1 === 1, `${m.h1} h1`);
  exigir(nome, m.scrollX === 0, `rolagem horizontal: scrollX ${m.scrollX}`);

  // Sair no meio do laco: o dispose nao pode derrubar a navegacao.
  await pagina.evaluate(() => window.scrollTo(0, document.documentElement.scrollHeight / 2));
  await pagina.waitForTimeout(500);
  await pagina.goto(`${BASE}/entrar`, { waitUntil: "networkidle" });
  await pagina.waitForTimeout(500);
  exigir(nome, erros.length === 0, erros.join(" | "));
  await pagina.close();
}

{
  const { pagina, erros } = await abrir({ width: 1280, height: 720 });
  const dobra = await pagina.evaluate(() =>
    [...document.querySelectorAll(".ln-hero .ln-botao")].every((b) => b.getBoundingClientRect().bottom <= window.innerHeight),
  );
  exigir("dobra 1280x720", dobra, "CTA do hero abaixo da dobra");
  exigir("dobra 1280x720", erros.length === 0, erros.join(" | "));
  await pagina.close();
}

{
  const { pagina, erros } = await abrir({ width: 1440, height: 900 }, { movimentoReduzido: true });
  const regime = await pagina.evaluate(() => document.querySelector(".ln")?.dataset.regime);
  exigir("movimento reduzido", regime === "poster", `regime ${regime}`);
  exigir("movimento reduzido", erros.length === 0, erros.join(" | "));
  await pagina.close();
}

{
  // Device perdido NO MEIO do laco (reset de driver, crash do processo de GPU):
  // a cena tem de cair no poster com o motivo escrito, sem pageerror, e a frase
  // do hero tem de voltar a ser legivel.
  const pagina = await navegador.newPage({ viewport: { width: 1440, height: 900 } });
  const erros = [];
  pagina.on("pageerror", (e) => erros.push(`pageerror: ${e.message}`));
  await pagina.addInitScript(() => {
    const original = GPUAdapter.prototype.requestDevice;
    GPUAdapter.prototype.requestDevice = async function (...args) {
      const device = await original.apply(this, args);
      window.__deviceDaCena = device;
      return device;
    };
  });
  await pagina.goto(`${BASE}/`, { waitUntil: "networkidle", timeout: 90_000 });
  await pagina.waitForTimeout(2500);
  await pagina.evaluate(() => window.__deviceDaCena?.destroy());
  await pagina.waitForTimeout(1500);
  const m = await pagina.evaluate(() => ({
    regime: document.querySelector(".ln")?.dataset.regime,
    cor: getComputedStyle(document.querySelector(".ln-fala__texto")).color,
  }));
  exigir("device perdido", m.regime === "poster", `regime ${m.regime}`);
  exigir("device perdido", !/rgba\(0, 0, 0, 0\)/.test(m.cor), "frase do hero continuou transparente");
  exigir("device perdido", erros.length === 0, erros.join(" | "));
  await pagina.close();
}

{
  const pagina = await navegador.newPage();
  const resposta = await pagina.goto(`${BASE}/leitura`, { waitUntil: "domcontentloaded", timeout: 90_000 });
  exigir("redirect /leitura", new URL(pagina.url()).pathname === "/", `parou em ${pagina.url()}`);
  exigir("redirect /leitura", resposta?.status() === 200, `status ${resposta?.status()}`);
  await pagina.close();
}

await navegador.close();
if (falhas.length) {
  console.error(`FALHOU\n- ${falhas.join("\n- ")}`);
  process.exit(1);
}
console.log("ok /: desktop, celular, dobra 1280x720, movimento reduzido, device perdido e redirect de /leitura");
