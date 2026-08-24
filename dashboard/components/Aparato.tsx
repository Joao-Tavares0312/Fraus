"use client";

import { AnimatePresence, motion } from "motion/react";
import { useState, type MouseEvent, type ReactNode } from "react";
import { cn } from "@/lib/utils";
import { TRANSICAO, aberturaDeAparato } from "@/lib/movimento";

/**
 * O APARATO: a nota de editor, recolhida.
 *
 * Metodo e ressalva vivem NO PE do sistema e na tipografia menor, nunca acima
 * do dado -- e a regra da secao 2 do DESIGN.md, e a razao de existir deste
 * componente. Recolher e permitido; remover nao.
 *
 * POR QUE EXTRAIR: este bloco estava escrito duas vezes, no `Painel` e na
 * `FaixaIndicadores`, com o mesmo chevron, as mesmas classes de foco e o mesmo
 * rotulo digitado a mao. Divergiram no detalhe que mais importa -- so uma das
 * duas tinha `focus-visible:ring` no lugar certo -- que e exatamente como
 * duplicacao cobra: nao no dia em que se copia, mas no dia em que uma das
 * copias e corrigida e a outra nao.
 *
 * POR QUE `<details>` CONTROLADO, e nao um `<div>` com `useState`: o elemento
 * nativo carrega a semantica de divulgacao de graca (o leitor de tela anuncia
 * "expandido/recolhido", o teclado ja funciona, e o localizar-na-pagina do
 * navegador acha texto fechado). Trocar isso por um botao para conseguir
 * animar seria pagar em acessibilidade por estetica.
 *
 * O PORQUE DO ESTADO DUPLO: `<details>` fechado esconde os filhos na hora, e
 * animacao de saida em filho escondido nao aparece. Entao `montado` mantem o
 * atributo `open` de pe ENQUANTO a saida roda, e so cai quando o Motion avisa
 * que terminou. `aberto` e a intencao de quem clicou; `montado` e o que o DOM
 * ainda precisa mostrar.
 */
export function Aparato({
  rotulo = "Método e ressalvas",
  className,
  children,
}: {
  /** Trocar so quando "método e ressalvas" nao descrever o conteudo. */
  rotulo?: string;
  className?: string;
  children: ReactNode;
}) {
  const [aberto, setAberto] = useState(false);
  const [montado, setMontado] = useState(false);

  function alternar(evento: MouseEvent<HTMLElement>) {
    // O navegador alternaria `open` sozinho, sem esperar a animacao. Aqui o
    // React e quem manda -- vale para clique e para Enter no teclado, que o
    // navegador entrega como clique no `summary`.
    evento.preventDefault();
    if (aberto) {
      setAberto(false);
      return;
    }
    setMontado(true);
    setAberto(true);
  }

  return (
    <details open={montado} className={cn("group", className)}>
      <summary
        onClick={alternar}
        className="inline-flex cursor-pointer list-none items-center gap-1.5 rounded-sm text-xs text-muted-foreground outline-none transition-colors hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring"
      >
        <motion.span
          aria-hidden
          className="inline-block"
          animate={{ rotate: aberto ? 90 : 0 }}
          transition={TRANSICAO.gesto}
        >
          ›
        </motion.span>
        {rotulo}
      </summary>

      <AnimatePresence onExitComplete={() => setMontado(false)}>
        {aberto ? (
          <motion.div
            variants={aberturaDeAparato}
            initial="fechado"
            animate="aberto"
            exit="fechado"
            transition={TRANSICAO.amplo}
            // A altura anima de 0 a `auto`: sem isto o conteudo transborda
            // durante o percurso em vez de ser revelado por ele.
            className="overflow-hidden"
          >
            {children}
          </motion.div>
        ) : null}
      </AnimatePresence>
    </details>
  );
}
