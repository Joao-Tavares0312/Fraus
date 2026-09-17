const LEITURAS = [
  ["espera", "41 min"],
  ["ironia", "provável"],
  ["emoção", "raiva"],
  ["polaridade", "negativa"],
] as const;

export function PartituraExemplo() {
  return (
    <figure className="lp-leitor w-full max-w-xl overflow-hidden border border-linha bg-card/70">
      <div className="flex items-center justify-between border-b border-compasso px-5 py-3.5">
        <div className="flex items-center gap-3">
          <span
            aria-hidden
            className="size-1.5 rounded-full bg-primary shadow-[0_0_10px_var(--primary)]"
          />
          <span className="font-mono text-xs uppercase tracking-[.14em] text-muted-foreground">
            amostra 00-A
          </span>
        </div>
        <span className="font-mono text-xs uppercase tracking-[.14em] text-muted-foreground">
          webchat · 00:41:08
        </span>
      </div>

      <div className="grid lg:grid-cols-[1.05fr_.95fr]">
        <div className="border-b border-compasso p-5 lg:border-b-0 lg:border-r">
          <p className="font-mono text-[0.6875rem] uppercase tracking-[.18em] text-dito-texto">
            ↑ material articulado
          </p>
          <ol className="mt-5 space-y-1">
            <li className="lp-leitor__turno grid grid-cols-[2.25rem_1fr] gap-3 py-3">
              <span className="num text-xs text-muted-foreground">01</span>
              <div>
                <span className="font-mono text-[0.6875rem] uppercase tracking-wider text-muted-foreground">
                  atendente
                </span>
                <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
                  Seu chamado foi encerrado. Posso ajudar em algo mais?
                </p>
              </div>
            </li>
            <li className="lp-leitor__turno grid grid-cols-[2.25rem_1fr] gap-3 py-3">
              <span className="num text-xs text-dito-texto">02</span>
              <div>
                <span className="font-mono text-[0.6875rem] uppercase tracking-wider text-dito-texto">
                  cliente
                </span>
                <p className="mt-1 text-sm leading-relaxed">
                  passei 40 minutos esperando pra isso
                </p>
              </div>
            </li>
            <li className="lp-leitor__turno lp-leitor__turno--marcado grid grid-cols-[2.25rem_1fr] gap-3 py-3">
              <span className="num text-xs text-dito-texto">03</span>
              <div>
                <span className="font-mono text-[0.6875rem] uppercase tracking-wider text-dito-texto">
                  cliente
                </span>
                <p className="mt-1 text-base font-medium text-dito-texto">
                  ok, obrigado 🙂
                </p>
                <p className="mt-2 font-mono text-[0.6875rem] uppercase tracking-wider text-muted-foreground">
                  trecho que puxou a leitura
                </p>
              </div>
            </li>
          </ol>
        </div>

        <div className="flex flex-col p-5">
          <p className="font-mono text-[0.6875rem] uppercase tracking-[.18em] text-medido-texto">
            ↓ telemetria inferida
          </p>
          <dl className="mt-5 grid grid-cols-2 border-l border-t border-compasso">
            {LEITURAS.map(([rotulo, valor]) => (
              <div
                key={rotulo}
                className="border-b border-r border-compasso p-3"
              >
                <dt className="font-mono text-[0.6875rem] uppercase tracking-wider text-muted-foreground">
                  {rotulo}
                </dt>
                <dd className="mt-1 text-sm font-medium text-medido-texto">
                  {valor}
                </dd>
              </div>
            ))}
          </dl>
          <div className="mt-auto pt-7">
            <div className="flex items-end justify-between gap-4">
              <div>
                <span className="num text-5xl font-medium leading-none text-medido-texto">
                  28
                </span>
                <span className="ml-2 font-mono text-[0.6875rem] uppercase tracking-wider text-muted-foreground">
                  / 100
                </span>
              </div>
              <span className="text-right font-mono text-[0.6875rem] uppercase tracking-[.15em] text-medido-texto">
                detrator · estimado
              </span>
            </div>
            <div className="mt-4 h-px bg-compasso">
              <div className="lp-leitor__score h-px w-[28%] bg-medido" />
            </div>
          </div>
        </div>
      </div>

      <figcaption className="border-t border-compasso px-5 py-3 text-xs leading-relaxed text-muted-foreground">
        Exemplo ilustrativo — os números não saíram do modelo. A peça demonstra
        como o “obrigado” educado muda de leitura quando encontra o contexto.
      </figcaption>
    </figure>
  );
}
