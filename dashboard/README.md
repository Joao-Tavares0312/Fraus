# Dashboard do Dolos

Interface de leitura dos atendimentos: quatro indicadores, o gráfico sobreposto
de NPS × latência, a distribuição das notas inferidas, o vocabulário
característico de cada classe, a tabela de atendimentos e o detalhe de cada
transcrição.

Next.js (App Router) · TypeScript · Tailwind · Recharts · TanStack Table ·
react-to-print. Export de CSV usa `Blob` nativo.

## Rodar

```bash
cp .env.local.example .env.local   # NEXT_PUBLIC_API_URL=http://localhost:8000
npm install
npm run dev
```

A API precisa estar no ar. Enquanto o modelo do Colab não existe, use o servidor
de demonstração da raiz do repositório — **só para desenvolvimento**:

```bash
cd .. && uv run python scripts/api_demo.py
```

## O que a interface não pode violar

1. `score: null` aparece como **"sem sinal"**, nunca como nota 0.
2. O NPS é **inferido do texto**, não perguntado ao cliente — sempre rotulado
   como estimativa, com nota de rodapé.
3. NPS e latência aparecem **sobrepostos** no mesmo gráfico, com eixos Y
   distintos, para deixar o trade-off visível.
4. Faixas de NPS: 0–6 detrator, 7–8 neutro, 9–10 promotor. A faixa saudável de
   CSAT (75–85%) fica marcada visualmente.
5. Falha de um indicador derruba apenas o card dele.

## Convenções

- Identificadores em português, sem acento em nomes de símbolo.
- Azul = grandeza **inferida**, laranja = grandeza **observada**. A paleta de
  status (detrator/neutro/promotor) é reservada e nunca vira cor de série.
- Todo número estimado carrega o sublinhado pontilhado de proveniência
  (`.estimado` em `app/globals.css`); número observado não carrega.
- Onde a API não expõe o dado, a tela mostra um estado vazio que nomeia o
  endpoint que resolveria — nunca um número inventado.
