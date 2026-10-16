"use client";

import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { classesDoNivel, type Nivel } from "@/lib/hierarquia";
import { RessalvaDaTela } from "./AparatoDaTela";

/** Região da tela com estado isolado e ressalvas preservadas no aparato. */
export function Painel({
  titulo,
  legenda,
  acessorio,
  rodape,
  semPadding,
  /**
   * Peso do sistema na tela. O padrao e `apoio` de proposito: painel que nao
   * declara nivel nao pode virar dominante por omissao, senao a tela passa a
   * ter dois -- e duas respostas principais e nenhuma.
   */
  nivel = "apoio",
  className,
  children,
  /**
   * A regua do sistema: dito ACIMA, medido ABAIXO (DESIGN.md §1).
   *
   * So passe isto quando o dado REALMENTE se divide nos dois lados. Onde as
   * duas series sao medidas -- o grafico de NPS x latencia e o caso -- a
   * regua nao entra: seria notacao decorativa, e a §1.1 proibe.
   */
  regua,
  /**
   * Falha isolada (DESIGN.md §5): o sistema que nao carrega mostra o proprio
   * erro NO LUGAR DELE, com o peso dele, e os vizinhos continuam de pe. Num
   * dominante isso importa mais: um aviso pequeno numa caixa grande le como
   * se nada tivesse acontecido.
   */
  erro,
  /**
   * Estado vazio nomeia O QUE FALTA e qual etapa ou endpoint resolveria.
   * Nunca preencher com numero simulado -- numa ferramenta batizada com o nome
   * do daemon do engano, dado plausivel inventado seria a pior falha possivel.
   */
  vazio,
}: {
  titulo: string;
  /** Metodo e ressalvas. Vai para o aparato, nunca acima do dado. */
  legenda?: ReactNode;
  acessorio?: ReactNode;
  rodape?: ReactNode;
  /** Para tabela e grafico, que gerenciam o proprio respiro. */
  semPadding?: boolean;
  nivel?: Nivel;
  className?: string;
  children: ReactNode;
  /** Metade dito, metade medido. So quando o dado de fato se divide assim. */
  regua?: { dito: ReactNode; medido: ReactNode };
  /** Substitui regua/children pelo proprio erro, no lugar do conteudo. */
  erro?: ReactNode;
  /** Substitui regua/children pelo estado vazio, no lugar do conteudo. */
  vazio?: ReactNode;
}) {
  return (
    <>
      <section
        className={cn(
          "quebra-evitar min-w-0 overflow-hidden",
          classesDoNivel(nivel),
          className,
        )}
      >
        {/* A regua do sistema. Mais espaco acima do titulo do que abaixo. */}
        <header className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-2">
          <h2 className="text-base font-medium text-foreground">
            {titulo}
          </h2>
          {acessorio ? <div className="shrink-0">{acessorio}</div> : null}
        </header>

        <div
          className={cn(
            "min-w-0",
            // O cancelamento acompanha o padding DO NIVEL: dominante usa
            // p-4 sm:p-6, apoio usa p-4 sm:p-5 (ver classesDoNivel). Um valor
            // fixo aqui so acerta um dos dois -- ja aconteceu com o dominante
            // ficando 4px para dentro da regua do cabecalho em >=640px.
            semPadding
              ? nivel === "dominante"
                ? "-mx-4 pt-3 sm:-mx-6"
                : "-mx-4 pt-3 sm:-mx-5"
              : "pt-4",
          )}
        >
          {erro ?? vazio ?? (regua ? (
            <div className="flex flex-col">
              <div className="pb-3">{regua.dito}</div>
              <div className="border-t border-linha" />
              <div className="pt-3">{regua.medido}</div>
            </div>
          ) : (
            children
          ))}
        </div>
      </section>
      {/* A ressalva sobe para o aparato da tela, identificada pelo titulo do
          painel -- ela e filho de verdade deste componente, entao re-renderiza
          quando `legenda`/`rodape` mudam, em vez de congelar num valor antigo
          copiado para estado. Os rotulos curtos ficam onde estao.

          `estado` avisa o aparato que este sistema nao produziu dado desta
          vez -- mesma precedencia do render acima (erro vence vazio), e
          `undefined` no caso normal, para o aparato ficar identico a hoje
          quando nenhum dos dois vier. */}
      <RessalvaDaTela
        titulo={titulo}
        estado={erro ? "erro" : vazio ? "vazio" : undefined}
      >
        {legenda}
        {rodape}
      </RessalvaDaTela>
    </>
  );
}
