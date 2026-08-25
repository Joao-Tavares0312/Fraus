"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useReducedMotion } from "motion/react";
import {
  CONTADOR_ZERADO,
  type EstadoContador,
  abriu,
  registrarClique,
} from "@/lib/contadorSegredo";
import { useMentira } from "@/lib/mentira";
import { type LeituraDeCliques, lerCliques } from "@/lib/pontuarCliques";
import { RevelacaoFraus } from "./RevelacaoFraus";

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
  const { mentir } = useMentira();

  // O updater e PURO -- nada de `setState` de outro estado aqui dentro. Os
  // instantes viajam DENTRO do contador exatamente por isto: a versao anterior
  // chamava `setInstantes` daqui, o React invocava o updater mais de uma vez, e
  // cada invocacao empurrava um instante repetido. O painel mostrava oito
  // latencias para cinco cliques, metade delas `0 ms`.
  const aoClicar = useCallback(() => {
    const agora = performance.now();
    setContador((anterior) => registrarClique(anterior, agora));
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

  // TRAVA 1 e 4: a mentira e ESTADO DE RENDER, ligada e desligada por este
  // efeito e por mais nada. Ela nasce com a fenda e morre com ela -- inclusive
  // se o componente desmontar no meio (o retorno do efeito), que e o caso de
  // quem navega para outra pagina com o painel aberto. Sem essa limpeza a
  // dashboard poderia continuar mentindo sem o selo por cima, que e exatamente
  // o defeito que as travas existem para impedir.
  useEffect(() => {
    mentir(aberta);
    return () => mentir(false);
  }, [aberta, mentir]);

  // A leitura so e calculada quando ha painel para mostra-la.
  const leitura: LeituraDeCliques | null = aberta
    ? lerCliques([...contador.instantes])
    : null;

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

      {aberta && <RevelacaoFraus leitura={leitura} aoFechar={fechar} />}
    </>
  );
}
