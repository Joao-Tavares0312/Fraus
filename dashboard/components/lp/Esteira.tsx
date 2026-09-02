/**
 * A ESTEIRA DOS SETE SINAIS — o ticker que corta a página logo abaixo do hero.
 *
 * O QUE ELA FAZ PELA PÁGINA, porque "faixa que anda" sozinho é decoração: ela
 * entrega os sete nomes ANTES da seção que os explica. Quem rola rápido — que é
 * quase todo mundo — sai sabendo que o sistema tem sete famílias de sinal mesmo
 * sem ler um parágrafo. É sumário, não enfeite, e é por isso que os nomes vêm
 * em caixa alta e mono: lista de inventário, não frase.
 *
 * É `<div aria-hidden>` na cópia e conteúdo de verdade na primeira passagem —
 * ver o comentário da classe `.esteira` no globals.css sobre por que a lista é
 * renderizada duas vezes e por que a segunda é invisível para leitor de tela.
 *
 * Sem `"use client"`: é CSS puro, sem estado e sem efeito. Renderiza no
 * servidor e anima sozinha.
 */

const SINAIS = [
  "texto",
  "emoji",
  "tempo",
  "emoção",
  "léxico",
  "ironia",
  "estilo",
] as const;

function Faixa({ oculta = false }: { oculta?: boolean }) {
  return (
    <ul
      aria-hidden={oculta || undefined}
      className="flex shrink-0 items-center"
      // `list-style: none` já vem do reset; o que importa aqui é não quebrar.
    >
      {SINAIS.map((nome) => (
        <li key={nome} className="flex items-center whitespace-nowrap">
          <span className="etiqueta-vitrine px-8 text-muted-foreground">
            {nome}
          </span>
          {/* O separador é um ponto e não uma barra: barra lê como caminho de
              arquivo, ponto lê como conta de rosário — que é o ritmo certo
              para uma lista que não tem começo nem fim visível. */}
          <span aria-hidden className="text-primary/70">
            ·
          </span>
        </li>
      ))}
    </ul>
  );
}

export function Esteira() {
  return (
    <div className="relative overflow-hidden border-y border-border/50 py-4">
      {/* As duas máscaras laterais dissolvem a esteira nas bordas. Sem elas o
          texto aparece e some numa linha reta, e a faixa lê como um bloco
          cortado em vez de algo que continua fora da tela. */}
      <div
        className="flex w-max"
        style={{
          maskImage:
            "linear-gradient(to right, transparent, black 6%, black 94%, transparent)",
          WebkitMaskImage:
            "linear-gradient(to right, transparent, black 6%, black 94%, transparent)",
        }}
      >
        <div className="esteira flex w-max">
          <Faixa />
          <Faixa oculta />
        </div>
      </div>
    </div>
  );
}
