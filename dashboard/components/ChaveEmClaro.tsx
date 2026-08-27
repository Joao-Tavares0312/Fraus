"use client";

import { useState } from "react";
import { Check, Copy } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";

/**
 * Uma credencial em claro, exibida AGORA ou nunca mais.
 *
 * A chave vive apenas no estado de quem renderiza este componente. Nada de
 * localStorage, sessionStorage ou URL -- ela tem que morrer quando a tela sai,
 * porque o servidor guarda so o hash e nao ha como reler. Guardar uma copia
 * "por conveniencia" no navegador desfaria exatamente a propriedade que faz o
 * banco vazado nao levar credencial junto.
 *
 * Existe como componente proprio porque sao DOIS os lugares que mostram
 * credencial dessa forma (chave de fonte em Integracoes, mestra e chave de
 * acesso em Configuracoes), e o aviso de "copie agora" e parte da credencial:
 * duas copias dele divergiriam, e a que divergisse seria a que promete menos.
 */
export function ChaveEmClaro({
  chave,
  titulo,
  children,
}: {
  chave: string;
  titulo: string;
  /** O que perder esta chave custa. Sempre concreto, nunca "guarde com segurança". */
  children: React.ReactNode;
}) {
  const [copiado, setCopiado] = useState(false);
  /**
   * A copia FALHOU, e o usuario precisa saber disso.
   *
   * `navigator.clipboard` so existe em contexto seguro: HTTPS ou localhost. Num
   * IP de LAN por HTTP -- o cenario que o proprio README descreve -- a promise
   * rejeita, e sem tratamento o botao ficava mudo. Aqui isso e pior do que em
   * qualquer outro lugar da dashboard: esta e a tela em que a credencial aparece
   * UMA vez, porque o servidor guarda so o hash. Botao mudo somado a "copie
   * agora" e uma chave perdida.
   */
  const [falhou, setFalhou] = useState(false);

  async function copiar() {
    try {
      await navigator.clipboard.writeText(chave);
      setCopiado(true);
      setFalhou(false);
    } catch {
      setFalhou(true);
    }
  }

  return (
    <Alert>
      <AlertTitle>{titulo}</AlertTitle>
      <AlertDescription>
        <div className="mb-2">{children}</div>
        <div className="flex flex-wrap items-center gap-2">
          <code className="num min-w-0 flex-1 overflow-x-auto rounded-sm bg-muted px-2 py-1.5 text-xs text-foreground">
            {chave}
          </code>
          <Button type="button" size="sm" variant="outline" onClick={copiar}>
            {copiado ? <Check aria-hidden /> : <Copy aria-hidden />}
            {copiado ? "Copiado" : "Copiar"}
          </Button>
        </div>
        {falhou ? (
          <p role="status" className="mt-2 max-w-[72ch] text-xs leading-relaxed">
            O navegador não deixou copiar — a área de transferência só funciona
            em HTTPS ou em <span className="num">localhost</span>.{" "}
            <strong>Selecione o valor acima e copie à mão antes de sair</strong>:
            ele não aparece de novo.
          </p>
        ) : null}
      </AlertDescription>
    </Alert>
  );
}
