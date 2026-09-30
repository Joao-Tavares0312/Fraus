import { Skeleton } from "@/components/ui/skeleton";

/**
 * O que a lista de atendimentos mostra ENQUANTO o servidor a monta.
 *
 * Esqueleto com a FORMA do resultado -- a armadura de quatro medianas e as
 * linhas da tabela --, e nao um "carregando" girando: a tela final chega onde o
 * olho ja estava. Nenhum numero inventado e, de proposito, NENHUM display
 * apagado: apagado quer dizer "o medidor leu e nao ha sinal", e aqui ele ainda
 * nao leu (mesma regra de `app/dashboard/loading.tsx`).
 */
export default function CarregandoAtendimentos() {
  return (
    <div className="flex flex-col gap-4 p-4 sm:p-6" aria-busy="true" aria-live="polite">
      <span className="sr-only">Carregando os atendimentos…</span>

      <Skeleton className="h-8 w-56" />

      <div className="border border-linha">
        <div className="grid grid-cols-2 gap-px bg-compasso sm:grid-cols-4">
          {[0, 1, 2, 3].map((indice) => (
            <div key={indice} className="flex flex-col gap-2 bg-card px-5 py-4">
              <Skeleton className="h-3 w-28" />
              <Skeleton className="h-7 w-24" />
              <Skeleton className="h-3 w-32" />
            </div>
          ))}
        </div>

        <div className="flex flex-col divide-y divide-compasso">
          {[0, 1, 2, 3, 4, 5, 6].map((indice) => (
            <div
              key={indice}
              className="grid grid-cols-[1.4fr_.6fr_.8fr_.6fr_.8fr] items-center gap-4 px-5 py-3.5"
            >
              <div className="flex flex-col gap-1.5">
                <Skeleton className="h-4 w-40" />
                <Skeleton className="h-3 w-28" />
              </div>
              <Skeleton className="h-4 w-10" />
              <Skeleton className="h-4 w-16" />
              <Skeleton className="h-4 w-20" />
              <Skeleton className="h-5 w-16" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
