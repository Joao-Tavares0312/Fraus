import { Skeleton } from "@/components/ui/skeleton";

/**
 * O que a tela mostra ENQUANTO o servidor monta a dashboard.
 *
 * POR QUE ELE PASSOU A EXISTIR: sem um `loading.tsx`, uma navegacao para
 * `/dashboard` nao pinta nada ate o servidor terminar -- a pagina ANTERIOR
 * fica congelada na tela. Numa instalacao local isso e imperceptivel; numa
 * publicada por tunel, o servidor da Vercel fala com a API na maquina de quem
 * hospeda, e a espera medida em producao foi de SEIS SEGUNDOS de tela imovel
 * depois de um login bem-sucedido. A pessoa conclui que quebrou, e nao esta
 * errada em concluir: a interface nao deu nenhum sinal do contrario.
 *
 * ESQUELETO, E NAO UM "carregando..." GIRANDO: o esqueleto ja mostra a FORMA
 * do que vem -- a armadura de quatro celulas em fileira, o grafico e a lista
 * de piores atendimentos --, entao a tela final chega no lugar onde o olho ja
 * estava. E o mesmo compromisso do resto do produto: nenhum numero inventado
 * aqui, so a moldura vazia do que esta a caminho. (A armadura passou de coluna
 * a fileira em 30/09/2026, no redesenho Instrumento; o esqueleto acompanha.)
 *
 * Ele NAO substitui os estados vazios: "ainda carregando" e "nao ha dado" sao
 * respostas diferentes, e continuam sendo desenhadas por componentes
 * diferentes. Confundir as duas faria um banco vazio parecer lentidao para
 * sempre. Em particular, NAO desenha celulas de LED apagadas: apagado quer
 * dizer "o medidor leu e nao ha sinal", e aqui ele ainda nao leu.
 */
export default function Carregando() {
  return (
    <div className="flex flex-col gap-4 p-6" aria-busy="true" aria-live="polite">
      <span className="sr-only">Carregando a dashboard…</span>

      <div className="flex items-center gap-4">
        <Skeleton className="h-7 w-40" />
        <Skeleton className="h-8 w-64" />
      </div>

      {/* A armadura: quatro celulas em fileira, separadas por regua. */}
      <div className="grid grid-cols-2 border border-linha lg:grid-cols-4">
        {[0, 1, 2, 3].map((indice) => (
          <div
            key={indice}
            className="flex flex-col gap-3 border-b border-r border-linha p-4 last:border-r-0 lg:border-b-0"
          >
            <Skeleton className="h-3 w-24" />
            <Skeleton className="h-10 w-28" />
            <Skeleton className="h-3 w-full" />
          </div>
        ))}
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)]">
        {/* A serie temporal. */}
        <Skeleton className="h-[320px] w-full" />
        {/* Piores atendimentos. */}
        <Skeleton className="h-[320px] w-full" />
      </div>
    </div>
  );
}
