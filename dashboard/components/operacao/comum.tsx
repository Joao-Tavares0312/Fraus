"use client";

import { useEffect, useState, type ReactNode } from "react";
import Link from "next/link";
import { consultarOperacao } from "@/lib/operacao";
import { anunciarAtualizacao } from "@/lib/atualizacao";
import type { IntervaloNps, ResumoConversa } from "@/lib/api";
import { formatarNumero, formatarDataHora } from "@/lib/formato";
import { SegmentoLED } from "@/components/instrumento/SegmentoLED";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { EstadoVazio } from "@/components/EstadoVazio";
import { IconeDeAcao } from "@/components/IconeDeAcao";

export const CAMPO = "w-full min-w-0 border border-input bg-background px-3 py-2 text-sm focus-visible:outline focus-visible:outline-ring";
export const PILHA = "flex flex-col gap-4";
export const GRADE = "grid gap-4 sm:grid-cols-2 lg:grid-cols-3";
export const LINHA = "flex flex-wrap items-center gap-3 border-b border-linha py-4";
export const lista = (texto: string) => [...new Set(texto.split(",").map((t) => t.trim()).filter(Boolean))];

export function useRecurso<T>(rota: string | null) {
  const [versao, setVersao] = useState(0);
  const [estado, setEstado] = useState<{ dado: T | null; erro: string | null; rota: string | null }>({ dado: null, erro: null, rota: null });
  useEffect(() => {
    let ativo = true;
    if (rota) void consultarOperacao<T>(rota).then((r) => { if (ativo) setEstado({ dado: r.ok ? r.dado : null, erro: r.ok ? null : r.erro, rota }); });
    return () => { ativo = false; };
  }, [rota, versao]);
  return { dado: estado.rota === rota ? estado.dado : null, erro: estado.rota === rota ? estado.erro : null, recarregar: () => setVersao((v) => v + 1) };
}

export function useAcao() {
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);
  async function executar<T>(rota: string, metodo: "POST" | "PUT" | "PATCH", corpo?: unknown, sucesso?: (dado: T) => void, mensagem = "Alteração salva.", grava = true) {
    if (ocupado) return;
    setOcupado(true); setErro(null); setAviso(null);
    try {
      const r = await consultarOperacao<T>(rota, metodo, corpo);
      if (r.ok) { sucesso?.(r.dado); setAviso(mensagem); if (grava) anunciarAtualizacao(); }
      else setErro(r.erro);
    } finally { setOcupado(false); }
  }
  return { ocupado, executar, feedback: <div role="status" aria-live="polite">{erro || aviso ? <Alert variant={erro ? "destructive" : "default"}><AlertDescription>{erro ?? aviso}</AlertDescription></Alert> : null}</div> };
}

export function Campo({ nome, children }: { nome: string; children: ReactNode }) {
  return <label className="flex min-w-0 flex-col gap-2 text-sm"><span className="rotulo-instrumento">{nome}</span>{children}</label>;
}
export function Numero({ nome, valor, aoMudar, min = 0, max, passo = 1 }: { nome: string; valor: number; aoMudar: (v: number) => void; min?: number; max?: number; passo?: number }) {
  return <Campo nome={nome}><Input type="number" required value={valor} min={min} max={max} step={passo} onChange={(e) => aoMudar(Number(e.target.value))} /></Campo>;
}
export function Medida({ nome, valor, casas = 0, unidade = "", estimativa = false }: { nome: string; valor: number | null; casas?: number; unidade?: string; estimativa?: boolean }) {
  return <div className="flex min-w-0 flex-col gap-2"><span className="rotulo-instrumento">{nome}</span><div className="flex flex-wrap items-end gap-2"><SegmentoLED valor={valor === null ? null : formatarNumero(valor, casas)} altura={28} celulas={3} rotulo={nome} cor={estimativa ? "medido" : "tinta"} /><span className="text-xs text-muted-foreground">{unidade} {estimativa ? "estimativa" : ""}</span></div></div>;
}
export function FaixaNps({ titulo, intervalo }: { titulo: string; intervalo: IntervaloNps | null }) {
  return <div className="flex flex-col gap-2"><Medida nome={titulo} valor={intervalo?.nps ?? null} casas={1} estimativa /><Medida nome="Conversas com sinal" valor={intervalo?.n ?? 0} /><p className="text-xs text-muted-foreground">{intervalo ? `IC 95%: ${formatarNumero(intervalo.ic_inferior, 1)} a ${formatarNumero(intervalo.ic_superior, 1)}. ${intervalo.nps === null ? "NPS oculto: menos de 30 conversas com sinal." : ""}` : "Sem conversas com sinal."}</p></div>;
}
export function Carregamento({ erro, recarregar }: { erro: string | null; recarregar: () => void }) {
  return erro ? <div className={PILHA}><EstadoVazio titulo="Não foi possível carregar" explicacao={erro} /><Button variant="outline" onClick={recarregar}><IconeDeAcao acao="atualizar" />Tentar novamente</Button></div> : <p role="status" className="text-sm text-muted-foreground">Consultando os dados da operação…</p>;
}
export function SelecionarConversas({ conversas, selecionadas, mudar }: { conversas: ResumoConversa[]; selecionadas: string[]; mudar: (ids: string[]) => void }) {
  const [busca, setBusca] = useState("");
  const visiveis = conversas.filter((c) => `${c.id} ${c.canal}`.toLocaleLowerCase("pt-BR").includes(busca.toLocaleLowerCase("pt-BR")));
  return <fieldset className={PILHA}><legend className="rotulo-instrumento mb-2">Conversas como evidência</legend>
    <Input aria-label="Buscar conversas por canal ou ID" value={busca} onChange={(e) => setBusca(e.target.value)} placeholder="Filtrar por canal ou ID" />
    <div className="max-h-52 overflow-y-auto border border-linha p-3">
      {!visiveis.length ? <p className="text-sm text-muted-foreground">Nenhuma conversa neste recorte.</p> : visiveis.map((c) => <label key={c.id} className="flex items-start gap-3 border-b border-border py-2 text-xs"><input type="checkbox" checked={selecionadas.includes(c.id)} onChange={(e) => mudar(e.target.checked ? [...selecionadas, c.id] : selecionadas.filter((i) => i !== c.id))} /><span className="min-w-0 break-all">{c.canal} · {formatarDataHora(c.iniciada_em)} · {c.id}</span></label>)}
    </div><Medida nome="Selecionadas" valor={selecionadas.length} />
  </fieldset>;
}
export function Caso({ id, sufixo }: { id: string; sufixo: string }) {
  return <Link className="break-all text-xs text-primary underline underline-offset-4" href={`/dashboard/atendimentos/${encodeURIComponent(id)}${sufixo}`}>{id}</Link>;
}
