import { Skeleton } from "@/components/ui/skeleton";

/**
 * O que a tela de UM atendimento mostra enquanto o servidor busca a conversa e a
 * atribuicao. A forma e a do resultado: a armadura de quatro leituras e a
 * transcricao em cartoes (fala do cliente com filete, resposta recuada e
 * tracejada). Sem numero inventado e sem display apagado -- "ainda nao leu" nao
 * e "sem sinal".
 */
export default function CarregandoAtendimento() {
  return (
    <div className="flex flex-col gap-4 p-4 sm:p-6" aria-busy="true" aria-live="polite">
      <span className="sr-only">Carregando o atendimento…</span>

      <Skeleton className="h-8 w-72" />

      <div className="grid grid-cols-1 gap-px border border-linha bg-linha sm:grid-cols-2 xl:grid-cols-4">
        {[0, 1, 2, 3].map((indice) => (
          <div key={indice} className="flex flex-col gap-3 bg-background px-4 py-3.5">
            <Skeleton className="h-3 w-28" />
            <Skeleton className="h-12 w-20" />
            <Skeleton className="h-3 w-full" />
          </div>
        ))}
      </div>

      <div className="flex flex-col gap-2.5 border border-linha p-3 sm:p-5">
        <Skeleton className="h-20 w-full border-l-2 border-l-dito" />
        <Skeleton className="ml-0 h-5 w-64 sm:ml-10" />
        <Skeleton className="ml-0 h-16 w-[calc(100%-2.5rem)] border border-dashed border-border sm:ml-10" />
        <Skeleton className="h-20 w-full border-l-2 border-l-dito" />
      </div>
    </div>
  );
}
