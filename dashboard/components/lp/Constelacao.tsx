/**
 * A CONSTELAÇÃO DO FUSOR — sete estrelas convergindo numa só.
 *
 * =============================================================================
 * POR QUE ELA EXISTE, e por que ela não é decoração
 * =============================================================================
 *
 * Esta seção era, até 01/09/2026, sete cartões de ícone + título + parágrafo
 * numa bento grid. Funcionava e era a coisa mais genérica da página — o mesmo
 * bloco que qualquer produto SaaS tem, e que não diz nada sobre ESTE produto.
 *
 * O que o sistema de fato faz é: sete famílias de sinal lêem a conversa por
 * ângulos independentes e um fusor combina as 38 features num único score. Isso
 * não é uma lista — é uma TOPOLOGIA, sete nós convergindo em um. E num tema cuja
 * tese é o espaço, uma topologia de sete pontos luminosos ligados a um centro
 * tem um nome próprio: constelação.
 *
 * Ou seja, o desenho não foi escolhido por ser bonito e depois justificado. Ele
 * é o diagrama de arquitetura do `fraus/fusor.py` desenhado com o vocabulário
 * visual que o tema já tinha. A forma diz o que o parágrafo ao lado diz.
 *
 * =============================================================================
 * AS CORES SÃO AS DE VERDADE
 * =============================================================================
 *
 * Cada estrela usa o TOKEN daquele sinal — o mesmo `--emocao`, `--lexico`,
 * `--ironia` que pinta as barras de contribuição em `BarrasDeFeature.tsx` na
 * dashboard. Quem vê a vitrine e depois entra na ferramenta encontra o mesmo
 * código de cor, e isso não é coincidência estética: é o encoding do PRODUCT.md
 * valendo nas duas superfícies.
 *
 * O CENTRO É `--medido`, e é obrigatório que seja: o score é o que foi MEDIDO.
 * As sete pontas são o que foi lido; o centro é o veredito. A régua dito/medido
 * governa até aqui.
 *
 * =============================================================================
 * GEOMETRIA E MOVIMENTO
 * =============================================================================
 *
 * As posições são calculadas, não digitadas: sete ângulos igualmente espaçados
 * numa ELIPSE (rx 300, ry 168). Elipse e não círculo porque círculo perfeito lê
 * como diagrama de slide; a razão ~1,8 lê como órbita vista de viés, que é a
 * leitura que o tema pede. O ângulo inicial é -90° para uma estrela ficar no
 * topo — constelação com ponta para cima tem eixo, constelação girada tem cara
 * de acidente.
 *
 * AS LINHAS SE DESENHAM ao entrar na tela, uma a uma, com `stroke-dasharray` e
 * atraso por índice. É o único movimento e ele CONTA ALGUMA COISA: a ordem de
 * entrada é a ordem em que os sinais foram somados ao vetor de features, e o
 * traço indo da ponta para o centro é literalmente a convergência que a seção
 * explica. Termina e para — não é laço infinito.
 *
 * `prefers-reduced-motion` recebe tudo desenhado, de uma vez. Ver o bloco
 * `.constelacao-*` no globals.css.
 *
 * =============================================================================
 * ACESSIBILIDADE
 * =============================================================================
 *
 * O SVG é `aria-hidden`. Ele é uma ILUSTRAÇÃO do que a lista logo abaixo dele
 * diz em texto — os sete nomes e as sete descrições vivem lá, em HTML de
 * verdade, e é de lá que leitor de tela e buscador leem. Duplicar os nomes no
 * SVG como `<text>` acessível faria a lista ser anunciada duas vezes.
 *
 * Os nomes aparecem no desenho como `<text>` porque são a legenda da figura
 * para quem enxerga — e é por isso que o `<title>`/`<desc>` do SVG não foi
 * usado: não há informação aqui que a lista já não entregue melhor.
 */

/** As sete famílias, na ordem em que entraram no vetor de features. */
const ESTRELAS = [
  { nome: "texto", token: "--dito" },
  { nome: "emoji", token: "--no-emoji" },
  { nome: "tempo", token: "--tempo" },
  { nome: "emoção", token: "--emocao" },
  { nome: "léxico", token: "--lexico" },
  { nome: "ironia", token: "--ironia" },
  { nome: "estilo", token: "--estilo" },
] as const;

const LARGURA = 900;
const ALTURA = 560;
const CX = LARGURA / 2;
const CY = ALTURA / 2;
const RX = 300;
const RY = 168;

/** Sete ângulos iguais a partir do topo. Em radianos, porque `Math.cos` pede. */
function posicao(indice: number) {
  const angulo = (indice / ESTRELAS.length) * Math.PI * 2 - Math.PI / 2;
  return {
    x: CX + Math.cos(angulo) * RX,
    y: CY + Math.sin(angulo) * RY,
    // O lado do rótulo depende do lado da elipse: texto sempre para FORA, senão
    // ele cai por cima das linhas que convergem.
    ancora:
      Math.cos(angulo) > 0.25
        ? "start"
        : Math.cos(angulo) < -0.25
          ? "end"
          : "middle",
    desvioX: Math.cos(angulo) * 22,
    desvioY: Math.sin(angulo) * 20 + 5,
  } as const;
}

export function Constelacao() {
  return (
    <svg
      aria-hidden
      viewBox={`0 0 ${LARGURA} ${ALTURA}`}
      className="constelacao h-auto w-full"
      // `visible` e não o `hidden` padrão: os halos de brilho passam da caixa
      // do viewBox de propósito, e cortá-los deixaria um quadrado visível.
      style={{ overflow: "visible" }}
    >
      <defs>
        {/* O brilho. Um `feGaussianBlur` composto com o original é o que
            transforma um círculo chapado em corpo luminoso — sem ele as sete
            pontas leem como bolinhas de gráfico de dispersão. */}
        <filter id="brilho-estrela" x="-120%" y="-120%" width="340%" height="340%">
          <feGaussianBlur stdDeviation="6" result="borrado" />
          <feMerge>
            <feMergeNode in="borrado" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
        <filter id="brilho-nucleo" x="-120%" y="-120%" width="340%" height="340%">
          <feGaussianBlur stdDeviation="12" result="borrado" />
          <feMerge>
            <feMergeNode in="borrado" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {/* A ÓRBITA: a elipse que passa pelas sete estrelas. Fraquíssima, e é ela
          que faz as sete lerem como UM sistema em vez de sete pontos soltos. */}
      <ellipse
        cx={CX}
        cy={CY}
        rx={RX}
        ry={RY}
        fill="none"
        stroke="var(--compasso)"
        strokeWidth="1"
      />

      {ESTRELAS.map(({ nome, token }, i) => {
        const p = posicao(i);
        return (
          <g key={nome} className="constelacao-braco" style={{ ["--i" as string]: i }}>
            {/* A LINHA vai da estrela para o CENTRO, e essa direção importa: é
                a convergência dos sinais no fusor, não a irradiação de um
                centro para as pontas. O gradiente some perto do meio para as
                sete não empastarem num nó de tinta. */}
            <line
              x1={p.x}
              y1={p.y}
              x2={CX}
              y2={CY}
              stroke={`var(${token})`}
              strokeWidth="1.25"
              strokeLinecap="round"
              opacity="0.42"
              className="constelacao-linha"
            />
            <circle
              cx={p.x}
              cy={p.y}
              r="5.5"
              fill={`var(${token})`}
              filter="url(#brilho-estrela)"
              className="constelacao-estrela"
            />
            <text
              x={p.x + p.desvioX}
              y={p.y + p.desvioY}
              textAnchor={p.ancora}
              className="constelacao-rotulo"
              fill="var(--muted-foreground)"
            >
              {nome}
            </text>
          </g>
        );
      })}

      {/* O NÚCLEO: o score. Dois círculos — o halo largo e translúcido é a
          "atmosfera" que separa o veredito das sete leituras; sem ele o centro
          tem o mesmo peso visual de mais uma estrela, e ele não é mais uma. */}
      <circle cx={CX} cy={CY} r="46" fill="var(--medido)" opacity="0.1" />
      <circle
        cx={CX}
        cy={CY}
        r="11"
        fill="var(--medido)"
        filter="url(#brilho-nucleo)"
        className="constelacao-nucleo"
      />
      <text
        x={CX}
        y={CY + 74}
        textAnchor="middle"
        className="constelacao-rotulo"
        fill="var(--medido-texto)"
      >
        score 0–100
      </text>
    </svg>
  );
}
