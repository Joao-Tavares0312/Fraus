"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Trash2 } from "lucide-react";
import { removerConversa } from "@/lib/api";
import { anunciarAtualizacao } from "@/lib/atualizacao";
import { Button } from "@/components/ui/button";

/**
 * Remove o atendimento gravado — só aparece para `dev`, e a API confere de novo.
 *
 * Existe para limpar o que nunca deveria ter entrado (um atendimento datado de
 * 2243, duplicatas de teste). Dois cliques de propósito: some dos indicadores
 * de todo mundo e não tem desfazer.
 */
export function RemoverAtendimento({ id, voltarPara }: { id: string; voltarPara: string }) {
  const roteador = useRouter();
  const [confirmando, setConfirmando] = useState(false);
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  async function remover() {
    setOcupado(true);
    setErro(null);
    const resposta = await removerConversa(id);
    if (!resposta.ok) {
      setOcupado(false);
      setErro(resposta.erro);
      return;
    }
    anunciarAtualizacao();
    roteador.push(voltarPara);
    roteador.refresh();
  }

  if (!confirmando) {
    return (
      <Button type="button" size="sm" variant="outline" onClick={() => setConfirmando(true)}>
        <Trash2 aria-hidden />
        Remover atendimento
      </Button>
    );
  }

  return (
    <span className="flex flex-wrap items-center gap-2" role="group" aria-label="Confirmar remoção">
      <span className="text-xs text-muted-foreground">Sai dos indicadores e não tem desfazer.</span>
      <Button type="button" size="sm" variant="destructive" onClick={remover} disabled={ocupado}>
        {ocupado ? "Removendo…" : "Confirmar remoção"}
      </Button>
      <Button type="button" size="sm" variant="ghost" onClick={() => setConfirmando(false)} disabled={ocupado}>
        Cancelar
      </Button>
      {erro ? <span className="text-xs text-destructive" role="alert">{erro}</span> : null}
    </span>
  );
}
