"use client";

import { createContext, useCallback, useContext, useMemo, useState } from "react";
import type { ReactNode } from "react";

/**
 * A MENTIRA -- e as travas que impedem que ela vire o defeito que este projeto
 * existe para nao cometer.
 *
 * Enquanto o painel do easter egg esta aberto, os quatro indicadores da visao
 * geral exibem numeros FALSOS. E uma violacao deliberada e ENCENADA da
 * invariante 2 ("nunca preencha com numero simulado"), e ela so se sustenta
 * porque encena. As quatro travas:
 *
 * 1. NADA SAI DA MEMORIA. Zero escrita no banco, zero chamada a API. E estado
 *    de render, e morre no fechamento. Nenhum agregado, export ou ordenacao
 *    chega perto disto.
 * 2. LEITOR DE TELA RECEBE A VERDADE. O numero falso e `aria-hidden`; um
 *    `sr-only` ao lado diz que o valor foi falsificado e qual e o real. Mentir
 *    para quem depende de leitor de tela nao tem piada nenhuma.
 * 3. O SELO E INESCAPAVEL. Enquanto isto esta ligado, um aviso em
 *    `--destructive` fica no mesmo quadro dos numeros -- nao existe captura de
 *    tela da dashboard mentindo sem o aviso dentro dela.
 * 4. VOLTA SOZINHA. 8s, `Esc` ou clique fora, o que vier primeiro.
 *
 * GRAFICOS E TABELA NAO MENTEM, por decisao: espalhar a mentira pelo Recharts e
 * onde ela deixa de ser contida e passa a arriscar sobrar na tela depois do
 * fechamento -- que e exatamente o defeito que as travas acima impedem.
 *
 * POR QUE CONTEXTO, e nao prop: quem LIGA a mentira e a marca, na navegacao
 * lateral; quem a EXIBE sao os indicadores, noutra sub-arvore. O estado precisa
 * viver acima dos dois, e o layout raiz e onde os dois se encontram.
 */
type EstadoDaMentira = {
  mentindo: boolean;
  mentir: (ligado: boolean) => void;
};

const ContextoDaMentira = createContext<EstadoDaMentira>({
  mentindo: false,
  // Fora do provedor a mentira simplesmente nao existe -- e o padrao certo:
  // um indicador renderizado sem provedor diz a verdade.
  mentir: () => {},
});

/** Os indicadores perguntam aqui se devem mentir. Padrao: nao. */
export function useMentira(): EstadoDaMentira {
  return useContext(ContextoDaMentira);
}

export function ProvedorDaMentira({ children }: { children: ReactNode }) {
  const [mentindo, setMentindo] = useState(false);
  const mentir = useCallback((ligado: boolean) => setMentindo(ligado), []);
  const valor = useMemo(() => ({ mentindo, mentir }), [mentindo, mentir]);

  return (
    <ContextoDaMentira.Provider value={valor}>
      {children}
    </ContextoDaMentira.Provider>
  );
}

/**
 * Um numero plausivel no lugar do verdadeiro.
 *
 * PLAUSIVEL, e nao aleatorio: o objetivo e a sensacao de "isso podia ser
 * verdade", que e a tese do produto. Ruido puro leria como bug de render, e bug
 * de render nao acusa ninguem de nada.
 *
 * DETERMINISTICO a partir do proprio valor, sem `Math.random`: o mesmo numero
 * mente sempre igual enquanto o painel esta aberto. Sortear a cada render faria
 * os quatro indicadores tremerem sozinhos -- movimento que a secao 6 do
 * DESIGN.md nao autorizou, e que denunciaria a encenacao como falha de render.
 *
 * So ALGARISMO e trocado: sinal, separador decimal e sufixo ficam, entao "−8,4"
 * continua parecendo um NPS e "61%" continua parecendo um CSAT.
 */
export function mentirSobre(formatado: string): string {
  return formatado.replace(/\d/g, (algarismo) =>
    String((Number(algarismo) * 7 + 3) % 10),
  );
}
