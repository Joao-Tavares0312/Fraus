import type { ReactNode } from "react";

export type Marca = {
  /** Posicao no dominio do medidor. */
  em: number;
  rotulo: string;
};

export type Faixa = {
  de: number;
  ate: number;
  cor: string;
  rotulo: string;
};

export type Medidor = {
  min: number;
  max: number;
  valor: number;
  /** Faixa de referencia pintada atras do trilho (ex.: CSAT saudavel 75-85%). */
  faixas?: Faixa[];
  marcas?: Marca[];
  cor: string;
};

/**
 * Uma celula da faixa de indicadores.
 *
 * Duas decisoes carregam o produto inteiro:
 *
 * 1. `natureza` marca a PROVENIENCIA do numero. "estimado" ganha o sublinhado
 *    pontilhado e a palavra "estimativa"; "observado" nao ganha nada. O NPS do
 *    Dolos e inferido do texto, nunca perguntado ao cliente, e a interface
 *    nao pode deixar isso implicito.
 * 2. `erro` e por celula. Se um indicador falha, so esta celula mostra falha --
 *    as outras continuam renderizando (regra de produto 5).
 */
export function CartaoIndicador({
  rotulo,
  valor,
  unidade,
  natureza,
  nota,
  medidor,
  erro,
}: {
  rotulo: string;
  valor?: string;
  unidade?: string;
  natureza: "estimado" | "observado";
  nota?: ReactNode;
  medidor?: Medidor;
  erro?: string;
}) {
  const estimado = natureza === "estimado";

  return (
    <div className="flex min-w-0 flex-col gap-3 px-5 py-4">
      <div className="flex items-baseline justify-between gap-2">
        <h3 className="text-[0.8125rem] font-medium text-[var(--tinta-2)]">
          {rotulo}
        </h3>
        {estimado ? (
          <span className="shrink-0 rounded-[2px] border border-[var(--filete)] px-1.5 py-px text-[0.625rem] font-medium text-[var(--tinta-3)]">
            estimativa
          </span>
        ) : null}
      </div>

      {erro ? (
        <FalhaDaCelula erro={erro} />
      ) : (
        <>
          <p className="flex items-baseline gap-1.5">
            <span
              className={`text-[2.125rem] leading-none font-semibold tracking-[-0.02em] text-[var(--tinta)] ${
                estimado ? "estimado" : ""
              }`}
            >
              {valor}
            </span>
            {unidade ? (
              <span className="text-[0.875rem] text-[var(--tinta-3)]">{unidade}</span>
            ) : null}
          </p>

          {medidor ? <Trilho {...medidor} /> : null}

          {nota ? (
            <p className="text-[0.75rem] leading-[1.45] text-[var(--tinta-3)]">{nota}</p>
          ) : null}
        </>
      )}
    </div>
  );
}

function FalhaDaCelula({ erro }: { erro: string }) {
  return (
    <div role="status" className="flex flex-col gap-1">
      <p className="text-[1.25rem] leading-none font-semibold text-[var(--tinta-3)]">
        indisponível
      </p>
      <p className="text-[0.75rem] leading-[1.45] text-[var(--detrator)]">{erro}</p>
      <p className="text-[0.75rem] leading-[1.45] text-[var(--tinta-3)]">
        Os demais indicadores continuam válidos.
      </p>
    </div>
  );
}

/**
 * Trilho de escala: mostra ONDE o valor cai no proprio dominio. Um numero de
 * NPS sem a escala -100..+100 ao lado nao diz nada a quem ve pela primeira vez.
 */
function Trilho({ min, max, valor, faixas = [], marcas = [], cor }: Medidor) {
  const amplitude = max - min || 1;
  const posicao = (n: number) =>
    `${Math.min(100, Math.max(0, ((n - min) / amplitude) * 100))}%`;

  return (
    <div className="pt-0.5">
      <div className="relative h-[6px] w-full bg-[var(--superficie-2)]">
        {faixas.map((faixa) => (
          <div
            key={faixa.rotulo}
            title={faixa.rotulo}
            className="absolute inset-y-0"
            style={{
              left: posicao(faixa.de),
              width: `calc(${posicao(faixa.ate)} - ${posicao(faixa.de)})`,
              background: faixa.cor,
            }}
          />
        ))}
        <div
          className="absolute top-[-3px] bottom-[-3px] w-[2px]"
          style={{ left: posicao(valor), background: cor }}
        />
      </div>
      <div className="relative mt-1 h-[0.875rem]">
        <span className="absolute left-0 text-[0.6875rem] tabular-nums text-[var(--tinta-3)]">
          {min}
        </span>
        {marcas.map((marca) => (
          <span
            key={marca.rotulo}
            className="absolute -translate-x-1/2 text-[0.6875rem] whitespace-nowrap text-[var(--tinta-3)]"
            style={{ left: posicao(marca.em) }}
          >
            {marca.rotulo}
          </span>
        ))}
        <span className="absolute right-0 text-[0.6875rem] tabular-nums text-[var(--tinta-3)]">
          {max}
        </span>
      </div>
    </div>
  );
}
