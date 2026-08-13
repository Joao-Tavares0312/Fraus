import type { Indicadores, Resultado } from "@/lib/api";
import { CSAT_SAUDAVEL, LIMIARES_LATENCIA } from "@/lib/derivacoes";
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
 *
 * Ausencia de MEDIDA nao e nenhuma das duas: `nps` e `csat` chegam `null`
 * quando nenhum atendimento tem score, e a celula cai no estado "sem sinal" --
 * o mesmo que o grafico ja mostra. Nunca 0.
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

  const campo = (
    nome: keyof Indicadores,
  ): { valor?: number; erro?: string; semDado?: string } => {
    if (erroGeral) return { erro: erroGeral };
    const bruto = dado?.[nome];
    if (bruto === null) {
      return {
        semDado:
          "nenhum atendimento com fala do cliente para pontuar — não há o que medir",
      };
    }
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
          semDado={nps.semDado}
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
          semDado={csat.semDado}
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
          semDado={contencao.semDado}
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
                max: LIMIARES_LATENCIA.degradando,
                valor: Math.min(tempoMediano, LIMIARES_LATENCIA.degradando),
                cor: "var(--serie-latencia)",
                faixas: [
                  {
                    de: 0,
                    ate: LIMIARES_LATENCIA.pico,
                    cor: "var(--faixa-saudavel)",
                    rotulo: `pico de satisfação na literatura de live chat: até ${LIMIARES_LATENCIA.pico} s (CSAT ~84,7%)`,
                  },
                ],
                marcas: [
                  { em: LIMIARES_LATENCIA.saudavel, rotulo: "60 s saudável" },
                ],
              }
        }
        nota="Mediana dos intervalos entre a fala do cliente e a resposta seguinte, calculada dos timestamps. Acima de 3 min é a faixa de abandono: 57% dos clientes desistem."
      />
    </div>
  );
}
