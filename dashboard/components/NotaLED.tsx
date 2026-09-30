import { SegmentoLED } from "./instrumento/SegmentoLED";

/**
 * A NOTA INFERIDA (0-10) NO DISPLAY.
 *
 * Um wrapper fino sobre `SegmentoLED`, e a razao de existir e uma so: a nota
 * aparece em cinco lugares (piores atendimentos, tabela, resumo do atendimento,
 * analisar, ficha) e o que ela faz com `null` tem que ser IGUAL em todos --
 * segmentos apagados, nunca `0`. Cinco chamadas soltas dariam cinco chances de
 * alguem escrever `nota ?? 0` (invariante 2).
 *
 * NAO calcula e NAO arredonda: `nota` e o inteiro que o SERVIDOR derivou
 * (invariante 3). Aqui so vira texto. Duas celulas cobrem 0..10 sem mexer no
 * tamanho do display quando a nota vai de 9 para 10.
 *
 * O rotulo e obrigatorio para a leitora de tela e por isso tem padrao: "nota
 * inferida" ja carrega a etiqueta de estimativa por extenso (o produto nao mede
 * satisfacao, infere). Quem chama pode trocar por algo mais especifico.
 */
export function NotaLED({
  nota,
  altura = 28,
  rotulo = "nota inferida, estimativa",
  className,
}: {
  /** Inteiro 0-10 vindo do servidor, ou `null` = sem sinal. */
  nota: number | null;
  altura?: number;
  rotulo?: string;
  className?: string;
}) {
  return (
    <SegmentoLED
      valor={nota === null ? null : String(nota)}
      celulas={2}
      altura={altura}
      rotulo={rotulo}
      className={className}
    />
  );
}
