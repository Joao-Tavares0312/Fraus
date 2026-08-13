import type { Indicadores, Resultado } from "@/lib/api";
import { CSAT_SAUDAVEL } from "@/lib/derivacoes";
import { formatarNps, formatarNumero, formatarSegundos } from "@/lib/formato";
import { CartaoIndicador } from "./CartaoIndicador";

/**
 * A faixa nao e uma grade de cartoes: e UM painel dividido por filetes, para
 * que os quatro numeros leiam como um so instrumento.
 *
 * A isolacao de falha e por celula. Como `/indicadores` entrega os quatro
 * numeros num payload unico, ha dois niveis de falha:
 *   - a requisicao inteira falha -> as quatro celulas falham, mas o resto da
 *     pagina (grafico, tabela) continua renderizando;
 *   - um campo vem ausente ou nao-numerico -> so a celula dele falha.
 */
export function FaixaIndicadores({
  indicadores,
  tempoMediano,
  erroTempo,
}: {
  indicadores: Resultado<Indicadores>;
  tempoMediano: number | null;
  erroTempo?: string;
}) {
  const erroGeral = indicadores.ok ? undefined : indicadores.erro;
  const dado = indicadores.ok ? indicadores.dado : null;

  const campo = (nome: keyof Indicadores): { valor?: number; erro?: string } => {
    if (erroGeral) return { erro: erroGeral };
    const bruto = dado?.[nome];
    if (typeof bruto !== "number" || !Number.isFinite(bruto)) {
      return { erro: `campo "${nome}" ausente na resposta de /indicadores` };
    }
    return { valor: bruto };
  };

  const nps = campo("nps");
  const csat = campo("csat");
  const contencao = campo("containment_rate");
  const total = dado?.total_conversas;
  const semSinal = dado?.sem_sinal;

  return (
    <div className="grid grid-cols-1 divide-y divide-[var(--filete)] border border-[var(--filete)] bg-[var(--superficie)] sm:grid-cols-2 sm:divide-y-0 lg:grid-cols-4">
      <div className="sm:border-b sm:border-[var(--filete)] lg:border-b-0 lg:border-r">
        <CartaoIndicador
          rotulo="NPS inferido"
          natureza="estimado"
          valor={nps.valor === undefined ? undefined : formatarNps(nps.valor)}
          erro={nps.erro}
          medidor={
            nps.valor === undefined
              ? undefined
              : {
                  min: -100,
                  max: 100,
                  valor: nps.valor,
                  cor: "var(--serie-nps)",
                  marcas: [{ em: 0, rotulo: "0" }],
                }
          }
          nota="Derivado do texto do atendimento. Não é pergunta declarada ao cliente."
        />
      </div>

      <div className="sm:border-b sm:border-[var(--filete)] lg:border-b-0 lg:border-r">
        <CartaoIndicador
          rotulo="CSAT"
          natureza="estimado"
          valor={csat.valor === undefined ? undefined : formatarNumero(csat.valor)}
          unidade="%"
          erro={csat.erro}
          medidor={
            csat.valor === undefined
              ? undefined
              : {
                  min: 0,
                  max: 100,
                  valor: csat.valor,
                  cor: "var(--serie-nps)",
                  faixas: [
                    {
                      de: CSAT_SAUDAVEL.de,
                      ate: CSAT_SAUDAVEL.ate,
                      cor: "var(--faixa-saudavel)",
                      rotulo: `faixa saudável de referência: ${CSAT_SAUDAVEL.de}–${CSAT_SAUDAVEL.ate}%`,
                    },
                  ],
                  marcas: [
                    { em: (CSAT_SAUDAVEL.de + CSAT_SAUDAVEL.ate) / 2, rotulo: "75–85 saudável" },
                  ],
                }
          }
          nota="Atendimentos com nota inferida ≥ 7. Faixa saudável de referência marcada no trilho."
        />
      </div>

      <div className="sm:border-b sm:border-[var(--filete)] lg:border-b-0 lg:border-r">
        <CartaoIndicador
          rotulo="Containment rate"
          natureza="observado"
          valor={
            contencao.valor === undefined
              ? undefined
              : formatarNumero(contencao.valor)
          }
          unidade="%"
          erro={contencao.erro}
          medidor={
            contencao.valor === undefined
              ? undefined
              : {
                  min: 0,
                  max: 100,
                  valor: contencao.valor,
                  cor: "var(--serie-latencia)",
                }
          }
          nota={
            total === undefined || semSinal === undefined
              ? "Atendimentos resolvidos sem passar para humano."
              : `Resolvidos sem passar para humano, sobre ${total} atendimentos — ${semSinal} deles sem fala do cliente.`
          }
        />
      </div>

      <CartaoIndicador
        rotulo="Tempo mediano de resposta"
        natureza="observado"
        valor={tempoMediano === null ? undefined : formatarSegundos(tempoMediano)}
        erro={
          erroTempo ??
          (tempoMediano === null
            ? "nenhuma resposta com par cliente→bot na janela"
            : undefined)
        }
        medidor={
          tempoMediano === null
            ? undefined
            : {
                min: 0,
                max: 180,
                valor: Math.min(tempoMediano, 180),
                cor: "var(--serie-latencia)",
                faixas: [
                  {
                    de: 5,
                    ate: 10,
                    cor: "var(--faixa-saudavel)",
                    rotulo: "pico de satisfação na literatura de live chat: 5–10 s",
                  },
                ],
                marcas: [{ em: 60, rotulo: "60 s" }],
              }
        }
        nota="Mediana dos intervalos entre a fala do cliente e a resposta seguinte, calculada dos timestamps."
      />
    </div>
  );
}
