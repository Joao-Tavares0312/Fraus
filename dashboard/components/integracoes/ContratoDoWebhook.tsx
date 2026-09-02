"use client";

import { useState } from "react";
import { Check, Copy } from "lucide-react";
import type { FonteIntegracao } from "@/lib/api";
import { Button } from "@/components/ui/button";

/** Copiar um trecho literal. A credencial NAO passa por aqui -- ela tem
 *  componente proprio (`ChaveEmClaro`), com o aviso de "copie agora" junto. */
function BotaoCopiar({ texto, rotulo }: { texto: string; rotulo: string }) {
  const [copiado, setCopiado] = useState(false);
  /**
   * `navigator.clipboard` so existe em contexto seguro (HTTPS ou localhost).
   * Num IP de LAN por HTTP a promise rejeita, e sem isto o botao ficava mudo.
   * O texto continua na tela ao lado, entao a saida e copiar a mao -- e a
   * mensagem precisa dizer isso, nao so "falhou".
   */
  const [falhou, setFalhou] = useState(false);

  async function copiar() {
    try {
      await navigator.clipboard.writeText(texto);
      setCopiado(true);
      setFalhou(false);
    } catch {
      setFalhou(true);
    }
  }

  return (
    <span className="flex shrink-0 flex-col items-end gap-1">
      <Button
        type="button"
        size="xs"
        variant="outline"
        onClick={copiar}
        className="shrink-0"
      >
        {copiado ? <Check aria-hidden /> : <Copy aria-hidden />}
        {copiado ? "Copiado" : rotulo}
      </Button>
      {falhou ? (
        <span role="status" className="text-[0.6875rem] text-muted-foreground">
          o navegador não deixou copiar fora de HTTPS — selecione o texto ao lado
        </span>
      ) : null}
    </span>
  );
}

/**
 * O CONTRATO que a plataforma precisa cumprir para entregar aqui.
 *
 * Substitui o `<details>` de `ChaveDaFonte.tsx`, que ensinava so o caminho de
 * `/ingestao` com chave `frs_`. Webhook e outra credencial: URL unica por fonte
 * e assinatura sobre o corpo, que e o padrao de mercado justamente porque
 * plataforma nenhuma deixa configurar cabecalho arbitrario.
 *
 * A ASSINATURA DO `curl` E UM MARCADOR, nao um valor. `<CALCULE_O_HMAC>` grita
 * que falta uma conta; um base64 de exemplo pareceria funcionar, seria colado
 * como esta e devolveria 401 -- e o integrador procuraria o defeito no segredo,
 * que estaria certo. Exemplo que parece funcionar e nao funciona custa mais que
 * exemplo nenhum.
 */
export function ContratoDoWebhook({
  fonte,
  base,
}: {
  fonte: FonteIntegracao;
  base: string;
}) {
  const url = `${base}/integracoes/webhook/${fonte.id}`;

  const exemplo = [
    `curl -X POST ${url} \\`,
    `  -H "webhook-id: msg_2f9a" \\`,
    `  -H "webhook-timestamp: 1756300000" \\`,
    `  -H "webhook-signature: v1,<CALCULE_O_HMAC>" \\`,
    `  -H "Content-Type: application/json" \\`,
    `  -d '{"id":"atendimento-123","mensagens":[`,
    `        {"autor":"cliente","texto":"meu pedido nao chegou","enviada_em":"2026-08-14T10:00:00-03:00"},`,
    `        {"autor":"bot","texto":"vou verificar","enviada_em":"2026-08-14T10:00:12-03:00"}`,
    `      ]}'`,
  ].join("\n");

  return (
    <div className="flex min-w-0 flex-col gap-4">
      <div className="flex min-w-0 flex-col gap-1.5">
        <p className="text-xs text-muted-foreground">
          A URL desta fonte — o canal ({fonte.canal}) é o dela, e quem manda o
          dado não escolhe onde ele é contabilizado.
        </p>
        <div className="flex flex-wrap items-center gap-2">
          <code className="num min-w-0 flex-1 overflow-x-auto rounded-sm bg-muted px-2 py-1.5 text-xs whitespace-nowrap text-foreground">
            {url}
          </code>
          <BotaoCopiar texto={url} rotulo="Copiar URL" />
        </div>
      </div>

      <div className="min-w-0 overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead>
            <tr className="border-b border-linha text-muted-foreground">
              <th className="py-1.5 pr-4 font-medium">Cabeçalho</th>
              <th className="py-1.5 font-medium">O que ele carrega</th>
            </tr>
          </thead>
          <tbody className="text-muted-foreground">
            <tr className="border-b border-compasso">
              <td className="num py-1.5 pr-4 whitespace-nowrap text-foreground">
                webhook-id
              </td>
              <td className="py-1.5">
                Identificador do evento. É por ele que a reentrega é reconhecida
                e não vira atendimento em dobro.
              </td>
            </tr>
            <tr className="border-b border-compasso">
              <td className="num py-1.5 pr-4 whitespace-nowrap text-foreground">
                webhook-timestamp
              </td>
              <td className="py-1.5">
                Segundos desde a época, em UTC. Fora de 5 min do relógio do
                servidor, a entrega é recusada — é o que faz uma captura da rede
                expirar.
              </td>
            </tr>
            <tr>
              <td className="num py-1.5 pr-4 whitespace-nowrap text-foreground">
                webhook-signature
              </td>
              <td className="py-1.5">
                <code className="num text-foreground">v1,&lt;base64&gt;</code> do
                HMAC-SHA256 de{" "}
                <code className="num text-foreground">
                  {"{id}.{timestamp}.{corpo}"}
                </code>
                , com a chave sendo o base64 <em>decodificado</em> do segredo
                <code className="num text-foreground"> whsec_…</code>. O corpo
                entra byte a byte, exatamente como foi enviado.
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div className="flex min-w-0 flex-col gap-1.5">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-xs text-muted-foreground">
            Uma entrega completa, com o formato do corpo:
          </p>
          <BotaoCopiar texto={exemplo} rotulo="Copiar curl" />
        </div>
        <pre className="num min-w-0 overflow-x-auto rounded-sm bg-muted p-3 text-[11px] leading-relaxed text-foreground">
          {exemplo}
        </pre>
        <p className="text-xs leading-relaxed text-muted-foreground">
          <code className="num text-foreground">&lt;CALCULE_O_HMAC&gt;</code> é
          marcador, não valor: a assinatura depende do corpo exato e do segredo
          de quem chama, então nenhum exemplo aqui serviria colado. Score, nota e
          categoria são derivados no servidor e ignorados se vierem no corpo.
        </p>
      </div>

      <p className="text-xs leading-relaxed text-muted-foreground">
        Os três cabeçalhos seguem o{" "}
        <a
          href="https://www.standardwebhooks.com/"
          target="_blank"
          rel="noreferrer"
          className="text-foreground underline underline-offset-2 outline-none focus-visible:ring-2 focus-visible:ring-ring"
        >
          Standard Webhooks
        </a>
        , e é por isso que eles não são nossos: com o padrão, quem integra
        assina com biblioteca de prateleira em vez de implementar HMAC lendo esta
        tela.
      </p>

      {/* A ressalva honesta, uma vez so. Ela existe porque a alternativa e
          deixar alguem apontar o webhook do provedor dele direto para ca e
          descobrir o desencontro pelo 400. */}
      <p className="border-t border-compasso pt-2 text-xs leading-relaxed text-muted-foreground">
        O Fraus recebe eventos <strong>neste contrato documentado</strong>. Não
        há adaptador para nenhuma plataforma nomeada: traduzir o formato de
        eventos da plataforma para o corpo acima é trabalho de quem integra.
      </p>
    </div>
  );
}
