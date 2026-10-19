import { Fragment } from "react";

/** Cada palavra numa mascara (`.w`) para o GSAP subir de dentro dela. Sai do
 * servidor ja quebrada: sem JS o titulo e texto comum, sem `innerHTML` no cliente. */
export function Palavras({ texto }: { texto: string }) {
  return texto.split(" ").map((palavra, i) => (
    <Fragment key={i}>{i > 0 && " "}<span className="w"><span>{palavra}</span></span></Fragment>
  ));
}

/** Letra a letra para o leitor de tela continuar ouvindo a frase inteira. */
export function Letras({ texto }: { texto: string }) {
  return (
    <>
      <span className="lp-so-leitor">{texto}</span>
      <span aria-hidden="true" data-letras>{[...texto].map((letra, i) => <span key={i}>{letra}</span>)}</span>
    </>
  );
}
