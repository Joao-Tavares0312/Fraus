"use client";

import dynamic from "next/dynamic";
import { useSyncExternalStore } from "react";
import WarpText from "@/components/WarpText";
import type { ReactNode } from "react";

/**
 * `ssr: false`, e ISTO NÃO É PREFERÊNCIA — o `GlassSurface` não consegue ser
 * renderizado no servidor de forma correta, por construção.
 *
 * Ele decide entre dois caminhos (`--svg` e `--fallback`) sniffando o
 * navegador e testando `div.style.backdropFilter` num elemento real, e faz
 * isso num `useEffect` com `useState(false)` de partida. Ou seja: o servidor
 * SEMPRE emite o fallback e o cliente SEMPRE troca depois de montar. O React
 * acusou a divergência com um erro de hidratação de verdade (o diff apontava
 * o `box-shadow` do fallback, cheio de `rgba(255,255,255,...)`), e o efeito
 * colateral visível era o painel piscar de um vidro branco leitoso para o
 * vidro certo a cada carregamento.
 *
 * Não dá para consertar do lado de fora sem editar o componente do registry.
 * Carregar só no cliente resolve na raiz: não há HTML de servidor para
 * divergir. O custo é o painel entrar um quadro depois — e ele já entra com o
 * reveal da seção, então na prática não se vê.
 */
const GlassSurface = dynamic(() => import("@/components/GlassSurface"), {
  ssr: false,
});

/**
 * O FECHO DA VITRINE — o painel de vidro do CTA final, com a manchete
 * atravessada pela refração.
 *
 * É a fronteira de cliente de dois componentes do registry `@react-bits` que
 * usam efeito (`GlassSurface` e `WarpText`). A página é um Server Component
 * assíncrono e não pode importá-los direto; este arquivo existe para isso e
 * para carregar as três decisões de integração abaixo.
 *
 * ---------------------------------------------------------------------------
 * 1. POR QUE O `GlassSurface` NÃO SUBSTITUI O `vidro` DA CASA.
 *
 * O projeto já tem um sistema de vidro líquido — três espessuras, cada uma com
 * um PISO medido por `scripts/pisos.mjs` e verificado por
 * `scripts/contraste.mjs`, e o DESIGN.md §7 registra o preço que já foi pago
 * para manter esses pisos honestos. O `GlassSurface` traz a própria receita
 * (`rgba(255,255,255,.25)`, brilho e saturação fixos) e é INVISÍVEL para os
 * dois portões: ele não declara token nenhum, então nenhum par de contraste
 * dele é medido.
 *
 * Por isso ele entra em UM lugar só, e justamente onde a ausência de medição
 * não cobra nada: um painel cujo único texto é DISPLAY (o `.display-vitrine`
 * passa de 60px, faixa em que o mínimo WCAG cai de 4,5:1 para 3:1) e um botão
 * com fundo próprio. Nenhum texto de leitura corrida se apoia nele. Painel,
 * tabela e cartão da ferramenta continuam no `vidro` verificado — trocar lá
 * seria trocar um sistema medido por um não medido, que é o oposto de
 * progresso.
 *
 * 2. POR QUE A COR DO `WarpText` É UM HEX E NÃO UM TOKEN.
 *
 * O componente rasteriza o texto num `<canvas>` antes de mandá-lo para o
 * shader, e `ctx.fillStyle` não resolve `var(--foreground)` — o canvas 2D não
 * tem cascata. O valor abaixo é o `--foreground` do tema espacial convertido.
 * Ele é a única cor deste arquivo que não acompanha troca de tema sozinha, e
 * fica registrado como custo assumido: é texto quase branco nos dois temas, e
 * a diferença entre eles neste token é de croma 0,006 — invisível.
 *
 * 3. POR QUE HÁ UM `<h2>` INVISÍVEL POR CIMA.
 *
 * O `WarpText` entrega `role="img"` com `aria-label`, o que é correto para
 * leitor de tela e ERRADO para a estrutura do documento: um pixel não é um
 * cabeçalho, e a página perderia o `<h2>` do fecho para o buscador e para a
 * navegação por títulos. O texto real existe em `sr-only` e o canvas fica
 * `aria-hidden` — decoração declarada como decoração.
 */
const COR_DISPLAY = "#f2f4f8";

/** Sem `matchMedia` no servidor: assume "reduzir", que é o lado seguro — ver a
 *  mesma decisão, com o argumento inteiro, em `CampoDeParticulas.tsx`. */
function assinarMovimento(aoMudar: () => void): () => void {
  const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
  mq.addEventListener("change", aoMudar);
  return () => mq.removeEventListener("change", aoMudar);
}
const lerMovimento = () =>
  window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const movimentoDoServidor = () => true;

export function FechoVitrine({
  titulo,
  children,
}: {
  /** O texto da manchete. Vai para o canvas E para o `<h2>` invisível — uma
   *  fonte só, para os dois nunca divergirem. */
  titulo: string;
  /** Os botões. */
  children: ReactNode;
}) {
  const menosMovimento = useSyncExternalStore(
    assinarMovimento,
    lerMovimento,
    movimentoDoServidor,
  );

  return (
    <GlassSurface
      width="100%"
      height="100%"
      borderRadius={28}
      // Frost e saturação baixos de propósito: o padrão do componente (0,93 de
      // opacidade no mapa) entrega um vidro leitoso que apagaria o ateliê atrás
      // — e o ateliê é a cena inteira deste tema. Aqui o vidro só precisa
      // curvar a luz, não guardá-la.
      backgroundOpacity={0.04}
      saturation={1.1}
      opacity={0.7}
      blur={14}
      displace={1.2}
      distortionScale={-140}
      redOffset={2}
      greenOffset={9}
      blueOffset={17}
      className="!h-auto w-full"
    >
      <div className="flex w-full flex-col items-center gap-8 px-6 py-16 text-center lg:py-24">
        <h2 className="sr-only">{titulo}</h2>

        {menosMovimento ? (
          // A QUEDA LIMPA: quem pediu menos movimento recebe o mesmo texto na
          // mesma escala, em tipo de verdade. Não é uma versão pobre — é a
          // manchete sem a refração, e a refração nunca carregou informação.
          <p aria-hidden className="display-vitrine max-w-4xl">
            {titulo}
          </p>
        ) : (
          <div aria-hidden className="w-full max-w-5xl">
            <WarpText
              text={titulo}
              color={COR_DISPLAY}
              // Contido. Os padrões do componente (0,08 / 1,7 / 0,55) foram
              // desenhados para uma palavra curta de vitrine; numa frase de
              // sete palavras eles borram a leitura. Aqui a distorção existe
              // para a frase parecer vista através de vidro — não para ela
              // parecer derretendo.
              warpStrength={0.045}
              warpScale={1.35}
              speed={0.4}
              pointerInfluence={0.38}
              pointerStrength={0.3}
              refraction={0.014}
              ripple
              fontSize="clamp(2.4rem, 6.5vw, 5.5rem)"
              fontWeight={500}
              letterSpacing="-0.035em"
              lineHeight={0.98}
              // A altura do canvas E a altura da caixa: o texto e desenhado
              // centrado nela, entao sobra reservada vira buraco entre a
              // manchete e o botao. `34vh` deixava ~230px de vazio, e 21vh ainda deixava ~90px.
              style={{ height: "clamp(118px, 15vh, 185px)" }}
            />
          </div>
        )}

        {children}
      </div>
    </GlassSurface>
  );
}
