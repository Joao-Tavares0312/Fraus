"use client";

import { useState } from "react";
import type { ResumoConversa } from "@/lib/api";
import type { Tema } from "@/lib/operacao";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { RadarOperacao, EscalaOperacao, JornadasOperacao } from "./Planejamento";
import { ProblemasOperacao } from "./Problemas";
import { ReplayOperacao, LaboratorioOperacao } from "./Leituras";
import { AcessoOperacao } from "./Acesso";

export type ContextoOperacao = { conversas: ResumoConversa[]; sufixo: string; administrador: boolean };

export function ConsoleOperacao(props: ContextoOperacao) {
  const [aba, setAba] = useState("radar");
  const [tema, setTema] = useState<Tema | null>(null);
  const abas = [["radar", "Radar"], ["escala", "Equipe e escala"], ["jornadas", "Jornadas"], ["problemas", "Investigações"], ["replay", "Replay"], ["laboratorio", "Laboratório"], ...(props.administrador ? [["acesso", "Acessos"]] : [])];
  return <Tabs value={aba} onValueChange={(v) => setAba(String(v))} className="gap-5">
    <div className="max-w-full overflow-x-auto pb-2"><TabsList variant="line" aria-label="Ferramentas de operação" className="h-auto min-h-9">{abas.map(([id, nome]) => <TabsTrigger key={id} value={id} className="min-h-9 px-3">{nome}</TabsTrigger>)}</TabsList></div>
    <TabsContent value="radar"><RadarOperacao {...props} investigar={(t) => { setTema(t); setAba("problemas"); }} /></TabsContent>
    <TabsContent value="escala"><EscalaOperacao {...props} /></TabsContent>
    <TabsContent value="jornadas"><JornadasOperacao {...props} /></TabsContent>
    <TabsContent value="problemas"><ProblemasOperacao key={tema?.id ?? "manual"} {...props} tema={tema} /></TabsContent>
    <TabsContent value="replay"><ReplayOperacao {...props} /></TabsContent>
    <TabsContent value="laboratorio"><LaboratorioOperacao {...props} /></TabsContent>
    {props.administrador ? <TabsContent value="acesso"><AcessoOperacao /></TabsContent> : null}
  </Tabs>;
}
