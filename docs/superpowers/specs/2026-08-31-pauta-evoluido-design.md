# Pauta evoluído — spec do refinamento do design system

**Data:** 31/08/2026
**Estado:** direção aprovada pelo dono do projeto ("evoluir o Pauta", decisão
de 31/08/2026); aguardando plano de implementação.
**Base:** pesquisa sobre os sites indicados pelo João (Howard Le, Revolut,
Cloudflare, Stripe, Lando Norris, Corn Revolutionized, Personaal Studio) mais
os design systems de produto documentados de Stripe, Linear, Vercel/Geist e
Revolut UI.

---

## 1. A decisão de rumo

O Pauta **não é substituído**. O grafite continua a identidade, a chuva de
neon continua opção, e os intocáveis continuam intocáveis: âmbar = dito /
azul = medido, dourado só em ação, textos de honestidade, NPS × latência
sobreposto. O que entra são os refinamentos que os produtos de referência
provam — e um **terceiro tema, claro**, que era pendência declarada do João
(a banca pode projetar em telão claro).

## 2. O que a pesquisa concluiu (síntese)

Os sete sites convergem em disciplina, não em estilo:

1. **Base quase-monocromática + um acento.** Cor nunca é decoração; é sinal.
   (O Pauta já cumpre — é a regra do §3 do DESIGN.md.)
2. **Nunca preto/branco puro em texto.** Stripe `#0A2540`, Revolut `#191C1F`,
   Linear `#F7F8F8` sobre `#08090A`. O "premium" mora nos meios-tons.
   (O grafite já cumpre; o tema claro precisa nascer cumprindo.)
3. **Hierarquia por tamanho + tracking negativo, não por peso 700.** Display
   em peso 400–550; tracking até −0.02em (nunca mais que isso em dado).
4. **Zero ou quase zero sombra.** Profundidade por degraus de superfície e
   borda de 1px (Linear, Vercel, Revolut).
5. **Fonte de UI "engenheirada" + números tabulares em todo dado.** Inter com
   `cv01`/`ss03` (o ajuste do Linear) e `tnum` — o Pauta já exige `.num`;
   a família é o que muda.
6. **Tokens semânticos em camadas.** Primitivo → semântico → camada de
   gráfico; componente só consome semântico. (O Pauta já faz; formalizar.)
7. **Motion curto e com propósito**: 120–300ms no produto; espetáculo só em
   site-vitrine. (A §6 do DESIGN.md já é mais rigorosa que o mercado —
   mantém-se.)

## 3. As mudanças, uma a uma

### 3.1 Tipografia: Inter variável, com mono nos dados

Sai a "sans de sistema", entra **Inter** (self-hosted via `next/font`, não
Google Fonts em runtime — nenhuma chamada de rede no caminho do analista) com
`font-feature-settings: "cv01", "ss03"` e `"tnum"` ligado em todo número que
se compara. **JetBrains Mono** (ou Geist Mono) para IDs de conversa,
timestamps e valores de KPI — o efeito Vercel: dado parece instrumento.

O que a §4 do DESIGN.md mantém: escala fixa em rem, razão apertada, dinâmica
por peso e tamanho sem gastar cor, medida de prosa 65–75ch, proibição de
fonte de display em rótulo e dado. A LP é a exceção já registrada: única tela
com licença de display.

Pesos intermediários da variável (450, 550) em vez de saltar de 400 para 700.
Tracking: −0.01em em títulos de painel, −0.02em só em display; **nunca**
negativo em célula de tabela.

### 3.2 Espaçamento e densidade: a escala vira contrato

Escala única em múltiplos de 4 — `4, 8, 12, 16, 24, 32, 48, 64` — declarada e
auditável. Tabelas: linha de 40px padrão (modo denso 36px), célula 12px
vertical / 16px horizontal, número alinhado à direita, texto à esquerda.
Padding de painel: 16–20px. Gap entre sistemas: 24px+, com o ritmo vertical
da §2.2 (mais espaço acima de título do que abaixo) preservado.

### 3.3 Elevação: o vidro fica, a sombra míngua

O vidro líquido é identidade e fica. O refinamento é no que está **em volta**
dele: sombra só em superfície flutuante real (dropdown, sheet), nunca em
painel apoiado; no claro, no máximo `0 1px 2px` a 5%. O contraste segue
governando a espessura — a regra da §7 não se move.

### 3.4 O tema claro (terceiro tema)

- Nasce como os outros: classe `.tema-claro` no `<html>`, só sobrepõe tokens,
  `scripts/contraste.mjs` já roda a matriz por tema sem mudança.
- Papel: fundo `oklch(~0.97 0.002 80)` (papel quente, nunca `#FFF` puro),
  superfície branca, tinta `oklch(~0.25)` (nunca preto puro), borda 1px no
  lugar de degrau de luz.
- **O ateliê quase apaga no claro**: papel pautado e marca impressa em
  opacidade mínima, grade e sol em zero — luz atrás de vidro é fenômeno de
  cena escura; num papel claro o vidro vira superfície com borda. Os pisos
  (`npm run pisos`) precisam ser medidos para o tema novo antes de qualquer
  ajuste fino.
- Âmbar/azul/dourado mantêm matiz e trocam claridade/croma para cruzar AA
  sobre claro — o mesmo movimento que a chuva fez no escuro, já com
  precedente na §8.2.
- O `dark` fixo do `<html>` deixa de ser fixo: o tema claro remove a classe.
  O `SCRIPT_ANTI_PISCADA` já existe e cobre a troca antes da pintura.
- O grafite **continua o padrão de fábrica**.

### 3.5 O que fica explicitamente como está

Régua dito/medido, cabeça vazada do sem-sinal, chanfro de 45° e radius 2px
(é a marca, não tendência), os dois momentos de movimento, a mentira
encenada dos cinco cliques, e os dois temas escuros existentes.

## 4. O que NÃO entra (alertas da pesquisa)

- WebGL, scroll-jacking, cinemática (Corn Revolutionized, Lando Norris) — a
  antítese de ferramenta de leitura de dados.
- Pills de 48px e radius 24px (Revolut) — roubam densidade; o chanfro é a
  identidade daqui.
- Lime neon como cor de dado (Lando/Linear) — não passa contraste no claro e
  colidiria com o encoding.
- Playfulness estrutural (Personaal, Howard Le) — emojis e urgência minam a
  credibilidade perante a banca; charme só em microinteração de ~120ms.
- Gradiente animado de hero (Stripe) — nem na LP: o ateliê já é a atmosfera.

## 5. Ordem de implementação sugerida

1. Tipografia (Inter + mono + features) — mexe em tudo, mede-se com
   `npm run contraste` e olho.
2. Escala de espaçamento e densidade de tabela.
3. Tema claro (tokens + pisos + contraste + olho nas telas cheia e vazia).
4. Passada de sombra/elevação.

Cada etapa termina com o ciclo completo da §9 do DESIGN.md — os cinco gates
e o olho, nos (agora) três temas.
