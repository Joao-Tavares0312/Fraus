"use client";

import { useEffect, useId, useState } from "react";
import { SegmentoLED } from "@/components/instrumento/SegmentoLED";
import { falasDecisivas, marcasDaAtribuicao, type MarcaAtribuicao } from "@/lib/derivacoes";
import { humorDaCategoria } from "@/lib/lp-nova/humor";
import { concordaComRoteiro, dataDaGravacao, type ConjuntoLeituras, type IdLeitura, type Leitura } from "@/lib/lp-nova/leituras";
import { useCena } from "./CenaLeitura";

const TITULOS: Record<IdLeitura, { aba: string; tese: string }> = {
  obrigado: { aba: "O obrigado", tese: "Agradeceu e saiu sem solução." },
  ironia: { aba: "A ironia", tese: "Elogiou para reclamar." },
  espera: { aba: "A espera", tese: "Educado do início ao fim, esperando." },
  promotor: { aba: "O elogio", tese: "No roteiro, o problema foi resolvido e o cliente elogiou." },
  "sem-sinal": { aba: "Sem sinal", tese: "O cliente nunca escreveu." },
};

const ROTULO_SENTIDO = {
  puxou_para_baixo: "inclinação textual negativa",
  puxou_para_cima: "inclinação textual positiva",
  sem_inclinacao: "sem inclinação clara",
} as const;

function porcentagem(v: number) {
  return `${Math.round(v * 100)}%`;
}

/**
 * O visitante escolhe uma analise gravada de conversa sintetica.
 *
 * Tudo que aparece aqui veio do servidor na gravacao: nota, categoria e a
 * probabilidade por mensagem. As marcas usam o saldo do classificador textual,
 * nao uma decomposicao da nota nem uma atribuicao causal por fala.
 * A cena de fundo muda de humor com a categoria escolhida.
 */
export function SeletorDeLeituras({ conjunto }: { conjunto: ConjuntoLeituras }) {
  const [atual, setAtual] = useState<IdLeitura>("obrigado");
  const { definirHumor } = useCena();
  const base = useId();
  const leitura = conjunto.leituras.find((l) => l.id === atual) as Leitura;

  useEffect(() => {
    const { humor, cinza } = humorDaCategoria(leitura.categoria);
    definirHumor(humor, cinza);
  }, [leitura, definirHumor]);

  const marcas = marcasDaAtribuicao(leitura.mensagens);
  const decisivas = falasDecisivas(marcas);

  return (
    <div className="ln-seletor">
      <div role="tablist" aria-label="Leituras gravadas" className="ln-abas">
        {conjunto.leituras.map((l) => (
          <button
            key={l.id}
            role="tab"
            id={`${base}-aba-${l.id}`}
            aria-selected={l.id === atual}
            aria-controls={`${base}-painel`}
            tabIndex={l.id === atual ? 0 : -1}
            className="ln-aba"
            onClick={() => setAtual(l.id)}
            onKeyDown={(e) => {
              const i = conjunto.leituras.findIndex((x) => x.id === atual);
              const passo = e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0;
              if (!passo) return;
              const proxima = conjunto.leituras[(i + passo + conjunto.leituras.length) % conjunto.leituras.length];
              setAtual(proxima.id);
              document.getElementById(`${base}-aba-${proxima.id}`)?.focus();
            }}
          >
            {TITULOS[l.id].aba}
          </button>
        ))}
      </div>

      <div role="tabpanel" id={`${base}-painel`} aria-labelledby={`${base}-aba-${atual}`} className="ln-painel">
        <ol className="ln-conversa" aria-label="Transcrição">
          {leitura.conversa.mensagens.map((m, indice) => {
            const marca: MarcaAtribuicao | undefined = marcas.get(indice);
            return (
              <li key={indice} className={`ln-msg ln-msg--${m.autor}`} data-sentido={marca?.sentido}>
                <span className="ln-rotulo">{m.autor}</span>
                <p className="ln-msg__texto">{m.texto}</p>
                {marca && marca.sentido !== "sem_inclinacao" && (
                  <span className="ln-msg__marca">
                    {ROTULO_SENTIDO[marca.sentido]} · classificador de texto: {porcentagem(marca.probabilidade)} {marca.classe}
                  </span>
                )}
              </li>
            );
          })}
        </ol>

        <aside className="ln-veredito" aria-label="O que o Fraus mediu">
          {/* O ROTEIRO e o que nos escrevemos; o veredito embaixo e o que o motor leu. */}
          <div>
            <span className="ln-rotulo">roteiro da conversa</span>
            <p className="titulo-vitrine ln-veredito__tese">{TITULOS[atual].tese}</p>
          </div>
          <div className="ln-veredito__nota">
            <SegmentoLED valor={leitura.nota === null ? null : String(leitura.nota)} rotulo="nota estimada" altura={64} cor="medido" traco="fino" celulas={2} />
            <span className="ln-rotulo">
              {leitura.categoria ? (
                <>
                  nota estimada · <strong>{leitura.categoria}</strong>
                </>
              ) : (
                <>sem sinal · sem fala do cliente, sem nota</>
              )}
            </span>
          </div>
          {!concordaComRoteiro(leitura) && (
            <p className="ln-veredito__discorda" role="note">
              O Fraus leu diferente do roteiro. A leitura fica como o motor disse: esconder o erro seria escolher a
              conversa a dedo.
            </p>
          )}
          {decisivas.length > 0 && (
            <p className="ln-veredito__decisiva">
              Maior inclinação no classificador de texto:{" "}
              <q>{leitura.conversa.mensagens[decisivas[0].indice]?.texto}</q>. Esse destaque não mede o efeito isolado da fala na nota.
            </p>
          )}
        </aside>
      </div>

      <p className="ln-procedencia">
        Análise gravada em {dataDaGravacao(conjunto.procedencia.gravado_em)} · API: {conjunto.procedencia.api} · hash parcial
        das importâncias: {conjunto.procedencia.modelo} (não identifica todos os modelos ou o pipeline).
        Conversas sintéticas, escritas para esta página; nota estimada, não NPS declarado. As probabilidades por fala
        são do classificador de texto; contribuições do fusor são termos na diferença entre logits de satisfeito e insatisfeito,
        não pontos da nota.
      </p>
    </div>
  );
}
