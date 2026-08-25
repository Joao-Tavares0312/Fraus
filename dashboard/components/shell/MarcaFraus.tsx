"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useReducedMotion } from "motion/react";
import {
  CONTADOR_ZERADO,
  type EstadoContador,
  abriu,
  registrarClique,
} from "@/lib/contadorSegredo";

/**
 * O QUE A FENDA REVELA.
 *
 * A fonte e Cicero, `De Natura Deorum` III.17, e nao a `Eneida` VI: Fraus NAO
 * esta na lista do vestibulo do Orco (la estao Luctus, Curae, Morbi, Senectus,
 * Metus, Fames, Egestas, Letum, Labos, Sopor, Bellum, as Eumenides e Discordia).
 * Cicero e quem a nomeia, e da a genealogia junto -- inclusive o irmao Dolus,
 * que e o nome antigo deste projeto.
 */
function Revelacao({ aoFechar }: { aoFechar: () => void }) {
  const painel = useRef<HTMLDivElement>(null);

  useEffect(() => {
    painel.current?.focus();
    const encerra = setTimeout(aoFechar, 8_000);
    function aoTeclar(evento: KeyboardEvent) {
      if (evento.key === "Escape") aoFechar();
    }
    document.addEventListener("keydown", aoTeclar);
    return () => {
      clearTimeout(encerra);
      document.removeEventListener("keydown", aoTeclar);
    };
  }, [aoFechar]);

  return (
    // O fundo e clicavel para fechar, e por isso NAO carrega papel de botao: quem
    // navega por teclado fecha com Esc, que o efeito acima escuta. Um `onClick`
    // em div de fundo sem par de teclado seria armadilha; aqui o par existe.
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm"
      onClick={aoFechar}
    >
      <div
        ref={painel}
        role="dialog"
        aria-modal="true"
        aria-label="Fraus, filha do Escuro e da Noite"
        tabIndex={-1}
        onClick={(evento) => evento.stopPropagation()}
        className="max-w-sm rounded-lg border border-border bg-card p-8 text-center outline-none"
      >
        <p className="text-3xl font-semibold tracking-[0.2em] text-primary">
          FRAVS
        </p>
        <p className="mt-4 text-sm text-muted-foreground">
          <em>Erebo et Nocte nata</em> — filha do Escuro e da Noite, irmã de{" "}
          <strong className="text-foreground">Dolus</strong> e de{" "}
          <strong className="text-foreground">Metus</strong>.
        </p>
        <p className="mt-4 text-xs text-muted-foreground">
          Cícero, <em>De Natura Deorum</em> III.17
        </p>
      </div>
    </div>
  );
}

/**
 * A MARCA, e o unico gesto que ela responde.
 *
 * POR QUE E SVG INLINE, e nao o `<Image src="/fraus-logo.svg">` que estava aqui:
 * um SVG referenciado por `<img>` e documento EXTERNO. `currentColor` nao
 * resolve, `var(--marca-cor-pe)` nao atravessa a fronteira, e nao ha como animar
 * uma parte do desenho. Inline, as tres coisas passam a existir. O arquivo
 * `public/fraus-logo.svg` continua no lugar com o dourado literal, porque o
 * `og:image` e o README consomem a marca fora do React, onde token nenhum chega.
 *
 * MOVIMENTO (DESIGN.md secao 6): parada, ela e IMOVEL -- nao anima por ter
 * montado, nao respira, nao pulsa. Tudo aqui e resposta a gesto, a mesma
 * categoria do `transition-colors` de 150ms que a navegacao inteira ja usa. Nao
 * e um terceiro momento autorado, e a secao 6 continua intacta.
 */
export function MarcaFraus({ tamanho = 28 }: { tamanho?: number }) {
  const [contador, setContador] = useState<EstadoContador>(CONTADOR_ZERADO);
  const semMovimento = useReducedMotion();
  const gatilho = useRef<SVGSVGElement>(null);

  const aoClicar = useCallback(() => {
    setContador((anterior) => registrarClique(anterior, performance.now()));
  }, []);

  // Fechar DEVOLVE o foco e zera o contador -- senao o proximo clique reabriria
  // de imediato, e o segredo deixaria de ser segredo.
  //
  // O foco volta para o <Link> QUE ENVOLVE a marca, nao para o <svg>: svg sem
  // `tabIndex` nao e focavel, e `focus()` nele seria uma chamada silenciosamente
  // sem efeito -- o teclado ficaria no <body> depois de fechar. Quem o teclado
  // alcanca nesta sidebar sempre foi o link.
  const fechar = useCallback(() => {
    setContador(CONTADOR_ZERADO);
    gatilho.current?.closest("a")?.focus();
  }, []);

  const aberta = abriu(contador);

  // Os quatro primeiros cliques tremem, e cada um treme mais: 0px, 1, 2, 3. E o
  // unico aviso de que ALGO esta sendo contado -- sem ele o segredo nao seria
  // descoberto por ninguem, so lido no codigo-fonte.
  const tremor = semMovimento ? 0 : Math.min(contador.cliques, 4) - 1;

  // As duas metades se afastam PELA FENDA, cada uma para o seu lado da diagonal.
  // Com `prefers-reduced-motion` nenhuma se move e a revelacao aparece em corte
  // seco -- os cinco cliques continuam contando. O segredo nao e privilegio de
  // quem tolera movimento.
  const afastar = aberta && !semMovimento;
  const transicaoDaMetade = semMovimento
    ? "none"
    : "transform 200ms var(--ease-fluid)";

  return (
    <>
      <svg
        ref={gatilho}
        viewBox="0 0 640 640"
        width={tamanho}
        height={tamanho}
        role="img"
        aria-label="Fraus"
        onClick={aoClicar}
        className="group/marca size-7 shrink-0 rounded-md"
        style={{
          // O tremor e transform, nao margin: nao reflui layout, e a sidebar
          // inteira nao se mexe junto.
          transform:
            tremor > 0
              ? `translateX(${tremor}px) rotate(${tremor}deg)`
              : undefined,
          transition: semMovimento
            ? "none"
            : "transform 150ms var(--ease-fluid)",
        }}
      >
        <defs>
          {/* A rampa vem dos tokens do globals.css -- dourada no grafite,
              magenta na chuva. Achatar em `currentColor` mataria o gradiente,
              que E a marca. */}
          <linearGradient id="rampa-marca" x1="0" y1="1" x2="0" y2="0">
            <stop offset="0" stopColor="var(--marca-cor-pe)" />
            <stop offset="1" stopColor="var(--marca-cor-topo)" />
          </linearGradient>
        </defs>

        <rect width="640" height="640" fill="black" />

        {/* O F -- a metade de baixo da fenda, entao ela desce e vai para a
            esquerda. */}
        <g
          transform="matrix(0.981095,0,0,8.44692,4.56477,-3599.83)"
          style={{
            transform: afastar ? "translate(-14px, 14px)" : undefined,
            transition: transicaoDaMetade,
          }}
        >
          <path
            d="M101.682,444.509L393.023,444.509L348.803,450.061L176.887,450.061L176.887,460.505L293.859,460.503L251.439,466.055L176.887,466.052L176.887,483.458L124.052,483.458L124.052,449.123C124.052,447.791 119.417,446.515 111.201,445.586C106.215,445.022 101.682,444.509 101.682,444.509Z"
            fill="white"
          />
        </g>

        {/* O S -- a metade de cima, entao sobe e vai para a direita. O dourado
            vira vermelho de erro enquanto a marca esta aberta: a divindade da
            fraude mostrando a cara. */}
        <path
          d="M444.887,289.944C468.708,289.944 488.048,270.604 488.048,246.783C488.048,222.962 468.708,202.059 444.887,202.059L428.65,202.059L365.123,202.112L408.778,154.084L444.887,154.084C495.186,154.084 536.023,196.484 536.023,246.783C536.023,297.082 495.186,337.919 444.887,337.919L408.425,337.919L542.538,484.486L473.955,484.24L300.814,289.944"
          fill={aberta ? "var(--destructive)" : "url(#rampa-marca)"}
          style={{
            transform: afastar ? "translate(14px, -14px)" : undefined,
            transition: transicaoDaMetade,
          }}
        />

        {/* A FENDA. Parada, e detalhe de desenho -- 18 unidades num viewBox de
            640 dao 0,8px aos 28px da navegacao. Ela e a JUNTA por onde a marca
            se abre nos cinco cliques: sem ela a revelacao seria efeito colado
            por cima do desenho, e nao o desenho se abrindo pela propria
            costura. */}
        <path
          id="fenda"
          d="M110,470L560,180"
          fill="none"
          stroke="black"
          strokeWidth="18"
        />

        {/* A VARREDURA do hover: uma faixa acesa subindo pela fenda. `opacity`
            em vez de `display`, para a transicao ter o que interpolar. */}
        <path
          d="M110,470L560,180"
          fill="none"
          stroke="var(--marca-cor-topo)"
          strokeWidth="8"
          className="opacity-0 transition-opacity duration-[220ms] ease-fluid group-hover/marca:opacity-100 motion-reduce:transition-none"
        />
      </svg>

      {aberta && <Revelacao aoFechar={fechar} />}
    </>
  );
}
