"use client";

import { useEffect, useRef } from "react";
import { animate, useInView, useReducedMotion } from "motion/react";

/**
 * O NÚMERO QUE SOBE ao entrar na tela.
 *
 * POR QUE ELE NÃO USA `useState`, e este é o ponto do arquivo: um contador
 * escrito do jeito óbvio (`setValor` a cada quadro) faz o React re-renderizar
 * ~60 vezes por segundo, por número, e são quatro na mesma faixa. O valor não é
 * estado de aplicação — é uma propriedade visual do DOM durante 900ms. Ele é
 * escrito direto no `textContent` do `<span>`, e o React nunca fica sabendo.
 * É a mesma disciplina que o `lib/movimento.ts` prega e a mesma razão pela qual
 * `SeletorTema` usa `useSyncExternalStore` em vez de efeito com setState.
 *
 * O QUE ELE CONTA, E O QUE ISSO CUSTA EM HONESTIDADE: os quatro números da
 * faixa são FATOS DO CÓDIGO (39 features, 7 famílias, 3 BERTimbau, 0 LLMs em
 * runtime), e a animação não pode sugerir que são medições ao vivo — por isso a
 * etiqueta "fatos do código · fraus.fusor.NOMES_FEATURES" fica logo abaixo,
 * como já ficava. O movimento aqui chama atenção para um número estático; ele
 * não simula telemetria.
 *
 * O ZERO NÃO ANIMA, e não é caso especial esquecido: "0 LLMs em runtime" é a
 * afirmação mais dura da faixa, e um zero que sobe de zero até zero seria uma
 * animação vazia ao lado de três que contam. Ele nasce e fica — parado, que é
 * exatamente o que a frase diz.
 *
 * `useReducedMotion` entrega o valor final direto. O número é a informação; a
 * contagem nunca foi.
 */
export function Contador({ valor }: { valor: number }) {
  const ref = useRef<HTMLSpanElement>(null);
  const naTela = useInView(ref, { once: true, margin: "-80px" });
  const menosMovimento = useReducedMotion();

  useEffect(() => {
    const alvo = ref.current;
    if (!alvo) return;

    if (menosMovimento || valor === 0) {
      alvo.textContent = String(valor);
      return;
    }

    // ZERA ANTES DE ENTRAR NA TELA, e sem isto há um salto visível: o HTML do
    // servidor traz o valor final (de propósito — ver a nota do `return`), e
    // começar a contagem em zero só quando o elemento aparece faria o número
    // pular de 38 para 0 na frente de quem acabou de olhar para ele. A faixa
    // fica a ~1.900px do topo, muito abaixo da dobra, então este zero acontece
    // longe de qualquer olho.
    if (!naTela) {
      alvo.textContent = "0";
      return;
    }

    const controles = animate(0, valor, {
      duration: 0.9,
      // `easeOut` e não a curva fluida da casa: `--ease-fluid` tem aceleração
      // na entrada, e número que começa devagar parece travado. Contador quer
      // partir rápido e assentar.
      ease: "easeOut",
      onUpdate: (v) => {
        alvo.textContent = String(Math.round(v));
      },
    });
    return () => controles.stop();
  }, [naTela, menosMovimento, valor]);

  // O valor final já vem no HTML do servidor: sem JavaScript, ou antes da
  // hidratação, o número correto está lá — a animação só o substitui.
  return <span ref={ref}>{valor}</span>;
}
