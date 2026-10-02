"use client";

import { useState } from "react";
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { Cenario, Comparacao, Replay } from "@/lib/operacao";
import type { ResumoConversa } from "@/lib/api";
import { formatarDataHora } from "@/lib/formato";
import { Painel } from "@/components/Painel";
import { NotaLED } from "@/components/NotaLED";
import { EtiquetaCategoria } from "@/components/EtiquetaCategoria";
import { EstadoVazio } from "@/components/EstadoVazio";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { ContextoOperacao } from "./ConsoleOperacao";
import { CAMPO, Campo, Carregamento, Caso, GRADE, LINHA, Medida, Numero, PILHA, SelecionarConversas, useAcao, useRecurso } from "./comum";
import { IconeDeAcao } from "@/components/IconeDeAcao";

function Seletor({ conversas, id, mudar }: { conversas: ResumoConversa[]; id: string; mudar: (id: string) => void }) {
  return <Campo nome="Conversa do recorte"><select aria-label="Conversa do recorte" className={CAMPO} value={id} onChange={(e) => mudar(e.target.value)}><option value="">Selecione uma conversa</option>{conversas.map((c) => <option key={c.id} value={c.id}>{c.canal} · {formatarDataHora(c.iniciada_em)} · {c.id}</option>)}</select></Campo>;
}

export function ReplayOperacao({ conversas, sufixo }: ContextoOperacao) {
  const [id, setId] = useState(""), [passo, setPasso] = useState(0);
  const r = useRecurso<Replay>(id ? `/replay/${encodeURIComponent(id)}` : null);
  const ponto = r.dado?.pontos[passo];
  return <Painel titulo="Replay da conversa" nivel="dominante" legenda={r.dado?.metodo ?? "Cada ponto considera apenas o prefixo da conversa já ocorrido. A variação não demonstra causa e o score do banco não é substituído. Limite: 80 mensagens, sendo até 40 do cliente."}>
    <div className={PILHA}><Seletor conversas={conversas} id={id} mudar={(v) => { setId(v); setPasso(0); }} />
      {!id ? <EstadoVazio titulo="Escolha um atendimento" explicacao="Avance pela conversa para ver como a estimativa muda com as evidências disponíveis em cada momento." /> : !r.dado ? <Carregamento erro={r.erro} recarregar={r.recarregar} /> : <>
        <Caso id={id} sufixo={sufixo} />
        <div className="h-64 min-w-0" role="img" aria-label="Evolução do score estimado por mensagem; a lista abaixo contém os mesmos valores."><ResponsiveContainer width="100%" height="100%"><LineChart data={r.dado.pontos} margin={{ left: 0, right: 15, top: 10, bottom: 10 }}><CartesianGrid stroke="var(--compasso)" vertical={false} /><XAxis dataKey="indice" tick={{ fill: "var(--muted-foreground)", fontSize: 11 }} /><YAxis domain={[0, 100]} width={35} tick={{ fill: "var(--muted-foreground)", fontSize: 11 }} /><Tooltip contentStyle={{ background: "var(--background)", borderColor: "var(--linha)", color: "var(--foreground)" }} labelFormatter={(v) => `Índice ${v}`} /><Line dataKey="score" name="Score estimado" type="linear" stroke="var(--medido)" strokeWidth={2} dot={{ r: 3 }} connectNulls={false} isAnimationActive={false} /><ReferenceLine x={passo} stroke="var(--primary)" /></LineChart></ResponsiveContainer></div>
        <div className="flex flex-wrap items-center gap-3"><Button variant="outline" disabled={passo <= 0} onClick={() => setPasso((p) => p - 1)}><IconeDeAcao acao="anterior" />Anterior</Button><Medida nome="Índice da mensagem" valor={passo} /><Button variant="outline" disabled={passo >= r.dado.pontos.length - 1} onClick={() => setPasso((p) => p + 1)}>Próxima<IconeDeAcao acao="proxima" /></Button></div>
        {ponto ? <div className="border-y border-linha py-5"><div className={GRADE}><div><p className="rotulo-instrumento">{ponto.autor} · {formatarDataHora(ponto.enviada_em)}</p><p className="mt-3 whitespace-pre-wrap break-words text-dito-texto">{ponto.texto}</p></div><div className={PILHA}><NotaLED nota={ponto.nota} altura={40} /><EtiquetaCategoria categoria={ponto.categoria} /></div><Medida nome="Δ score estimado" valor={ponto.delta} casas={1} estimativa /></div>{ponto.virada ? <p className="mt-3 text-sm">Virada observada: variação de pelo menos dez pontos na estimativa.</p> : null}</div> : null}
        <ol className="max-h-80 overflow-y-auto">{r.dado.pontos.map((p) => <li key={p.indice}><Button variant="ghost" className="h-auto w-full justify-between gap-4 border-b border-border py-3" aria-pressed={passo === p.indice} onClick={() => setPasso(p.indice)}><span className="min-w-0 truncate text-xs">{p.autor} · {p.texto}</span><NotaLED nota={p.nota} altura={18} />{p.virada ? <span className="rotulo-instrumento">Virada</span> : null}</Button></li>)}</ol>
      </>}
    </div>
  </Painel>;
}

export function LaboratorioOperacao({ conversas, sufixo }: ContextoOperacao) {
  const [id, setId] = useState(""), [espera, setEspera] = useState(30), [limitar, setLimitar] = useState(true), [indice, setIndice] = useState("");
  const [cenario, setCenario] = useState<Cenario | null>(null), [comparacao, setComparacao] = useState<Comparacao | null>(null), [ids, setIds] = useState<string[]>([]);
  const acao = useAcao(), comparar = useAcao();
  return <div className={PILHA}><Painel titulo="Laboratório de cenários" nivel="dominante" legenda={cenario?.metodo ?? "Altere uma condição e observe a sensibilidade da estimativa. A simulação não prevê o efeito real no cliente; nenhuma conversa ou nota do banco é alterada."}>
    <form className={PILHA} onSubmit={(e) => { e.preventDefault(); void acao.executar<Cenario>("/laboratorio/cenario", "POST", { conversa_id: id, espera_maxima_s: limitar ? espera : null, ocultar_mensagem: indice === "" ? null : Number(indice) }, setCenario, "Cenário calculado sem alterar o banco.", false); }}>
      <Seletor conversas={conversas} id={id} mudar={(v) => { setId(v); setCenario(null); }} /><label className="flex items-center gap-3 text-sm"><input type="checkbox" checked={limitar} onChange={(e) => setLimitar(e.target.checked)} />Limitar a espera pela resposta</label>
      <div className={GRADE}>{limitar ? <Numero nome="Espera máxima · segundos" valor={espera} aoMudar={setEspera} min={1} max={14400} /> : null}<Campo nome="Índice da fala do cliente a ocultar · opcional"><Input type="number" min={0} step={1} value={indice} onChange={(e) => setIndice(e.target.value)} placeholder="Consulte o índice no Replay" /></Campo></div>
      <Button type="submit" disabled={acao.ocupado || !id || (!limitar && indice === "")}><IconeDeAcao acao="executar" />Comparar cenário com original</Button>{acao.feedback}
    </form>
    {cenario ? <div className={`${PILHA} mt-6`}><div className={GRADE}><div className={PILHA}><span className="rotulo-instrumento">Original · estimativa</span><NotaLED nota={cenario.original.nota} altura={38} /><EtiquetaCategoria categoria={cenario.original.categoria} /></div><div className={PILHA}><span className="rotulo-instrumento">Cenário · estimativa</span><NotaLED nota={cenario.cenario.nota} altura={38} /><EtiquetaCategoria categoria={cenario.cenario.categoria} /></div><Medida nome="Δ score estimado" valor={cenario.delta_score} casas={1} estimativa /></div><Caso id={cenario.original.id} sufixo={sufixo} /><details><summary className="cursor-pointer text-sm">Transcrição do cenário</summary>{cenario.mensagens_cenario.map((m, i) => <div key={i} className="border-b border-linha py-3"><p className="text-xs text-muted-foreground">{m.autor} · {formatarDataHora(m.enviada_em)}</p><p className="mt-1 whitespace-pre-wrap break-words text-sm text-dito-texto">{m.texto}</p></div>)}</details></div> : null}
  </Painel><Painel titulo="Comparar fusores" legenda={comparacao?.metodo ?? "A comparação exige um candidato compatível disponibilizado pelo administrador no servidor. As mesmas features alimentam ambos os modelos. Mudança de categoria não significa melhoria sem avaliação independente."}>
    <form className={PILHA} onSubmit={(e) => { e.preventDefault(); void comparar.executar<Comparacao>("/laboratorio/comparar", "POST", { conversa_ids: ids }, setComparacao, "Comparação concluída. O modelo ativo foi preservado.", false); }}><SelecionarConversas conversas={conversas} selecionadas={ids} mudar={setIds} /><Button type="submit" variant="outline" disabled={comparar.ocupado || !ids.length || ids.length > 30}><IconeDeAcao acao="executar" />Comparar ativo e candidato</Button>{comparar.feedback}</form>
    {comparacao ? <div className={`${PILHA} mt-5`}><div className={GRADE}>{comparacao.fatias.map((f) => <div key={f.canal} className={PILHA}><h3 className="text-sm">{f.canal}</h3><Medida nome="Conversas comparadas" valor={f.n} /><Medida nome="Categorias diferentes" valor={f.mudaram} /></div>)}</div>{comparacao.resultados.map((r) => <div key={r.atual.id} className={LINHA}><div className="min-w-0 flex-1"><Caso id={r.atual.id} sufixo={sufixo} /></div><div className={PILHA}><span className="rotulo-instrumento">Ativo</span><NotaLED nota={r.atual.nota} /><EtiquetaCategoria categoria={r.atual.categoria} /></div><div className={PILHA}><span className="rotulo-instrumento">Candidato</span><NotaLED nota={r.candidato.nota} /><EtiquetaCategoria categoria={r.candidato.categoria} /></div></div>)}</div> : null}
  </Painel></div>;
}
