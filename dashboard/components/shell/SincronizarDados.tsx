"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { CHAVE_ATUALIZACAO } from "@/lib/atualizacao";

/** Rele os Server Components ao gravar ou voltar a uma aba da ferramenta. */
export function SincronizarDados() {
  const router = useRouter();
  useEffect(() => {
    const atualizar = () => { if (document.visibilityState === "visible") router.refresh(); };
    const aoArmazenar = (evento: StorageEvent) => { if (evento.key === CHAVE_ATUALIZACAO) atualizar(); };
    window.addEventListener(CHAVE_ATUALIZACAO, atualizar);
    window.addEventListener("storage", aoArmazenar);
    window.addEventListener("focus", atualizar);
    return () => {
      window.removeEventListener(CHAVE_ATUALIZACAO, atualizar);
      window.removeEventListener("storage", aoArmazenar);
      window.removeEventListener("focus", atualizar);
    };
  }, [router]);
  return null;
}
