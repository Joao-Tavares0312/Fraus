"use client";

import { motion } from "motion/react";
import type { ReactNode } from "react";
import { cn } from "@/lib/utils";
import { entradaDeSistema } from "@/lib/movimento";
import { useEspecular } from "@/hooks/useEspecular";
import { Aparato } from "./Aparato";

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
 * Recolher e permitido; remover nao. O aparato abre com um gesto, e os rotulos
 * curtos que qualificam o numero (`estimativa`, `observado`, `sem sinal`) NAO
 * sao aparato: ficam colados ao dado, sempre visiveis.
 */
export function Painel({
  titulo,
  legenda,
  acessorio,
  rodape,
  semPadding,
  className,
  children,
}: {
  titulo: string;
  /** Metodo e ressalvas. Vai para o aparato, nunca acima do dado. */
  legenda?: ReactNode;
  acessorio?: ReactNode;
  rodape?: ReactNode;
  /** Para tabela e grafico, que gerenciam o proprio respiro. */
  semPadding?: boolean;
  className?: string;
  children: ReactNode;
}) {
  const temAparato = Boolean(legenda || rodape);
  const refEspecular = useEspecular<HTMLElement>();

  return (
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
        "vidro especular chanfro quebra-evitar min-w-0 overflow-hidden rounded-lg p-4 sm:p-5",
        className,
      )}
    >
      {/* A regua do sistema. Mais espaco acima do titulo do que abaixo. */}
      <header className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 border-b border-linha pb-2">
        <h2 className="text-sm font-semibold tracking-tight text-foreground">
          {titulo}
        </h2>
        {acessorio ? <div className="shrink-0">{acessorio}</div> : null}
      </header>

      <div
        className={cn(
          "min-w-0",
          semPadding ? "-mx-4 pt-3 sm:-mx-5" : "pt-4",
        )}
      >
        {children}
      </div>

      {temAparato ? (
        <Aparato className="mt-3 border-t border-compasso pt-2">
          <div className="mt-2 flex max-w-[72ch] flex-col gap-2 text-xs leading-relaxed text-muted-foreground">
            {legenda}
            {rodape}
          </div>
        </Aparato>
      ) : null}
    </motion.section>
  );
}
