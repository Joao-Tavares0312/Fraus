# Vaporwave assumido — spec de design

**Data:** 2026-08-24
**Decisão de:** dono do projeto
**Escopo:** `dashboard/` — ateliê, chassi e camada de dado, nos **dois** temas

---

## 1. O pedido

Empurrar o Fraus para um vaporwave assumido, com inspiração no vocabulário
estabelecido da estética. Três decisões tomadas pelo dono do projeto:

1. **Os dois temas**, com a **mesma estrutura**. As peças existem no componente
   nos dois e o tema decide cor e intensidade — o padrão que o ateliê já usa.
   Os dois sobem de nível, para comparação posterior; qual prevalece é decisão
   de outro dia.
2. **O corte vai até a camada de dado**, e não só até o papel de parede.
3. **A camada de dado ganha neon com o matiz travado**: croma e claridade
   sobem, o matiz de cada família fica.

## 2. O vocabulário, e de onde ele vem

Pesquisa em referências de vaporwave/synthwave aplicado a interface. Os
elementos que aparecem de forma consistente:

| Elemento | Aparece como |
|---|---|
| grade a laser em perspectiva | plano fugindo ao ponto de fuga; o chão de toda cena |
| retrosun | sol listrado, gradiente do amarelo ao magenta |
| scanlines / CRT | linhas horizontais finas, sugerindo varredura e erro de tracking |
| glow no lugar de sombra | halo colorido; o elemento emite em vez de bloquear |
| geometria angular | cantos duros (~2px), perspectiva, ângulos fechados |
| croma alto sobre fundo escuro | ciano, magenta, violeta sobre quase-preto |

**O que fica de fora, e por quê:** aberração cromática em texto (briga com o
portão e com legibilidade de prosa metodológica), glitch animado (a §6 já gastou
os dois momentos de movimento da interface), palmeira e busto romano (fantasia
literal — a §1.1 já recusa esse tipo de citação para o vocabulário musical, e a
razão vale aqui).

Referências:
- <https://styleshift.design/styles/synthwave>
- <https://digitalheroesco.com/styles/vaporwave/>
- <https://retrowave.com/the-ultimate-outrun-color-palette-guide-for-retro-vibes/>
- <https://aesthetics.fandom.com/wiki/Synthwave>

## 3. Ateliê — a grade e o sol

### 3.1 A grade a laser

O "reflexo no asfalto" de hoje é uma faixa de luz difusa subindo do rodapé. Ela
passa a ser **chão**: linhas fugindo ao ponto de fuga mais linhas horizontais
comprimindo com a distância, em `perspective` + `rotateX`, desenhada com
`repeating-linear-gradient` — não mil elementos.

**Estática**, pelo mesmo motivo que a chuva não cai: a §6 já gastou os dois
momentos de movimento, e grade animada seria um terceiro que não comunica
estado nenhum.

Tokens: `--grade-cor`, `--grade-op`, `--grade-espaco`, `--grade-horizonte`.
O grafite recebe ouro fosco; a chuva, ciano.

### 3.2 O sol listrado

**Não é peça nova.** É a mancha quente que já existe no ateliê ganhando faixas
horizontais e borda definida, reposicionada para nascer no horizonte da grade.
No grafite ele é a lâmpada de sódio do poste (a §8.1 já estabeleceu essa
leitura); na chuva, o retrosun magenta-coral.

Tokens: `--sol-cor-alta`, `--sol-cor-baixa`, `--sol-op`, `--sol-faixa`.

### 3.3 A pauta já é scanline

Linha horizontal de ritmo constante **é** varredura de CRT — o mesmo desenho
com outro nome. Nenhum código novo, e continua não sendo pentagrama (§1.1).
Registrado aqui para que a próxima sessão não a reimplemente sob outro nome.

### 3.4 Por que essas peças são baratas

A grade e o sol moram no **terço de baixo**, onde a máscara da pauta já zerou e
onde a marca impressa já vive. `scripts/pisos.mjs` compõe a **mais clara das
alternativas** daquela região em vez de somá-las, porque as máscaras são
disjuntas. Enquanto grade e sol ficarem abaixo do teto da pauta, o vidro não
engrossa um ponto.

**Isso é uma restrição de projeto, não uma esperança:** a intensidade de cada
peça nova é escolhida no teto em que ela ainda não é a camada que manda no
piso. O script diz qual camada venceu; se a resposta deixar de ser "papel
pautado", a peça passou do teto.

## 4. Chassi — o chanfro no lugar do raio

### 4.1 O chanfro

O canto arredondado sai; entra **chanfro a 45°**, recortado do próprio
monograma.

A §3.3.1 já argumentava nessa direção: `--radius` caiu de 0,625rem para
0,375rem porque "o F e o R são chanfrados a 45° e não têm uma curva de canto
sequer", e só **não foi a zero** para não brigar com o resto do chassi. Com o
chassi inteiro endurecendo, a objeção deixa de existir. O chanfro é mais fiel à
marca que o raio — que a estética peça exatamente isso é coincidência
conveniente, não a justificativa.

Vale para os dois temas: é **estrutura**, e a decisão foi estrutura igual.

### 4.2 Glow no lugar de sombra

Na chuva já existe (derrame violeta). O grafite ganha a versão em ouro fosco.
Sombra preta sob painel que flutua sobre luz lê como buraco.

### 4.3 Réguas e quinas

Sobem nos dois temas, nos tokens que já existem: `--linha`, `--compasso`,
`--vidro-quina`, `--vidro-quina-baixa`.

### 4.4 Custo

**Zero de contraste.** Nenhuma das três clareia o fundo atrás do vidro. O que
elas pedem é varredura de componente, não remedição.

## 5. Camada de dado — neon com matiz travado

### 5.1 A regra

As sete famílias de sinal (`--dito`, `--medido`, `--tempo`, `--emocao`,
`--lexico`, `--ironia`, `--estilo`) e as três categorias de NPS (`--detrator`,
`--neutro`, `--promotor`), mais os pares `-texto` de cada uma, ganham **croma e
claridade**. **O matiz de cada uma não se move.**

O matiz é o que carrega o significado. Quem aprendeu a cor num print do
trabalho continua lendo no outro; muda a voltagem, não o vocabulário.

### 5.2 O teto é do portão, cor por cor

`npm run contraste` continua sendo quem decide: `--*-texto` cruza 4,5:1 e
`--*` de marcação cruza 3:1, agora contra pisos de vidro mais claros. Cor que
não couber **para onde couber**, e o relatório registra qual foi e quanto
sobrou. O portão nunca é afrouxado.

### 5.3 As nove cores que o portão não enxerga entram junto

`scripts/contraste.mjs` só faz parse de `oklch()` literal, e existem nove
tokens escritos em `hsl()`: `--destructive-rich-*`, `--success-rich-*`,
`--warning-rich-*`. **Três carregam texto e nunca foram medidos, em tema
nenhum** — e o rosa de `--destructive-rich-text` sobre o índigo da chuva já foi
confirmado ilegível numa captura de tela.

Eram dívida de outra PR, e passam a ser desta. O motivo é direto: uma spec que
repinta a camada de dado inteira e deixa três cores de texto cegas entrega uma
inconsistência pior do que a que encontrou, e o relatório sairia verde sem ter
medido justamente as cores que já se sabe quebradas.

Convertidos para `oklch()` com o matiz preservado, o gate passa a enxergá-los
sem nenhuma mudança no script — que era o modo de falha silenciosa que o
próprio comentário da lista `fundos` descreve.

### 5.4 O que não muda

- **`--primary` continua fora de dado.** É a regra da §3.3 que separa o dourado
  fosco da marca (croma 0,085) do âmbar saturado do "dito" (croma 0,15) —
  metálico contra pigmento. Subir o croma do dito **afasta** os dois, não
  aproxima.
- **Categoria continua acompanhada de rótulo textual** (`PRODUCT.md`).
- **Nada que carrega dado vira translúcido** (§7).

### 5.5 A emenda que isto exige

A §8.2 do `DESIGN.md` diz que a camada de dado inteira fica como está e que o
magenta vive só no ateliê. **Isso passa a não valer**, por decisão do dono do
projeto, e a emenda precisa dizer o que continua de pé: o matiz de cada família
é intocado, então o *encoding* — que é o compromisso real do `PRODUCT.md` —
sobrevive. O que muda é a saturação, e ela nunca carregou significado.

Registrar também a correção de rota: a §8.2 apresentava "a camada de dado não
muda com o tema" como compromisso vinculante do `PRODUCT.md`. Não é. O
`PRODUCT.md` exige AA por cálculo e categoria nunca comunicada só por cor;
ambos continuam valendo. A regra da §8.2 era decisão de design, e é dela que
esta spec é emenda.

## 6. O teto, e o que fazer quando bater nele

Cada peça acesa no ateliê levanta o pior caso das superfícies translúcidas, e a
espessura do vidro ganha opacidade até o portão passar (§7). **Vidro grosso
apaga o ateliê que a peça acabou de acender** — na chuva ele já está em 81% no
fino e 85% no médio.

A ordem quando bater no teto, e ela não é negociável:

1. A espessura cede primeiro. O portão nunca é afrouxado.
2. Se a espessura passar de ~90%, **a peça nova é que cede** — vidro a 90% não
   é vidro, e o reskin inteiro morreria para proteger uma superfície que quase
   ninguém vê.
3. Baixar a luz para salvar o contraste continua sendo resolver pelo lado
   errado, **exceto** no caso 2, onde a alternativa é perder a materialidade.

Isso é reportado, não escondido: se uma peça ficou abaixo do que o pedido
queria, a spec de fechamento diz qual e por quê.

## 7. Verificação

Nenhuma destas é opcional:

- `npm run pisos` — os pisos no CSS batem com os medidos, em ambos os temas.
- `npm run contraste` — verde nos dois temas.
- `npx tsc --noEmit` e `npm run lint` — limpos.
- **Conferência no navegador, nos dois temas, em pelo menos uma tela cheia e
  uma tela vazia.** Duas rodadas de trabalho visual já foram entregues sem uma
  única conferência, e foi assim que "chamativo" saiu invisível. Prova por
  cálculo não substitui olhar.
- `uv run pytest -q` — 428 passam (nada de Python muda; é sanidade).

## 8. Emendas de documento obrigatórias

O projeto é acadêmico e julgado por rigor; código citando documento que não diz
aquilo é o defeito mais caro que existe aqui.

- **§3.1** — a grade e o sol entram no fundo.
- **§3.3.1** — o raio vira chanfro, com o argumento da própria seção.
- **§8.2** — a camada de dado passa a acompanhar o tema, com matiz travado; e a
  correção sobre o que é de fato compromisso do `PRODUCT.md`.
- **§8.5** — a tabela de "onde a chuva pode gritar" passa a valer para os dois
  temas.

## 9. Fora de escopo

- Figura contra fundo por matiz (`--medido` 265 sobre fundo 274). Contraste mede
  luminância, não matiz; é julgamento de olho e entra na conferência da §7.
- Animação de qualquer tipo.
