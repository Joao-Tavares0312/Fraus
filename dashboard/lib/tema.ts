/**
 * OS DOIS TEMAS.
 *
 * O "espaco profundo" e o PADRAO DE FABRICA desde 01/09/2026, e por isso ele
 * mora no `:root` do globals.css e nao num bloco proprio: tema padrao e a
 * AUSENCIA de classe (ver `classeDoTema`). A "chuva de neon" e a opcao.
 *
 * O GRAFITE FOI DESCARTADO na mesma data, por decisao do dono do projeto. Ele
 * era o padrao desde o inicio; o que ele tinha de melhor -- o papel pautado e o
 * ouro fosco da marca -- foi absorvido pelo espaco em vez de ser jogado fora.
 * Quem tiver "grafite" gravado no storage cai no padrao sozinho: `temaValido`
 * so aceita o que existe, entao a migracao nao precisou de codigo.
 *
 * O QUE MUDA E O QUE NAO MUDA: o tema troca o CHASSI (fundo, superficie,
 * borda, quina do vidro, luz do atelie). A camada de DADO nao entra aqui --
 * `--dito` continua ambar e `--medido` continua azul nos dois, porque o
 * encoding e compromisso do PRODUCT.md e nao pele. Ver globals.css.
 *
 * A classe vive no `<html>` e nao num provider de contexto: quem precisa saber
 * o tema e o CSS, e o CSS ja sabe ler classe. Estado em React aqui so criaria
 * uma segunda fonte de verdade para uma coisa que o navegador ja guarda.
 */

export const TEMAS = ["espacial", "chuva"] as const;

export type Tema = (typeof TEMAS)[number];

export const TEMA_PADRAO: Tema = "espacial";

/** Onde a escolha sobrevive ao refresh. */
export const CHAVE_TEMA = "fraus-tema";

/**
 * A classe que o `<html>` carrega. O PADRAO e a AUSENCIA de classe, nao uma
 * classe propria: ele e o `:root`, e um tema padrao que precisa se declarar
 * para funcionar quebra em toda tela que renderiza antes do JavaScript.
 *
 * Escrito contra `TEMA_PADRAO` e nao contra o nome literal do tema: foi
 * exatamente essa indirecao que permitiu trocar o padrao de grafite para
 * espacial em 01/09/2026 sem tocar nesta funcao.
 */
export function classeDoTema(tema: Tema): string | null {
  return tema === TEMA_PADRAO ? null : `tema-${tema}`;
}

/** Aceita so o que existe. Valor estranho no storage cai no padrao. */
export function temaValido(valor: unknown): Tema {
  return TEMAS.includes(valor as Tema) ? (valor as Tema) : TEMA_PADRAO;
}

/**
 * O SCRIPT ANTI-PISCADA, injetado no `<head>` e executado antes da primeira
 * pintura.
 *
 * Sem ele o servidor manda o HTML sem classe, a tela pinta no tema padrao, o
 * React hidrata e so entao aplica a "chuva" -- um flash de troca de paleta a
 * cada navegacao. E preciso ser string inline: qualquer arquivo externo chega
 * depois do primeiro quadro, que e exatamente o quadro que se quer corrigir.
 *
 * `try/catch` porque `localStorage` levanta em navegacao privada de alguns
 * navegadores, e falhar aqui derrubaria a pagina inteira por causa de uma cor.
 */
export const SCRIPT_ANTI_PISCADA = `
(function(){try{
var t=localStorage.getItem(${JSON.stringify(CHAVE_TEMA)});
if(t&&t!==${JSON.stringify(TEMA_PADRAO)}){document.documentElement.classList.add("tema-"+t)}
}catch(e){}})();
`.trim();

/**
 * O evento que avisa a interface que o tema mudou nesta aba.
 *
 * `storage` do navegador so dispara nas OUTRAS abas -- a aba que escreveu nao
 * se ouve. Sem este evento proprio, o botao que voce acabou de clicar seria o
 * unico lugar da tela que nao saberia da troca.
 */
export const EVENTO_TEMA = "fraus:tema";

/**
 * Assina as duas fontes de mudanca, para `useSyncExternalStore`: a aba atual
 * (evento proprio) e as outras abas (evento nativo `storage`).
 */
export function assinarTema(aoMudar: () => void): () => void {
  window.addEventListener(EVENTO_TEMA, aoMudar);
  window.addEventListener("storage", aoMudar);
  return () => {
    window.removeEventListener(EVENTO_TEMA, aoMudar);
    window.removeEventListener("storage", aoMudar);
  };
}

/** O snapshot do SERVIDOR, que nao tem storage: sempre o padrao de fabrica. */
export function temaDoServidor(): Tema {
  return TEMA_PADRAO;
}

/** Le a escolha guardada. So no cliente. */
export function lerTema(): Tema {
  if (typeof window === "undefined") return TEMA_PADRAO;
  try {
    return temaValido(window.localStorage.getItem(CHAVE_TEMA));
  } catch {
    return TEMA_PADRAO;
  }
}

/**
 * Aplica e guarda. Remove as classes de TODOS os temas antes de por a nova --
 * so tirar a anterior deixaria lixo com tres ou mais. O projeto ja teve tres
 * (24/08 a 01/09/2026), entao isto nao e hipotese: e caso ja vivido.
 */
export function aplicarTema(tema: Tema): void {
  const raiz = document.documentElement;
  for (const outro of TEMAS) {
    const classe = classeDoTema(outro);
    if (classe) raiz.classList.remove(classe);
  }
  const classe = classeDoTema(tema);
  if (classe) raiz.classList.add(classe);
  try {
    window.localStorage.setItem(CHAVE_TEMA, tema);
  } catch {
    // Sem storage a escolha vale so para esta sessao. Nao e motivo de erro.
  }
  // Depois de escrever, e nao antes: quem ouvir vai chamar `lerTema`.
  window.dispatchEvent(new Event(EVENTO_TEMA));
}
