"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { MarcaFraus } from "@/components/shell/MarcaFraus";
import { Button } from "@/components/ui/button";
import { entrarNoGrupo, mensagemDoGrupo, type ResultadoDoGrupo } from "@/lib/anotacao";

type Falha = Exclude<ResultadoDoGrupo, { tipo: "pessoal" }>;

/**
 * Link de grupo: troca o link compartilhado pelo link PESSOAL desta pessoa e
 * segue para ele. A regra (guardar, nao gastar vaga duas vezes, traduzir o
 * status) mora em `lib/anotacao.ts`; aqui so se liga ao roteador.
 */
export function EntrarNoGrupo({ token }: { token: string }) {
  const roteador = useRouter();
  const [falha, setFalha] = useState<Falha | null>(null);
  const [tentativa, setTentativa] = useState(0);

  useEffect(() => {
    let vivo = true;
    void entrarNoGrupo(token).then((r) => {
      if (!vivo) return;
      if (r.tipo === "pessoal") roteador.replace(`/anotar/${r.token}`);
      else setFalha(r);
    });
    return () => { vivo = false; };
  }, [token, roteador, tentativa]);

  const podeTentarDeNovo = falha && (falha.tipo === "rede" || falha.tipo === "limite" || falha.tipo === "erro");

  return (
    <main className="mx-auto flex min-h-svh w-full max-w-2xl flex-col gap-5 px-4 py-6 sm:py-10">
      <header className="flex items-center gap-2.5">
        <MarcaFraus tamanho={24} />
        <span className="rotulo-instrumento text-foreground">Fraus · anotação</span>
      </header>
      {falha ? (
        <section className="flex flex-col items-start gap-3 border border-linha bg-card p-5" role="alert">
          <p className="text-sm">{mensagemDoGrupo(falha)}</p>
          {podeTentarDeNovo ? (
            <Button variant="outline" onClick={() => { setFalha(null); setTentativa((n) => n + 1); }}>Tentar de novo</Button>
          ) : null}
        </section>
      ) : (
        <p className="text-sm text-muted-foreground">Preparando o seu link…</p>
      )}
    </main>
  );
}
