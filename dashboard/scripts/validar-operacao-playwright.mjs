/** QA do produto em instancia local, com API e modelos reais; sem mocks HTTP. */
import { chromium } from "playwright";
import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";

const base = process.env.FRAUS_QA_URL ?? "http://localhost:3017";
if (!["localhost", "127.0.0.1"].includes(new URL(base).hostname)) throw new Error("A validacao usa somente a instancia local temporaria.");
const pasta = path.resolve(".next-operacao-qa/capturas");
await mkdir(pasta, { recursive: true });
const browser = await chromium.launch({ headless: true });
const erros = [];
let page;
try {
  const contexto = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
  page = await contexto.newPage();
  page.on("pageerror", (e) => erros.push(e.message));
  const login = await contexto.request.post(`${base}/api/sessao/entrar`, { data: { email: "validacao@example.test", senha: "validacao-local-123" } });
  if (!login.ok()) throw new Error(`Login da instancia de QA: ${login.status()}`);
  await page.goto(`${base}/dashboard/operacao`, { waitUntil: "networkidle" });
  const fotografar = async (nome) => {
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.evaluate(() => document.fonts.ready);
    await page.screenshot({ path: path.join(pasta, `${nome}.png`), fullPage: true });
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 1);
    if (overflow) throw new Error(`Rolagem horizontal no documento: ${nome}`);
  };
  await page.getByRole("heading", { name: "Radar de temas", exact: true }).waitFor();
  await page.getByText("Conversas examinadas", { exact: true }).waitFor();
  await fotografar("desktop-radar");
  await page.getByRole("tab", { name: "Equipe e escala", exact: true }).click();
  await page.getByRole("button", { name: "Simular escala", exact: true }).click();
  await page.getByText("Simulação calculada. Os atendimentos permanecem preservados.", { exact: true }).waitFor();
  await fotografar("desktop-escala");
  await page.getByText("Equipe de validacao · integrantes, hierarquia e convites", { exact: true }).click();
  await page.getByRole("button", { name: "Gerar link de convite", exact: true }).click();
  await page.getByLabel("Link do convite", { exact: true }).waitFor();
  const link = await page.getByLabel("Link do convite", { exact: true }).inputValue();
  await fotografar("desktop-equipe-convite");
  const convitePage = await contexto.newPage();
  await convitePage.goto(link, { waitUntil: "networkidle" });
  await convitePage.getByRole("button", { name: "Aceitar convite", exact: true }).waitFor();
  await convitePage.screenshot({ path: path.join(pasta, "desktop-convite.png"), fullPage: true });
  await convitePage.close();
  for (const [aba, titulo] of [["Jornadas", "Jornadas entre canais"], ["Investigações", "Investigações e ações"], ["Laboratório", "Laboratório de cenários"], ["Acessos", "Mapa de alcance de acesso"]]) {
    await page.getByRole("tab", { name: aba, exact: true }).click();
    await page.getByRole("heading", { name: titulo, exact: true }).waitFor();
    await fotografar(`desktop-${aba}`);
  }
  await page.getByRole("tab", { name: "Replay", exact: true }).click();
  const id = (await (await contexto.request.get(`${base}/api/fraus/conversas`)).json())[0].id;
  await page.getByLabel("Conversa do recorte", { exact: true }).selectOption(id);
  await page.getByRole("button", { name: "Próxima", exact: true }).waitFor();
  await page.getByRole("button", { name: "Próxima", exact: true }).click();
  await fotografar("desktop-replay");
  await page.getByRole("tab", { name: "Laboratório", exact: true }).click();
  await page.getByLabel("Conversa do recorte", { exact: true }).selectOption(id);
  await page.getByRole("button", { name: "Comparar cenário com original", exact: true }).click();
  await page.getByText("Cenário calculado sem alterar o banco.", { exact: true }).waitFor();
  await fotografar("desktop-cenario");
  await page.setViewportSize({ width: 390, height: 844 });
  for (const aba of ["Radar", "Equipe e escala", "Jornadas", "Investigações", "Replay", "Laboratório", "Acessos"]) {
    await page.getByRole("tab", { name: aba, exact: true }).click();
    await fotografar(`mobile-${aba}`);
  }
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto(`${base}/dashboard/analisar`, { waitUntil: "networkidle" });
  await page.getByText("Colar uma conversa", { exact: true }).click();
  const csv = "conversa_id,canal,autor,texto,enviada_em,escalou_para_humano\nui-salva,chat,cliente,cobranca duplicada preciso estorno,2026-09-18T10:00:00+00:00,true\nui-salva,chat,humano,vou verificar,2026-09-18T10:05:00+00:00,true\n";
  await page.getByLabel("Conversa para analisar", { exact: true }).fill(csv);
  await page.getByRole("button", { name: "Analisar conversa", exact: true }).click();
  await page.getByText(/1 conversa\(s\) salva\(s\) no banco local/).waitFor({ timeout: 60000 });
  await fotografar("desktop-analisar-salva");
  const indicador = await (await contexto.request.get(`${base}/api/fraus/indicadores?de=2026-09-18&ate=2026-09-18`)).json();
  if (indicador.total_conversas !== 1) throw new Error("A conversa salva na interface nao apareceu no recorte.");
  await page.goto(`${base}/dashboard?de=2026-09-18&ate=2026-09-18`, { waitUntil: "networkidle" });
  await fotografar("desktop-dashboard-atualizada");
  if (erros.length) throw new Error(erros.join("\n"));
  await writeFile(path.join(pasta, "resultado.json"), JSON.stringify({ abas: 7, desktop: true, mobile: true, simulacao: true, convite: true, replay: true, cenario: true, upload_salvo: true, filtro_dashboard: true, erros: [] }, null, 2));
  console.log(JSON.stringify({ resultado: "ok", capturas: pasta, erros: [] }));
} catch (erro) {
  if (page) {
    await page.screenshot({ path: path.join(pasta, "falha.png"), fullPage: true });
    await writeFile(path.join(pasta, "falha.txt"), (await page.locator("body").innerText()) + "\n" + String(erro) + "\n" + erros.join("\n"));
  }
  throw erro;
} finally {
  await browser.close();
}
