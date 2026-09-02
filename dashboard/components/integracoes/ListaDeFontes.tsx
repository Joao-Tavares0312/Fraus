"use client";

import { Plus } from "lucide-react";
import type { FonteIntegracao, TipoDeFonte } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/**
 * A COLUNA MESTRE do mestre-detalhe.
 *
 * A tela era tres paineis empilhados com uma tabela larga no meio; com o
 * webhook, cada fonte passou a carregar mais quatro blocos, e uma tabela que
 * cresce em largura por fonte nao tem para onde ir. A lista fica estreita e
 * constante -- a fonte numero doze nao piora a tela --, e tudo que e de uma
 * fonte abre a direita.
 *
 * O DOURADO AQUI E LEGITIMO. A §3.3 do DESIGN.md reserva `--primary` para acao
 * e foco e proibe que ele codifique dado; o item selecionado e exatamente foco,
 * nao valor. O ponto de estado (ativa/inativa) e outra coisa e por isso NAO usa
 * dourado -- e tambem nunca vai sozinho: o rotulo textual acompanha, porque
 * cor sozinha nao comunica estado (PRODUCT.md, acessibilidade).
 *
 * SAO BOTOES, nao `div` com `onClick`: navegacao por teclado, foco visivel e
 * `aria-current` saem de graca do elemento certo, e nao ha reimplementacao de
 * Enter/Espaco para divergir depois.
 */
export function ListaDeFontes({
  fontes,
  tipos: TIPOS,
  selecionada,
  aoSelecionar,
  aoCadastrar,
}: {
  fontes: FonteIntegracao[];
  tipos: TipoDeFonte[];
  selecionada: number | null;
  aoSelecionar: (id: number) => void;
  /** Abre o formulario de cadastro, que mora no componente pai. */
  aoCadastrar: () => void;
}) {
  return (
    <div className="flex min-w-0 flex-col">
      <div className="flex items-center justify-between gap-2 border-b border-linha pb-2">
        <h3 className="text-xs font-semibold tracking-wide text-muted-foreground uppercase">
          Fontes{" "}
          <span className="num tabular-nums text-foreground">
            {fontes.length}
          </span>
        </h3>
        <Button
          type="button"
          size="xs"
          variant="outline"
          onClick={aoCadastrar}
          // `title`, e nao `aria-label`: sobrescrever o nome acessivel de um
          // botao cujo texto visivel e "Nova" quebra o Label in Name (WCAG
          // 2.5.3) e faz "clicar em Nova" falhar no comando de voz. O `sr-only`
          // COMPLEMENTA o rotulo visivel em vez de troca-lo -- o nome acessivel
          // vira "Nova fonte", que ainda comeca pelo que se le na tela.
          title="Cadastrar uma fonte"
        >
          <Plus aria-hidden />
          Nova<span className="sr-only"> fonte</span>
        </Button>
      </div>

      {/* Lista vazia NAO ganha texto proprio. O painel ao lado ja diz o mesmo,
          com mais espaco e com o endpoint; dois avisos identicos lado a lado
          sao a ressalva repetida que a regra 3.7 combate -- e a contagem `0` no
          cabecalho acima ja nomeia a ausencia sem gastar um paragrafo. */}
      {fontes.length === 0 ? null : (
        <ul className="flex min-w-0 flex-col py-1">
          {fontes.map((fonte) => {
            const ativa = fonte.id === selecionada;
            const rotuloTipo =
              TIPOS.find((tipo) => tipo.valor === fonte.tipo)?.rotulo ??
              fonte.tipo;

            return (
              <li key={fonte.id} className="min-w-0">
                <button
                  type="button"
                  // `aria-current` e o que diz ao leitor de tela QUAL item da
                  // lista esta aberto a direita. Sem ele, a barra dourada seria
                  // informacao exclusiva de quem enxerga.
                  aria-current={ativa ? "true" : undefined}
                  onClick={() => aoSelecionar(fonte.id)}
                  className={cn(
                    "flex w-full min-w-0 flex-col gap-0.5 border-l-2 py-2 pr-2 pl-2.5 text-left transition-colors",
                    "outline-none focus-visible:ring-2 focus-visible:ring-ring",
                    ativa
                      ? "border-primary bg-primary/10"
                      : "border-transparent hover:bg-muted/40",
                  )}
                >
                  <span className="flex min-w-0 items-center gap-2">
                    <span
                      aria-hidden
                      // Cheia = ativa, VAZADA = inativa. A cabeca vazada e a
                      // gramatica que a §1.1 do DESIGN.md ja usa para "ocupa a
                      // posicao e nao soa"; reaproveitar aqui evita gastar cor
                      // de categoria de NPS (teal/vermelho) num estado que nao
                      // e NPS nenhum. O rotulo textual ao lado carrega o mesmo.
                      className={cn(
                        "size-1.5 shrink-0 rounded-full border border-muted-foreground",
                        fonte.ativa && "bg-foreground border-foreground",
                      )}
                    />
                    <span className="min-w-0 truncate text-sm text-foreground">
                      {fonte.nome}
                    </span>
                  </span>
                  <span className="truncate pl-3.5 text-[0.6875rem] text-muted-foreground">
                    {fonte.canal} · {rotuloTipo} ·{" "}
                    {fonte.ativa ? "ativa" : "inativa"}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
