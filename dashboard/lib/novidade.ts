import { useEffect, useSyncExternalStore } from "react";

/**
 * Atendimento NOVO = chegou ao servidor depois da ultima vez que esta pessoa
 * olhou a lista NESTE navegador.
 *
 * A comparacao usa `recebida_em` (quando o servidor gravou ou viu a conversa
 * mudar), nunca `iniciada_em`: um export de setembro enviado hoje comecou em
 * setembro e e novo mesmo assim. O marco mora no `localStorage` porque e uma
 * conveniencia de quem olha, nao um fato do atendimento -- nada disso vai ao
 * servidor nem muda nota, categoria ou indicador.
 */
export const CHAVE_VISTO_ATE = "fraus:atendimentos-vistos-ate";

export function ehNovo(recebidaEm: string | null | undefined, vistoAte: number | null): boolean {
  if (!recebidaEm || vistoAte === null) return false;
  const chegada = Date.parse(recebidaEm);
  return Number.isFinite(chegada) && chegada > vistoAte;
}

// O marco DESTA visita a lista. `undefined` = ainda nao lido; `null` = nao ha
// como saber (armazenamento bloqueado), e ai nada e marcado como novo.
let marcoDaVisita: number | null | undefined;

function gravar(instante: number) {
  try { localStorage.setItem(CHAVE_VISTO_ATE, String(instante)); } catch { /* armazenamento indisponivel */ }
}

function lerMarco(): number | null {
  if (marcoDaVisita !== undefined) return marcoDaVisita;
  try {
    const guardado = Number(localStorage.getItem(CHAVE_VISTO_ATE));
    if (Number.isFinite(guardado) && guardado > 0) {
      marcoDaVisita = guardado;
    } else {
      // Primeira visita: tudo que ja esta na lista conta como visto. Marcar o
      // banco inteiro como novo nao diria nada a ninguem.
      marcoDaVisita = Date.now();
      gravar(marcoDaVisita);
    }
  } catch {
    marcoDaVisita = null;
  }
  return marcoDaVisita;
}

const semAssinantes = () => () => {};

/**
 * Ate quando a lista ja foi vista, fixo enquanto ela estiver aberta.
 *
 * Fixo de proposito: o que chega com a lista aberta continua marcado ate a
 * pessoa sair -- se o marco andasse a cada releitura, o selo piscaria por
 * quinze segundos e sumiria. Ao sair (ou fechar a aba) o marco avanca, e na
 * proxima visita so o que chegou depois disso aparece como novo.
 */
export function useVistoAte(): number | null {
  const marco = useSyncExternalStore(semAssinantes, lerMarco, () => null);
  useEffect(() => {
    const encerrar = () => gravar(Date.now());
    window.addEventListener("pagehide", encerrar);
    return () => {
      window.removeEventListener("pagehide", encerrar);
      encerrar();
      marcoDaVisita = undefined;
    };
  }, []);
  return marco;
}
