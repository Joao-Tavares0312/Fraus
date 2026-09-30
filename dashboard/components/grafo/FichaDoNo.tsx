"use client";

import Link from "next/link";
import type { NoDoGrafo, TipoDeNo } from "@/lib/api";
import { EtiquetaCategoria } from "@/components/EtiquetaCategoria";
import { SegmentoLED } from "@/components/instrumento/SegmentoLED";
import { ROTULO_SEM_SINAL, formatarNumero } from "@/lib/formato";

/**
 * A FICHA: o que o grafo sabe do no selecionado.
 *
 * Ela e o unico lugar da tela onde o no vira texto legivel por qualquer
 * tecnologia -- o canvas ao lado e bitmap. Por isso ela e uma regiao viva
 * (`aria-live`): selecionar pela lista `sr-only` precisa ANUNCIAR o que
 * abriu, senao a navegacao por teclado seleciona no vazio.
 *
 * `sem_sinal` escreve "sem sinal", nunca 0. Um zero aqui afirmaria que o
 * atendimento foi pessimo quando o que houve foi nao ter sido medido.
 */
export const ROTULO_TIPO: Record<TipoDeNo, string> = {
  conversa: "Atendimento",
  categoria: "Categoria",
  canal: "Canal",
  desfecho: "Desfecho",
  termo: "Termo",
  emoji: "Emoji",
  feature: "Feature",
  fonte: "Fonte",
  importacao: "Importação",
};

const ROTULO_CAMADA = {
  lexico: "léxico",
  dominio: "domínio",
  proveniencia: "proveniência",
} as const;

/** `conversa:<id>` — o id do no carrega o tipo como prefixo (fraus/grafo.py). */
function idDaConversa(idDoNo: string): string {
  return idDoNo.slice(idDoNo.indexOf(":") + 1);
}

export function FichaDoNo({ no }: { no: NoDoGrafo | null }) {
  return (
    <div aria-live="polite" className="min-w-0">
      {no === null ? (
        <p className="text-xs leading-relaxed text-muted-foreground">
          Nenhum nó selecionado. Clique num ponto do grafo — ou percorra a lista
          por teclado — para ver o que o sistema guarda sobre ele.
        </p>
      ) : (
        <dl className="flex min-w-0 flex-col gap-3">
          <div className="min-w-0">
            <dt className="rotulo-instrumento">
              {ROTULO_TIPO[no.tipo]} · {ROTULO_CAMADA[no.camada]}
            </dt>
            <dd className="mt-0.5 text-sm font-medium break-words text-foreground">
              {no.rotulo}
            </dd>
          </div>

          <div>
            <dt className="rotulo-instrumento">
              Conexões
            </dt>
            {/* O grau e o que dita o raio do ponto la no canvas: escrever o
                numero aqui e o que fecha a leitura de "por que este e maior". */}
            <dd className="num mt-0.5 text-sm text-foreground">{no.grau}</dd>
          </div>

          {no.tipo === "conversa" ? (
            <>
              <div>
                <dt className="rotulo-instrumento">
                  Nota
                </dt>
                <dd className="mt-1 flex items-end gap-2">
                  {no.sem_sinal || no.nota === null || no.nota === undefined ? (
                    <>
                      <SegmentoLED
                        valor={null}
                        celulas={2}
                        altura={28}
                        rotulo="nota do atendimento"
                      />
                      <span className="text-sm text-muted-foreground">
                        {ROTULO_SEM_SINAL}
                      </span>
                    </>
                  ) : (
                    <SegmentoLED
                      valor={formatarNumero(no.nota)}
                      altura={28}
                      rotulo="nota estimada do atendimento"
                    />
                  )}
                </dd>
              </div>

              <div>
                <dt className="rotulo-instrumento">
                  Categoria
                </dt>
                <dd className="mt-0.5">
                  <EtiquetaCategoria categoria={no.categoria ?? null} />
                </dd>
              </div>

              <Link
                href={`/dashboard/atendimentos/${encodeURIComponent(idDaConversa(no.id))}`}
                className="rounded-sm text-xs text-primary underline-offset-4 transition-colors duration-150 ease-fluid hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              >
                Abrir o atendimento →
              </Link>
            </>
          ) : null}
        </dl>
      )}
    </div>
  );
}
