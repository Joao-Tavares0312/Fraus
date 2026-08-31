/**
 * O visual do hero: a tese do produto desenhada — acima da linha o que foi
 * DITO (âmbar), abaixo o que foi MEDIDO (azul). É a régua do Pauta virando
 * peça de vitrine.
 *
 * TODO NÚMERO AQUI É ILUSTRATIVO E ESTÁ ROTULADO. A honestidade metodológica
 * vale na LP como em qualquer tela: dado sintético circula rotulado como tal,
 * e este cartão diz isso no rodapé — não é saída do modelo.
 */

export function PartituraExemplo() {
  return (
    <figure className="vidro w-full max-w-xl p-0">
      {/* cabeçalho do cartão */}
      <div className="flex items-center justify-between border-b border-compasso px-5 py-3">
        <span className="font-mono text-xs text-muted-foreground">
          atendimento · exemplo ilustrativo
        </span>
        <span className="font-mono text-xs text-muted-foreground">webchat</span>
      </div>

      {/* ACIMA DA LINHA — o dito */}
      <div className="flex flex-col gap-3 px-5 py-5">
        <div className="max-w-[85%] self-start rounded-md rounded-bl-none bg-muted/60 px-3.5 py-2.5 text-sm text-muted-foreground">
          Seu chamado foi encerrado. Posso ajudar em algo mais?
        </div>
        <div className="max-w-[85%] self-end rounded-md rounded-br-none bg-dito/10 px-3.5 py-2.5 text-sm text-dito-texto">
          passei 40 minutos esperando pra isso
        </div>
        <div className="max-w-[85%] self-end rounded-md rounded-br-none bg-dito/10 px-3.5 py-2.5 text-sm text-dito-texto">
          ok, obrigado 🙂
        </div>
      </div>

      {/* A RÉGUA — a linha que separa as duas vozes */}
      <div className="relative border-t border-linha">
        <span className="absolute -top-2.5 left-5 bg-transparent font-mono text-[10px] uppercase tracking-widest text-dito-texto">
          dito
        </span>
        <span className="absolute -bottom-2.5 left-5 font-mono text-[10px] uppercase tracking-widest text-medido-texto">
          medido
        </span>
      </div>

      {/* ABAIXO DA LINHA — o medido */}
      <div className="flex flex-col gap-4 px-5 pb-4 pt-6">
        <div className="flex flex-wrap gap-2">
          {[
            "espera: 41 min",
            "ironia: provável",
            "emoção: raiva",
            "polaridade: negativa",
          ].map((leitura) => (
            <span
              key={leitura}
              className="rounded-sm bg-medido/10 px-2 py-1 font-mono text-xs text-medido-texto"
            >
              {leitura}
            </span>
          ))}
        </div>
        <div className="flex items-center gap-4">
          <span className="num text-3xl font-semibold text-medido-texto">28</span>
          <div className="flex-1">
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted/60">
              <div className="h-full w-[28%] rounded-full bg-medido" />
            </div>
            <div className="mt-1.5 flex justify-between font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
              <span>score 0–100</span>
              <span>detrator · estimado</span>
            </div>
          </div>
        </div>
      </div>

      <figcaption className="border-t border-compasso px-5 py-2.5 text-xs text-muted-foreground">
        Exemplo ilustrativo — estes números não saíram do modelo. O “obrigado”
        educado é exatamente o caso que a pesquisa declarada não captura.
      </figcaption>
    </figure>
  );
}
