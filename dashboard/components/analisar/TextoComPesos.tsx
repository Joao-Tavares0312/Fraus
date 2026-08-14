import type { PesoDePalavra } from "@/lib/api";

/**
 * Intensidade a partir da qual a palavra ganha fundo.
 *
 * Sem um piso, TODA palavra sai colorida -- inclusive as de peso 0,002, que na
 * pratica nao moveram nada -- e o grifo deixa de destacar. O corte e sobre o
 * valor absoluto porque as duas direcoes importam igualmente.
 */
const PISO_VISIVEL = 0.02;

/** Peso que ja satura a cor. Acima disso o fundo nao fica mais forte. */
const TETO_COR = 0.6;

/**
 * A mensagem com cada palavra grifada pelo peso que o modelo deu a ela.
 *
 * O grifo usa os indices `inicio`/`fim` que o SERVIDOR mediu, e o texto entre
 * eles sai literal do original. A tela nunca re-tokeniza: uma segunda
 * tokenizacao aqui acabaria grifando trecho diferente do que foi medido, e o
 * usuario veria a cor em cima da palavra errada.
 *
 * Verde empurrou a leitura para satisfeito, vermelho para insatisfeito -- as
 * mesmas cores que promotor e detrator ja usam no resto da dashboard.
 *
 * Palavra sem medida (acima do teto do servidor) fica SEM grifo e com um
 * pontilhado embaixo. Ela nao pode parecer peso zero: "nao mediram esta" e
 * "mediram e deu zero" sao respostas diferentes.
 */
export function TextoComPesos({
  texto,
  palavras,
}: {
  texto: string;
  palavras: PesoDePalavra[] | null;
}) {
  if (!palavras || palavras.length === 0) {
    return <span>{texto}</span>;
  }

  const ordenadas = [...palavras].sort((a, b) => a.inicio - b.inicio);
  const pedacos: React.ReactNode[] = [];
  let cursor = 0;

  ordenadas.forEach((item, indice) => {
    // O que vem ANTES da palavra (espaco, pontuacao) sai literal.
    if (item.inicio > cursor) {
      pedacos.push(texto.slice(cursor, item.inicio));
    }

    const trecho = texto.slice(item.inicio, item.fim);

    if (item.peso === null) {
      pedacos.push(
        <span
          key={indice}
          className="underline decoration-dotted decoration-muted-foreground underline-offset-4"
          title="Acima do limite de palavras medidas nesta mensagem — sem medição, o que é diferente de peso zero."
        >
          {trecho}
        </span>,
      );
    } else if (Math.abs(item.peso) < PISO_VISIVEL) {
      pedacos.push(
        <span key={indice} title={`peso ${item.peso.toFixed(3)}`}>
          {trecho}
        </span>,
      );
    } else {
      const intensidade = Math.min(1, Math.abs(item.peso) / TETO_COR);
      const positivo = item.peso > 0;
      pedacos.push(
        <span
          key={indice}
          className={`rounded-[3px] px-0.5 ${positivo ? "text-success-rich-text" : "text-destructive-rich-text"}`}
          style={{
            backgroundColor: positivo
              ? `color-mix(in oklch, var(--success-rich) ${Math.round(intensidade * 100)}%, transparent)`
              : `color-mix(in oklch, var(--destructive-rich) ${Math.round(intensidade * 100)}%, transparent)`,
          }}
          title={`${positivo ? "empurrou para satisfeito" : "puxou para insatisfeito"}: ${item.peso > 0 ? "+" : ""}${item.peso.toFixed(2)}`}
        >
          {trecho}
        </span>,
      );
    }
    cursor = item.fim;
  });

  if (cursor < texto.length) {
    pedacos.push(texto.slice(cursor));
  }

  return <span>{pedacos}</span>;
}
