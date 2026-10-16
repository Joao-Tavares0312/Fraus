/** WCAG sobre as duas paletas reais; erro em cor desconhecida nunca vira aprovação. */
import { temas, contraste } from "./cores.mjs";

const textos = ["--foreground", "--muted-foreground", "--primary", "--dito-texto", "--medido-texto", "--tempo-texto", "--emocao-texto", "--lexico-texto", "--ironia-texto", "--estilo-texto", "--incongruencia-texto", "--outros-sinal-texto", "--detrator-texto", "--neutro-texto", "--promotor-texto", "--secondary-foreground", "--popover-foreground", "--card-foreground", "--sidebar-foreground", "--destructive", "--success", "--warning", "--destructive-rich-text", "--success-rich-text", "--warning-rich-text"];
const marcas = ["--dito", "--medido", "--emocao", "--lexico", "--ironia", "--estilo", "--incongruencia", "--tempo", "--detrator", "--neutro", "--promotor", "--sem-sinal", "--no-conversa", "--no-termo", "--no-emoji", "--no-feature", "--no-categoria", "--no-canal", "--no-desfecho", "--no-fonte", "--no-importacao"];
let falhou = false;
for (const tema of temas) {
  const linhas = [];
  const conferir = (texto, fundo, minimo) => {
    const razao = contraste(tema.cor(texto), tema.cor(fundo));
    const ok = razao >= minimo;
    falhou ||= !ok;
    linhas.push({ texto, sobre: fundo, razao: razao.toFixed(2), minimo, resultado: ok ? "PASS" : "FAIL" });
  };
  for (const texto of textos) {
    for (const fundo of ["--background", "--card", "--muted", "--popover", "--sidebar"]) conferir(texto, fundo, 4.5);
  }
  for (const marca of marcas) {
    for (const fundo of ["--background", "--card"]) conferir(marca, fundo, 3);
  }
  for (const [texto, fundo] of [
    ["--primary-foreground", "--primary"],
    ["--sidebar-primary-foreground", "--sidebar-primary"],
    ["--sidebar-accent-foreground", "--sidebar-accent"],
    ["--destructive-rich-text", "--destructive-rich"],
    ["--success-rich-text", "--success-rich"],
    ["--warning-rich-text", "--warning-rich"],
  ]) conferir(texto, fundo, 4.5);
  console.log(`\n=== tema: ${tema.nome} ===`);
  console.table(linhas);
}
if (falhou) {
  console.error("FALHOU: texto abaixo de 4,5:1 ou marca abaixo de 3:1.");
  process.exitCode = 1;
} else {
  console.log("Texto e marcas cruzam os mínimos nos dois temas. Matiz e composição ainda exigem inspeção visual.");
}
