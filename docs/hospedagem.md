# Hospedar o Fraus

> **Estado atual (30/09/2026).** A aplicação real roda em **dois projetos
> Vercel** — dashboard `fraus` e API `fraus-api` (ONNX, sem torch) —, com
> **Supabase Postgres** para o estado e **Oracle Object Storage** só para o ZIP
> de modelos, baixado no build. O passo a passo está em
> [Deploy gratuito na Vercel](deploy-vercel.md).
>
> Essa API é serverless e **esfria**. O aquecimento em segundo plano e o
> workflow `api-aquecer` reduzem o cold start, mas não o eliminam. O caminho
> definitivo é um **container sempre ligado** com pelo menos 1,5–2 GB de RAM
> (este documento). O **Render gratuito não serve**: 512 MB contra ~1.056 MB
> medidos, e ainda dorme em 15 min. O Cloud Run
> ([API no Google Cloud Run](cloud-run.md)) e a Oracle Ampere continuam como
> alternativas documentadas, não como produção.

O Fraus são **duas peças com necessidades opostas**, e é por isso que elas não
moram no mesmo lugar:

| | precisa de | cabe na Vercel? |
|---|---|---|
| **dashboard** (Next.js) | CPU por milissegundos, nenhum estado | sim |
| **API** (FastAPI + BERTimbau) | 1,8 GB de disco, RAM, banco que persiste | **não** |

## O que mudou em 2026, e o que não mudou

> **Atualizado em 11/09/2026.** Duas premissas desta página envelheceram, e uma
> delas era o argumento principal. Os números abaixo foram medidos nesta data,
> não estimados.

**O teto da Vercel subiu.** O limite de função Python passou de 250 MB para
**500 MB** em 24/02/2026, e há **Large Functions** (até 5 GB, em Fluid compute)
ainda em beta. O argumento "só o torch já é o dobro do teto" deixou de valer.

**E mesmo assim a API não vai para lá**, por três motivos que o tamanho nunca
foi:

1. **RAM.** Medido: **1.056 MB de RSS** com os três modelos carregados e uma
   pontuação executada. Isso é o piso, não o pico sob carga.
2. **Cold start.** Carregar 1,3 GB de pesos a cada instância fria é dezenas de
   segundos, toda vez que a função dorme.
3. **Disco que persiste.** O SQLite precisa sobreviver entre requisições.

Caber em 500 MB exigiria a quantização int8 — que foi **medida e recusada**:
1,7% dos atendimentos trocavam de categoria, um deles de detrator para
promotor. Ver [Encolher os modelos](encolhimento.md).

## Por que a API não vai para a Vercel

Não é preferência, é medida:

- `torch` instalado ocupa **497 MB**, contra teto de **500 MB** — e sobram 3 MB
  para os 1,3 GB de pesos, o FastAPI e o scikit-learn.
- Os três BERTimbau somam **1,3 GB** de pesos.
- Cada requisição roda inferência em CPU. A rota `/analisar` faz uma passada de
  modelo **por palavra** do cliente; isso leva segundos e estoura o tempo máximo
  de uma função serverless.
- O SQLite precisa de disco que sobreviva entre requisições. Em sistema de
  arquivos efêmero, toda importação some no próximo boot.

O mesmo raciocínio vale para Lambda e Cloud Functions.

## Onde a API cabe — as opções gratuitas, conferidas em 11/09/2026

O requisito que elimina quase todo mundo é **~1,1 GB de RAM medidos** mais um
**volume que persista**.

| host | RAM grátis | dorme? | serve? |
|---|---|---|---|
| **Oracle Cloud Always Free** | 4 ARM cores / **24 GB** | **não** | ✅ **a recomendação** |
| Google Cloud Run | até 4 GB, 2M req/mês | sim (escala a zero) | ⚠️ sem volume — pesos na imagem ou baixados no boot |
| Render free | **512 MB** | sim, 30–50 s para acordar | ❌ não cabe |
| Hugging Face Spaces | 2 vCPU / 16 GB | — | ❌ Docker Space exige **PRO** desde 2026 |
| Railway | crédito único de US$ 5 | — | ❌ é teste, não plano grátis |

### Por que Oracle Always Free, e não Cloud Run

Você pediu custo zero e aceitou cold start — e o detalhe é que **com Oracle você
não precisa aceitar**: a VM fica ligada, `docker run` sobe o `Dockerfile` desta
raiz **sem nenhuma alteração**, e os volumes de `/modelos` e `/dados` funcionam
porque há disco de verdade.

No Cloud Run seria preciso mudar o desenho: sem volume persistente, ou os
1,3 GB de pesos entram na imagem (e cada deploy reenvia tudo, o que o
`Dockerfile` recusa por escrito) ou são baixados a cada instância fria. E o
SQLite precisaria virar Postgres — o `psycopg` já está nas dependências, então
não é impossível, é só outro projeto.

O preço da Oracle é você administrar uma VM: `docker`, um `systemd` para
reiniciar sozinho, e TLS. Meia tarde, uma vez.

> **Na semana da banca isso importa mais que tudo:** uma instância que não
> dorme não tem o momento "professor, espera carregar".

## As três peças, e onde cada uma mora

```
dashboard (Next.js)     -> Vercel                  grátis, já está lá
documentação (MkDocs)   -> repositório PÚBLICO      grátis, espelho do build
API (FastAPI+BERTimbau) -> Oracle Always Free VM   grátis, sempre no ar
```

### Por que a documentação mora em outro repositório

Este repositório é **privado e continua privado**. GitHub Pages a partir de
repositório privado exige plano pago — então o site mora num repositório
público separado que contém **apenas o site construído**: nunca o código,
nunca as specs, nunca o `docs/` cru.

**O build acontece do lado privado**, e é isso que faz o arranjo funcionar: o
`mkdocstrings` precisa do código Python para ler as docstrings, e o código só
existe aqui. O repositório público recebe HTML pronto.

E a fronteira não é só de hospedagem, é de **conteúdo**. O build público usa
`mkdocs-publico.yml`, que:

- **exclui** `superpowers/`, `notas/`, `handoff.md`, `hospedagem.md` (esta
  página) e `colab.md`;
- **desliga `show_source`** do mkdocstrings.

> ⚠️ **`not_in_nav` não exclui nada.** Ele só silencia o aviso de página fora
> do menu — o MkDocs continua construindo o arquivo, que fica acessível por URL
> direta e listado no `sitemap.xml`. Quem tira do build é `exclude_docs`. Essa
> confusão custou, no build de 10/09/2026, **38 specs publicadas** e 12 blocos
> de código-fonte embutidos no HTML.

Há três camadas defendendo isso, porque uma só falharia em silêncio:

1. `tests/test_documentacao.py` — amarra as exclusões e o `show_source: false`
   nos **dois** configs publicados (o do site e o do PDF);
2. o workflow **inspeciona o `site/` construído** antes de empurrar, e morre se
   algo escapou;
3. `force_orphan` — cada publicação substitui a anterior por completo, então
   um arquivo que sai do recorte hoje não continua servido amanhã.

O PDF do anexo herda do config **público** pelo mesmo motivo: PDF é o formato
mais difícil de despublicar que existe.

E duas variáveis amarram tudo:

```bash
# na Vercel, no projeto da dashboard
FRAUS_API_URL=https://api.seu-dominio.com
NEXT_PUBLIC_URL_DOCS=https://joao-tavares0312.github.io/fraus-docs/

# na VM, no docker run
FRAUS_ORIGENS=https://sua-dashboard.vercel.app
```

`FRAUS_ORIGENS` não tem padrão de propósito: sem ele a API só aceita origem
local e a dashboard publicada toma erro de CORS. **Falha visível, que se
conserta — em vez de uma porta aberta que ninguém nota.**

## Onde a API cabe — o requisito técnico

Qualquer host de **container com volume**: uma VM, Render pago, Railway, Fly.io.
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

### O login de usuário (LP + `/dashboard`)

Desde 31/08/2026 a raiz é a página pública do produto e as telas moram em
`/dashboard`, atrás de login **quando ele existe**. Duas variáveis na **API**
(não na Vercel) o ligam:

```
FRAUS_JWT_SEGREDO=<openssl rand -hex 32>   # assina o token de sessão
FRAUS_CODIGO_DEV=<código de convite>       # opcional: sem ele, ninguém nasce dev
```

Com `FRAUS_JWT_SEGREDO` definida, a dashboard exige entrar (ou criar conta) e
o papel decide o que aparece: `dev` administra, `usuario` analisa — e o
servidor da API nega rota administrativa a `usuario` com 403, com ou sem tela.
O token vive num cookie `httpOnly` do domínio da dashboard; o navegador nunca
o vê. Quem publica **sem** a variável mantém o comportamento antigo: dashboard
aberta, sem conceito de usuário.

Quando há sessão ativa, o proxy usa **o token do usuário** como credencial
perante a API (degrau zero, antes de `FRAUS_CHAVE_ACESSO`) — é o que faz o
403 de papel valer de verdade através do proxy.

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

---

# Passo a passo: subir a API na Oracle Ampere A1

> Escrito em 11/09/2026. O alvo é **custo zero e sempre no ar**. São ~40 minutos
> na primeira vez, e a maior parte é espera de download.
>
> Esta página **não vai para o site público** (`exclude_docs` em
> `mkdocs-publico.yml`): ela nomeia variáveis de segredo e descreve a topologia.

!!! tip "Os passos 2 a 8 estão automatizados"
    ```bash
    uv run python scripts/abrir_portas_oracle.py   # o firewall da NUVEM
    scripts/provisionar_oracle.sh SEU_IP [dominio.com]   # o resto
    ```
    O script é **idempotente**: rodar de novo depois de uma falha no meio não
    refaz o que já deu certo — e, em particular, **não regera segredo**. Um
    `.env` que já existe é lido, nunca reescrito, porque recriar a
    `FRAUS_CHAVE_MESTRA` invalidaria em silêncio a chave que a Vercel usa, e o
    sintoma ("401 em tudo") apareceria horas depois, longe da causa.

    O texto abaixo continua sendo a fonte do **porquê** de cada passo. Leia-o
    quando algo falhar — o script executa as decisões, esta página as explica.

## 0. O que você precisa antes de começar

- conta na Oracle Cloud (a gratuita basta);
- uma chave SSH (`ssh-keygen -t ed25519`) — a pública vai para a instância;
- os **1,3 GB de modelos** na sua máquina, em `modelos/`;
- a URL da dashboard na Vercel;
- um subdomínio apontando para a VM, se quiser HTTPS com certificado válido.

---

## 1. Criar a instância — e o passo que todo mundo erra

Console → **Compute → Instances → Create instance**.

| campo | valor |
|---|---|
| Image | **Ubuntu 24.04** (Canonical) |
| Shape | **VM.Standard.A1.Flex** — *Ampere*, não AMD |
| OCPUs / RAM | **2 OCPU / 12 GB** |
| SSH key | cole sua chave pública |

!!! warning "As VMs x86 grátis não servem"
    As *Always Free* AMD têm **1 GB de RAM** e a API mede **1.056 MB**. Tem que
    ser a ARM.

!!! danger "\"Out of host capacity\""
    É o erro mais comum da Oracle grátis, e **não é culpa sua**: a capacidade
    ARM é disputada. Tente outro *availability domain* (AD-1, AD-2, AD-3) ou
    outro horário. Não adianta insistir no mesmo botão.

**Por que 2 OCPU e não 4:** a conta gratuita dá 4 no total. Deixando 2 livres
você consegue criar uma segunda instância depois sem destruir esta.

---

## 2. Abrir a porta — os DOIS lugares

Este é o passo que faz as pessoas perderem uma hora: a Oracle bloqueia em
**dois** níveis, e abrir só um não dá nenhum erro — a conexão só fica pendurada.

**2.1 — Security List (o firewall da nuvem)**

Networking → *Virtual Cloud Networks* → sua VCN → *Security Lists* → *Default* →
**Add Ingress Rules**:

| Source CIDR | Protocol | Port |
|---|---|---|
| `0.0.0.0/0` | TCP | **80** |
| `0.0.0.0/0` | TCP | **443** |

**2.2 — iptables (o firewall dentro da máquina)**

A imagem Ubuntu da Oracle vem com regras que **descartam tudo menos a 22**.
Isso não está em lugar nenhum do assistente de criação:

```bash
ssh ubuntu@SEU_IP

sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save
```

> Se você abriu a Security List e a conexão ainda expira, **é este passo que
> está faltando**. Não é DNS, não é Docker.

---

## 3. Docker

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker ubuntu
exit          # sai e entra de novo — o grupo só vale em sessão nova
```

---

## 4. Mandar o código e os modelos

Da **sua máquina**:

```bash
# O codigo (o repositorio e privado; mandar por tar evita credencial na VM)
tar -czf - --exclude=.git --exclude=modelos --exclude=dashboard \
           --exclude=node_modules --exclude=site . \
  | ssh ubuntu@SEU_IP "mkdir -p ~/fraus && tar -xzf - -C ~/fraus"

# Os pesos. 1,3 GB -- aqui e onde o tempo vai.
tar -czhf - -C modelos . \
  | ssh ubuntu@SEU_IP "mkdir -p ~/fraus-modelos && tar -xzf - -C ~/fraus-modelos"
```

!!! warning "`tar | ssh`, e não `rsync`"
    O **Git Bash do Windows não traz `rsync`** — e é nele que este projeto é
    desenvolvido. A versão anterior deste passo pedia `rsync` e falhava na
    máquina de quem escreveu o roteiro. `tar` e `ssh` existem dos dois lados.

!!! tip "Os modelos ficam FORA da imagem, de propósito"
    O `Dockerfile` recusa assar os pesos: cada deploy reenviaria 1,3 GB por uma
    mudança de uma linha. Eles entram por volume — e é exatamente por isso que
    a Oracle serve e o Cloud Run não.

---

## 5. Construir e subir

```bash
cd ~/fraus
docker build -t fraus-api .
```

**Confira que o `torch` veio sem CUDA** — o erro é silencioso, a imagem só fica
3 GB maior:

```bash
docker run --rm fraus-api python -c "import torch; print(torch.__version__, torch.version.cuda)"
# esperado: uma versao terminada em "+cpu" e None. Ex.: 2.14.0+cpu None
```

!!! warning "Não confira isso por tamanho"
    A versão anterior deste passo mandava medir `~500 MB` com `du`. Em
    11/09/2026 o build mediu **769 MB de `torch 2.14.0+cpu`** — CPU puro, sem
    um pacote `nvidia` sequer. A biblioteca engordou entre versões, e a sonda
    de tamanho acusaria CUDA onde não há. `torch.version.cuda` é o fato;
    megabyte é palpite.

!!! tip "Alternativa sem torch: `BACKEND=onnx`"
    ```bash
    docker build --build-arg BACKEND=onnx -t fraus-api .
    ```
    Não instala o torch e lê os grafos de `/modelos-onnx` (gerados por
    `scripts/encolher_modelos.py`), então monte **também**
    `-v "$PWD/modelos-onnx:/modelos-onnx:ro"`. O `/modelos` continua necessário
    por causa do `fusor.joblib` e das métricas. Medido em 15/09/2026: imagem de
    995 MB, pico de 1.347 MB contra 1.848 MB do torch, e 0 de 180 categorias
    trocadas. Ver `docs/encolhimento.md`.

Agora as credenciais. **Gere e GUARDE** — a mestra não é recuperável:

```bash
openssl rand -hex 32          # FRAUS_CHAVE_MESTRA
openssl rand -hex 32          # FRAUS_JWT_SEGREDO
```

`~/fraus/.env`:

```bash
FRAUS_CHAVE_MESTRA=<o primeiro hex>
FRAUS_JWT_SEGREDO=<o segundo hex>
FRAUS_CODIGO_CONVITE=<uma frase sua>
FRAUS_ORIGENS=https://sua-dashboard.vercel.app

# OPCIONAL: Postgres do Supabase no lugar do SQLite. Com ele, o banco
# sobrevive a recriar o container -- e `fraus/db.py` ja aceita os dois.
# FRAUS_DATABASE_URL=postgresql://...
```

!!! danger "A porta destrancada"
    `FRAUS_CHAVE_MESTRA` + `FRAUS_JWT_SEGREDO` **sem** `FRAUS_CODIGO_CONVITE`
    deixa a API **aberta**: qualquer um faz `registrar` → `entrar` e o JWT lê
    tudo que a mestra protege. A API grita isso no boot — **leia o log da
    primeira subida.**

`~/fraus/compose.yml`:

```yaml
services:
  api:
    image: fraus-api
    restart: always          # volta sozinha depois de reboot da VM
    env_file: .env
    ports:
      - "127.0.0.1:8000:8000"   # SO local: quem fala com a internet e o Caddy
    volumes:
      - /home/ubuntu/fraus-modelos:/modelos:ro
      - /home/ubuntu/fraus-dados:/dados
```

```bash
docker compose up -d
docker compose logs -f        # espere "motor":"real"
curl -s localhost:8000/saude  # {"status":"ok","motor":"real"}
```

> **Se disser `"motor":"duble"`, pare.** Os modelos não foram encontrados, e a
> API está pronta para servir número sintético com cara de predição.

---

## 6. HTTPS com o Caddy

A dashboard está em `https://`, então o navegador **recusa** chamar uma API em
`http://` — *mixed content*. HTTPS não é opcional aqui.

O Caddy emite e renova o certificado sozinho:

```bash
sudo apt install -y caddy
```

`/etc/caddy/Caddyfile`:

```
api.seu-dominio.com {
    reverse_proxy 127.0.0.1:8000
}
```

```bash
sudo systemctl restart caddy
curl -s https://api.seu-dominio.com/saude
```

!!! note "Sem domínio próprio"
    O Let's Encrypt não emite certificado para IP. Um subdomínio gratuito
    (DuckDNS, por exemplo) resolve — e o Caddy funciona igual.

---

## 7. Ligar as pontas

Na **Vercel**, projeto da dashboard:

```
FRAUS_API_URL        = https://api.seu-dominio.com
FRAUS_CHAVE_ACESSO   = fra_...        (gerada pela mestra)
NEXT_PUBLIC_URL_DOCS = https://<usuario>.github.io/fraus-docs/
```

A chave de acesso sai da mestra:

```bash
curl -X POST https://api.seu-dominio.com/acesso/chaves \
     -H "Authorization: Bearer $FRAUS_CHAVE_MESTRA" \
     -H "Content-Type: application/json" \
     -d '{"nome":"dashboard"}'
```

Redeploy na Vercel e a dashboard passa a ler dado real.

---

## 8. Sobreviver ao reboot

`restart: always` do compose já religa os containers, mas só se o Docker subir.
Garanta os dois:

```bash
sudo systemctl enable docker
sudo systemctl enable caddy
```

Teste de verdade — `sudo reboot`, espere dois minutos, e:

```bash
curl -s https://api.seu-dominio.com/saude
```

Se responder `{"status":"ok","motor":"real"}`, acabou.

---

## Conferência final

- [ ] `/saude` responde `"motor":"real"` **pela URL pública**
- [ ] a dashboard na Vercel mostra dado real, não estado vazio
- [ ] `docker compose logs` **não** tem aviso de porta destrancada
- [ ] sobreviveu a um `reboot`
- [ ] a `FRAUS_CHAVE_MESTRA` está guardada **fora da VM**

## Quando algo não responde

| sintoma | causa quase sempre |
|---|---|
| conexão pendura, sem erro | **iptables** (passo 2.2), não a Security List |
| `"motor":"duble"` | volume de `/modelos` errado ou vazio |
| dashboard vazia, API respondendo | `FRAUS_ORIGENS` não tem a URL exata da Vercel |
| 401 em tudo | falta `FRAUS_CHAVE_ACESSO` na Vercel |
| imagem gigante | `torch` veio com CUDA — reveja o passo 5 |
