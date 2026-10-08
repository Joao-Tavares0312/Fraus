"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { MarcaFraus } from "@/components/shell/MarcaFraus";
import { Button } from "@/components/ui/button";
import {
  carregarFila,
  enviarResposta,
  estadoDaFila,
  faltam,
  fila,
  respostaDaTecla,
  type EstadoDaFila,
  type Resposta,
} from "@/lib/anotacao";

const OPCOES: { resposta: Resposta; tecla: string; rotulo: string }[] = [
  { resposta: "ironico", tecla: "1", rotulo: "Irônico" },
  { resposta: "nao_ironico", tecla: "2", rotulo: "Não irônico" },
  { resposta: "contexto", tecla: "3", rotulo: "Depende do contexto" },
];

type Tela = { tipo: "carregando" } | { tipo: "invalido" } | { tipo: "limite" } | { tipo: "erro" } | { tipo: "fila" };

/**
 * Anotacao da regua de ironia, as cegas, uma frase por vez. Tela de tarefa:
 * sem navegacao, sem ids, sem nada alem do texto da frase. Toda a regra de
 * avanco mora em `lib/anotacao.ts`; aqui so se liga ao DOM.
 */
export function AnotarIronia({ token }: { token: string }) {
  const [tela, setTela] = useState<Tela>({ tipo: "carregando" });
  const [estado, setEstado] = useState<EstadoDaFila | null>(null);
  // A fonte da verdade e a ref: o handler de teclado e o de clique leem o
  // estado de AGORA, nao o do render em que foram criados.
  const ref = useRef<EstadoDaFila | null>(null);
  const aplicar = useCallback((e: EstadoDaFila) => { ref.current = e; setEstado(e); }, []);

  const [tentativa, setTentativa] = useState(0);
  useEffect(() => {
    let vivo = true;
    void carregarFila(token).then((c) => {
      if (!vivo) return;
      if (c.tipo !== "ok") return setTela({ tipo: c.tipo });
      aplicar(estadoDaFila(c.frases, c.respostas));
      setTela({ tipo: "fila" });
    });
    return () => { vivo = false; };
  }, [token, aplicar, tentativa]);

  const responder = useCallback(async (resposta: Resposta) => {
    const atual = ref.current;
    if (!atual || !fila(atual).podeResponder) return;
    const frase = atual.frases[atual.pos];
    aplicar(fila(atual).enviar());
    const r = await enviarResposta(token, frase.id, resposta);
    aplicar(r.ok ? fila(ref.current!).sucesso(frase.id, resposta) : fila(ref.current!).falha(r.falha));
  }, [token, aplicar]);

  const voltar = useCallback(() => { if (ref.current) aplicar(fila(ref.current).voltar()); }, [aplicar]);

  useEffect(() => {
    if (tela.tipo !== "fila") return;
    const aoTecla = (ev: KeyboardEvent) => {
      const r = respostaDaTecla(ev);
      if (!r) return;
      ev.preventDefault();
      void responder(r);
    };
    document.addEventListener("keydown", aoTecla);
    return () => document.removeEventListener("keydown", aoTecla);
  }, [tela.tipo, responder]);

  return (
    <main className="mx-auto flex min-h-svh w-full max-w-2xl flex-col gap-5 px-4 py-6 sm:py-10">
      <header className="flex items-center gap-2.5">
        <MarcaFraus tamanho={24} />
        <span className="rotulo-instrumento text-foreground">Fraus · anotação</span>
      </header>
      {tela.tipo === "carregando" ? <p className="text-sm text-muted-foreground">Carregando as frases…</p> : null}
      {tela.tipo === "invalido" ? (
        <section className="border border-linha bg-card p-5">
          <h1 className="titulo-instrumento text-lg">Link inválido ou revogado</h1>
        </section>
      ) : null}
      {tela.tipo === "limite" ? (
        <section className="flex flex-col items-start gap-3 border border-linha bg-card p-5" role="alert">
          <p className="text-sm">Muitas tentativas seguidas. Aguarde alguns segundos e recarregue a página.</p>
          <Button variant="outline" onClick={() => { setTela({ tipo: "carregando" }); setTentativa((n) => n + 1); }}>Tentar de novo</Button>
        </section>
      ) : null}
      {tela.tipo === "erro" ? (
        <section className="flex flex-col items-start gap-3 border border-linha bg-card p-5" role="alert">
          <p className="text-sm">Não consegui carregar as frases. Suas respostas anteriores continuam guardadas.</p>
          <Button variant="outline" onClick={() => { setTela({ tipo: "carregando" }); setTentativa((n) => n + 1); }}>Tentar de novo</Button>
        </section>
      ) : null}
      {tela.tipo === "fila" && estado ? <Fila estado={estado} responder={responder} voltar={voltar} /> : null}
    </main>
  );
}

export function Fila({ estado, responder, voltar }: { estado: EstadoDaFila; responder: (r: Resposta) => void; voltar: () => void }) {
  const f = fila(estado);
  const total = estado.frases.length;
  const feitas = total - faltam(estado);
  const atual = f.fim ? null : estado.frases[estado.pos];

  if (f.fim) {
    return (
      <section className="flex flex-col items-start gap-4 border border-linha bg-card p-5">
        <h1 className="titulo-instrumento text-xl leading-snug">Obrigado — suas {feitas} respostas foram salvas.</h1>
        <Button variant="outline" onClick={voltar}>← Voltar e mudar a última resposta</Button>
      </section>
    );
  }

  return (
    <>
      <p className="max-w-[65ch] text-sm text-muted-foreground">
        Ironia aqui é dizer o contrário do que se quer dizer, em tom de crítica ou zombaria. &quot;Depende do contexto&quot; é resposta válida, não falha.
      </p>
      <p className="-mt-3 text-xs text-muted-foreground">Para continuar em outro aparelho, guarde o endereço desta página.</p>
      {estado.erro ? <p role="alert" className="border border-destructive/60 bg-destructive/10 px-3.5 py-3 text-sm text-destructive">{estado.erro}</p> : null}
      <section className="flex flex-col gap-5">
        <div className="flex min-h-9 items-center justify-between gap-3">
          <span aria-live="polite" className="rotulo-instrumento tabular-nums text-foreground">
            {faltam(estado) === 1 ? "Falta 1" : `Faltam ${faltam(estado)}`}
          </span>
          {estado.pos > 0 ? (
            <Button
              variant="ghost"
              // aria-disabled e clique ignorado, como as respostas: `disabled`
              // tiraria o foco do teclado a cada envio.
              aria-disabled={estado.enviando}
              onClick={() => { if (!estado.enviando) voltar(); }}
              className="h-9 px-3 aria-disabled:opacity-60"
            >
              ← Voltar
            </Button>
          ) : null}
        </div>
        <div className="h-1 bg-compasso" aria-hidden="true"><div className="h-full bg-primary" style={{ width: `${(100 * feitas) / total}%` }} /></div>
        <div className="flex min-h-40 items-center border border-linha bg-card px-5 py-7 sm:px-6">
          <p aria-live="polite" className="min-w-0 text-balance text-2xl leading-snug [overflow-wrap:anywhere] sm:text-3xl">{atual?.texto}</p>
        </div>
        <div className="grid gap-2.5">
          {OPCOES.map((o) => {
            const marcada = atual ? estado.respostas[atual.id] === o.resposta : false;
            return (
              <Button
                key={o.resposta}
                variant={marcada ? "default" : "outline"}
                // aria-disabled, e nao disabled: o foco do teclado nao pode
                // sumir a cada envio.
                aria-disabled={estado.enviando || estado.encerrada}
                onClick={() => { if (!estado.enviando && !estado.encerrada) responder(o.resposta); }}
                className="h-auto min-h-14 justify-start gap-3 px-4 py-3 text-sm aria-disabled:opacity-60"
              >
                <kbd className="grid size-7 shrink-0 place-items-center border border-current/40 font-mono text-xs">{o.tecla}</kbd>
                {o.rotulo}
              </Button>
            );
          })}
        </div>
      </section>
    </>
  );
}
