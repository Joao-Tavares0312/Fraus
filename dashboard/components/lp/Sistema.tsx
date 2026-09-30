import { SegmentoLED } from "@/components/instrumento/SegmentoLED";
import { Revelar } from "./Revelar";

/**
 * As SETE FAMILIAS do vetor, com a descricao que o CLAUDE.md faz de cada uma.
 * Nao ha claim novo aqui: cada linha e o que o codigo ja faz.
 *
 * `voz` diz de que lado da regua a familia mora -- `dito` (o que o cliente
 * articulou) ou `medido` (o que se mediu sobre a conversa). A lampada carrega a
 * palavra junto com a cor, sempre: cor nunca e o unico portador de sentido.
 */
const FAMILIAS = [
  {
    no: "01",
    nome: "Texto",
    texto: "BERTimbau fine-tunado em português. A probabilidade é por mensagem, não por conversa.",
    voz: "dito",
  },
  {
    no: "02",
    nome: "Emoji",
    texto: "Léxico com 969 entradas do Emoji Sentiment Ranking e a posição relativa na mensagem.",
    voz: "dito",
  },
  {
    no: "03",
    nome: "Tempo",
    texto: "Latência, escalação e abandono. Treinado em conversas sintéticas — limitação declarada.",
    voz: "medido",
  },
  {
    no: "04",
    nome: "Emoção",
    texto: "Sete classes de Ekman. O desprezo é derivado da díade raiva + nojo.",
    voz: "medido",
  },
  {
    no: "05",
    nome: "Léxico",
    texto: "SentiLex-PT02 com escopo de negação: “não gostei” não conta como “gostei”.",
    voz: "dito",
  },
  {
    no: "06",
    nome: "Estilo",
    texto: "Caixa alta, pontuação, alongamento, palavrão e censura na forma da escrita.",
    voz: "dito",
  },
  {
    no: "07",
    nome: "Incongruência",
    texto: "Polaridade emoji × texto, marcador de contraste, hipérbole e aspas irônicas.",
    voz: "medido",
  },
] as const;

function Lampada({ voz }: { voz: "dito" | "medido" | "vazio" }) {
  const rotulos = { dito: "dito", medido: "medido", vazio: "sem sinal" } as const;
  return (
    <span className={`vt-lampada is-${voz}`}>
      <i aria-hidden />
      {rotulos[voz]}
    </span>
  );
}

export function Sistema() {
  return (
    <section id="sistema" aria-labelledby="titulo-sistema" className="vt-sec">
      <div className="vt-wrap">
        <Revelar className="mb-12 grid gap-8 lg:mb-16 lg:grid-cols-[1fr_1fr] lg:items-end">
          <div>
            <p className="vt-rotulo">02 — o sistema</p>
            <h2 id="titulo-sistema" className="titulo-vitrine mt-8 max-w-[14ch]">
              Sete sinais, um fusor, uma nota.
            </h2>
          </div>
          <p className="vt-prosa lg:justify-self-end">
            Cada sinal enxerga uma coisa e nenhum decide sozinho. As famílias
            entram num mesmo vetor e um fusor aprende quanto cada uma pesa.
          </p>
        </Revelar>

        <Revelar>
          <div className="vt-grade">
            <div className="vt-cel vt-cel--fusor">
              <span className="vt-cel__no">FUSOR</span>
              <h3>Regressão logística sobre 39 features</h3>
              <p className="max-w-[24rem]">
                As sete famílias viram um vetor de 39 números. A nota sai de 0 a
                100, vira 0–10 e ganha a categoria de NPS — sempre no servidor,
                nunca no navegador.
              </p>
              <SegmentoLED
                className="vt-fusor__led"
                valor="39"
                altura={120}
                cor="marca"
                rotulo="features no fusor"
              />
              <p className="vt-fusor__formula">
                score 0–100 → nota 0–10 → categoria NPS
                <br />a ironia é lida por mensagem e fica fora do vetor
              </p>
            </div>

            {FAMILIAS.map((f) => (
              <div key={f.no} className="vt-cel">
                <span className="vt-cel__no">{f.no}</span>
                <h3>{f.nome}</h3>
                <p>{f.texto}</p>
                <span className="vt-cel__rodape">
                  {f.nome === "Tempo" ? (
                    <SegmentoLED
                      valor="4:12"
                      altura={16}
                      rotulo="exemplo de latência, quatro minutos e doze segundos"
                      className="mr-2 align-middle"
                    />
                  ) : null}
                  <Lampada voz={f.voz} />
                </span>
              </div>
            ))}

            <div className="vt-cel">
              <span className="vt-cel__no">—</span>
              <h3>Sem sinal</h3>
              <p>
                Sem fala do cliente, não há o que pontuar: o atendimento não
                entra na média e nunca vira zero.
              </p>
              <span className="vt-cel__rodape">
                <SegmentoLED
                  valor={null}
                  altura={16}
                  cor="tinta"
                  celulas={2}
                  rotulo="atendimento sem fala do cliente"
                  className="mr-2 align-middle"
                />
                <Lampada voz="vazio" />
              </span>
            </div>
          </div>
        </Revelar>
      </div>
    </section>
  );
}
