# Dashboard do Fraus

Aplicativo de três seções sobre um app shell com sidebar:

- **Visão geral** — os quatro indicadores com faixa de referência, o gráfico
  sobreposto de NPS × latência, a distribuição das notas inferidas, os piores
  atendimentos e o vocabulário característico de cada categoria.
- **Atendimentos** — tabela filtrável, exportável, e o detalhe de cada
  transcrição com latência anotada e as contribuições daquele atendimento.
- **Modelo** — peso global das 40 features, métricas do treino, lexicon de
  emoji navegável e o **simulador ao vivo** de `POST /modelo/simular`.

Um **filtro de período global** (`?de=&ate=` na URL) recorta indicadores, série,
tabela e export ao mesmo tempo, e viaja junto na navegação.

Next.js (App Router) · TypeScript · **shadcn/ui sobre Tailwind v4, tokens em
OKLCH, tema escuro único** · Recharts · TanStack Table. Export de CSV usa `Blob`
nativo. O contrato visual está em [`DESIGN.md`](DESIGN.md).

## Rodar

```bash
cp .env.local.example .env.local   # FRAUS_API_URL=http://localhost:8000
npm install
npm run dev
npm run contraste                  # verifica AA dos tokens por cálculo
```

As variáveis que o app lê são **server-side**: `FRAUS_API_URL` (destino das
chamadas, tanto dos Server Components quanto do proxy `/api/fraus`) e
`FRAUS_CHAVE_ACESSO` (a chave `fra_...`, anexada como `Authorization: Bearer`
e necessária só quando a API sobe com `FRAUS_CHAVE_MESTRA`). Sem o prefixo
`NEXT_PUBLIC_`, elas não são embutidas no bundle do navegador — que é a razão
de a chave morar aqui e não em `NEXT_PUBLIC_*`. Mudá-las exige reiniciar o
processo. `NEXT_PUBLIC_API_URL` não é destino de chamada nenhuma: sobrevive só
como o endereço exibido no exemplo de `curl` da tela de integrações.

A API precisa estar no ar. Enquanto o modelo do Colab não existe, use o servidor
de demonstração da raiz do repositório — **só para desenvolvimento**:

```bash
cd .. && uv run python scripts/api_demo.py
```

## O que a interface não pode violar

1. `score: null` aparece como **"sem sinal"**, nunca como nota 0 — em célula,
   gráfico, ordenação, export e agregado.
2. Agregado sem dado é **estado vazio**, não zero.
3. O NPS é **inferido do texto**, não perguntado ao cliente — sempre rotulado
   como estimativa, com nota metodológica.
4. NPS e latência aparecem **sobrepostos** no mesmo gráfico, com as três
   mitigações do `DESIGN.md` (domínio fixo, eixos rotulados e coloridos com a
   série + latência tracejada, visão de tabela no mesmo painel).
5. Faixas de NPS **lidas de `GET /modelo`**, não digitadas aqui.
6. `importancias` (peso global) e `contribuicoes` (o que pesou naquele
   atendimento, com sinal) nunca aparecem sem distinção — telas, geometrias e
   cores diferentes.
7. Falha de um painel derruba apenas ele.
8. Lime só na marca, nunca em dado.

## Convenções

- Identificadores em português, sem acento em nomes de símbolo.
- **Âmbar (`--dito`) é o que foi dito; azul (`--medido`) é o que foi medido**;
  `--tempo` é latência e é sempre tracejada. A escala divergente de NPS
  (detrator/neutro/promotor) é reservada e nunca vira cor de série.
- Cor de marcação e cor de tipo não são a mesma coisa: quando um token de dado
  carrega texto, entra a variante `-texto`, verificada por cálculo em
  `scripts/contraste.mjs`.
- Todo número estimado carrega o sublinhado pontilhado de proveniência
  (`.estimado` em `app/globals.css`); número observado não carrega. Número que
  se compara é monoespaçado e tabular (`.num`).
- Onde a API não expõe o dado, a tela mostra um estado vazio que nomeia o
  endpoint ou a etapa que resolveria — nunca um número inventado.
