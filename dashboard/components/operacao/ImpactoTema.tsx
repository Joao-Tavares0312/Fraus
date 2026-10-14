import type { ImpactoTema as Impacto } from "@/lib/operacao";

// exceptZero decide o sinal depois do arredondamento: -0,04 escreve "0,0", nunca "−0,0".
const SINAL = new Intl.NumberFormat("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1, signDisplay: "exceptZero" });
const comSinal = (v: number) => SINAL.format(v).replace("-", "−");

export function ImpactoTema({ impacto }: { impacto: Impacto | undefined }) {
  if (!impacto) return <p className="text-xs text-muted-foreground">Impacto no NPS inferido indisponível nesta versão da API.</p>;
  const semSinal = impacto.sem_sinal_tema > 0 ? ` · ${impacto.sem_sinal_tema} sem sinal` : "";
  if (impacto.impacto_nps === null) {
    return <p className="text-xs text-muted-foreground">Impacto no NPS inferido indisponível ({impacto.motivo ?? "motivo não informado"}): {impacto.n_tema} conversas com sinal no tema e {impacto.n_resto} no resto do recorte; mínimo {impacto.minimo} em cada lado.{impacto.sem_sinal_tema > 0 ? ` ${impacto.sem_sinal_tema} sem sinal.` : ""}</p>;
  }
  const ic = impacto.ic_inferior !== null && impacto.ic_superior !== null ? ` (IC 95%: ${comSinal(impacto.ic_inferior)} a ${comSinal(impacto.ic_superior)})` : "";
  return <div className="flex flex-col gap-1">
    <p className="text-sm">Impacto no NPS inferido: {comSinal(impacto.impacto_nps)} pontos contra o resto do recorte{ic} · {impacto.n_tema} no tema, {impacto.n_resto} no resto{semSinal}</p>
    <p className="text-xs text-muted-foreground">{impacto.rotulo} · IC só amostral, não cobre o erro do modelo</p>
  </div>;
}
