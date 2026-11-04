import { ehFalhaDeConexao } from "@/lib/api";

/**
 * Rota e status so aparecem para dev. A falha de conexao segue igual para todos
 * porque o `EstadoVazio` a reconhece pela frase e aponta a faixa do topo.
 */
export function mostraDetalheDoErro(erro: string, ehDev: boolean): boolean {
  return ehDev || ehFalhaDeConexao(erro);
}

export function erroParaTela(erro: string, ehDev: boolean): string {
  if (mostraDetalheDoErro(erro, ehDev)) return erro;
  return "Não conseguimos carregar agora. Tente de novo em instantes.";
}

/** Para quando outra frase vem depois do erro. */
export function erroEmFrase(erro: string, ehDev: boolean): string {
  const texto = erroParaTela(erro, ehDev);
  return texto.endsWith(".") ? texto : `${texto}.`;
}
