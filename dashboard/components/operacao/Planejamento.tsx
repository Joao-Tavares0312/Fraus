"use client";

import { useState } from "react";
import type { Acesso, Equipe, Jornada, Radar, SimulacaoEscala, Tema, Turno } from "@/lib/operacao";
import { formatarDataHora } from "@/lib/formato";
import { Painel } from "@/components/Painel";
import { EstadoVazio } from "@/components/EstadoVazio";
import { NotaLED } from "@/components/NotaLED";
import { EtiquetaCategoria } from "@/components/EtiquetaCategoria";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { ContextoOperacao } from "./ConsoleOperacao";
import { ConvitesEquipe } from "./Convites";
import { Campo, Carregamento, Caso, FaixaNps, GRADE, LINHA, lista, Medida, Numero, PILHA, SelecionarConversas, useAcao, useRecurso } from "./comum";
import { IconeDeAcao } from "@/components/IconeDeAcao";

export function RadarOperacao({ sufixo, investigar }: ContextoOperacao & { investigar: (tema: Tema) => void }) {
  const r = useRecurso<Radar>(`/radar${sufixo}`);
  return <Painel titulo="Radar de temas" nivel="dominante" legenda={r.dado?.metodo} acessorio={<Button variant="ghost" onClick={r.recarregar}><IconeDeAcao acao="atualizar" />Atualizar</Button>}>
    {!r.dado ? <Carregamento erro={r.erro} recarregar={r.recarregar} /> : <div className={PILHA}>
      <div className={GRADE}><Medida nome="Conversas examinadas" valor={r.dado.amostra} /><Medida nome="Temas encontrados" valor={r.dado.temas.length} /><Medida nome="Fora do limite de leitura" valor={r.dado.truncadas} /></div>
      {r.dado.janela ? <p className="text-xs text-muted-foreground">Janela recente: {r.dado.janela.de} a {r.dado.janela.ate}. Taxas calculadas sobre todas as conversas de cada janela, inclusive as sem tema.</p> : null}
      {!r.dado.temas.length ? <EstadoVazio titulo="Ainda não há temas recorrentes" explicacao="O radar precisa de pelo menos duas conversas com vocabulário semelhante. Analise e salve mais conversas ou amplie o período." /> : r.dado.temas.map((t) => <article key={t.id} className="border-t border-linha pt-5">
        <div className="flex flex-wrap items-baseline justify-between gap-3"><h3 className="font-medium text-dito-texto">{t.termos.join(" · ")}</h3><span className="rotulo-instrumento">{t.emergente ? "↑ Tema em crescimento" : "Tema recorrente"}</span></div>
        <div className={`${GRADE} my-4`}><Medida nome="Ocorrências recentes" valor={t.recentes} /><Medida nome="Taxa recente" valor={t.taxa_atual === null ? null : t.taxa_atual * 100} casas={1} unidade="%" /><Medida nome="Taxa anterior" valor={t.taxa_anterior === null ? null : t.taxa_anterior * 100} casas={1} unidade="%" /></div>
        <details className="text-sm"><summary className="cursor-pointer">Evidências e NPS estimado</summary><div className="mt-4 flex flex-col gap-3"><FaixaNps titulo="NPS do tema" intervalo={t.intervalo} />{t.conversa_ids.slice(0, 50).map((id) => <Caso key={id} id={id} sufixo={sufixo} />)}{t.conversa_ids.length > 50 ? <p>Exibindo as primeiras 50 evidências.</p> : null}</div></details>
        <Button className="mt-4" variant="outline" onClick={() => investigar(t)}><IconeDeAcao acao="abrir" />Abrir investigação com evidências</Button>
      </article>)}
    </div>}
  </Painel>;
}

export function EscalaOperacao({ sufixo, administrador }: ContextoOperacao) {
  const equipes = useRecurso<{ equipes: Equipe[] }>("/equipes");
  const acesso = useRecurso<Acesso>(administrador ? "/acesso" : null);
  const equipeAcao = useAcao(), simulacaoAcao = useAcao();
  const [nome, setNome] = useState(""), [competencias, setCompetencias] = useState(""), [canais, setCanais] = useState("");
  const [membros, setMembros] = useState<number[]>([]);
  const [editando, setEditando] = useState<string | null>(null);
  const [turnos, setTurnos] = useState<(Turno & { canaisTexto: string })[]>([{ inicio: 8, fim: 18, pessoas: 2, canais: [], canaisTexto: "" }]);
  const [duracao, setDuracao] = useState(600), [custo, setCusto] = useState(30);
  const [resultado, setResultado] = useState<SimulacaoEscala | null>(null);
  const [anterior, setAnterior] = useState<SimulacaoEscala | null>(null);
  function turno(i: number, campo: keyof (Turno & { canaisTexto: string }), valor: number | string[] | string) { setTurnos((ts) => ts.map((t, j) => j === i ? { ...t, [campo]: valor } : t)); }
  return <div className={PILHA}>
    <Painel titulo="Simulador de escala" nivel="dominante" legenda={resultado?.metodo ?? "Simulação de fila sobre chegadas históricas. Pessoas, duração e custo são hipóteses; os horários seguem o fuso registrado. Custo considera todos os dias entre o primeiro e último registro do recorte."}>
      <form className={PILHA} onSubmit={(e) => { e.preventDefault(); void simulacaoAcao.executar<SimulacaoEscala>(`/escala/simular${sufixo}`, "POST", { turnos: turnos.map(({ canaisTexto, ...t }) => ({ ...t, canais: lista(canaisTexto) })), duracao_s: duracao, custo_hora: custo }, (r) => { setAnterior(resultado); setResultado(r); }, "Simulação calculada. Os atendimentos permanecem preservados.", false); }}>
        <p className="text-sm text-muted-foreground">Reproduza a demanda humana registrada e compare cenários. Ajuste os postos por horário e canal; canais vazios atendem toda a demanda.</p>
        {turnos.map((t, i) => <fieldset key={i} className="border-b border-linha pb-4"><legend className="rotulo-instrumento mb-3">Turno {String.fromCharCode(65 + i)}</legend><div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5"><Numero nome="Início · hora" valor={t.inicio} aoMudar={(v) => turno(i, "inicio", v)} max={23} /><Numero nome="Fim · hora" valor={t.fim} aoMudar={(v) => turno(i, "fim", v)} min={1} max={24} /><Numero nome="Pessoas" valor={t.pessoas} aoMudar={(v) => turno(i, "pessoas", v)} max={100} /><Campo nome="Canais · vírgulas"><Input value={t.canaisTexto} onChange={(e) => turno(i, "canaisTexto", e.target.value)} /></Campo><Button type="button" variant="ghost" disabled={turnos.length === 1} onClick={() => setTurnos((ts) => ts.filter((_, j) => j !== i))}><IconeDeAcao acao="remover" />Remover turno</Button></div></fieldset>)}
        <Button type="button" variant="outline" disabled={turnos.length >= 24} onClick={() => setTurnos((ts) => [...ts, { inicio: 8, fim: 18, pessoas: 1, canais: [], canaisTexto: "" }])}><IconeDeAcao acao="criar" />Adicionar turno</Button>
        <div className={GRADE}><Numero nome="Duração por contato · segundos" valor={duracao} aoMudar={setDuracao} min={1} max={14400} /><Numero nome="Custo por pessoa / hora · R$" valor={custo} aoMudar={setCusto} max={10000} passo={0.01} /></div>
        <Button type="submit" disabled={simulacaoAcao.ocupado}><IconeDeAcao acao="executar" />{simulacaoAcao.ocupado ? "Simulando…" : "Simular escala"}</Button>{simulacaoAcao.feedback}
      </form>
      {resultado ? <div className="mt-6 flex flex-col gap-5"><div className={GRADE}><Medida nome="Demanda humana observada" valor={resultado.demanda} /><Medida nome="Atendidas no cenário" valor={resultado.atendidas} estimativa /><Medida nome="Pendentes no cenário" valor={resultado.pendentes} estimativa /><Medida nome="Espera mediana" valor={resultado.espera_mediana_s} unidade="s" estimativa /><Medida nome="Espera P95" valor={resultado.espera_p95_s} unidade="s" estimativa /><Medida nome="Custo no recorte" valor={resultado.custo} casas={2} unidade="R$" estimativa /></div>
        {anterior ? <div className={GRADE}><Medida nome="Δ espera vs. cenário anterior" valor={resultado.espera_mediana_s !== null && anterior.espera_mediana_s !== null ? resultado.espera_mediana_s - anterior.espera_mediana_s : null} casas={1} unidade="s" estimativa /><Medida nome="Δ pendentes" valor={resultado.pendentes - anterior.pendentes} estimativa /><Medida nome="Δ custo" valor={resultado.custo - anterior.custo} casas={2} unidade="R$" estimativa /></div> : null}
        <details><summary className="cursor-pointer text-sm">Demanda típica por dia da semana</summary><div className={`${GRADE} mt-4`}>{resultado.previsao.map((p) => <div key={p.dia_semana} className={PILHA}><Medida nome={["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado", "Domingo"][p.dia_semana]} valor={p.contatos_medios} casas={1} estimativa /><Medida nome="Dias com registros na base" valor={p.dias_observados} /></div>)}</div></details>
      </div> : null}
    </Painel>
    <Painel titulo="Equipes e competências">
      {!equipes.dado ? <Carregamento erro={equipes.erro} recarregar={equipes.recarregar} /> : <div className={PILHA}>{!equipes.dado.equipes.length ? <p className="text-sm text-muted-foreground">Nenhuma equipe cadastrada no seu escopo.</p> : equipes.dado.equipes.map((t) => <div key={t.id} className={LINHA}><div className="flex-1"><h3>{t.nome}</h3><p className="text-xs text-muted-foreground">{t.competencias.join(" · ") || "Competências não informadas"} · {t.canais.join(" · ") || "Nenhum canal definido"}</p></div><Medida nome="Membros" valor={t.membros.length} />{administrador ? <Button variant="outline" onClick={() => { setEditando(t.id); setNome(t.nome); setMembros(t.membros); setCompetencias(t.competencias.join(", ")); setCanais(t.canais.join(", ")); }}><IconeDeAcao acao="editar" />Editar</Button> : null}</div>)}</div>}
      {administrador ? <form className={`${PILHA} mt-5`} onSubmit={(e) => { e.preventDefault(); void equipeAcao.executar(editando ? `/equipes/${editando}` : "/equipes", editando ? "PUT" : "POST", { nome, membros, competencias: lista(competencias), canais: lista(canais) }, () => { equipes.recarregar(); setNome(""); setMembros([]); setEditando(null); }); }}><div className={GRADE}><Campo nome="Nome da equipe"><Input required maxLength={100} value={nome} onChange={(e) => setNome(e.target.value)} /></Campo><Campo nome="Competências · vírgulas"><Input value={competencias} onChange={(e) => setCompetencias(e.target.value)} /></Campo><Campo nome="Canais · vírgulas"><Input value={canais} onChange={(e) => setCanais(e.target.value)} /></Campo></div>
        <fieldset><legend className="rotulo-instrumento mb-2">Membros</legend>{acesso.dado ? acesso.dado.usuarios.filter((u) => u.ativo).map((u) => <label key={u.id} className="mr-5 inline-flex items-center gap-2 text-sm"><input type="checkbox" checked={membros.includes(u.id)} onChange={(e) => setMembros(e.target.checked ? [...membros, u.id] : membros.filter((i) => i !== u.id))} />{u.nome}</label>) : <Carregamento erro={acesso.erro} recarregar={acesso.recarregar} />}</fieldset><p className="text-xs text-muted-foreground">Competências documentam a equipe. A simulação distribui por canais e postos; permissões de acesso são definidas na aba Acessos.</p><Button type="submit" disabled={equipeAcao.ocupado}><IconeDeAcao acao="salvar" />{editando ? "Salvar equipe" : "Criar equipe"}</Button>{editando ? <Button type="button" variant="ghost" onClick={() => { setEditando(null); setNome(""); setMembros([]); setCanais(""); setCompetencias(""); }}><IconeDeAcao acao="cancelar" />Cancelar edição</Button> : null}{equipeAcao.feedback}</form> : null}
    </Painel>
    {equipes.dado?.equipes.length ? <Painel titulo="Hierarquia e convites">{equipes.dado.equipes.map((t) => <ConvitesEquipe key={t.id} equipe={t} recarregar={equipes.recarregar} />)}</Painel> : null}
  </div>;
}

export function JornadasOperacao({ conversas, sufixo }: ContextoOperacao) {
  const r = useRecurso<{ jornadas: Jornada[] }>(`/jornadas${sufixo}`), acao = useAcao();
  const [referencia, setReferencia] = useState(""), [ids, setIds] = useState<string[]>([]);
  return <div className={PILHA}><Painel titulo="Jornadas entre canais" nivel="dominante" legenda="A ligação é explícita, por referência pseudônima. O servidor guarda somente seu hash. Recontatos são contados dentro do período; fechamento não é resolução. Vincular novamente uma conversa substitui sua referência anterior.">
    {!r.dado ? <Carregamento erro={r.erro} recarregar={r.recarregar} /> : !r.dado.jornadas.length ? <EstadoVazio titulo="Nenhuma jornada vinculada" explicacao="Selecione os contatos de uma mesma referência pseudônima abaixo. O Fraus não tenta identificar pessoas pelo texto." /> : r.dado.jornadas.map((j) => <article key={j.referencia} className="border-b border-linha py-4"><h3 className="break-all font-mono text-xs">{j.referencia}</h3><div className={`${GRADE} my-4`}><Medida nome="Recontatos no período" valor={j.recontatos} /><div><p className="rotulo-instrumento">Canais</p><p className="mt-2 text-sm">{j.canais.join(" → ")}</p></div><div><p className="rotulo-instrumento">Resolução declarada · último contato</p><p className="mt-2 text-sm">{j.resolucao_declarada === null ? "Não informada" : j.resolucao_declarada ? "Confirmada pelo cliente" : "Não confirmada pelo cliente"}</p></div></div><ol>{j.contatos.map((c) => <li key={c.id} className={LINHA}><div className="min-w-0 flex-1"><p className="text-xs">{formatarDataHora(c.iniciada_em)} · {c.canal}</p><Caso id={c.id} sufixo={sufixo} /></div><NotaLED nota={c.nota} /><EtiquetaCategoria categoria={c.categoria} /></li>)}</ol></article>)}
  </Painel><Painel titulo="Vincular contatos"><form className={PILHA} onSubmit={(e) => { e.preventDefault(); void acao.executar("/jornadas", "POST", { referencia, conversa_ids: ids }, () => { r.recarregar(); setIds([]); }, "Contatos vinculados à jornada."); }}><Campo nome="Referência pseudônima"><Input required minLength={6} maxLength={80} pattern="[A-Za-z0-9_-]+" value={referencia} onChange={(e) => setReferencia(e.target.value)} placeholder="cliente_anonimo_001" /></Campo><p className="text-xs text-muted-foreground">Use uma chave externa anônima. Não informe nome, telefone, e-mail ou CPF.</p><SelecionarConversas conversas={conversas} selecionadas={ids} mudar={setIds} /><Button type="submit" disabled={acao.ocupado || !ids.length || ids.length > 50}><IconeDeAcao acao="vincular" />Vincular contatos</Button>{acao.feedback}</form></Painel></div>;
}
