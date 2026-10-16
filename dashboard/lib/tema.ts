/** A preferência só colore a ferramenta; as chegadas permanecem escuras. */
export const TEMAS = ["escuro", "claro"] as const;
export type Tema = (typeof TEMAS)[number];
export const TEMA_PADRAO: Tema = "escuro";
export const CHAVE_TEMA = "fraus-tema";
export const EVENTO_TEMA = "fraus:tema";

export function classeDoTema(tema: Tema): "dark" | "light" {
  return tema === "claro" ? "light" : "dark";
}

export function temaValido(valor: unknown): Tema {
  return TEMAS.includes(valor as Tema) ? (valor as Tema) : TEMA_PADRAO;
}

export function temaDaRota(caminho: string, preferencia: Tema): Tema {
  return caminho === "/dashboard" || caminho.startsWith("/dashboard/")
    ? preferencia
    : TEMA_PADRAO;
}

export const SCRIPT_ANTI_PISCADA = `
(function(){var t="escuro";try{var p=localStorage.getItem(${JSON.stringify(CHAVE_TEMA)});if(p==="claro")t=p}catch(e){}
var d=location.pathname==="/dashboard"||location.pathname.indexOf("/dashboard/")===0;
var c=d&&t==="claro"?"light":"dark";var r=document.documentElement;
r.classList.remove("light","dark");r.classList.add(c);r.style.colorScheme=c;})();
`.trim();

export function assinarTema(aoMudar: () => void): () => void {
  window.addEventListener(EVENTO_TEMA, aoMudar);
  window.addEventListener("storage", aoMudar);
  return () => {
    window.removeEventListener(EVENTO_TEMA, aoMudar);
    window.removeEventListener("storage", aoMudar);
  };
}

export function temaDoServidor(): Tema {
  return TEMA_PADRAO;
}

// Mantém a escolha da aba mesmo quando o navegador bloqueia localStorage.
let preferenciaSemStorage: Tema = TEMA_PADRAO;
export function lerTema(): Tema {
  if (typeof window === "undefined") return TEMA_PADRAO;
  try {
    return temaValido(window.localStorage.getItem(CHAVE_TEMA));
  } catch {
    return preferenciaSemStorage;
  }
}

export function sincronizarTemaDaRota(caminho: string): void {
  const classe = classeDoTema(temaDaRota(caminho, lerTema()));
  const raiz = document.documentElement;
  raiz.classList.remove("light", "dark");
  raiz.classList.add(classe);
  raiz.style.colorScheme = classe;
}

export function aplicarTema(tema: Tema): void {
  preferenciaSemStorage = tema;
  try {
    window.localStorage.setItem(CHAVE_TEMA, tema);
  } catch {
    // A escolha continua válida nesta aba, sem transformar cor em erro de tela.
  }
  sincronizarTemaDaRota(window.location.pathname);
  window.dispatchEvent(new Event(EVENTO_TEMA));
}
