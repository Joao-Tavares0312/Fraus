import { SegmentoLED } from "@/components/instrumento/SegmentoLED";
import { formatarSegundosLED, ROTULO_DESFECHO } from "@/lib/formato";
import type { ResumoConversa } from "@/lib/api";

/**
 * Faixa de totais acima da lista: quantos atendimentos, quanto se esperou,
 * como eles terminaram.
 *
 * POR QUE MEDIANA E NAO MEDIA. Espera de atendimento tem cauda longa: um punhado
 * de conversas esquecidas por horas puxa a media para um valor que nao descreve
 * atendimento nenhum -- nem os rapidos, nem os lentos. A mediana responde "a
 * metade dos clientes esperou ate isso", que e a frase que alguem de operacao
 * consegue usar. O resto do projeto ja decide assim: `latencia_mediana_s` e
 * feature do fusor, e a serie diaria agrega por mediana. Trocar aqui faria a
 * faixa discordar do grafico da Visao geral usando os mesmos dados.
 *
 * O rotulo diz "mediana" com todas as letras. Chamar mediana de media, mesmo
 * sendo a estatistica melhor, e a mesma classe de defeito que este produto
 * combate no NPS.
 */
function mediana(valores: number[]): number | null {
  if (valores.length === 0) return null;
  const ordenados = [...valores].sort((a, b) => a - b);
  const meio = Math.floor(ordenados.length / 2);
  return ordenados.length % 2 === 1
    ? ordenados[meio]
    : (ordenados[meio - 1] + ordenados[meio]) / 2;
}

/** So os numeros que existem: nulo e ausencia de espera, nao espera de zero. */
function medidos(
  linhas: ResumoConversa[],
  campo: keyof ResumoConversa,
): number[] {
  return linhas
    .map((linha) => linha[campo])
    .filter((valor): valor is number => typeof valor === "number");
}

/**
 * Uma medida da faixa, no display. `valor: null` NAO e zero: e uma espera que
 * nao existiu (nenhum atendimento chegou a um humano, por exemplo), e o display
 * a mostra APAGADO -- o mesmo desenho de "sem sinal" do resto do produto -- com
 * o motivo escrito embaixo. Um `0 s` ali leria como "respondeu na hora".
 */
function Medida({
  rotulo,
  valor,
  unidade,
  detalhe,
}: {
  rotulo: string;
  valor: string | null;
  unidade?: string;
  detalhe: string;
}) {
  return (
    <div className="flex min-w-0 flex-col gap-2 bg-card px-5 py-4">
      <dt className="rotulo-instrumento">{rotulo}</dt>
      <dd className="flex items-end gap-1.5">
        <SegmentoLED valor={valor} rotulo={rotulo} altura={28} />
        {valor !== null && unidade ? (
          <span className="pb-0.5 text-xs leading-none text-muted-foreground">
            {unidade}
          </span>
        ) : null}
      </dd>
      <p className="text-[11px] leading-tight text-muted-foreground">{detalhe}</p>
    </div>
  );
}

/** Mediana em segundos -> par do display, ou nulo quando nao houve espera. */
function emLED(segundos: number | null): { valor: string | null; unidade?: string } {
  if (segundos === null) return { valor: null };
  return formatarSegundosLED(segundos);
}

export function ResumoDaLista({ linhas }: { linhas: ResumoConversa[] }) {
  const primeiras = medidos(linhas, "latencia_primeira_resposta_s");
  const doBot = medidos(linhas, "latencia_mediana_bot_s");
  const doHumano = medidos(linhas, "latencia_mediana_humano_s");

  const porDesfecho = new Map<string, number>();
  for (const linha of linhas) {
    porDesfecho.set(linha.desfecho, (porDesfecho.get(linha.desfecho) ?? 0) + 1);
  }

  const comEscalada = doHumano.length;

  return (
    // A armadura da lista: quatro celulas separadas por filete de 1px (o `gap-px`
    // sobre fundo de compasso), como a armadura da Visao geral. Cada celula pinta
    // o proprio fundo opaco -- e dado, e nao fica sobre vidro.
    <dl className="grid grid-cols-2 gap-px border-b border-linha bg-compasso sm:grid-cols-4">
      <Medida
        rotulo="Registros"
        valor={String(linhas.length)}
        detalhe={`${linhas.reduce((total, l) => total + l.qtd_mensagens, 0)} mensagens no total`}
      />
      <Medida
        rotulo="1ª resposta (mediana)"
        {...emLED(mediana(primeiras))}
        detalhe={
          primeiras.length === linhas.length
            ? "de todos os atendimentos"
            : `${primeiras.length} de ${linhas.length} tiveram resposta`
        }
      />
      <Medida
        rotulo="Resposta do bot (mediana)"
        {...emLED(mediana(doBot))}
        detalhe={`em ${doBot.length} atendimento(s)`}
      />
      <Medida
        rotulo="Resposta humana (mediana)"
        {...emLED(mediana(doHumano))}
        detalhe={
          comEscalada === 0
            ? "nenhum atendimento chegou a um humano"
            : `em ${comEscalada} atendimento(s)`
        }
      />

      <div className="col-span-2 flex min-w-0 flex-col gap-1 bg-card px-5 py-3 sm:col-span-4">
        <dt className="rotulo-instrumento">Desfecho</dt>
        <dd className="flex flex-wrap items-baseline gap-x-4 gap-y-1">
          {Object.keys(ROTULO_DESFECHO)
            .filter((chave) => porDesfecho.has(chave))
            .map((chave) => (
              <span key={chave} className="text-xs text-muted-foreground">
                <span className="num text-sm text-foreground">
                  {porDesfecho.get(chave)}
                </span>{" "}
                {ROTULO_DESFECHO[chave].toLowerCase()}
              </span>
            ))}
        </dd>
      </div>
    </dl>
  );
}
