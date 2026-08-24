"use client";

import { useEffect, useState } from "react";

const LARGURA_MOBILE = 768;

/**
 * Hook padrao do chassi shadcn, exigido por `components/ui/sidebar.tsx` para
 * decidir entre a barra fixa e a gaveta.
 *
 * Comeca `false` e nao `undefined` porque o `SidebarProvider` usa o valor no
 * primeiro render: o servidor nao sabe a largura da janela, entao o desktop e o
 * palpite que evita renderizar a gaveta e troca-la um frame depois.
 */
export function useIsMobile() {
  const [ehMobile, setEhMobile] = useState(false);

  useEffect(() => {
    const consulta = window.matchMedia(`(max-width: ${LARGURA_MOBILE - 1}px)`);
    const aplicar = () => setEhMobile(consulta.matches);
    aplicar();
    consulta.addEventListener("change", aplicar);
    return () => consulta.removeEventListener("change", aplicar);
  }, []);

  return ehMobile;
}
