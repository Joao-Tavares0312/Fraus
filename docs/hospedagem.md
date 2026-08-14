# Hospedar o Fraus

O Fraus são **duas peças com necessidades opostas**, e é por isso que elas não
moram no mesmo lugar:

| | precisa de | cabe na Vercel? |
|---|---|---|
| **dashboard** (Next.js) | CPU por milissegundos, nenhum estado | sim |
| **API** (FastAPI + BERTimbau) | 1,8 GB de disco, RAM, banco que persiste | **não** |

## Por que a API não vai para a Vercel

Não é preferência, é medida:

- `torch` instalado ocupa **497 MB**. O teto de uma função da Vercel é **250 MB**
  descompactado — só a biblioteca já é o dobro.
- Os três BERTimbau somam **1,3 GB** de pesos.
- Cada requisição roda inferência em CPU. A rota `/analisar` faz uma passada de
  modelo **por palavra** do cliente; isso leva segundos e estoura o tempo máximo
  de uma função serverless.
- O SQLite precisa de disco que sobreviva entre requisições. Em sistema de
  arquivos efêmero, toda importação some no próximo boot.

O mesmo raciocínio vale para Lambda e Cloud Functions.

## Onde a API cabe

Qualquer host de **container com volume**: Render, Railway, Fly.io ou uma VM.
O `Dockerfile` na raiz está pronto e espera duas coisas montadas:

- `/modelos` — os pesos (1,3 GB). **Não estão na imagem** de propósito: assar
  1,3 GB ali faria cada deploy reenviar tudo por uma mudança de uma linha, e os
  pesos mudam muito menos que o código.
- `/dados` — o SQLite e a pasta de importação.

```bash
docker build -t fraus-api .
docker run -p 8000:8000 \
  -v "$PWD/modelos:/modelos:ro" \
  -v "$PWD/dados:/dados" \
  -e FRAUS_ORIGENS=https://SUA-DASHBOARD.vercel.app \
  fraus-api
```

Os pesos podem chegar ao host por volume persistente, por bucket, ou publicados
no Hugging Face Hub e baixados no boot. Para trabalho de faculdade, o volume
persistente do Render/Fly é o caminho mais curto.

### RAM

Três BERTimbau carregados em CPU pedem **~2 GB**. Plano de 512 MB mata o
processo no boot, sem mensagem clara. Se o orçamento apertar, `FRAUS_CAMINHO_
MODELO_EMOCAO` e `_IRONIA` podem ficar apontando para pasta inexistente: a API
sobe sem essas duas cabeças e o score sai **idêntico**, porque nenhuma delas
entra no fusor. O que some é a leitura de emoção e ironia na tela.

## Dashboard na Vercel

O diretório do projeto é `dashboard/`, não a raiz.

```bash
cd dashboard
vercel deploy --prod
```

Uma variável importa:

```
NEXT_PUBLIC_API_URL=https://sua-api.onrender.com
```

Sem ela, a dashboard aponta para `http://localhost:8000` e **toda tela mostra
"API não respondeu"** — o que é honesto, e é exatamente o que se vê enquanto a
API não tem endereço público.

## O laço de CORS

Os dois lados precisam se nomear, e a ordem importa:

1. publique a API, anote a URL;
2. publique a dashboard com `NEXT_PUBLIC_API_URL` apontando para ela;
3. anote a URL da dashboard e coloque em `FRAUS_ORIGENS` na API;
4. **reinicie a API** — a lista de origens é lida no boot.

`FRAUS_ORIGENS` aceita lista separada por vírgula e nunca deve ser `*`: esta API
lê atendimentos e não tem autenticação nas rotas de leitura, então qualquer
página aberta no mesmo navegador poderia varrer as conversas.

## Antes de expor para a internet

A chave de API protege **só a ingestão**. Todo o resto — inclusive a rota que
gera a chave — continua sem autenticação, porque o Fraus foi feito para rodar
local. Quem alcança a API pode ler todas as conversas e gerar uma chave para si.

Publicar com dado real de cliente exige autenticação na API inteira antes.
Para demonstração com o banco do simulador, o risco é o que está escrito aqui.

### Alternativa para demonstrar sem hospedar a API

Um túnel (`cloudflared tunnel --url http://localhost:8000`) dá um endereço
público temporário para a API rodando na sua máquina. Serve para mostrar a
dashboard funcionando de verdade — e vale lembrar que ele expõe a API sem
autenticação enquanto estiver aberto, então feche depois.
