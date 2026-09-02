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
 * do que vem (os quatro indicadores, o grafico, as duas faixas de baixo),
 * entao a tela final chega no lugar onde o olho ja estava. E o mesmo
 * compromisso do resto do produto -- nenhum numero inventado aqui, so a
 * moldura vazia do que esta a caminho.
 *
 * Ele NAO substitui os estados vazios: "ainda carregando" e "nao ha dado" sao
 * respostas diferentes, e continuam sendo desenhadas por componentes
 * diferentes. Confundir as duas faria um banco vazio parecer lentidao para
 * sempre.
 */
export default function Carregando() {
  return (
    <div className="flex flex-col gap-6 p-6" aria-busy="true" aria-live="polite">
      <span className="sr-only">Carregando a dashboard…</span>

      <div className="flex items-center gap-4">
        <Skeleton className="h-8 w-40" />
        <Skeleton className="h-8 w-64" />
      </div>

      <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
        {/* Os quatro indicadores da coluna da esquerda. */}
        <div className="flex flex-col gap-4 rounded-xl border p-4">
          {[0, 1, 2, 3].map((indice) => (
            <div key={indice} className="flex flex-col gap-2">
              <Skeleton className="h-4 w-28" />
              <Skeleton className="h-7 w-24" />
              <Skeleton className="h-3 w-full" />
            </div>
          ))}
        </div>
        {/* A serie temporal. */}
        <Skeleton className="h-[320px] w-full rounded-xl" />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Skeleton className="h-56 w-full rounded-xl" />
        <Skeleton className="h-56 w-full rounded-xl" />
      </div>
    </div>
  );
}
