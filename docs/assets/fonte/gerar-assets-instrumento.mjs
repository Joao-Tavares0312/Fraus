/**
 * Gera os rasters e o SVG de icone do redesign Instrumento (30/09/2026).
 *
 * FONTE UNICA de: dashboard/app/icon.svg, apple-icon.png, favicon.ico,
 * dashboard/public/icon-32.png, icon-512.png, og-fraus.png e
 * docs/assets/banner-instrumento.png. Nao ha edicao manual em nenhum deles --
 * mexeu no desenho, roda este script. Proveniencia em dashboard/public/PROVENIENCIA.md.
 *
 * Uso (da raiz do repositorio):   node docs/assets/fonte/gerar-assets-instrumento.mjs
 *
 * O MONOGRAMA NAO E REDESENHADO. As tres formas (F, R e a fenda) sao os
 * caminhos literais de dashboard/public/fraus-logo.svg; so muda o recorte
 * (quadrado, para icone) e o fundo (#070707, o da marca, no icone).
 *
 * Os rasters saem do Chromium (Playwright, o mesmo do `npm run test:lp`) com
 * `omitBackground`: assim o PNG e RGBA. O Next recusa PNG RGB em favicon e
 * icone (`The PNG is not in RGBA format!`, ver docs/design.md), e o screenshot
 * padrao do Chromium sai RGB quando a pagina e opaca.
 */
import { createRequire } from "node:module";
import { mkdir, writeFile } from "node:fs/promises";
import { fileURLToPath, pathToFileURL } from "node:url";
import { dirname, join } from "node:path";
import { tmpdir } from "node:os";
import { deflateSync, inflateSync, crc32 } from "node:zlib";

const raiz = join(dirname(fileURLToPath(import.meta.url)), "..", "..", "..");
const requireDoDashboard = createRequire(join(raiz, "dashboard", "package.json"));
const { chromium } = requireDoDashboard("playwright");

const FUNDO_MARCA = "#070707"; // o preto da logo (PRODUCT.md, Brand Commitments)
const FUNDO = "#09090b"; // o `--background` do Instrumento (oklch 0.14 0.004 285)
const OURO = "#d9b45f";
const MEDIDO = "#62a8ff";

/* --- O monograma: caminhos LITERAIS de public/fraus-logo.svg --------------- */
const F_TRANSFORM = "matrix(0.981095,0,0,8.44692,4.56477,-3599.83)";
const F_PATH =
  "M101.682,444.509L393.023,444.509L348.803,450.061L176.887,450.061L176.887,460.505L293.859,460.503L251.439,466.055L176.887,466.052L176.887,483.458L124.052,483.458L124.052,449.123C124.052,447.791 119.417,446.515 111.201,445.586C106.215,445.022 101.682,444.509 101.682,444.509Z";
const R_PATH =
  "M444.887,289.944C468.708,289.944 488.048,270.604 488.048,246.783C488.048,222.962 468.708,202.059 444.887,202.059L428.65,202.059L365.123,202.112L408.778,154.084L444.887,154.084C495.186,154.084 536.023,196.484 536.023,246.783C536.023,297.082 495.186,337.919 444.887,337.919L408.425,337.919L542.538,484.486L473.955,484.24L300.814,289.944";
const FENDA = "M110,470L560,180";

/** As tres formas do monograma, sem `<svg>` em volta. `corFenda` e a do fundo. */
function formas(id, corFenda, larguraFenda = 18) {
  return `<defs><linearGradient id="${id}" x1="0" y1="0" x2="1" y2="0" gradientUnits="userSpaceOnUse" gradientTransform="matrix(2.21157e-14,-361.177,361.177,2.21157e-14,375.355,453.046)"><stop offset="0" stop-color="rgb(170,134,80)"/><stop offset="1" stop-color="rgb(226,195,148)"/></linearGradient></defs>
<g transform="${F_TRANSFORM}"><path d="${F_PATH}" fill="#fff"/></g>
<path d="${R_PATH}" fill="url(#${id})"/>
<path d="${FENDA}" fill="none" stroke="${corFenda}" stroke-width="${larguraFenda}"/>`;
}

/** O icone: quadrado, fundo da marca, monograma centrado com folga. */
function svgIcone() {
  // o desenho ocupa x 100..545, y 154..485; centro (322,319). Lado 520 deixa ~37px.
  const [x, y, l] = [62, 59, 520];
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${x} ${y} ${l} ${l}" width="${l}" height="${l}"><rect x="${x}" y="${y}" width="${l}" height="${l}" fill="${FUNDO_MARCA}"/>${formas("ouro", FUNDO_MARCA)}</svg>`;
}

/** O monograma solto (sem fundo), para as paginas de og e banner. */
function svgMonograma(id, corFenda, altura) {
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="100 150 446 338" height="${altura}">${formas(id, corFenda)}</svg>`;
}

/* --- Vocabulario visual do Instrumento (as mesmas paradas do mockup) ------- */
const FONTES =
  '<link rel="preconnect" href="https://fonts.googleapis.com"><link href="https://fonts.googleapis.com/css2?family=Martian+Mono:wght@400;500;700&family=Bricolage+Grotesque:opsz,wght@12..96,800&display=swap" rel="stylesheet">';

const CSS_BASE = `
*{box-sizing:border-box;margin:0;padding:0}
html,body{background:${FUNDO}}
body{position:relative;overflow:hidden;color:#ececee;font-family:"Martian Mono",monospace}
.tele{position:absolute;left:0;right:0;top:0;height:40px;border-bottom:1px solid rgba(255,255,255,.26);padding:0 32px;display:flex;align-items:center;justify-content:space-between;font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:#8d8d93}
.tele b{color:${OURO};font-weight:500}
.halo{position:absolute;background:radial-gradient(closest-side,rgba(193,75,214,.22),transparent)}
.orb{position:absolute;border-radius:50%}
.orb i{position:absolute;inset:0;border-radius:50%;mix-blend-mode:screen}
.orb i:nth-child(1){background:radial-gradient(circle at 30% 30%,#e8a23a,transparent 60%)}
.orb i:nth-child(2){background:radial-gradient(circle at 72% 40%,${MEDIDO},transparent 58%)}
.orb i:nth-child(3){background:radial-gradient(circle at 50% 78%,#c14bd6,transparent 58%)}
.orb:after{content:"";position:absolute;inset:0;border-radius:50%;box-shadow:inset 0 0 80px rgba(0,0,0,.7),inset 0 0 0 1px rgba(255,255,255,.22)}
.grain{position:absolute;inset:0;opacity:.14;background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='160' height='160'><filter id='n'><feTurbulence baseFrequency='.9' numOctaves='2'/></filter><rect width='160' height='160' filter='url(%23n)' opacity='.6'/></svg>")}
.chip{position:absolute;display:inline-flex;align-items:center;gap:10px;border:1px solid rgba(255,255,255,.26);padding:9px 14px;font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:#cfcfd6;background:rgba(9,9,11,.6)}
.chip i{width:8px;height:8px;background:${MEDIDO};box-shadow:0 0 10px ${MEDIDO}}
.foot{position:absolute;left:0;right:0;bottom:0;height:52px;border-top:1px solid rgba(255,255,255,.26);padding:0 32px;display:flex;align-items:center;justify-content:space-between;font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:#8d8d93;background:rgba(9,9,11,.55)}
h1{font-family:"Bricolage Grotesque";font-weight:800;letter-spacing:-.05em;line-height:.94;text-shadow:0 0 50px rgba(0,0,0,.65)}
.marca{display:flex;align-items:center;gap:16px;font-size:16px;letter-spacing:.24em}
`;

function paginaOg() {
  return `<!doctype html><html><head><meta charset="utf-8">${FONTES}<style>${CSS_BASE}
body{width:1200px;height:630px}
.orb{left:690px;top:118px;width:420px;height:420px}
h1{position:absolute;left:64px;top:226px;font-size:88px;z-index:2}
.marca{position:absolute;left:64px;top:96px}
.chip{left:64px;top:470px;z-index:2}
</style></head><body>
<div class="tele"><span>FRAUS / OBSERVATÓRIO DE CONVERSAS</span><span>NPS <b>ESTIMATIVA</b> · LLM <b>00</b></span></div>
<div class="halo" style="left:480px;top:-100px;width:760px;height:760px"></div>
<div class="orb"><i></i><i></i><i></i></div>
<div class="grain"></div>
<div class="marca">${svgMonograma("og", FUNDO, 64)}FRAUS</div>
<h1>Leia o que ficou<br>nas entrelinhas.</h1>
<div class="chip"><i></i>estimativa · sem LLM em runtime</div>
<div class="foot"><span>07 famílias de sinal · 39 features · 00 LLMs na inferência</span><span>estimativa, não NPS declarado</span></div>
</body></html>`;
}

function paginaBanner() {
  return `<!doctype html><html><head><meta charset="utf-8">${FONTES}<style>${CSS_BASE}
body{width:1280px;height:320px}
.tele{height:34px;font-size:10.5px}
.orb{left:900px;top:44px;width:400px;height:400px}
h1{position:absolute;left:190px;top:96px;font-size:60px;z-index:2}
.marca{position:absolute;left:44px;top:96px}
.sub{position:absolute;left:190px;top:246px;font-size:12px;letter-spacing:.14em;text-transform:uppercase;color:#a9a9af;z-index:2}
</style></head><body>
<div class="tele"><span>FRAUS / OBSERVATÓRIO DE CONVERSAS</span><span>NPS <b>ESTIMATIVA</b> · LLM <b>00</b></span></div>
<div class="halo" style="left:640px;top:-260px;width:760px;height:760px"></div>
<div class="orb"><i></i><i></i><i></i></div>
<div class="grain"></div>
<div class="marca">${svgMonograma("bn", FUNDO, 86)}</div>
<h1>Leia o que ficou<br>nas entrelinhas.</h1>
<div class="sub">análise de satisfação em atendimentos por chatbot · sem LLM em runtime</div>
</body></html>`;
}

function paginaIcone(lado) {
  return `<!doctype html><html><head><meta charset="utf-8"><style>*{margin:0}html,body{background:transparent}svg{display:block;width:${lado}px;height:${lado}px}</style></head><body>${svgIcone()}</body></html>`;
}

/* --- RGB -> RGBA -----------------------------------------------------------------
   O Chromium devolve PNG RGB (tipo 2) quando a pagina e opaca, mesmo com
   `omitBackground`. O Next exige RGBA nos icones, entao o pixel opaco ganha um
   canal alfa 255 aqui. So le o que o Chromium escreve: 8 bits, sem entrelacamento. */
function paraRgba(png) {
  if (png[25] === 6) return png;
  if (png[25] !== 2 || png[24] !== 8 || png[28] !== 0) throw new Error("PNG fora do formato esperado (RGB 8 bits, sem entrelacamento)");
  const w = png.readUInt32BE(16), h = png.readUInt32BE(20);
  const idat = [];
  for (let o = 8; o < png.length;) {
    const n = png.readUInt32BE(o), tipo = png.toString("latin1", o + 4, o + 8);
    if (tipo === "IDAT") idat.push(png.subarray(o + 8, o + 8 + n));
    o += 12 + n;
  }
  const cru = inflateSync(Buffer.concat(idat));
  const bruto = Buffer.alloc(h * w * 3);
  const larg = w * 3;
  for (let y = 0; y < h; y++) {
    const filtro = cru[y * (larg + 1)];
    for (let x = 0; x < larg; x++) {
      const v = cru[y * (larg + 1) + 1 + x];
      const a = x >= 3 ? bruto[y * larg + x - 3] : 0;
      const b = y > 0 ? bruto[(y - 1) * larg + x] : 0;
      const c = x >= 3 && y > 0 ? bruto[(y - 1) * larg + x - 3] : 0;
      const pr = filtro === 0 ? 0 : filtro === 1 ? a : filtro === 2 ? b : filtro === 3 ? (a + b) >> 1 : (() => { const p = a + b - c, pa = Math.abs(p - a), pb = Math.abs(p - b), pc = Math.abs(p - c); return pa <= pb && pa <= pc ? a : pb <= pc ? b : c; })();
      bruto[y * larg + x] = (v + pr) & 255;
    }
  }
  const saida = Buffer.alloc(h * (w * 4 + 1));
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const d = y * (w * 4 + 1) + 1 + x * 4, o = (y * w + x) * 3;
      saida[d] = bruto[o]; saida[d + 1] = bruto[o + 1]; saida[d + 2] = bruto[o + 2]; saida[d + 3] = 255;
    }
  }
  const pedaco = (tipo, dados) => {
    const t = Buffer.from(tipo, "latin1");
    const cab = Buffer.alloc(4); cab.writeUInt32BE(dados.length);
    const rod = Buffer.alloc(4); rod.writeUInt32BE(crc32(Buffer.concat([t, dados])) >>> 0);
    return Buffer.concat([cab, t, dados, rod]);
  };
  const ihdr = Buffer.alloc(13);
  ihdr.writeUInt32BE(w, 0); ihdr.writeUInt32BE(h, 4); ihdr[8] = 8; ihdr[9] = 6;
  return Buffer.concat([png.subarray(0, 8), pedaco("IHDR", ihdr), pedaco("IDAT", deflateSync(saida)), pedaco("IEND", Buffer.alloc(0))]);
}

/* --- ICO: cabecalho + entradas + PNGs (RGBA) --------------------------------- */
function montarIco(pngs) {
  const cab = Buffer.alloc(6);
  cab.writeUInt16LE(0, 0);
  cab.writeUInt16LE(1, 2);
  cab.writeUInt16LE(pngs.length, 4);
  let deslocamento = 6 + 16 * pngs.length;
  const entradas = pngs.map(({ lado, png }) => {
    const e = Buffer.alloc(16);
    e.writeUInt8(lado >= 256 ? 0 : lado, 0);
    e.writeUInt8(lado >= 256 ? 0 : lado, 1);
    e.writeUInt16LE(1, 4); // planos
    e.writeUInt16LE(32, 6); // bits por pixel
    e.writeUInt32LE(png.length, 8);
    e.writeUInt32LE(deslocamento, 12);
    deslocamento += png.length;
    return e;
  });
  return Buffer.concat([cab, ...entradas, ...pngs.map((p) => p.png)]);
}

/* --- Execucao ---------------------------------------------------------------- */
const tmp = join(tmpdir(), "fraus-assets-instrumento");
await mkdir(tmp, { recursive: true });

let navegador;
try {
  navegador = await chromium.launch({ channel: "chrome", headless: true });
} catch {
  navegador = await chromium.launch({ headless: true });
}

async function capturar(html, nome, largura, altura) {
  const arquivo = join(tmp, `${nome}.html`);
  await writeFile(arquivo, html);
  const pagina = await navegador.newPage({ viewport: { width: largura, height: altura }, deviceScaleFactor: 1 });
  await pagina.goto(pathToFileURL(arquivo).href, { waitUntil: "networkidle" });
  await pagina.evaluate(() => document.fonts.ready);
  const png = await pagina.screenshot({ omitBackground: true, clip: { x: 0, y: 0, width: largura, height: altura } });
  await pagina.close();
  return png;
}

const saida = (...partes) => join(raiz, ...partes);

// icone vetorial (o Next serve app/icon.svg por convencao)
await writeFile(saida("dashboard", "app", "icon.svg"), svgIcone());

// rasters do icone, cada tamanho renderizado do SVG (nao reduzido de um maior)
const icones = {};
for (const lado of [16, 32, 48, 180, 512]) icones[lado] = paraRgba(await capturar(paginaIcone(lado), `icone-${lado}`, lado, lado));
await writeFile(saida("dashboard", "public", "icon-32.png"), icones[32]);
await writeFile(saida("dashboard", "public", "icon-512.png"), icones[512]);
await writeFile(saida("dashboard", "app", "apple-icon.png"), icones[180]);
await writeFile(saida("dashboard", "app", "favicon.ico"), montarIco([16, 32, 48].map((lado) => ({ lado, png: icones[lado] }))));

// og:image e banner
await writeFile(saida("dashboard", "public", "og-fraus.png"), await capturar(paginaOg(), "og", 1200, 630));
await writeFile(saida("docs", "assets", "banner-instrumento.png"), await capturar(paginaBanner(), "banner", 1280, 320));

await navegador.close();
console.log("assets do Instrumento gerados; paginas temporarias em", tmp);
