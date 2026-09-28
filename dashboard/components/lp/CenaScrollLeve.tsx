import { Constelacao } from "@/components/lp/Constelacao";

const ETAPAS = [
  ["01", "Sinais se apresentam.", "Texto, emoji, tempo, emoção, léxico, ironia e estilo entram como leituras independentes da mesma conversa."],
  ["02", "Evidências convergem.", "As 39 features se aproximam do núcleo. Nenhuma camada decide sozinha e cada contribuição mantém sua proveniência."],
  ["03", "O contexto produz o score.", "O fusor transforma o conjunto em uma leitura operacional de 0 a 100, acompanhada pelos trechos que sustentam o resultado."],
] as const;

export function CenaScrollLeve() {
  return (
    <section className="relative border-y border-linha bg-card/10 py-20 sm:py-28" data-cena="leve">
      <div className="mx-auto grid w-full max-w-[88rem] gap-12 px-5 sm:px-8 lg:grid-cols-[.9fr_1.1fr] lg:px-12">
        <div className="self-center opacity-70"><Constelacao /></div>
        <div className="border-t border-linha">
          {ETAPAS.map(([numero, titulo, texto]) => (
            <article key={numero} className="grid gap-3 border-b border-compasso py-7 sm:grid-cols-[3rem_1fr]">
              <span className="font-mono text-xs text-primary">{numero} / 03</span>
              <div><h3 className="text-2xl font-medium tracking-[-.025em] sm:text-3xl">{titulo}</h3><p className="mt-3 max-w-xl leading-relaxed text-muted-foreground">{texto}</p></div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
