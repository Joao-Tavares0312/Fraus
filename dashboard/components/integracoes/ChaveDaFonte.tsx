"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Check, Copy, KeyRound, Trash2 } from "lucide-react";
import { gerarChave, revogarChave, type FonteIntegracao } from "@/lib/api";
import { formatarDataHora } from "@/lib/formato";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";

/**
 * Chave de API de uma fonte: gerar, exibir UMA vez, revogar.
 *
 * A chave em claro vive apenas no estado deste componente. Nada de
 * localStorage, sessionStorage ou URL -- ela tem que morrer quando a tela sai,
 * porque o servidor guarda so o hash e nao ha como reler. Guardar uma copia
 * "por conveniencia" no navegador desfaria exatamente a propriedade que faz o
 * banco vazado nao levar credencial junto.
 */
export function ChaveDaFonte({
  fonte,
  base,
}: {
  fonte: FonteIntegracao;
  base: string;
}) {
  const router = useRouter();
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [chave, setChave] = useState<string | null>(null);
  const [copiado, setCopiado] = useState(false);

  /**
   * Dica da chave vigente, com o que ACABOU de acontecer tendo precedencia.
   *
   * `undefined` significa "ainda nao mexi, vale o que veio do servidor";
   * `null` significa "revoguei agora". A distincao e necessaria porque a lista
   * de fontes vive em estado do componente pai, semeado uma vez: `router.
   * refresh()` revalida o servidor mas nao reescreve esse estado, entao a prop
   * `fonte` continua a de antes. Sem isto, a tela exibia "Sem chave: esta
   * fonte ainda nao recebe atendimento pela rede" logo abaixo da chave recem
   * gerada -- duas afirmacoes contrarias na mesma linha.
   */
  const [dicaLocal, setDicaLocal] = useState<string | null | undefined>(
    undefined,
  );
  const dica = dicaLocal === undefined ? fonte.chave_dica : dicaLocal;

  async function gerar() {
    setOcupado(true);
    setErro(null);
    const resposta = await gerarChave(fonte.id);
    setOcupado(false);
    if (!resposta.ok) {
      setErro(resposta.erro);
      return;
    }
    setChave(resposta.dado.chave);
    setDicaLocal(resposta.dado.fonte.chave_dica);
    setCopiado(false);
    router.refresh();
  }

  async function revogar() {
    setOcupado(true);
    setErro(null);
    const resposta = await revogarChave(fonte.id);
    setOcupado(false);
    if (!resposta.ok) {
      setErro(resposta.erro);
      return;
    }
    setChave(null);
    setDicaLocal(null);
    router.refresh();
  }

  async function copiar() {
    if (!chave) return;
    await navigator.clipboard.writeText(chave);
    setCopiado(true);
  }

  const exemplo = [
    `curl -X POST ${base}/ingestao \\`,
    `  -H "Authorization: Bearer ${chave ?? "SUA_CHAVE"}" \\`,
    `  -H "Content-Type: application/json" \\`,
    `  -d '{"id":"atendimento-123","mensagens":[`,
    `        {"autor":"cliente","texto":"meu pedido nao chegou","enviada_em":"2026-08-14T10:00:00-03:00"},`,
    `        {"autor":"bot","texto":"vou verificar","enviada_em":"2026-08-14T10:00:12-03:00"}`,
    `      ]}'`,
  ].join("\n");

  return (
    <div className="flex flex-col gap-3">
      {erro ? (
        <Alert variant="destructive">
          <AlertTitle>Não foi possível</AlertTitle>
          <AlertDescription>{erro}</AlertDescription>
        </Alert>
      ) : null}

      {/* A chave em claro: aparece agora ou nunca mais. */}
      {chave ? (
        <Alert>
          <AlertTitle>Copie agora — esta chave não pode ser lida de novo</AlertTitle>
          <AlertDescription>
            <p className="mb-2">
              O servidor guarda apenas o hash dela. Se você perder, o conserto é
              gerar outra — e a de agora para de funcionar.
            </p>
            <div className="flex flex-wrap items-center gap-2">
              <code className="num min-w-0 flex-1 overflow-x-auto rounded-sm bg-muted px-2 py-1.5 text-xs text-foreground">
                {chave}
              </code>
              <Button type="button" size="sm" variant="outline" onClick={copiar}>
                {copiado ? <Check aria-hidden /> : <Copy aria-hidden />}
                {copiado ? "Copiado" : "Copiar"}
              </Button>
            </div>
          </AlertDescription>
        </Alert>
      ) : null}

      <div className="flex flex-wrap items-center gap-3">
        <Button type="button" size="sm" variant="outline" onClick={gerar} disabled={ocupado}>
          <KeyRound aria-hidden />
          {dica ? "Gerar outra chave" : "Gerar chave"}
        </Button>

        {dica ? (
          <>
            <span className="num text-xs text-muted-foreground">
              chave ativa termina em {dica}
              {/* A data so vale para a chave que veio do servidor: a que
                  acabou de nascer e "agora", e exibir o horario antigo ao lado
                  dela mentiria sobre quando ela passou a valer. */}
              {dicaLocal === undefined && fonte.chave_criada_em
                ? ` · criada em ${formatarDataHora(fonte.chave_criada_em)}`
                : null}
            </span>
            <Button
              type="button"
              size="sm"
              variant="ghost"
              onClick={revogar}
              disabled={ocupado}
            >
              <Trash2 aria-hidden />
              Revogar
            </Button>
          </>
        ) : (
          <span className="text-xs text-muted-foreground">
            Sem chave: esta fonte ainda não recebe atendimento pela rede.
          </span>
        )}
      </div>

      {dica ? (
        <details className="text-xs text-muted-foreground">
          <summary className="cursor-pointer">Como mandar um atendimento</summary>
          <pre className="num mt-2 overflow-x-auto rounded-sm bg-muted p-3 text-[11px] leading-relaxed text-foreground">
            {exemplo}
          </pre>
          <p className="mt-2">
            O <strong>canal</strong> é o desta fonte ({fonte.canal}) — quem manda
            o dado não escolhe onde ele é contabilizado. Score, nota e categoria
            são derivados no servidor e ignorados se vierem no corpo. Desativar a
            fonte aqui recusa a ingestão com 403, sem precisar revogar a chave.
          </p>
        </details>
      ) : null}
    </div>
  );
}
