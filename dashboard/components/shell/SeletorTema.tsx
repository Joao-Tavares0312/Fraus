"use client";

import { useSyncExternalStore } from "react";
import { CloudRain, Orbit, type LucideIcon } from "lucide-react";
import { SidebarMenuButton } from "@/components/ui/sidebar";
import {
  aplicarTema,
  assinarTema,
  lerTema,
  temaDoServidor,
  TEMAS,
  type Tema,
} from "@/lib/tema";

const ROTULOS: Record<Tema, string> = {
  espacial: "Espaço profundo",
  chuva: "Chuva de neon",
};

const ICONES: Record<Tema, LucideIcon> = {
  espacial: Orbit,
  chuva: CloudRain,
};

/**
 * O ALTERNADOR DE TEMA, no rodape da armadura.
 *
 * CICLA na ordem de `TEMAS`, voltando ao inicio. Com os dois temas de hoje
 * (o grafite foi descartado em 01/09/2026) isso e uma alternancia simples, mas
 * o codigo continua escrito como ciclo de propósito: foi assim que a entrada e
 * a saida de um terceiro tema custaram zero linha aqui. O rotulo e o
 * `aria-label` dizem para onde o proximo clique leva, entao nao e adivinhacao.
 *
 * O `Record<Tema, ...>` das duas tabelas e proposital: acrescentar um tema em
 * `lib/tema.ts` sem dar rotulo e icone a ele nao compila. O tipo e o gate.
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
  const proximo: Tema = TEMAS[(TEMAS.indexOf(tema) + 1) % TEMAS.length];
  const Icone = ICONES[tema];
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
