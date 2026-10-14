import type { RegraSinalizador, Sinalizador } from "@/lib/api";

/**
 * Sinalizadores por regra (E5): o que disparou nesta conversa, com o detalhe
 * escrito pelo servidor (que traz o limiar). Marca e informa, não corrige: a
 * nota continua a mesma e o atendimento continua no NPS.
 *
 * `null` é NÃO AVALIADO (sem fala do cliente) e tem frase própria; `[]` é
 * "nada disparou". Confundir os dois faria ausência de dado parecer conversa
 * limpa (invariante 2).
 *
 * Sem estado e sem efeito: sai inteiro do markup do servidor, como a
 * `MarcaContestacao`.
 */
export const ROTULO_SINALIZADOR: Record<RegraSinalizador, string> = {
  loop_do_bot: "Loop do bot",
  cliente_repete: "Cliente repete",
  pedido_de_humano_ignorado: "Pedido de humano ignorado",
  escalada_tardia: "Escalada tardia",
  abandono: "Abandono",
};

function listaDeMensagens(evidencia: number[]): string {
  const n = evidencia.map((i) => String(i + 1));
  if (n.length === 1) return `mensagem ${n[0]}`;
  return `mensagens ${n.slice(0, -1).join(", ")} e ${n[n.length - 1]}`;
}

export function Sinalizadores({ sinalizadores }: { sinalizadores: Sinalizador[] | null | undefined }) {
  if (sinalizadores === undefined) {
    return (
      <p className="border-b border-border px-3 py-2.5 text-xs text-muted-foreground sm:px-5">
        Sinalizadores indisponíveis nesta versão da API.
      </p>
    );
  }
  if (sinalizadores === null) {
    return (
      <p className="border-b border-border px-3 py-2.5 text-xs text-muted-foreground sm:px-5">
        Sinalizadores não avaliados: sem fala do cliente.
      </p>
    );
  }
  if (sinalizadores.length === 0) {
    return (
      <p className="border-b border-border px-3 py-2.5 text-xs text-muted-foreground sm:px-5">
        Nenhum sinalizador disparou.
      </p>
    );
  }
  return (
    <div className="flex flex-col gap-1.5 border-b border-border px-3 py-2.5 sm:px-5">
      <ul className="flex flex-col gap-1">
        {sinalizadores.map((s) => (
          <li key={s.regra} className="text-xs">
            <span className="inline-flex items-baseline gap-1.5 font-medium text-warning-rich-text">
              <span aria-hidden>⚑</span>
              {ROTULO_SINALIZADOR[s.regra] ?? s.regra}
            </span>{" "}
            <span className="text-muted-foreground">
              — {s.detalhe} · {listaDeMensagens(s.evidencia)}
            </span>
          </li>
        ))}
      </ul>
      <p className="text-[0.6875rem] text-muted-foreground">
        Regras de superfície sobre falas do cliente, do bot e contagens; não avalia
        o atendente e não muda a nota.
      </p>
    </div>
  );
}
