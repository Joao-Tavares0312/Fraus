"use client";

import { usePathname } from "next/navigation";
import { coreografiaValeEm } from "@/lib/cena";
import { useProgressoDaCena } from "@/hooks/useProgressoDaCena";

/**
 * O ATELIE: a luz que o vidro refrata.
 *
 * Sem esta camada o reskin de vidro nao existe. Vidro sobre fundo chapado e
 * indistinguivel de um cinza um pouco mais claro, porque nao ha nada atras
 * para refratar -- `backdrop-filter` borra o que esta atras, e atras de um
 * grafite uniforme so ha mais grafite.
 *
 * Duas manchas radiais sobre o `--background`: a da marca e a fria que a
 * contrapesa. O sol listrado herdou o posto da terceira mancha, fraca, que
 * quebrava a simetria das duas -- que sozinhas leriam como gradiente de
 * template.
 *
 * As cores vem de `--atelie-marca` / `--atelie-fria`, e o desacoplamento dos
 * tokens de dado E PARCIAL -- vale dizer qual metade, porque o oposto ja foi
 * escrito aqui e era falso. No tema "chuva de neon" os dois sao literais e
 * independentes do encoding, e e isso que permite trocar a luz sem encostar
 * na camada de dado. No GRAFITE nao: `--atelie-fria` continua sendo
 * `var(--medido)`, ou seja, a propria cor do canal de dado usada como luz. A
 * consequencia e real e ja foi paga: repintar o dado move a luz do grafite
 * junto, e os pisos de vidro precisam ser remedidos quando isso acontece.
 * `--atelie-marca` e `var(--primary)` no grafite -- cor de marca, nao de dado.
 *
 * No tema grafite as duas tem croma BAIXO: elas iluminam, nao pintam. No tema
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
 *
 * TRES CAMADAS (grade, sol, estrelas) ACOMPANHAM A ROLAGEM, SO NA VITRINE:
 * `useProgressoDaCena` escreve `--cena-grade`/`--cena-planeta`/`--cena-estrelas`
 * na raiz, e cada opacidade abaixo multiplica o token de opacidade do tema por
 * essa variavel (`calc(var(--x-op) * var(--cena-x, 1))`). O fallback e 1, nao
 * o valor de hoje: assim a primeira pintura, antes do hook montar, mostra a
 * cena exatamente como ela e hoje, e o zero deliberado de `--estrelas-op` na
 * chuva sobrevive por construcao (fator vezes zero e zero). Ver `lib/cena.ts`.
 *
 * ESTE COMPONENTE MORA NO LAYOUT RAIZ e e a MESMA instancia na LP e no
 * Operate -- por isso `ativo` vem de `coreografiaValeEm(usePathname())`, nao
 * de duas versoes do `Atelier`. Ate 04/09/2026 a coreografia rodava
 * incondicionalmente e a cena acompanhava a rolagem tambem dentro da
 * ferramenta, atras de tabela e grafico -- decoracao rodando o tempo todo,
 * contra a secao 6 do DESIGN.md. Fora da vitrine `ativo` e `false` e a cena
 * fica parada no estado inicial (ver `useProgressoDaCena`), pixel a pixel
 * identica à de hoje: nada muda visualmente no Operate, ela so para de
 * reagir.
 */
export function Atelier() {
  const pathname = usePathname();
  useProgressoDaCena(coreografiaValeEm(pathname));

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

      {/* O CAMPO DE ESTRELAS -- so o tema "espaco profundo" acende (nos outros
          dois a opacidade e zero, mesmo mecanismo do asfalto e da chuva).

          TRES TILES DE TAMANHOS PRIMOS ENTRE SI (137, 191, 89), e essa e a
          peca inteira: um `background-repeat` unico ladrilha visivelmente --
          o olho acha a grade em dois segundos e o ceu vira papel de parede.
          Tres periodos sem divisor comum so repetem o conjunto a cada
          137x191x89 pixels, ou seja, nunca dentro de uma tela. E o mesmo
          truque de quebra de simetria que a terceira mancha do atelie fazia,
          aplicado a uma textura em vez de a uma luz.

          As tres camadas tambem tem BRILHO diferente (0.95 / 0.75 / 0.55) e
          nao so posicao: estrela toda do mesmo peso le como ruido de sensor.
          Profundidade num campo de pontos vem de variacao de magnitude.

          ESTATICO, sem `requestAnimationFrame`. Cintilancia rodaria um quadro
          por frame atras da tabela e do grafico que o analista le por horas,
          e a secao 6 do DESIGN.md ja gastou os dois momentos de movimento da
          interface. O espetaculo de particulas em WebGL existe -- mas na LP,
          que e visita de 40 segundos e outro contrato. Ver components/lp-nova/.

          A mascara clareia o campo no ALTO e o apaga descendo, pelo mesmo
          motivo do papel pautado: o terco de baixo pertence ao planeta e a
          grade, e estrela por cima de horizonte iluminado nao existe. */}
      <div
        className="absolute inset-0"
        style={{
          opacity: "calc(var(--estrelas-op) * var(--cena-estrelas, 1))",
          backgroundImage: [
            "radial-gradient(1.2px 1.2px at 23px 31px, oklch(0.98 0.02 230 / 0.95), transparent 100%)",
            "radial-gradient(1px 1px at 118px 74px, oklch(0.96 0.03 250 / 0.75), transparent 100%)",
            "radial-gradient(0.8px 0.8px at 47px 12px, oklch(0.94 0.04 84 / 0.55), transparent 100%)",
          ].join(","),
          backgroundSize: "137px 137px, 191px 191px, 89px 89px",
          maskImage:
            "radial-gradient(130% 105% at 50% 0%, black 25%, transparent 82%)",
          WebkitMaskImage:
            "radial-gradient(130% 105% at 50% 0%, black 25%, transparent 82%)",
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
      {/* O SOL LISTRADO: o retrosun, nascendo no horizonte da grade.

          Herda o posto da antiga "mancha quente fraca", e de propósito: a
          função dela era quebrar a simetria das outras duas manchas, e um
          disco fora do eixo faz isso melhor que um borrão. Peça nova somaria
          luz ao pior caso das superfícies translúcidas; esta apenas troca de
          forma.

          As faixas são `repeating-linear-gradient` sobre o gradiente do
          disco, cortadas pelo `rounded-full` -- o disco é a máscara, as
          faixas são o preenchimento. Elas ENGROSSAM descendo porque é assim
          que o retrosun se lê: sol se pondo, não bola listrada.

          Fica ATRÁS da grade na ordem do DOM: o sol se põe no horizonte, e o
          chão está na frente dele. */}
      <div
        className="absolute bottom-[26vh] left-[52%] h-[38vmin] w-[38vmin] -translate-x-1/2 rounded-full blur-[2px]"
        style={{
          opacity: "calc(var(--sol-op) * var(--cena-planeta, 1))",
          background:
            "repeating-linear-gradient(to bottom, transparent 0 var(--sol-faixa), oklch(0 0 0 / 0.85) var(--sol-faixa) calc(var(--sol-faixa) * 1.5))," +
            "linear-gradient(to bottom, var(--sol-cor-alta), var(--sol-cor-baixa))",
          maskImage: "linear-gradient(to bottom, black 55%, transparent 96%)",
          WebkitMaskImage:
            "linear-gradient(to bottom, black 55%, transparent 96%)",
        }}
      />

      {/* A MARCA NO FUNDO: o monograma sangrando pela quina inferior direita.

          E MASCARA, NAO IMAGEM DE FUNDO, e a distincao e o inteiro da peca.
          `fraus-marca.svg` nao carrega cor nenhuma -- sao as duas letras em
          branco puro sobre transparente, com o viewBox colado nelas. Quem
          pinta e o `background` deste div, entao a mesma marca sai dourada no
          grafite e magenta na chuva, sem gerar dois arquivos e sem tema novo
          pedir asset novo.
          Usar `fraus-logo.svg` direto como `background-image` pintaria um
          quadrado preto OPACO por cima do atelie -- ele tem um `<rect>` de
          fundo cobrindo os 640x640, e e exatamente o bug que o `SidebarInset`
          com `bg-background` ja causou, matando a luz de seis das sete telas.
          `fraus-marca.svg` e o mesmo desenho com esse `<rect>` removido e as
          duas letras forcadas a branco.

          E VETOR, e a troca importa: o PNG anterior tinha 461px de largura e
          era esticado para perto de 800px na tela, entao a marca chegava
          borrada justo na escala em que ela e grande. Mascara em SVG nao tem
          escala nativa para perder.

          O "fade + gradiente" e a SEGUNDA camada de mascara: `mask-composite:
          intersect` corta a marca contra um gradiente radial ancorado na
          quina, entao ela nasce solida onde sai da tela e se dissolve subindo
          para o centro. Sem isso ela leria como adesivo colado; com isso, como
          marca d'agua impressa no papel.

          Fica DEPOIS das manchas de luz (a sala ilumina o papel, a marca esta
          impressa nele e recebe a luz por cima) e ANTES do asfalto e da chuva
          -- chuva cai na FRENTE da fachada, nao atras. */}
      <div
        className="absolute -bottom-[10%] -right-[8%] h-[72vmin] w-[72vmin]"
        style={{
          opacity: "var(--marca-op)",
          background: "var(--marca-cor)",
          // O `-webkit-` continua obrigatorio: o Safari so implementa `mask`
          // sem prefixo desde a 15.4, e a versao prefixada nao entende
          // `mask-composite: intersect` -- ela usa `source-in`.
          WebkitMaskImage:
            "url(/fraus-marca.svg), radial-gradient(150% 150% at 100% 100%, black 34%, transparent 96%)",
          WebkitMaskSize: "contain, cover",
          WebkitMaskRepeat: "no-repeat, no-repeat",
          WebkitMaskPosition: "center, center",
          WebkitMaskComposite: "source-in",
          maskImage:
            "url(/fraus-marca.svg), radial-gradient(150% 150% at 100% 100%, black 34%, transparent 96%)",
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
            opacity: "calc(var(--grade-op) * var(--cena-grade, 1))",
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
