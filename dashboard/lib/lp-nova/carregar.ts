import { readFile } from "node:fs/promises";
import path from "node:path";
import { validarLeituras, type ConjuntoLeituras, type Falta } from "./leituras";

/**
 * Le o `leituras.json` no SERVIDOR, na hora do build da pagina estatica.
 *
 * Arquivo ausente nao e erro de build: e o estado antes de alguem rodar
 * `scripts/gravar_leituras_lp.py`, e a pagina o mostra como estado vazio que
 * nomeia o que falta -- nunca como leitura inventada.
 */
export async function carregarLeituras(): Promise<ConjuntoLeituras | Falta> {
  try {
    const bruto = await readFile(path.join(process.cwd(), "lib/lp-nova/leituras.json"), "utf8");
    return validarLeituras(JSON.parse(bruto));
  } catch {
    return validarLeituras(null);
  }
}
