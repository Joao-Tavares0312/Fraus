# Dashboard do Fraus

Next.js 16.3.6 (App Router), React 19 e TypeScript. Interface Instrumento com
shadcn/ui sobre Base UI, Tailwind v4, dois temas escuros e Recharts. O contrato
visual está em [DESIGN.md](DESIGN.md); o contrato de produto, em
[PRODUCT.md](PRODUCT.md).

## Seções

| Seção | O que oferece |
|---|---|
| Visão geral | indicadores, série de NPS × latência, distribuição de notas, piores atendimentos e vocabulário |
| Atendimentos | tabela filtrável, exportação autorizada e detalhe da transcrição com contribuições |
| Analisar | arquivo ou texto, análise avulsa ou gravação das conversas analisadas no banco real |
| Modelo | pesos das **39 features**, métricas, léxicos e simulador |
| Grafo | relações derivadas das conversas persistidas e do período selecionado |
| Configurações | parâmetros e administração disponíveis ao papel global autorizado |
| Integrações | fontes, ingestão e webhook |
| Operação | Radar, Equipe e escala, Jornadas, Investigações, Replay, Laboratório e Acessos |

O filtro de período (`?de=&ate=`) acompanha a navegação e recorta indicadores,
série, tabela e exportação. Gravar em Analisar atualiza os dados do dashboard
e oferece navegação para o período salvo e o grafo; os indicadores vêm da API.

Equipes têm proprietário, gestor e membro. Convites expirantes são gerados em
Equipe e escala e aceitos em `/convite/{token}`, após login ou cadastro.
Hierarquia de equipe não concede papel global `dev`. Resposta incompleta de
hierarquia mostra erro recuperável e não libera controles de gestão.

## Rodar com a API real

Na raiz, com dependências e modelos reais instalados:

```bash
uv run python -m uvicorn fraus.api.main:app --port 8001 --reload --reload-dir fraus
```

O backend padrão é Torch; defina `FRAUS_BACKEND=onnx` no ambiente para usar os
artefatos ONNX. Dentro de `dashboard/`, copie `.env.local.example` para
`.env.local` e ajuste **`FRAUS_API_URL=http://127.0.0.1:8001`**. Depois:

```bash
npm install
npm run dev
npm run contraste
```

No PowerShell, use `npm.cmd` se a política de execução bloquear `npm.ps1`.
`scripts/api_demo.py`, na raiz, usa a porta **8000**, snapshot sintético
temporário e motor real quando os artefatos existem; caso contrário anuncia
o dublê. É uma opção de demonstração local, nunca produção. O exemplo de
ambiente conserva essa porta como padrão; escolha o destino explicitamente.

## Ambiente e sessão

- `FRAUS_API_URL` é o destino server-side dos Server Components e do proxy
  `/api/fraus`. Também fornece o endereço apresentado nos exemplos de integração.
- `FRAUS_CHAVE_ACESSO` fica apenas no servidor. Em desenvolvimento, a dashboard
  pode ler a chave gerada pela API em `.fraus-chaves.txt`, na raiz. A primeira
  subida local da API gera credenciais automaticamente; ausência dessa variável
  na dashboard não significa que a API esteja aberta.
- Uma sessão de usuário tem precedência sobre a credencial técnica: o proxy
  usa o JWT do cookie HTTP-only para respeitar papel e escopo por canal.
- `NEXT_PUBLIC_API_URL` é legado e não é usado como destino ou endereço exibido.
  Nunca coloque credencial em uma variável `NEXT_PUBLIC_*`.
- `NEXT_PUBLIC_URL_DOCS` mostra o link do site público de documentação. Para
  MkDocs local, use uma porta separada, como **8010**.

Alterar variáveis do servidor exige reiniciar o Next. Em produção, exige novo
deploy. Dashboard `fraus` e API `fraus-api` publicam separadamente; merge do
front não comprova que o back recebeu novas rotas.

## Invariantes de interface

1. `score: null` é **“sem sinal”**, nunca nota zero, em célula, gráfico,
   ordenação, exportação ou agregado.
2. Agregado sem dados mostra estado vazio. LED numérico sem sinal fica apagado.
3. NPS é inferido e rotulado como estimativa. O cartão não exibe o ponto abaixo
   de 30 conversas com sinal; não substitua `nps_intervalo.nps = null` pelo bruto.
4. NPS e latência sobrepostos conservam as mitigações do DESIGN: domínios e
   eixos explícitos, latência tracejada e alternativa em tabela.
5. Faixas de NPS vêm de `GET /modelo`; score, nota e categoria são derivados
   no servidor.
6. `importancias` globais e `contribuicoes` por atendimento são conceitos e
   visualizações diferentes.
7. Falha de um painel fica localizada, com possibilidade de tentar novamente.
8. Instrumento conserva tipografia, cores semânticas, hairlines e raio zero do
   DESIGN; não introduza um sistema visual paralelo em Operação.

Identificadores são em português, sem acento nos símbolos. Âmbar (`--dito`)
representa o dito; azul (`--medido`), o medido; `--tempo` é latência tracejada.
Texto em tokens de dados usa a variante `-texto` validada em
`scripts/contraste.mjs`. Estimativas usam proveniência `.estimado`; números
comparáveis usam `.num`. Estado vazio explica o que falta, sem inventar valor.

## Verificação e referência interna

```bash
npm test
npm run build
```

Em 30/09/2026: **163 testes em 20 arquivos**, TypeScript e build aprovados;
sete abas de Operação exercitadas no navegador local. O QA com motor real usa
`scripts/validar_operacao_real.py`, na raiz, e
`scripts/validar-operacao-playwright.mjs`, neste diretório, com banco temporário
e URL local. `FRAUS_DIST_DIR` permite separar o build de QA do servidor usual.

Fluxos, permissões, limites, evidências e configuração pendente estão em
[Operação e produção](../docs/notas/2026-09-30-operacao-producao.md). Publicação
das duas unidades está em [deploy Vercel](../docs/deploy-vercel.md).
