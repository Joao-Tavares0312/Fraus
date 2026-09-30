/**
 * O ALFABETO DO DISPLAY DE SETE SEGMENTOS.
 *
 * Parte PURA do `SegmentoLED`: dado um caractere, quais segmentos acendem. Mora
 * em `lib/` (e nao dentro do componente) porque e a regra que decide se um
 * valor aparece como numero ou como ausencia, e regra dessas tem que ser
 * testavel sem montar React -- o runner da dashboard e `environment: node`.
 *
 * Os sete segmentos seguem a convencao de todo display desse tipo:
 *
 *      aaa
 *     f   b
 *      ggg
 *     e   c
 *      ddd
 *
 * O componente NAO calcula, arredonda nem converte nada: recebe a string que o
 * chamador ja formatou em pt-BR (`formatarNps`, `formatarNumero`...). Formatar
 * aqui seria uma segunda fonte de formatacao, e a invariante 3 do CLAUDE.md
 * existe justamente porque regra duplicada no front diverge.
 */

export type Segmento = "a" | "b" | "c" | "d" | "e" | "f" | "g";

/** Segmentos acesos por digito. O hifen e o segmento do meio -- o sinal de menos. */
const DIGITOS: Readonly<Record<string, readonly Segmento[]>> = {
  "0": ["a", "b", "c", "d", "e", "f"],
  "1": ["b", "c"],
  "2": ["a", "b", "d", "e", "g"],
  "3": ["a", "b", "c", "d", "g"],
  "4": ["b", "c", "f", "g"],
  "5": ["a", "c", "d", "f", "g"],
  "6": ["a", "c", "d", "e", "f", "g"],
  "7": ["a", "b", "c"],
  "8": ["a", "b", "c", "d", "e", "f", "g"],
  "9": ["a", "b", "c", "d", "f", "g"],
  "-": ["g"],
};

/**
 * Uma celula do display, ja classificada.
 *
 *  - `digito`: celula larga com os sete segmentos; `acesos` diz quais brilham.
 *  - `mais`: o sinal de mais do NPS positivo (`+12`). O display de sete
 *    segmentos nao tem `+`; desenha-se o segmento do meio mais um traco
 *    vertical, que e o que qualquer painel de instrumento faz.
 *  - `virgula`: o ponto decimal, celula estreita (o pt-BR escreve `2,9`).
 *  - `doispontos`: separador de hora (`4:12`), celula estreita.
 *  - `espaco`: respiro entre grupos, sem desenho.
 *  - `cru`: caractere fora do alfabeto. NAO e descartado: some um caractere e o
 *    numero muda de significado sem ninguem ver -- entra como texto legivel.
 */
export type Celula =
  | { tipo: "digito"; acesos: readonly Segmento[] }
  | { tipo: "mais" }
  | { tipo: "virgula" }
  | { tipo: "doispontos" }
  | { tipo: "espaco" }
  | { tipo: "cru"; texto: string };

export function celulaDe(caractere: string): Celula {
  // O MENOS TIPOGRAFICO (U+2212) e o hifen sao o MESMO sinal: `Intl` e o
  // servidor podem entregar qualquer um dos dois, e o NPS negativo nao pode
  // mudar de desenho conforme quem formatou.
  const chave = caractere === "−" ? "-" : caractere;
  const acesos = DIGITOS[chave];
  if (acesos) return { tipo: "digito", acesos };
  if (caractere === "+") return { tipo: "mais" };
  if (caractere === "," || caractere === ".") return { tipo: "virgula" };
  if (caractere === ":") return { tipo: "doispontos" };
  if (caractere === " ") return { tipo: "espaco" };
  return { tipo: "cru", texto: caractere };
}

/**
 * As celulas de um valor. `null` e AUSENCIA, nunca zero: devolve `celulas`
 * digitos com todos os segmentos apagados -- a "cabeca vazada" do display
 * (DESIGN.md §1.1). O `0` aceso e uma afirmacao; o apagado nao afirma nada.
 */
export function celulasDoValor(
  valor: string | null,
  celulasSemSinal: number,
): Celula[] {
  if (valor === null) {
    return Array.from(
      { length: Math.max(1, celulasSemSinal) },
      (): Celula => ({ tipo: "digito", acesos: [] }),
    );
  }
  // `Array.from` de string separa por ponto de codigo, nao por unidade UTF-16:
  // um emoji perdido no valor viraria duas metades quebradas.
  return Array.from(valor, celulaDe);
}

/** Quantos segmentos estao acesos no total. Serve ao teste e a inspecao. */
export function totalDeAcesos(celulas: readonly Celula[]): number {
  return celulas.reduce(
    (soma, c) => soma + (c.tipo === "digito" ? c.acesos.length : 0),
    0,
  );
}
