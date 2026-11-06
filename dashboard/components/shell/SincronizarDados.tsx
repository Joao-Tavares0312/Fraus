"use client";

import { useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { CHAVE_ATUALIZACAO, deveAtualizarNoFoco } from "@/lib/atualizacao";

/**
 * Rele os Server Components ao gravar numa aba da ferramenta. Voltar o foco so
 * rele depois de 60 s: cada refresh refaz todas as leituras da pagina.
 */
export function SincronizarDados() {
  const router = useRouter();
  const ultima = useRef(Date.now());
  useEffect(() => {
    const atualizar = () => {
      if (document.visibilityState !== "visible") return;
      ultima.current = Date.now();
      router.refresh();
    };
    const aoFocar = () => {
      if (document.visibilityState !== "visible") return;
      if (!deveAtualizarNoFoco(Date.now(), ultima.current)) return;
      atualizar();
    };
    const aoArmazenar = (evento: StorageEvent) => { if (evento.key === CHAVE_ATUALIZACAO) atualizar(); };
    window.addEventListener(CHAVE_ATUALIZACAO, atualizar);
    window.addEventListener("storage", aoArmazenar);
    window.addEventListener("focus", aoFocar);
    return () => {
      window.removeEventListener(CHAVE_ATUALIZACAO, atualizar);
      window.removeEventListener("storage", aoArmazenar);
      window.removeEventListener("focus", aoFocar);
    };
  }, [router]);
  return null;
}
