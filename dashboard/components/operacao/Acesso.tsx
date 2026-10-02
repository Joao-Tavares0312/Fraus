"use client";

import { useState } from "react";
import { minutosRestantesDeExportacao, TETO_MINUTOS_EXPORTACAO, type Acesso, type UsuarioAcesso } from "@/lib/operacao";
import { formatarDataHora } from "@/lib/formato";
import { Painel } from "@/components/Painel";
import { Button } from "@/components/ui/button";
import { CAMPO, Campo, Carregamento, GRADE, LINHA, Medida, Numero, PILHA, useAcao, useRecurso } from "./comum";
import { IconeDeAcao } from "@/components/IconeDeAcao";

export function AcessoOperacao() {
  const r = useRecurso<Acesso>("/acesso");
  const [selecionado, setSelecionado] = useState<number | null>(null);
  const usuario = r.dado?.usuarios.find((u) => u.id === selecionado);
  return <div className={PILHA}><Painel titulo="Mapa de alcance de acesso" nivel="dominante" legenda={r.dado?.aviso}>
    {!r.dado ? <Carregamento erro={r.erro} recarregar={r.recarregar} /> : <div className={PILHA}><p className="text-sm text-muted-foreground">Selecione uma conta para simular quais canais ela alcançaria em caso de comprometimento. O alcance considera seu papel, estado ativo e política atual.</p>
      <div className={GRADE}><Medida nome="Contas ativas" valor={r.dado.usuarios.filter((u) => u.ativo).length} /><Medida nome="Canais no banco" valor={r.dado.canais.length} /><div><p className="rotulo-instrumento">Modo de autenticação técnica</p><p className="mt-3 text-sm">{r.dado.modo === "autenticado" ? "Chave administrativa configurada" : "Instalação local sem chave administrativa"}</p></div></div>
      <Campo nome="Conta para simular"><select className={CAMPO} value={selecionado ?? ""} onChange={(e) => setSelecionado(e.target.value === "" ? null : Number(e.target.value))}><option value="">Selecione uma conta</option>{r.dado.usuarios.map((u) => <option key={u.id} value={u.id}>{u.nome} · {u.papel} · {u.ativo ? "ativa" : "desativada"}</option>)}</select></Campo>
      {usuario ? <><div className="grid gap-4 border-y border-linha py-5 sm:grid-cols-[1fr_2fr]"><div className="flex items-center justify-center border border-linha p-5"><span className="break-words font-mono text-xs">{usuario.nome}</span></div><div className="flex flex-col gap-3">{r.dado.canais.map((c) => <div key={c} className={`border-l-2 pl-4 text-sm ${usuario.canais.includes(c) ? "border-medido text-medido-texto" : "border-linha text-muted-foreground"}`}><span aria-hidden>{usuario.canais.includes(c) ? "→ " : "× "}</span>{c} · {usuario.canais.includes(c) ? "Acesso permitido" : "Acesso bloqueado"}</div>)}</div></div><Politica key={usuario.id} usuario={usuario} acesso={r.dado} recarregar={r.recarregar} /></> : null}
      <div className="overflow-x-auto"><table className="w-full text-left text-xs"><caption className="mb-3 text-left rotulo-instrumento">Políticas atuais</caption><thead><tr className="border-b border-linha"><th className="p-3">Conta</th><th className="p-3">Papel / estado</th><th className="p-3">Canais acessíveis</th><th className="p-3">Exportação</th></tr></thead><tbody>{r.dado.usuarios.map((u) => <tr key={u.id} className="border-b border-border"><td className="p-3"><Button variant="ghost" onClick={() => setSelecionado(u.id)}>{u.nome}</Button></td><td className="p-3">{u.papel} · {u.ativo ? "ativa" : "desativada"}</td><td className="p-3">{u.canais.join(", ") || "Nenhum"}{!u.configurado && u.papel !== "dev" ? " · acesso anterior preservado" : ""}</td><td className="p-3">{u.exportacao_liberada ? u.papel === "dev" ? "Administrativa" : `Até ${formatarDataHora(u.exporta_ate!)}` : "Bloqueada"}</td></tr>)}</tbody></table></div>
    </div>}
  </Painel><Painel titulo="Trilha de auditoria" legenda={r.dado?.auditoria.metodo}>
    {!r.dado ? <Carregamento erro={r.erro} recarregar={r.recarregar} /> : <div className={PILHA}><div className={GRADE}><Medida nome="Eventos registrados" valor={r.dado.auditoria.total} /><div><p className="rotulo-instrumento">Integridade da cadeia</p><p role="status" className={`mt-3 text-sm ${r.dado.auditoria.integra ? "text-foreground" : "text-destructive"}`}>{r.dado.auditoria.integra ? "Encadeamento válido" : "Alteração detectada"}</p></div></div><p className="text-xs text-muted-foreground">Últimos 200 eventos. A cadeia detecta alterações parciais; não protege contra reescrita integral por quem controla o banco.</p><ol>{r.dado.auditoria.eventos.toReversed().map((e, i) => <li key={i} className={LINHA}><span className="text-xs text-muted-foreground">{formatarDataHora(e.em)}</span><span className="break-all font-mono text-xs">{e.acao} · ator {e.ator} · {e.recurso}</span></li>)}</ol></div>}
  </Painel></div>;
}

function Politica({ usuario, acesso, recarregar }: { usuario: UsuarioAcesso; acesso: Acesso; recarregar: () => void }) {
  const [canais, setCanais] = useState(usuario.canais), [equipe, setEquipe] = useState(usuario.equipe_id ?? "");
  // A JANELA DE EXPORTACAO SO MUDA SE ALGUEM MEXER NELA. A rota so aceita
  // `exportar_minutos` e grava `exporta_ate: None` quando vem 0 -- nao ha como
  // dizer "nao mexa". O campo nascia em 0 e era sempre enviado: editar so os
  // canais de uma conta encerrava a exportacao dela. `minutos === null` e "nao
  // mexi"; nesse caso vai o que RESTA da janela, recalculado no envio (o
  // formulario pode ficar aberto minutos, e o valor da montagem a esticaria).
  // `exportaAte` e `restantes` sao estado, e nao leitura direta da prop, porque
  // a `key` deste componente e so o id (ver acima): quem os atualiza depois de
  // aplicar e a propria resposta do PUT.
  const [exportaAte, setExportaAte] = useState(usuario.exporta_ate);
  const [restantes, setRestantes] = useState(() => minutosRestantesDeExportacao(usuario.exporta_ate, Date.now()));
  const [minutos, setMinutos] = useState<number | null>(null);
  const acao = useAcao(), revogar = useAcao();
  const [confirmarRevogacao, setConfirmarRevogacao] = useState(false);
  const aplicada = (politica: { exporta_ate: string | null }) => { setExportaAte(politica.exporta_ate); setRestantes(minutosRestantesDeExportacao(politica.exporta_ate, Date.now())); setMinutos(null); recarregar(); };
  return <div className={PILHA}>{usuario.papel !== "dev" ? <form className={PILHA} onSubmit={(e) => { e.preventDefault(); void acao.executar(`/acesso/${usuario.id}`, "PUT", { canais, equipe_id: equipe || null, exportar_minutos: minutos ?? minutosRestantesDeExportacao(exportaAte, Date.now()) }, aplicada, "Política aplicada. O próximo acesso já usará este escopo."); }}>
    <fieldset><legend className="rotulo-instrumento mb-3">Canais permitidos</legend>{acesso.canais.map((c) => <label key={c} className="mr-5 inline-flex items-center gap-2 text-sm"><input type="checkbox" checked={canais.includes(c)} onChange={(e) => setCanais(e.target.checked ? [...canais, c] : canais.filter((v) => v !== c))} />{c}</label>)}</fieldset>
    <div className={GRADE}><Numero nome="Liberar exportação · minutos" valor={minutos ?? restantes} aoMudar={setMinutos} max={TETO_MINUTOS_EXPORTACAO} /><Campo nome="Equipe da política"><select className={CAMPO} value={equipe} onChange={(e) => setEquipe(e.target.value)}><option value="">Sem equipe</option>{acesso.equipes.map((t) => <option key={t.id} value={t.id}>{t.nome}</option>)}</select></Campo></div><p className="text-xs text-muted-foreground">O campo abre com os minutos que restam da janela atual; sem mexer nele, a janela é mantida. Zero minutos bloqueia a exportação. Nenhum canal selecionado bloqueia o acesso a todas as conversas. A associação de equipe não altera permissões por conta própria.</p><Button type="submit" disabled={acao.ocupado}><IconeDeAcao acao="confirmar" />Aplicar política</Button>{acao.feedback}
  </form> : <p className="text-sm text-muted-foreground">Contas dev têm acesso administrativo. O escopo por canal vale para contas usuario.</p>}
    <div className="border-t border-linha pt-4">{confirmarRevogacao ? <div className={PILHA}><p className="text-sm">Encerrar todas as sessões atuais de {usuario.nome}? A conta poderá entrar novamente com sua senha.</p><div className="flex gap-3"><Button disabled={revogar.ocupado} onClick={() => void revogar.executar(`/acesso/${usuario.id}/revogar-sessoes`, "POST", undefined, () => { setConfirmarRevogacao(false); recarregar(); }, "Sessões revogadas imediatamente.")}><IconeDeAcao acao="sair" />Encerrar sessões</Button><Button variant="ghost" onClick={() => setConfirmarRevogacao(false)}><IconeDeAcao acao="cancelar" />Cancelar</Button></div></div> : <Button variant="outline" onClick={() => setConfirmarRevogacao(true)}><IconeDeAcao acao="sair" />Revogar sessões desta conta</Button>}{revogar.feedback}</div>
  </div>;
}
