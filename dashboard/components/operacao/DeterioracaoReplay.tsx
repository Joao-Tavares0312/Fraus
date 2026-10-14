import type { Deterioracao } from "@/lib/operacao";
import { formatarSegundos } from "@/lib/formato";

export function DeterioracaoReplay({ deterioracao }: { deterioracao: Deterioracao | undefined }) {
  if (!deterioracao) return null;
  const { indice_virada: k, falas_ate_o_fim: falas, segundos_ate_o_fim: seg } = deterioracao;
  let frase: string;
  if (k === null) frase = `Sem início de deterioração: ${deterioracao.motivo ?? "não identificado"}.`;
  else if (falas === null || seg === null) frase = `Início da deterioração no índice ${k}: a estimativa ficou detratora e não voltou; tempo até o fim indisponível.`;
  else if (falas === 0) frase = `Início da deterioração no índice ${k}: a estimativa ficou detratora e não voltou, só no fim da conversa.`;
  else frase = `Início da deterioração no índice ${k}: a estimativa ficou detratora e não voltou — ${falas} ${falas === 1 ? "mensagem" : "mensagens"} e ${formatarSegundos(seg)} antes do fim.`;
  return <div className="flex flex-col gap-1"><p className="text-sm">{frase}</p><p className="text-xs text-muted-foreground">{deterioracao.rotulo}. Critério: {deterioracao.criterio}.</p></div>;
}
