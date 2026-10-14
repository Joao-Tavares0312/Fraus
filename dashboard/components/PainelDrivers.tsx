"use client";

import { useState } from "react";
import { obterDrivers } from "@/lib/api";
import type { Drivers, GrupoDeDrivers } from "@/lib/api";
import { ROTULO_SINAL, type SinalDaFeature } from "@/lib/derivacoes";
import { formatarComSinal } from "@/lib/formato";

const AMOSTRA = 50;

/**
 * Drivers por familia, SOB DEMANDA: cada conversa da amostra custa uma
 * passagem de modelo, entao nada carrega sozinho -- so o clique. O servidor
 * entrega as medias (em pontos do eixo do modelo) e o intervalo; aqui so se
 * desenha, e grupo sem dado diz que esta sem dado, nunca 0 (invariante 2).
 */
export function PainelDrivers({
  de,
  ate,
}: {
  de: string | null;
  ate: string | null;
}) {
  const [carregando, setCarregando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [drivers, setDrivers] = useState<Drivers | null>(null);

  async function medir() {
    setCarregando(true);
    setErro(null);
    const resposta = await obterDrivers({ de, ate, n: AMOSTRA });
    setCarregando(false);
    if (resposta.ok) {
      setDrivers(resposta.dado);
    } else {
      setDrivers(null);
      setErro(resposta.erro);
    }
  }

  return (
    <section className="flex min-w-0 flex-col gap-3">
      <div className="flex flex-wrap items-center gap-3">
        <h2 className="text-sm text-foreground">O que mais pesa na nota, por sinal</h2>
        <button
          type="button"
          onClick={medir}
          disabled={carregando}
          className="h-8 border border-linha px-3 text-xs text-foreground hover:bg-accent disabled:opacity-50"
        >
          {carregando
            ? "Medindo…"
            : `Medir drivers numa amostra de ${AMOSTRA} atendimentos`}
        </button>
      </div>
      <div aria-live="polite" className="flex flex-col gap-2">
        {erro && <p className="text-xs text-detrator-texto">{erro}</p>}
        {drivers && <TabelaDrivers drivers={drivers} />}
      </div>
    </section>
  );
}

function rotuloDaFamilia(familia: string): string {
  return ROTULO_SINAL[familia as SinalDaFeature] ?? familia;
}

function CelulaDoGrupo({
  grupo,
  vazio,
}: {
  grupo: GrupoDeDrivers;
  vazio: string;
}) {
  if (grupo.n === 0 || grupo.media === null) {
    return <span className="text-muted-foreground">{vazio}</span>;
  }
  return (
    <span className="num text-foreground">
      {formatarComSinal(grupo.media, 2)}{" "}
      {grupo.ic ? (
        <span className="text-muted-foreground">
          [{formatarComSinal(grupo.ic[0], 2)}; {formatarComSinal(grupo.ic[1], 2)}]
        </span>
      ) : (
        <span className="text-muted-foreground">n = {grupo.n}, sem intervalo</span>
      )}
    </span>
  );
}

function descreverRecorte(recorte: Drivers["recorte"]): string {
  const { de, ate } = recorte;
  if (!de && !ate) return "período medido: todo o histórico";
  if (de && ate) return `período medido: de ${de} até ${ate}`;
  return de ? `período medido: a partir de ${de}` : `período medido: até ${ate}`;
}

export function TabelaDrivers({ drivers }: { drivers: Drivers }) {
  return (
    <div className="flex min-w-0 flex-col gap-3">
      <p className="num text-xs text-foreground">{descreverRecorte(drivers.recorte)}</p>
      <p className="num text-xs text-foreground">
        amostra de {drivers.amostra} de {drivers.elegiveis} elegíveis ·{" "}
        {drivers.sem_sinal} sem sinal · {drivers.defasadas} de outra régua
        (repontuar para incluir)
      </p>
      <p className="text-xs text-foreground">{drivers.rotulo}</p>
      <p className="text-xs text-muted-foreground">
        valores em unidade de logit (satisfeito × insatisfeito), não em pontos de score
      </p>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[32rem] border-collapse text-left text-xs">
          <thead>
            <tr className="border-b border-border text-muted-foreground">
              <th scope="col" className="py-1.5 pr-3 font-normal">
                sinal
              </th>
              <th scope="col" className="py-1.5 pr-3 font-normal">
                detratores (logit)
              </th>
              <th scope="col" className="py-1.5 font-normal">
                promotores (logit)
              </th>
            </tr>
          </thead>
          <tbody>
            {drivers.familias.map((f) => (
              <tr key={f.familia} className="border-b border-border align-top">
                <th scope="row" className="py-1.5 pr-3 font-normal text-foreground">
                  {rotuloDaFamilia(f.familia)}
                </th>
                <td className="py-1.5 pr-3">
                  <CelulaDoGrupo
                    grupo={f.detratores}
                    vazio="sem detratores na amostra"
                  />
                </td>
                <td className="py-1.5">
                  <CelulaDoGrupo
                    grupo={f.promotores}
                    vazio="sem promotores na amostra"
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <p className="max-w-[62ch] text-xs text-muted-foreground">{drivers.metodo}</p>
    </div>
  );
}
