"use client";

import { lazy, Suspense, useSyncExternalStore } from "react";
import { usePathname } from "next/navigation";
import { assinarTema, lerTema, temaDoServidor, type Tema } from "@/lib/tema";
import { permiteParticulas } from "@/lib/capacidade-visual";

const Particles = lazy(() => import("@/components/Particles"));

/**
 * O CAMPO DE PARTICULAS DO HERO — o unico WebGL do produto, e so aqui.
 *
 * POR QUE ELE PODE EXISTIR NA LP E NAO NA DASHBOARD, que e a pergunta que este
 * arquivo tem que responder antes de qualquer outra: sao dois contratos
 * diferentes. A secao 6 do DESIGN.md gasta os dois momentos de movimento que a
 * FERRAMENTA se permite, e o argumento por tras da regra e o tempo de
 * exposicao -- o analista fica horas na tabela, e uma GPU girando atras do dado
 * que ele le e ruido permanente. A vitrine e visita de 40 segundos com a
 * atencao inteira na tela, e ali o espetaculo E o produto. O tema "espaco
 * profundo" acende o mesmo ceu na dashboard com tres `radial-gradient`
 * estaticos (ver `components/shell/Atelier.tsx`), justamente para nao levar
 * `requestAnimationFrame` para dentro da ferramenta.
 *
 * QUEM MOVIMENTO NAO SERVE FICA SEM ELE. `prefers-reduced-motion: reduce`
 * devolve `null`, e nao uma versao mais lenta: o pedido do sistema e "menos
 * movimento", e um campo de particulas lento continua sendo um campo de
 * particulas. O hero nao perde nada legivel -- o ateliê do tema continua
 * pintado atras, e ele ja e uma cena completa.
 *
 * A PALETA VEM DO TEMA, e o `Record<Tema, ...>` e o gate: tema novo em
 * `lib/tema.ts` sem paleta aqui nao compila. As cores sao HEX e nao OKLCH
 * porque e o que o shader do componente de terceiro consome (`hexToRgb`), e
 * escrever OKLCH aqui exigiria carregar a conversao de espaco de cor para o
 * bundle do cliente por causa de tres constantes. Elas ficam invisiveis para
 * `scripts/contraste.mjs`, que so le `oklch()` literal -- e tudo bem, e a
 * distincao e a mesma que o resto do sistema ja faz: isto e camada de LUZ, nao
 * carrega texto nem dado, entao nao ha par de contraste a verificar.
 */
const PALETA: Record<Tema, string[]> = {
  // Magnitude e temperatura de estrela de verdade: brancas-azuladas dominam,
  // e a dourada e a mesma estrela que ilumina o ateliê do tema.
  instrumento: ["#eaf2ff", "#a9c6ff", "#f2d9a8"],
  // O par canonico do vaporwave, o mesmo da quina do vidro deste tema.
  chuva: ["#7fe6ff", "#ff8ad4", "#e6d9ff"],
};

/** A consulta de midia, assinada -- ela muda em tempo de execucao quando a
 *  pessoa mexe na preferencia do sistema, e um `matchMedia` lido uma vez nao
 *  ficaria sabendo. */
const CONSULTA_MOVIMENTO = "(prefers-reduced-motion: reduce)";

function assinarMovimento(aoMudar: () => void): () => void {
  const mq = window.matchMedia(CONSULTA_MOVIMENTO);
  mq.addEventListener("change", aoMudar);
  return () => mq.removeEventListener("change", aoMudar);
}

function lerMovimento(): boolean {
  return window.matchMedia(CONSULTA_MOVIMENTO).matches;
}

/**
 * O SNAPSHOT DO SERVIDOR E `true` -- "reduzir movimento" --, e essa escolha
 * nao e simetrica por acaso. O servidor nao tem `matchMedia` e precisa chutar;
 * chutar `false` faria o HTML vir com o campo e o cliente arranca-lo na
 * hidratacao de quem pediu menos movimento, que e exatamente a pessoa para
 * quem um elemento aparecendo e sumindo e pior que nao ter elemento nenhum.
 * Chutando `true`, o pior caso vira o campo ENTRAR um quadro depois para todo
 * mundo -- e ele ja entra com o reveal do hero de qualquer jeito.
 */
function movimentoDoServidor(): boolean {
  return true;
}

/**
 * `useSyncExternalStore` nos dois estados, pelo mesmo motivo do `SeletorTema`:
 * tema e preferencia de movimento moram FORA do React (localStorage e
 * matchMedia), e ler estado externo num efeito para devolve-lo com `setState`
 * e o padrao que `react-hooks/set-state-in-effect` existe para barrar. Este
 * hook resolve os dois lados de uma vez, incluindo o snapshot do servidor --
 * e sem ele o HTML do servidor e o do cliente divergiriam, que e um erro de
 * hidratacao de verdade e nao um detalhe.
 *
 * O componente de particulas remonta sozinho quando a paleta muda, porque
 * `particleColors` entra na lista de dependencias do efeito dele.
 */
export function CampoDeParticulas() {
  const tema = useSyncExternalStore(assinarTema, lerTema, temaDoServidor);
  const pathname = usePathname();
  const menosMovimento = useSyncExternalStore(
    assinarMovimento,
    lerMovimento,
    movimentoDoServidor,
  );

  const navegador = typeof navigator === "undefined" ? undefined : navigator as Navigator & {
    connection?: { saveData?: boolean };
    deviceMemory?: number;
  };
  const permitir = typeof window !== "undefined" && permiteParticulas({
    largura: window.innerWidth,
    movimentoReduzido: menosMovimento,
    economizarDados: navegador?.connection?.saveData === true,
    memoriaGb: navegador?.deviceMemory,
    nucleos: navegador?.hardwareConcurrency,
  });

  if (!permitir) return null;

  return (
    <div
      aria-hidden
      className="pointer-events-none absolute inset-0 -z-10"
      style={{
        // O campo se apaga para as bordas e para baixo: sem a mascara ele
        // encosta no texto do hero e disputa leitura com ele, e a secao
        // seguinte comeca com particula cortada numa linha reta.
        maskImage:
          "radial-gradient(115% 85% at 50% 35%, black 30%, transparent 88%)",
        WebkitMaskImage:
          "radial-gradient(115% 85% at 50% 35%, black 30%, transparent 88%)",
      }}
    >
      <Suspense fallback={null}><Particles
        particleColors={PALETA[pathname === "/" ? "instrumento" : tema]}
        // Contido de proposito. O componente aceita muito mais, e muito mais
        // vira nevoeiro: o hero tem TEXTO por cima, e densidade alta apaga a
        // frase que a secao inteira existe para entregar.
        // 170 -> 260 -> 520. O ceu comporta densidade: as particulas sao
        // pontos com queda alfa, nao discos, entao dobrar a contagem adensa
        // sem fechar o fundo. O teto pratico nao e estetico e sim de custo --
        // sao 520 vertices num unico draw call de `gl.POINTS`, o que e barato
        // ate em GPU integrada.
        particleCount={520}
        // ESPALHAMENTO E DISTANCIA SAO O CONSERTO DO "BLOB", e o defeito vale
        // registrado porque ele nao aparece lendo as props: o vertex shader do
        // componente calcula `gl_PointSize = uBaseSize * (1 + sizeRandomness *
        // r) / length(mvPos)` -- ou seja, tamanho INVERSAMENTE proporcional a
        // distancia da camera -- e ainda multiplica o z por 10. Com espalhamento
        // 13 e camera a 20, uma parte das particulas nascia quase colada na
        // lente e virava um disco cinza borrado de 40px atravessando o topo da
        // tela. Lia como sujeira no vidro, nao como estrela.
        // Espalhar menos e afastar a camera fecha a faixa de distancias, e
        // `sizeRandomness` baixo tira a cauda de tamanhos grandes que sobrava.
        particleSpread={9}
        cameraDistance={26}
        speed={0.06}
        particleBaseSize={110}
        // BAIXO DE PROPOSITO, e o numero foi achado na tela. Com o corpo base
        // em 110 (o dobro do anterior), variedade alta reintroduz o "blob":
        // 0.55 devolveu tres ou quatro discos cinzas grandes atravessando o
        // hero, o mesmo defeito que espalhamento e distancia de camera ja
        // tinham consertado uma vez. 0.32 mantem magnitudes visivelmente
        // diferentes -- que e o que separa ceu de grade de pontos iguais --
        // sem a cauda que produz smudge.
        sizeRandomness={0.32}
        alphaParticles
        moveParticlesOnHover
        particleHoverFactor={0.6}
        disableRotation={false}
        // O padrao do componente e 1, e em tela HiDPI isso entrega ponto
        // serrilhado. Teto em 2 porque acima disso o custo por quadro sobe
        // sem diferenca visivel num ponto de 1px.
        pixelRatio={
          typeof window !== "undefined"
            ? Math.min(window.devicePixelRatio || 1, 2)
            : 1
        }
      /></Suspense>
    </div>
  );
}
