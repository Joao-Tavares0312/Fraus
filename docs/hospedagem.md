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

A dashboard não fala com a API direto: toda chamada sai por um proxy no
servidor Next (`app/api/fraus/[...caminho]/route.ts`). Duas variáveis
**server-side** — nunca `NEXT_PUBLIC_*`, então nenhuma delas vai para o bundle
do navegador — importam na Vercel:

```
FRAUS_API_URL=https://sua-api.onrender.com
FRAUS_CHAVE_ACESSO=fra_...
```

Sem `FRAUS_API_URL`, o proxy aponta para `http://localhost:8000` e **toda tela
mostra "API não respondeu"** — o que é honesto, e é exatamente o que se vê
enquanto a API não tem endereço público. Sem `FRAUS_CHAVE_ACESSO`, o proxy
repassa sem `Authorization` — só serve se a API do outro lado estiver aberta
(sem `FRAUS_CHAVE_MESTRA`).

## Passo a passo com as chaves

A ordem importa, porque cada peça depende da anterior:

1. defina `FRAUS_CHAVE_MESTRA` no host da API e suba (ou reinicie) o container
   — é ela que liga a exigência de autenticação em toda rota, exceto
   `POST /ingestao`;
2. gere uma chave de acesso para a dashboard, com a mestra:
   ```bash
   curl -X POST https://sua-api.onrender.com/acesso/chaves \
     -H "Authorization: Bearer $FRAUS_CHAVE_MESTRA" \
     -H "content-type: application/json" \
     -d '{"nome": "dashboard Vercel"}'
   ```
   a resposta traz a chave **em claro uma única vez** — copie antes de fechar
   o terminal; o banco guarda só o hash e uma dica de 4 caracteres;
3. publique a dashboard com `FRAUS_API_URL` apontando para a API e
   `FRAUS_CHAVE_ACESSO` com a chave do passo 2;
4. anote a URL da dashboard e coloque em `FRAUS_ORIGENS` na API;
5. **reinicie a API** — a lista de origens é lida no boot.

`FRAUS_ORIGENS` aceita lista separada por vírgula e nunca deve ser `*`. Com a
mestra definida, isso já não é a única linha de defesa das rotas de leitura —
mas continua valendo como defesa em profundidade, porque o caminho normal virou
servidor→servidor pelo proxy do Next, e CORS é quem barra uma chamada feita
direto do navegador.

## Antes de expor para a internet

Sem `FRAUS_CHAVE_MESTRA`, a API roda **aberta**: quem alcança a URL lê todas as
conversas e gera uma chave para si — aceitável no banco do simulador, e **não**
com atendimento real. Definir a mestra fecha a API inteira, inclusive a rota
que gera chave (`POST /acesso/chaves` e `POST /integracoes/fontes/{id}/chave`
exigem a mestra; nenhuma chave de acesso gerencia outras chaves).

**A mestra protege a API, não a dashboard.** O proxy do Next é um relay: ele
anexa a chave do deploy em toda chamada que chega nele, e a dashboard publicada
continua **sem login** — quem alcança a URL da Vercel lê os dados pelo proxy,
usando a chave do deploy, sem apresentar credencial nenhuma. Para publicar com
dado real, proteja também o deploy (por exemplo, Vercel Deployment Protection)
— ou não publique com dado real.

Publicar com dado real de cliente exige a mestra definida **antes** de expor a
URL — o adaptador da Totalk já traz conversa real, com nome, documento e
endereço no texto das mensagens mesmo com as colunas de contato descartadas.
Para demonstração com o banco do simulador, rodar aberto é uma escolha
consciente, não a única opção: o passo a passo acima leva minutos.

### Alternativa para demonstrar sem hospedar a API

Um túnel (`cloudflared tunnel --url http://localhost:8000`) dá um endereço
público temporário para a API rodando na sua máquina. Serve para mostrar a
dashboard funcionando de verdade. Com `FRAUS_CHAVE_MESTRA` definida antes de
subir a API, quem chega no endereço esbarra em 401 sem chave — em toda rota
menos duas, que têm credencial própria e por isso não passam pela chave mestra:
`POST /ingestao`, que exige a chave de fonte `frs_`, e
`POST /integracoes/webhook/{fonte_id}`, que exige a assinatura HMAC sobre o
corpo.

A rota do webhook é **anônima por desenho**: a plataforma que entrega nela não
tem, nem pode ter, uma chave `fra_`, e a credencial dela é a assinatura. Sem
assinatura válida nada é gravado, e cada tentativa fica no histórico de entregas
da fonte. Mas ela é uma **porta pública de escrita**: com o túnel aberto,
qualquer um pode chamá-la e gerar tentativas recusadas. A mestra não fecha essa
porta — o segredo do webhook é que fecha. Publique sabendo disso.

Sem a mestra, vale o aviso de sempre: feche o túnel depois de demonstrar.
