"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  CHAVE_ATUALIZACAO,
  INTERVALO_DE_SONDA_MS,
  deveAtualizarNoFoco,
  mudouAAssinatura,
} from "@/lib/atualizacao";

/** `null` quando a sonda falha: quem decide o que fazer com isso e `mudouAAssinatura`. */
async function lerAssinatura(): Promise<string | null> {
  try {
    const resposta = await fetch("/api/fraus/conversas/assinatura", { cache: "no-store" });
    if (!resposta.ok) return null;
    const corpo: unknown = await resposta.json();
    const assinatura = (corpo as { assinatura?: unknown } | null)?.assinatura;
    return typeof assinatura === "string" ? assinatura : null;
  } catch {
    return null;
  }
}

/**
 * Rele os Server Components quando os dados mudam.
 *
 * Tres gatilhos: gravar numa aba da ferramenta, voltar o foco depois de 60 s
 * (cada refresh refaz todas as leituras da pagina) e a SONDA -- atendimento
 * que chega pelo TARS nao passa por esta aba, e sem ela a tela aberta so via o
 * dado novo quando alguem recarregava. A sonda pergunta uma coisa barata e so
 * rele quando a resposta muda; aba oculta nao pergunta nada.
 */
export function SincronizarDados() {
  const router = useRouter();
  useEffect(() => {
    let vivo = true;
    let relogio: number | undefined;
    let base: string | null = null;
    let ultima = Date.now();
    const visivel = () => document.visibilityState === "visible";
    const atualizar = () => {
      if (!visivel()) return;
      ultima = Date.now();
      router.refresh();
    };
    const aoFocar = () => {
      if (!visivel()) return;
      if (!deveAtualizarNoFoco(Date.now(), ultima)) return;
      atualizar();
    };
    const aoArmazenar = (evento: StorageEvent) => { if (evento.key === CHAVE_ATUALIZACAO) atualizar(); };
    const sondar = async () => {
      if (!vivo || !visivel()) return;
      const atual = await lerAssinatura();
      if (!vivo) return;
      if (mudouAAssinatura(base, atual)) atualizar();
      if (atual !== null) base = atual;
      if (visivel()) relogio = window.setTimeout(sondar, INTERVALO_DE_SONDA_MS);
    };
    const aoMudarVisibilidade = () => {
      window.clearTimeout(relogio);
      if (visivel()) void sondar();
    };
    window.addEventListener(CHAVE_ATUALIZACAO, atualizar);
    window.addEventListener("storage", aoArmazenar);
    window.addEventListener("focus", aoFocar);
    document.addEventListener("visibilitychange", aoMudarVisibilidade);
    void sondar();
    return () => {
      vivo = false;
      window.clearTimeout(relogio);
      window.removeEventListener(CHAVE_ATUALIZACAO, atualizar);
      window.removeEventListener("storage", aoArmazenar);
      window.removeEventListener("focus", aoFocar);
      document.removeEventListener("visibilitychange", aoMudarVisibilidade);
    };
  }, [router]);
  return null;
}
