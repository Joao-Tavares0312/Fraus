"use client";

import { useEffect, useRef } from "react";

/**
 * O REPOUSO: onde o brilho fica quando ninguem esta apontando. Meio da largura,
 * topo -- luz de cima, que e a unica posicao neutra plausivel. Espelha o valor
 * inicial que o `.especular` declara em globals.css.
 */
const REPOUSO_X = 50;
const REPOUSO_Y = 0;

/**
 * Quanto da distancia ate o alvo o brilho come por quadro.
 *
 * 0.14 a 60 Hz da um atraso perceptivel de ~4 quadros: o realce ARRASTA atras
 * do ponteiro em vez de colar nele, que e a diferenca entre parecer luz sobre
 * vidro e parecer um elemento posicionado. Mais alto perde o efeito; mais
 * baixo e o brilho parece preso em melado.
 *
 * NAO e compensado por tempo (delta). Numa tela de 120 Hz o brilho chega em
 * metade do tempo, e isso e aceitavel para um enfeite -- a alternativa era
 * carregar `performance.now()` e uma exponencial por quadro num laco que roda
 * em toda superficie de vidro da tela.
 */
const SUAVIDADE = 0.14;

/** Abaixo disto (em % da caixa) considera-se chegado. Ver `quadro`. */
const PARADA = 0.05;

/**
 * A CAMADA 2 do vidro liquido: o realce que segue o ponteiro.
 *
 * Escreve `--px`/`--py` no proprio no, que e o que `.especular::after` le para
 * posicionar o gradiente radial. Ver DESIGN.md, secao 7, e o bloco `.especular`
 * em globals.css -- o CSS ja define o repouso (50%/0%), entao um no sem hook
 * montado mostra um brilho discreto no alto em vez de nada.
 *
 * POR QUE ESCREVER NO ESTILO E NAO EM ESTADO REACT: o ponteiro dispara dezenas
 * de eventos por segundo, e cada um viraria render da arvore inteira do sistema
 * -- em `Painel` isso re-renderizaria grafico e tabela a cada pixel do mouse.
 * `setProperty` toca so a variavel CSS, sem passar pelo React.
 *
 * O BRILHO NAO COLA NO PONTEIRO: ele PERSEGUE, comendo uma fracao da distancia
 * por quadro (ver `SUAVIDADE`), e ao sair volta ao repouso pelo mesmo caminho
 * em vez de saltar. As duas coisas sao a mesma decisao -- luz sobre vidro tem
 * inercia, e posicao exata a cada quadro denuncia que aquilo e um elemento
 * posicionado. O laco dorme assim que chega, entao superficie parada nao custa
 * quadro nenhum.
 *
 * POR QUE NAO `transition` no CSS, que sairia de graca: transicao so interpola
 * custom property registrada com `@property`, e registrar `--px`/`--py` como
 * `<percentage>` mudaria o contrato dessas variaveis para todo mundo que as
 * le. O laco fica no lugar onde a decisao ja morava.
 *
 * OS DOIS DESLIGAMENTOS espelham exatamente as media queries do CSS:
 *
 *   - `prefers-reduced-motion` -- o realce e movimento, e a secao 6 manda
 *     desliga-lo;
 *   - `pointer: coarse` -- touch nao tem hover. Sem isto o realce ficaria aceso
 *     e PARADO no ultimo ponto tocado, que le como sujeira na tela.
 *
 * Em ambos os casos o listener nem e registrado: nao adianta esconder o efeito
 * no CSS e seguir pagando o custo do evento em JS.
 */
export function useEspecular<T extends HTMLElement>() {
  const referencia = useRef<T>(null);

  useEffect(() => {
    const no = referencia.current;
    if (!no) return;

    // `matchMedia` em vez de checar `ontouchstart`: cobre o hibrido (notebook
    // com tela de toque continua com ponteiro fino e ganha o realce).
    const semMovimento = window.matchMedia("(prefers-reduced-motion: reduce)");
    const ponteiroGrosso = window.matchMedia("(pointer: coarse)");
    if (semMovimento.matches || ponteiroGrosso.matches) return;

    let agendado = 0;
    // Onde o brilho ESTA e para onde ele VAI, em porcentagem da caixa. A
    // distancia entre os dois e o que o laco come a cada quadro.
    let atualX = REPOUSO_X;
    let atualY = REPOUSO_Y;
    let alvoX = REPOUSO_X;
    let alvoY = REPOUSO_Y;
    let clienteX = 0;
    let clienteY = 0;
    let temPonteiro = false;

    /**
     * Um quadro do laco.
     *
     * O ALVO e recalculado aqui, e nao no `pointermove`: `getBoundingClientRect`
     * e leitura de layout, e faze-la por EVENTO significa faze-la centenas de
     * vezes por segundo com um mouse rapido. Aqui ela acontece no maximo uma
     * vez por quadro.
     */
    const quadro = () => {
      agendado = 0;
      const caixa = no.getBoundingClientRect();
      // Caixa de dimensao zero (sistema recolhido, aba oculta) dividiria por
      // zero e escreveria `NaN%` na variavel -- valor invalido, que o CSS
      // descarta deixando o realce preso onde estava.
      if (caixa.width === 0 || caixa.height === 0) return;

      if (temPonteiro) {
        alvoX = ((clienteX - caixa.left) / caixa.width) * 100;
        alvoY = ((clienteY - caixa.top) / caixa.height) * 100;
      }

      atualX += (alvoX - atualX) * SUAVIDADE;
      atualY += (alvoY - atualY) * SUAVIDADE;

      const perto =
        Math.abs(alvoX - atualX) < PARADA && Math.abs(alvoY - atualY) < PARADA;
      if (perto) {
        // ENCOSTA no alvo em vez de parar assintoticamente perto dele: sem
        // isto o brilho ficaria uma frac~ao de porcento fora do lugar para
        // sempre, e o laco nunca teria licenca para dormir.
        atualX = alvoX;
        atualY = alvoY;
      }

      no.style.setProperty("--px", `${atualX.toFixed(2)}%`);
      no.style.setProperty("--py", `${atualY.toFixed(2)}%`);

      // O laco DORME assim que chega no alvo, mesmo com o ponteiro em cima:
      // quem o acorda de novo e o proximo `pointermove`. Manter o rAF vivo
      // enquanto ha hover seria, numa tela cheia de sistemas de vidro, dezenas
      // de lacos eternos reescrevendo o mesmo valor.
      if (!perto) agendado = requestAnimationFrame(quadro);
    };

    /** Religa o laco se ele estiver dormindo. */
    const acordar = () => {
      if (!agendado) agendado = requestAnimationFrame(quadro);
    };

    const mover = (evento: PointerEvent) => {
      // So guarda para onde ir. Quem escreve e o laco, uma vez por quadro --
      // um mouse de 1000 Hz nao pode forcar recalculo de estilo mais vezes do
      // que a tela sabe desenhar.
      clienteX = evento.clientX;
      clienteY = evento.clientY;
      temPonteiro = true;
      acordar();
    };

    // Ao sair, o realce VOLTA AO REPOUSO -- brilho parado no meio da
    // superficie nao e um estado plausivel de luz e o olho registra como
    // artefato. Ele volta DESLIZANDO, pelo mesmo laco: um salto de volta
    // denunciaria que o brilho e um elemento posicionado, e nao luz.
    const sair = () => {
      temPonteiro = false;
      alvoX = REPOUSO_X;
      alvoY = REPOUSO_Y;
      acordar();
    };

    no.addEventListener("pointermove", mover);
    no.addEventListener("pointerleave", sair);

    return () => {
      if (agendado) cancelAnimationFrame(agendado);
      agendado = 0;
      no.removeEventListener("pointermove", mover);
      no.removeEventListener("pointerleave", sair);
    };
  }, []);

  return referencia;
}
