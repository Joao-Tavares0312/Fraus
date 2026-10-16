"use client";

import { useLayoutEffect } from "react";
import { usePathname } from "next/navigation";
import { assinarTema, sincronizarTemaDaRota } from "@/lib/tema";

/** Sincroniza antes da pintura, inclusive no retorno à LP por navegação cliente. */
export function TemaDaRota() {
  const caminho = usePathname();
  useLayoutEffect(() => {
    const sincronizar = () => sincronizarTemaDaRota(caminho);
    sincronizar();
    return assinarTema(sincronizar);
  }, [caminho]);
  return null;
}
