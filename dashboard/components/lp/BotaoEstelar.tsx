import Link from "next/link";
import { ArrowRight } from "lucide-react";
import StarBorder from "@/components/StarBorder";

/**
 * O CTA PRINCIPAL DA VITRINE — o `StarBorder` do registry `@react-bits` ligado
 * ao sistema de cor do Fraus.
 *
 * POR QUE ELE CABE AQUI, e não é só "efeito bonito": a borda do componente é
 * um ponto de luz varrendo a aresta, e num tema cuja tese é o vazio com poucos
 * corpos luminosos isso lê como um corpo passando. É o mesmo vocabulário da
 * quina acesa do vidro (`--vidro-quina`) — a diferença é que ali a luz está
 * parada e aqui ela anda, porque o botão é a única coisa da página que pede
 * ação.
 *
 * AS QUATRO CORES SÃO TOKENS, e passam como `var(...)` porque o componente as
 * despeja em `style` inline — onde a cascata do CSS funciona normalmente. Isso
 * é o oposto do caso do `WarpText` (ver `FechoVitrine.tsx`), que rasteriza em
 * canvas e por isso precisou de um hex literal. Aqui o botão acompanha a troca
 * de tema sozinho.
 *
 * O DOURADO CONTINUA SENDO A ÚNICA COR DE AÇÃO — invariante do DESIGN.md, e ela
 * não abre exceção para componente de terceiro. A luz que corre é `--primary`,
 * o miolo é `--primary` chapado e o texto é `--primary-foreground`, exatamente
 * como no `botaoVitrine`. O que muda é a aresta, não a semântica.
 *
 * Sem `"use client"`: o `StarBorder` é CSS puro, sem hook nenhum, então isto
 * renderiza no servidor como o resto da página.
 */
export function BotaoEstelar({
  href,
  children,
}: {
  href: string;
  children: React.ReactNode;
}) {
  return (
    <StarBorder
      as={Link}
      href={href}
      // `6s` é o padrão do componente e é rápido demais para uma página em que
      // nada mais se move nesse ritmo: a luz passava como um piscar e o botão
      // lia como notificação. Devagar, ela lê como órbita.
      speed="9s"
      thickness={1}
      color="var(--primary)"
      backgroundColor="var(--primary)"
      textColor="var(--primary-foreground)"
      borderColor="transparent"
      className="group outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
    >
      <span className="flex items-center justify-center gap-2 text-base font-medium">
        {children}
        <ArrowRight
          aria-hidden
          className="size-4 shrink-0 transition-transform duration-150 ease-fluid group-hover:translate-x-0.5"
        />
      </span>
    </StarBorder>
  );
}
