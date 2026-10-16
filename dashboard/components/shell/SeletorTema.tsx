"use client";

import { useSyncExternalStore } from "react";
import { Moon, Sun } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { SidebarMenuButton } from "@/components/ui/sidebar";
import {
  aplicarTema,
  assinarTema,
  lerTema,
  temaDoServidor,
  TEMAS,
} from "@/lib/tema";
import type { Tema } from "@/lib/tema";

const ROTULOS: Record<Tema, string> = {
  escuro: "Escuro",
  claro: "Claro",
};

const ICONES: Record<Tema, LucideIcon> = {
  escuro: Moon,
  claro: Sun,
};

/** O rótulo anuncia o destino; a preferência permanece ao sair da ferramenta. */
export function SeletorTema() {
  const tema = useSyncExternalStore(assinarTema, lerTema, temaDoServidor);
  const proximo: Tema = TEMAS[(TEMAS.indexOf(tema) + 1) % TEMAS.length];
  const Icone = ICONES[tema];
  const descricao = `Tema: ${ROTULOS[tema]}. Trocar para ${ROTULOS[proximo]}.`;

  return (
    <SidebarMenuButton
      onClick={() => aplicarTema(proximo)}
      tooltip={descricao}
      title={descricao}
      aria-label={descricao}
      className="h-10 px-3 text-xs text-muted-foreground"
    >
      <Icone aria-hidden />
      <span className="truncate group-data-[collapsible=icon]:hidden">{ROTULOS[tema]}</span>
    </SidebarMenuButton>
  );
}
