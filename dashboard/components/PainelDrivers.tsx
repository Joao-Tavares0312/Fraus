"use client";

import { useState } from "react";
import { obterDrivers } from "@/lib/api";
import type { Drivers, GrupoDeDrivers } from "@/lib/api";
import { ROTULO_SINAL, type SinalDaFeature } from "@/lib/derivacoes";
import { formatarComSinal } from "@/lib/formato";
import { Painel } from "@/components/Painel";
import { Button } from "@/components/ui/button";
import { RessalvaDaTela } from "@/components/AparatoDaTela";

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
    <section className="min-w-0">
      <Painel
        titulo="O que influenciou as notas"
        legenda="Contribuições médias por família de sinal, calculadas sob demanda. Os valores medem a diferença entre as classes satisfeito e insatisfeito na escala interna do modelo (logit), não pontos da nota. Não demonstram causa."
      >
        <div className="flex flex-col gap-4">
          <div className="flex flex-wrap items-center gap-3">
            <Button type="button" variant="outline" onClick={medir} disabled={carregando}>
              {carregando ? "Calculando influência…" : "Ver influência dos sinais"}
            </Button>
            <p className="max-w-prose text-sm leading-relaxed text-muted-foreground">O cálculo examina até {AMOSTRA} atendimentos elegíveis do período e só começa quando você pedir.</p>
          </div>
          <div aria-live="polite" className="flex flex-col gap-2">
            {erro && <p role="alert" className="text-sm text-detrator-texto">{erro}</p>}
            {drivers && <TabelaDrivers drivers={drivers} />}
          </div>
        </div>
      </Painel>
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
      <p className="num text-sm text-foreground">{descreverRecorte(drivers.recorte)}</p>
      <p className="num text-sm text-foreground">
        amostra de {drivers.amostra} de {drivers.elegiveis} elegíveis ·{" "}
        {drivers.sem_sinal} sem sinal · {drivers.defasadas} de outra régua
        (repontuar para incluir)
      </p>
      <p className="text-sm text-foreground">{drivers.rotulo}</p>
      <p className="text-sm text-muted-foreground">
        Contribuições na escala interna do modelo, não pontos da nota.
      </p>

      <div className="overflow-x-auto">
        <table className="w-full min-w-[32rem] border-collapse text-left text-sm">
          <thead>
            <tr className="border-b border-border text-muted-foreground">
              <th scope="col" className="py-1.5 pr-3 font-normal">
                sinal
              </th>
              <th scope="col" className="py-1.5 pr-3 font-normal">
                detratores
              </th>
              <th scope="col" className="py-1.5 font-normal">
                promotores
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

      <RessalvaDaTela titulo="Influência dos sinais — método da amostra">
        <p className="max-w-prose text-sm leading-relaxed text-muted-foreground">{drivers.metodo}</p>
      </RessalvaDaTela>
    </div>
  );
}
