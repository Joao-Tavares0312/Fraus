"use client";

import { useSyncExternalStore } from "react";
import { CloudRain, Pencil } from "lucide-react";
import { SidebarMenuButton } from "@/components/ui/sidebar";
import {
  aplicarTema,
  assinarTema,
  lerTema,
  temaDoServidor,
  type Tema,
} from "@/lib/tema";

const ROTULOS: Record<Tema, string> = {
  grafite: "Grafite",
  chuva: "Chuva de neon",
};

/**
 * O ALTERNADOR DE TEMA, no rodape da armadura.
 *
 * Dois estados, entao um botao que alterna -- nao um `select`. Menu suspenso
 * para escolher entre duas coisas cobra um clique a mais e uma camada a mais
 * por nada.
 *
 * POR QUE `useSyncExternalStore` E NAO `useState` + `useEffect`: o tema mora
 * no `localStorage`, que e estado FORA do React, e ler estado externo dentro
 * de um efeito para depois chama-lo de volta com `setState` e o padrao que a
 * regra `react-hooks/set-state-in-effect` existe para barrar -- ele produz um
 * render em cascata a cada montagem. Este hook foi feito para exatamente este
 * caso e resolve os dois lados de uma vez: o `temaDoServidor` da o snapshot do
 * HTML gerado no servidor (que nao tem storage) e o `lerTema` da o do cliente,
 * entao a hidratacao nao acusa divergencia.
 *
 * A COR NAO ESPERA POR ISTO: o script anti-piscada do `layout` ja pos a classe
 * no `<html>` antes da primeira pintura. O que este componente controla e so o
 * ROTULO e o icone.
 */
export function SeletorTema() {
  const tema = useSyncExternalStore(assinarTema, lerTema, temaDoServidor);
  const proximo: Tema = tema === "grafite" ? "chuva" : "grafite";
  const Icone = tema === "chuva" ? CloudRain : Pencil;
  const descricao = `Tema: ${ROTULOS[tema]}. Trocar para ${ROTULOS[proximo]}.`;

  return (
    <SidebarMenuButton
      onClick={() => aplicarTema(proximo)}
      // O `title` cobre a armadura recolhida, onde so o icone aparece.
      title={descricao}
      aria-label={descricao}
      className="text-xs text-muted-foreground"
    >
      <Icone aria-hidden />
      <span className="truncate">{ROTULOS[tema]}</span>
    </SidebarMenuButton>
  );
}
