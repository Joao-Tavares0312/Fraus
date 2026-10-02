"use client";

import { useState } from "react";
import { KeyRound, Trash2 } from "lucide-react";
import { gerarChave, revogarChave, type FonteIntegracao } from "@/lib/api";
import { formatarDataHora } from "@/lib/formato";
import { ChaveEmClaro } from "@/components/ChaveEmClaro";
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
  aoMudarChave,
}: {
  fonte: FonteIntegracao;
  base: string;
  /**
   * Recarrega a lista do PAI depois de gerar ou revogar.
   *
   * Obrigatorio, e nao um `router.refresh()` aqui dentro: a lista de fontes e
   * estado do pai, semeado uma vez, e o refresh do servidor nao a reescreve.
   * Sem isto, gerar a chave da fonte A, abrir a B e voltar para a A remontava
   * este componente (o `key` do painel) com a `fonte` de antes -- "Sem chave" e
   * o botao "Gerar chave" sobre uma chave ATIVA no servidor, e um clique ali
   * invalidava a credencial ja entregue ao integrador.
   */
  aoMudarChave: () => void | Promise<void>;
}) {
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [chave, setChave] = useState<string | null>(null);

  /**
   * Dica da chave vigente, com o que ACABOU de acontecer tendo precedencia.
   *
   * `undefined` significa "ainda nao mexi, vale o que veio do servidor";
   * `null` significa "revoguei agora". A distincao cobre o intervalo ate o
   * pai terminar de recarregar a lista (`aoMudarChave`): nesse meio tempo a
   * prop `fonte` ainda e a de antes, e sem isto a tela exibia "Sem chave: esta
   * fonte ainda nao recebe atendimento pela rede" logo abaixo da chave recem
   * gerada -- duas afirmacoes contrarias na mesma linha. Ela NAO sobrevive a
   * remontagem; quem sobrevive e a lista do pai, e por isso o pai e avisado.
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
    void aoMudarChave();
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
    void aoMudarChave();
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

      {/* A chave em claro: aparece agora ou nunca mais. Mesmo componente que
          exibe a mestra em Configuracoes -- o aviso de "copie agora" e parte da
          credencial, e duas copias dele divergiriam. */}
      {chave ? (
        <ChaveEmClaro
          chave={chave}
          titulo="Copie agora — esta chave não pode ser lida de novo"
        >
          <p>
            O servidor guarda apenas o hash dela. Se você perder, o conserto é
            gerar outra — e a de agora para de funcionar.
          </p>
        </ChaveEmClaro>
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
