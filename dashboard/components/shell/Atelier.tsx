/**
 * O ATELIE: a luz que o vidro refrata.
 *
 * Sem esta camada o reskin de vidro nao existe. Vidro sobre fundo chapado e
 * indistinguivel de um cinza um pouco mais claro, porque nao ha nada atras
 * para refratar -- `backdrop-filter` borra o que esta atras, e atras de um
 * grafite uniforme so ha mais grafite.
 *
 * Tres manchas radiais sobre o `--background`: a da marca, a fria que a
 * contrapesa, e uma terceira fraca que quebra a simetria das duas -- que
 * sozinhas leriam como gradiente de template.
 *
 * As cores vem de `--atelie-marca` / `--atelie-fria` / `--atelie-quente`, e
 * NAO dos tokens de dado. O atelie usava `--dito` e `--medido` emprestados, o
 * que amarrava a iluminacao da sala ao canal que carrega significado. Sao
 * token proprio desde 24/08/2026, o que tambem e o que permite ao tema
 * "chuva de neon" trocar a luz sem encostar no encoding.
 *
 * No tema grafite as tres tem croma BAIXO: elas iluminam, nao pintam. No tema
 * chuva o croma sobe, e pode subir justamente porque esta camada nao carrega
 * dado nenhum -- cor saturada aqui nao inventa canal de significado.
 *
 * E ESTATICO, e isso e uma decisao, nao uma pendencia. A alternativa avaliada
 * -- a luz mudar de cor conforme o resultado do periodo -- foi rejeitada: ela
 * criaria um canal de cor sem rotulo, contra o principio de que categoria
 * nunca e comunicada so por cor, e contra a regra de que a cor da marca nunca
 * codifica valor. Ver DESIGN.md, seccao 3.3.
 *
 * `aria-hidden` e `pointer-events-none` porque isto nao e conteudo nem alvo:
 * e o papel de parede da sala.
 */
export function Atelier() {
  return (
    <div
      aria-hidden
      className="pointer-events-none fixed inset-0 -z-10 overflow-hidden bg-background"
    >
      {/* O PAPEL PAUTADO: linhas horizontais de ritmo constante, nos DOIS
          temas.

          NAO E UM PENTAGRAMA, e a distincao nao e preciosismo: a secao 1.1 do
          DESIGN.md proibe desenhar glifo musical e manda a gramatica entrar
          como estrutura e ritmo. Agrupar em cincos seria desenhar a pauta;
          ritmo constante e papel pautado. A regua do sistema (`--linha`)
          continua sendo a unica linha que AFIRMA algo -- estas sao papel, e
          por isso moram aqui, na camada que nao carrega dado.

          VEM ANTES das manchas de luz, de proposito: o papel esta EMBAIXO da
          iluminacao da sala, entao a luz passa por cima dele e o realca de um
          lado. Desenhado por cima, ele leria como grade sobreposta.

          A mascara faz o fade duplo -- as linhas nascem no topo e se apagam
          descendo, e tambem se apagam para as bordas laterais. Sem ela a
          textura ladrilharia a tela inteira com peso igual, que e a diferenca
          entre papel e papel de parede. */}
      <div
        className="absolute inset-0"
        style={{
          opacity: "var(--pauta-op)",
          background:
            "repeating-linear-gradient(to bottom, var(--pauta-cor) 0 var(--pauta-peso), transparent var(--pauta-peso) var(--pauta-espaco))",
          maskImage:
            "radial-gradient(140% 100% at 50% -10%, black 15%, transparent 70%)",
        }}
      />

      {/* dourada -- a marca, alto a esquerda */}
      <div
        className="absolute -left-[15%] -top-[25%] h-[70vmax] w-[70vmax] rounded-full blur-[80px]"
        style={{
          opacity: "var(--atelie-op-marca)",
          background:
            "radial-gradient(closest-side, var(--atelie-marca), transparent)",
        }}
      />
      {/* fria -- contrapeso do lado do medido, baixo a direita */}
      <div
        className="absolute -bottom-[30%] -right-[20%] h-[75vmax] w-[75vmax] rounded-full blur-[90px]"
        style={{
          opacity: "var(--atelie-op-fria)",
          background:
            "radial-gradient(closest-side, var(--atelie-fria), transparent)",
        }}
      />
      {/* quente fraca -- quebra a simetria das outras duas */}
      <div
        className="absolute left-[45%] top-[55%] h-[45vmax] w-[45vmax] rounded-full blur-[100px]"
        style={{
          opacity: "var(--atelie-op-quente)",
          background:
            "radial-gradient(closest-side, var(--atelie-quente), transparent)",
        }}
      />

      {/* A MARCA NO FUNDO: o monograma sangrando pela quina inferior direita.

          E MASCARA, NAO IMAGEM DE FUNDO, e a distincao e o inteiro da peca.
          `fraus-marca.png` nao carrega cor nenhuma -- e branco puro com o alfa
          derivado da luminancia do logotipo. Quem pinta e o `background` deste
          div, entao a mesma marca sai dourada no grafite e ciano/magenta na
          chuva, sem gerar dois arquivos e sem tema novo pedir asset novo.
          Usar o PNG original como `background-image` pintaria um quadrado
          #070707 OPACO por cima do atelie -- que e exatamente o bug que o
          `SidebarInset` com `bg-background` ja causou, matando a luz de seis
          das sete telas.

          O "fade + gradiente" e a SEGUNDA camada de mascara: `mask-composite:
          intersect` corta a marca contra um gradiente radial ancorado na
          quina, entao ela nasce solida onde sai da tela e se dissolve subindo
          para o centro. Sem isso ela leria como adesivo colado; com isso, como
          marca d'agua impressa no papel.

          Fica DEPOIS das manchas de luz (a sala ilumina o papel, a marca esta
          impressa nele e recebe a luz por cima) e ANTES do asfalto e da chuva
          -- chuva cai na FRENTE da fachada, nao atras. */}
      <div
        className="absolute -bottom-[12%] -right-[10%] h-[115vmin] w-[115vmin]"
        style={{
          opacity: "var(--marca-op)",
          background: "var(--marca-cor)",
          // O `-webkit-` continua obrigatorio: o Safari so implementa `mask`
          // sem prefixo desde a 15.4, e a versao prefixada nao entende
          // `mask-composite: intersect` -- ela usa `source-in`.
          WebkitMaskImage:
            "url(/fraus-marca.png), radial-gradient(150% 150% at 100% 100%, black 34%, transparent 96%)",
          WebkitMaskSize: "contain, cover",
          WebkitMaskRepeat: "no-repeat, no-repeat",
          WebkitMaskPosition: "center, center",
          WebkitMaskComposite: "source-in",
          maskImage:
            "url(/fraus-marca.png), radial-gradient(150% 150% at 100% 100%, black 34%, transparent 96%)",
          maskSize: "contain, cover",
          maskRepeat: "no-repeat, no-repeat",
          maskPosition: "center, center",
          maskComposite: "intersect",
        }}
      />

      {/* O REFLEXO NO ASFALTO -- so a chuva acende (no grafite a opacidade e
          zero). Faixa larga subindo do rodape: e o que transforma "fundo roxo
          com manchas" em "fachada espelhada no chao molhado". Fica DEPOIS das
          manchas para se somar a elas, e nao por baixo. */}
      <div
        className="absolute inset-x-0 bottom-0 h-[45vh] blur-[60px]"
        style={{
          opacity: "var(--atelie-asfalto)",
          background:
            "linear-gradient(to top, var(--atelie-fria), transparent 78%)",
        }}
      />

      {/* A GRADE A LASER: o chao da cena.

          A perspectiva e o truque inteiro, e precisa de DOIS elementos, nao
          um. Correcao de 24/08/2026: a primeira versao punha `perspective()`
          dentro da propria funcao `transform` do elemento rotacionado -- e um
          elemento so, girado 74deg em torno da propria borda de baixo, fica
          quase de perfil e COLAPSA numa faixa fina colada no rodape em vez de
          se estender ate um horizonte. Pior: nada recortava a metade do plano
          que passa do ponto de fuga, e ela se projetava de volta ACIMA do
          horizonte como uma malha cobrindo a tela inteira -- o artefato
          classico de `rotateX` alto com `perspective` curta demais.

          A tecnica correta separa CONTEINER de PLANO:
          - o CONTEINER fica ancorado no rodape, com `perspective` como
            PROPRIEDADE CSS dele (nao dentro de `transform`) -- e isso que faz
            o ponto de fuga ser o do conteiner, produzindo convergencia de
            verdade em vez de um plano so comprimido. `overflow-hidden` no
            conteiner e OBRIGATORIO: e ele que come a metade espelhada do
            plano que passaria do horizonte. Tirar o `overflow-hidden` para
            "simplificar" reintroduz a malha cobrindo a tela.
          - o PLANO INTERNO e bem mais alto que o conteiner (`h-[200%]`) e e
            SO ELE que gira em `rotateX`, com `transformOrigin` na propria
            borda de baixo. As linhas que correm para o fundo CONVERGEM
            sozinhas, porque a projecao em perspectiva faz isso; nao ha
            gradiente conico nem SVG envolvido.

          `inset-x-[-50%]` no plano interno, e nao `inset-x-0`: rotacionado,
          o plano encolhe na horizontal perto do horizonte e mostraria borda
          se tivesse a largura da tela. Sangrar meia tela para cada lado
          resolve sem custo.

          A mascara, no plano interno, apaga a grade subindo, para ela virar
          horizonte em vez de parar numa linha reta -- que leria como o fim
          de uma textura, e nao como distancia.

          ESTATICA. Ver o comentario da chuva logo abaixo sobre por que. */}
      <div
        className="absolute inset-x-0 bottom-0 h-[45vh] overflow-hidden"
        style={{
          perspective: "var(--grade-horizonte)",
          perspectiveOrigin: "50% 0%",
        }}
      >
        <div
          className="absolute inset-x-[-50%] bottom-0 h-[200%]"
          style={{
            opacity: "var(--grade-op)",
            background:
              "repeating-linear-gradient(to right, var(--grade-cor) 0 1px, transparent 1px var(--grade-espaco))," +
              "repeating-linear-gradient(to bottom, var(--grade-cor) 0 1px, transparent 1px var(--grade-espaco))",
            transform: "rotateX(68deg)",
            transformOrigin: "bottom center",
            maskImage: "linear-gradient(to top, black 0%, transparent 92%)",
            WebkitMaskImage: "linear-gradient(to top, black 0%, transparent 92%)",
          }}
        />
      </div>

      {/* A CHUVA: riscos diagonais finos, ESTATICOS.
          Por que nao cai: a secao 6 do DESIGN.md ja gastou os dois momentos de
          movimento que a interface se permite, e chuva animada seria um
          terceiro que nao comunica estado nenhum -- decoracao pela decoracao,
          rodando atras de tabela e grafico o tempo todo. Estatica ela entrega
          a TEXTURA (o vidro tem o que refratar) sem cobrar quadro nenhum.
          `repeating-linear-gradient` e mascara em vez de mil elementos. */}
      <div
        className="absolute inset-0"
        style={{
          opacity: "var(--atelie-chuva)",
          background:
            "repeating-linear-gradient(74deg, transparent 0 6px, oklch(0.92 0.08 250) 6px 7px, transparent 7px 19px)",
          maskImage:
            "radial-gradient(120% 90% at 50% 0%, black 20%, transparent 75%)",
        }}
      />
    </div>
  );
}
