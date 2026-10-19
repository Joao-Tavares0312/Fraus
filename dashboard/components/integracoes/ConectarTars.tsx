"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Bot, KeyRound } from "lucide-react";
import { criarFonte, gerarChave, type FonteIntegracao } from "@/lib/api";
import { fonteDoTars, urlDeIngestao } from "@/lib/tars";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { ChaveEmClaro } from "@/components/ChaveEmClaro";

/**
 * Conectar o TARS em dois cliques (19/10/2026).
 *
 * O TARS manda cada conversa para `POST /ingestao` com a chave da fonte, e o
 * Fraus pontua no servidor como em qualquer entrada. A tela só cria a fonte,
 * gera a chave (mostrada uma única vez) e diz o que colar do lado do TARS.
 */
export function ConectarTars({ fontes, baseDaApi }: {
  fontes: FonteIntegracao[];
  baseDaApi: string;
}) {
  const roteador = useRouter();
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [chave, setChave] = useState<string | null>(null);
  const fonte = fonteDoTars(fontes);
  const url = urlDeIngestao(baseDaApi);

  async function conectar() {
    setOcupado(true);
    setErro(null);
    let alvo = fonte;
    if (!alvo) {
      const criada = await criarFonte({ nome: "TARS", canal: "tars", tipo: "webhook" });
      if (!criada.ok) {
        setOcupado(false);
        setErro(criada.erro);
        return;
      }
      alvo = criada.dado;
    }
    const gerada = await gerarChave(alvo.id);
    setOcupado(false);
    if (!gerada.ok) {
      setErro(gerada.erro);
      return;
    }
    setChave(gerada.dado.chave);
    roteador.refresh();
  }

  return (
    <div className="flex flex-col gap-4 px-5 py-4">
      <div className="flex items-start gap-3">
        <span aria-hidden className="flex size-9 shrink-0 items-center justify-center rounded-md bg-muted">
          <Bot className="size-4" />
        </span>
        <div className="flex min-w-0 flex-col gap-1">
          <p className="text-sm font-medium">
            {fonte?.chave_dica
              ? `Conectado — chave terminando em ${fonte.chave_dica}`
              : "Ainda não conectado"}
          </p>
          <p className="max-w-[72ch] text-sm text-muted-foreground">
            Cada conversa do TARS chega aqui depois de cada resposta do bot e
            entra nos indicadores com o canal <span className="num">tars</span>.
            Reenviar a mesma conversa atualiza o atendimento, não duplica.
          </p>
        </div>
      </div>

      {chave ? (
        <ChaveEmClaro chave={chave} titulo="Chave do TARS">
          Cole esta chave no TARS, em Integrações → Fraus. Ela não aparece de
          novo; se perder, gere outra — a anterior deixa de valer.
        </ChaveEmClaro>
      ) : null}

      <dl className="grid gap-1 text-sm sm:grid-cols-[10rem_1fr]">
        <dt className="text-muted-foreground">Endereço no TARS</dt>
        <dd className="num break-all">{url}</dd>
      </dl>

      {erro ? (
        <Alert variant="destructive">
          <AlertDescription>{erro}</AlertDescription>
        </Alert>
      ) : null}

      <div>
        <Button type="button" onClick={conectar} disabled={ocupado}>
          <KeyRound aria-hidden />
          {ocupado
            ? "Gerando…"
            : fonte?.chave_dica
              ? "Gerar nova chave"
              : "Conectar o TARS"}
        </Button>
      </div>
    </div>
  );
}
