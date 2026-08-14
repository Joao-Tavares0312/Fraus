import { formatarEsperaOuTraco, ROTULO_DESFECHO } from "@/lib/formato";
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

function Medida({
  rotulo,
  valor,
  detalhe,
}: {
  rotulo: string;
  valor: string;
  detalhe: string;
}) {
  return (
    <div className="flex min-w-0 flex-col gap-0.5">
      <dt className="text-xs text-muted-foreground">{rotulo}</dt>
      <dd className="num text-lg leading-none text-foreground">{valor}</dd>
      <p className="text-[11px] leading-tight text-muted-foreground">{detalhe}</p>
    </div>
  );
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
    <dl className="grid grid-cols-2 gap-x-6 gap-y-4 border-b border-linha px-5 py-4 sm:grid-cols-4">
      <Medida
        rotulo="Registros"
        valor={String(linhas.length)}
        detalhe={`${linhas.reduce((total, l) => total + l.qtd_mensagens, 0)} mensagens no total`}
      />
      <Medida
        rotulo="1ª resposta (mediana)"
        valor={formatarEsperaOuTraco(mediana(primeiras))}
        detalhe={
          primeiras.length === linhas.length
            ? "de todos os atendimentos"
            : `${primeiras.length} de ${linhas.length} tiveram resposta`
        }
      />
      <Medida
        rotulo="Resposta do bot (mediana)"
        valor={formatarEsperaOuTraco(mediana(doBot))}
        detalhe={`em ${doBot.length} atendimento(s)`}
      />
      <Medida
        rotulo="Resposta humana (mediana)"
        valor={formatarEsperaOuTraco(mediana(doHumano))}
        detalhe={
          comEscalada === 0
            ? "nenhum atendimento chegou a um humano"
            : `em ${comEscalada} atendimento(s)`
        }
      />

      <div className="col-span-2 flex min-w-0 flex-col gap-1 sm:col-span-4">
        <dt className="text-xs text-muted-foreground">Desfecho</dt>
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
