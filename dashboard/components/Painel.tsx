"use client";

import { motion } from "motion/react";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { entradaDeSistema } from "@/lib/movimento";
import { useEspecular } from "@/hooks/useEspecular";
import { classesDoNivel, type Nivel } from "@/lib/hierarquia";
import { RessalvaDaTela } from "./AparatoDaTela";

/**
 * O SISTEMA: a unidade de composicao da interface.
 *
 * Como numa partitura, um sistema e uma faixa de largura total que carrega uma
 * linha e tudo que a anota. A pagina e uma PILHA DE SISTEMAS, nao uma grade de
 * cartoes -- o cartao com borda e fundo proprio deixou de ser o agrupador
 * padrao, e quem agrupa agora e espaco mais regua. Ver DESIGN.md, secao 2.
 *
 * A MUDANCA QUE IMPORTA e a posicao da prosa. Antes, a legenda metodologica
 * ficava no cabecalho, ACIMA do conteudo: somando os paineis, isso empurrava o
 * grafico que carrega a tese da tela para 560px abaixo do topo. Nenhuma
 * explicacao foi removida -- ela virou APARATO, no rodape do sistema e na
 * tipografia menor, que e onde a partitura poe nota de editor.
 *
 * Recolher e permitido; remover nao -- so o LUGAR mudou de novo: a ressalva
 * ja nao abre no proprio painel, ela SOBE para o aparato da TELA, um so por
 * pagina, no rodape (ver `AparatoDaTela.tsx`). Os rotulos curtos que
 * qualificam o numero (`estimativa`, `observado`, `sem sinal`) NAO sao
 * aparato: ficam colados ao dado, sempre visiveis.
 */
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
  const refEspecular = useEspecular<HTMLElement>();

  return (
    <>
      <motion.section
        ref={refEspecular}
        // A ENTRADA. `whileInView` com `once` em vez de `animate` puro: o sistema
        // sobe quando ENTRA em cena, e nao todos juntos no instante do primeiro
        // quadro. Numa pagina que rola, isso da o escalonamento de graca, na
        // ordem em que o olho chega -- sem precisar coordenar indice entre
        // sistemas que moram em grades diferentes.
        //
        // `margin` negativo embaixo: o gatilho dispara pouco ANTES do sistema
        // aparecer, senao ele entra ja animando e o movimento e visto pela
        // metade.
        variants={entradaDeSistema}
        initial="oculto"
        whileInView="presente"
        viewport={{ once: true, margin: "0px 0px -64px 0px" }}
        className={cn(
          "especular chanfro quebra-evitar min-w-0 overflow-hidden rounded-lg",
          classesDoNivel(nivel),
          className,
        )}
      >
        {/* A regua do sistema. Mais espaco acima do titulo do que abaixo. */}
        <header className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 border-b border-linha pb-2">
          <h2
            className={cn(
              // Titulo de painel e ROTULO de instrumento: mono, caixa alta.
              "rotulo-instrumento font-medium",
              nivel === "dominante" ? "text-xs text-foreground" : "text-[0.6875rem]",
            )}
          >
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
      </motion.section>
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
