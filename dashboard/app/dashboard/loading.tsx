import { Skeleton } from "@/components/ui/skeleton";

/** Esqueleto do fluxo real: não confunde carregamento com ausência de dados. */
export default function Carregando() {
  return (
    <div className="flex flex-col gap-4 p-6" aria-busy="true" aria-live="polite">
      <span className="sr-only">Carregando a dashboard…</span>

      <div className="flex items-center gap-4">
        <Skeleton className="h-7 w-40" />
        <Skeleton className="h-8 w-64" />
      </div>

      {/* A armadura: quatro celulas em fileira, separadas por regua. */}
      <div className="faixa-indicadores">
        {[0, 1, 2, 3].map((indice) => (
          <div
            key={indice}
            className="flex min-w-0 flex-col gap-3 p-4"
          >
            <Skeleton className="h-3 w-24" />
            <Skeleton className="h-10 w-28" />
            <Skeleton className="h-3 w-full" />
          </div>
        ))}
      </div>

      <Skeleton className="h-[380px] w-full rounded-lg" />
      <div className="grid gap-4 xl:grid-cols-2">
        <Skeleton className="h-[220px] w-full rounded-lg" />
        <Skeleton className="h-[220px] w-full rounded-lg" />
      </div>
    </div>
  );
}
