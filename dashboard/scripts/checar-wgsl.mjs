/**
 * Valida cada `.wgsl` da LP nova com o `vgpu check`, sem rodar o shader.
 *
 * `--require-validation` porque, sem ele, numa maquina sem dispositivo WebGPU
 * o check vira so "parse e reflexao" e um shader invalido passa calado. Aqui
 * a falta de GPU e falha, nao aviso: e a mesma regra do modelo ausente.
 */
import { readdir } from "node:fs/promises";
import { join } from "node:path";
import { spawnSync } from "node:child_process";

const pasta = "lib/lp-nova/shaders";
const arquivos = (await readdir(pasta)).filter((nome) => nome.endsWith(".wgsl")).sort();
if (arquivos.length === 0) {
  console.error(`nenhum .wgsl em ${pasta}`);
  process.exit(1);
}
for (const nome of arquivos) {
  const caminho = join(pasta, nome);
  const r = spawnSync("npx", ["vgpu", "check", caminho, "--require-validation"], { encoding: "utf8" });
  if (r.status !== 0) {
    console.error(`FALHOU ${caminho}\n${r.stdout}\n${r.stderr}`);
    process.exit(1);
  }
  console.log(`ok ${caminho}`);
}
