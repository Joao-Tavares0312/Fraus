# Nota de sessão — 11/09/2026: subir a API na Oracle

> Esta nota **não vai para o site público** (`notas/` está em `exclude_docs`).
> Ela cita OCIDs, cotas de conta e topologia de rede.
>
> Contexto: a sessão começou querendo "parar de rodar o Fraus localmente". Ela
> terminou com a API **provada de pé num container** e a VM ainda não criada,
> por um motivo que não depende de nós.

---

## 1. Onde as coisas pararam, em uma tela

| peça | estado |
|---|---|
| Conta Oracle, CLI e credencial de API | **pronta** — `oci` autenticada, chave registrada |
| VCN, sub-rede pública, Security List | **pronta** — 22, 80 e 443 liberadas |
| Instância Ampere A1 | **NÃO CRIADA** — sem capacidade na região |
| Script de provisionamento | **pronto e testado**, esperando um IP |
| Imagem Docker da API | **construída e validada** — `motor: real`, predição correta |
| Site público da documentação | **bloqueado** — faltam 3 valores no GitHub |

O laço que fica pedindo a máquina roda **destacado** desta sessão (ver §5).

---

## 2. O que foi feito

### 2.1 Acesso programático à Oracle

A `oci` CLI está instalada e autenticada. Duas armadilhas no caminho, ambas
resolvidas, ambas com chance de voltar:

- **O instalador oficial falha nesta máquina.** Ele escolhe o Python 3.14 do
  registro, e o PyYAML ainda não publica wheel para 3.14 — ele tenta compilar e
  morre em `Microsoft Visual C++ 14.0 or greater is required`. O contorno é
  `uv tool install oci-cli --python 3.12`, que baixa o interpretador certo.
  Sobraram `C:\Users\dell08\lib\oracle-cli` e `C:\Users\dell08\bin` do
  instalador que falhou — inúteis, podem ser apagados.
- **`oci setup config` não roda aqui.** É interativo, e o prompt não recebe
  stdin nem pelo `!` do Claude Code — devolve `Aborted!` na primeira pergunta.
  O `~/.oci/config` foi escrito à mão, com o par de chaves gerado por
  `openssl`, o que é equivalente e não depende de terminal interativo.

O par de chaves da API vive em `~/.oci/oci_api_key.pem`, fingerprint
`57:a4:09:b8:cf:10:f1:35:dc:40:b2:b4:60:1b:5c:15`.

!!! warning "São DOIS pares de chave, e eles não se misturam"
    `~/.ssh/id_ed25519` (Ed25519) entra na **VM** por SSH.
    `~/.oci/oci_api_key.pem` (RSA) assina chamadas da **API da Oracle**.
    O laço de pesca usa a segunda para criar a máquina; o provisionamento usa
    a primeira para entrar nela depois.

### 2.2 A rede, e o firewall que não é um só

VCN `fraus-vcn` criada pelo assistente, com sub-rede pública e privada. A
pública é a que importa.

`scripts/abrir_portas_oracle.py` abriu 80 e 443 na Security List — **já
executado**, 3 → 5 regras, com a 22 preservada (conferido depois).

O arquivo existe em vez de ser um comando solto por um motivo que custa caro:
**a API de update SUBSTITUI a lista inteira de regras.** Quem manda só as duas
novas apaga as antigas, inclusive a da porta 22 — e o próximo passo é perder o
SSH para a própria máquina. O script lê o que existe, compara **por faixa**
(uma regra 1‑65535 já cobre a 443) e reenvia o conjunto.

Falta ainda o **outro** firewall, o `iptables` de dentro da VM, que a imagem
Ubuntu da Oracle traz descartando tudo menos a 22. Ele é o passo 1 do script de
provisionamento. Abrir só um dos dois não dá erro nenhum: a conexão fica
pendurada até expirar.

### 2.3 O provisionamento virou script

`scripts/provisionar_oracle.sh SEU_IP [dominio.com]` executa os passos 2 a 8 de
`docs/hospedagem.md`: iptables, Docker, envio do código e dos pesos, build,
`.env`, compose, conferência de `motor: real`, Caddy e systemd.

Duas decisões que merecem sobreviver:

- **Idempotente, e o caso que importa é o segredo.** Um `.env` que já existe é
  lido, **nunca reescrito**. Regerar a `FRAUS_CHAVE_MESTRA` numa segunda
  execução invalidaria em silêncio a `FRAUS_CHAVE_ACESSO` que a dashboard usa
  na Vercel, e o sintoma ("401 em tudo") apareceria horas depois, longe da
  causa. Há teste prendendo isso.
- **Erro que não é de capacidade interrompe.** Credencial errada ou subnet
  inexistente não melhoram com o tempo; repetir esconderia o motivo real.

### 2.4 O ensaio do deploy, e os quatro defeitos que ele achou

Com a VM indisponível, o deploy foi **ensaiado localmente no Docker** antes de
existir máquina. Ele se pagou:

1. **A API não subia.** `ModuleNotFoundError: No module named 'jwt'`. Faltavam
   **cinco** dependências na imagem: `pyjwt`, `openpyxl`, `python-docx`,
   `pypdf`, `python-multipart`. A imagem **construía sem erro** e só morria no
   boot — na VM isso apareceria depois do build e depois de enviar 1,3 GB.

   A causa não é descuido, é desenho: o `Dockerfile` mantinha uma lista de
   dependências **à mão**, em paralelo à do `pyproject.toml`. Quem acrescenta
   uma dependência mexe no `pyproject` e não tem motivo nenhum para lembrar do
   `Dockerfile`. Consertar as cinco deixaria a sexta acontecer — agora a imagem
   instala o próprio projeto, e há teste impedindo a lista de renascer.

2. **A sonda do torch media a coisa errada.** Mandava conferir "~500 MB" com
   `du`; o build mediu **769 MB de `torch 2.14.0+cpu`** — CPU puro,
   `torch.version.cuda` é `None`, zero pacotes `nvidia`. A biblioteca engordou
   entre versões, e um limiar de tamanho acusaria CUDA onde não há. Agora a
   sonda pergunta à própria biblioteca.

3. **O roteiro mandava usar `rsync`,** que o Git Bash do Windows **não tem** —
   o passo 4 falharia na máquina em que o roteiro foi escrito. Trocado por
   `tar | ssh`.

4. **`.sh` era commitado com CRLF.** Na VM Ubuntu isso vira
   `bad interpreter: /usr/bin/env bash^M`, erro que não menciona fim de linha em
   lugar nenhum. `.gitattributes` criado; conferido byte a byte no índice.

E o pin de ARM do `Dockerfile` **ganhou a evidência** que o comentário afirmava
sem número: o wheel `cp312 manylinux_2_28_aarch64` da `torch 2.10.0` pesa
**146 MB** contra **420 MB** da `2.11.0`. O triplo é a CUDA de ARM entrando.

### 2.5 O que o ensaio provou

Dentro do container, medido:

- `/saude` → `{"status":"ok","motor":"real"}` em 10 segundos;
- a API sobe **fechada** — até `/openapi.json` exige `Bearer`;
- nenhum aviso de porta destrancada (o convite estava definido);
- predição real de três conversas: detrator `0,20`, promotor `97,10`, e
  **`None`** para a conversa em que só o bot falou.

Esse último é o que mais vale: **invariante 2 de pé dentro da imagem** —
ausência de fala do cliente virou `None`, não zero, não "insatisfeito".

O ramo **ARM** do `Dockerfile` continua **não exercitado**: a máquina de
desenvolvimento é x86, e o `if aarch64` nunca executa ali. Ele só será provado
na primeira build dentro da Ampere.

---

## 3. Por que a instância não existe — e o que já foi descartado

O erro é sempre o mesmo:

```
Out of capacity for shape VM.Standard.A1.Flex in availability domain AD-1
```

Foram **~35 tentativas** ao longo do dia, sem nenhuma exceção. O que a
investigação fechou:

- **Não é configuração.** O formulário chegou correto: Ubuntu 24.04 aarch64,
  A1.Flex, sub-rede pública, chave SSH. O erro é de hardware disponível.
- **Não é a imagem.** `Out of capacity` é sobre o *shape*. Trocar Ubuntu por
  Oracle Linux ou Debian daria exatamente o mesmo erro.
- **Não é fragmentação de hardware.** O laço passou a alternar `2 OCPU/12 GB` e
  `1 OCPU/6 GB`; **os dois falham**. Se fosse buraco pequeno, o menor entraria.
- **Não é cota.** Medido pela API:
  `standard-a1-core-count: used 0, available 2`.
- **Não há outro availability domain.** São Paulo tem só `AD-1`.
- **`VM.Standard.E2.1.Micro` não serve.** É x86 e tem **1 GB** de RAM; a API
  mede **1.056 MB**. Não cabe, e forçar com swap levaria a inferência a dezenas
  de segundos por mensagem.

### O que mudar de região faria — e por que não resolve

**Recurso Always Free só existe na região de origem.** A conta tem uma única
região assinada, `sa-saopaulo-1`, e ela **é** a de origem. Assinar Vinhedo e
criar lá sairia **cobrado**, e região de origem não se troca depois do
cadastro.

Isso corrige um conselho dado mais cedo nesta mesma sessão: "tenta Vinhedo"
vale para conta paga, **não** para Always Free.

### A cota da conta é metade da documentada

Medido, e vale saber porque muda o que faz sentido pedir:

| cota | esta conta | Always Free documentado |
|---|---|---|
| `standard-a1-core-count` | **2** | 4 |
| `standard-a1-memory-count` | **12** | 24 |

Ou seja: **`2 OCPU / 12 GB` não é preferência, é o teto da conta.** Pedir mais
seria recusado por cota, antes mesmo da capacidade.

---

## 4. O que falta — em ordem

### P0 — Conseguir a instância

O laço está pescando (§5). Se atravessar o fim de semana sem sucesso, a
alavanca que sobra é **upgrade para Pay As You Go**:

- contas de teste/grátis são despriorizadas pela Oracle na fila de A1, e o
  upgrade costuma destravar quase imediatamente;
- **os recursos Always Free continuam gratuitos numa conta PAYG** — os mesmos
  2 OCPU / 12 GB, sem custo;
- **o risco é real e não deve ser suavizado:** exige cartão, e qualquer coisa
  além da franquia passa a ser cobrada de verdade — um volume esquecido, uma
  segunda VM, um IP reservado. Alerta de orçamento avisa, **não bloqueia**.

É decisão do João, porque envolve cartão dele.

### P0 — Depois que a instância nascer

Um comando:

```bash
scripts/provisionar_oracle.sh <IP_PUBLICO> [dominio.com]
```

Sem domínio, a API só responde em `localhost:8000` dentro da VM — o Let's
Encrypt não emite certificado para IP, e a dashboard em `https://` **recusa**
chamar uma API em `http://` (mixed content). Um subdomínio gratuito (DuckDNS)
resolve, e aí é rodar o script de novo com ele.

Depois disso, na Vercel: `FRAUS_API_URL`, `FRAUS_CHAVE_ACESSO` (gerada pela
mestra, dentro da VM) e `NEXT_PUBLIC_URL_DOCS`.

### P1 — O site público da documentação

Toda a máquina está pronta e testada (build limpo, três camadas de guarda
contra vazamento). Faltam **três valores que só o João pode criar**, no
repositório privado:

| onde | nome | o que é |
|---|---|---|
| Secrets | `DEPLOY_KEY_DOCS` | chave SSH **privada**, com escrita no repo público |
| Variables | `REPO_DOCS` | `usuario/nome-do-repo-publico` |
| Variables | `FRAUS_URL_DASHBOARD` | URL da dashboard, para o link "← Dashboard" |

A chave se cria uma vez:

```bash
ssh-keygen -t ed25519 -C "fraus-docs" -f chave -N ""
```

A **pública** vai em *Settings → Deploy keys* do repositório **público**, com
**"Allow write access" marcado**. A **privada** vira o secret no repositório
**privado**. Um `GITHUB_TOKEN` não serve: ele só tem poder no repositório em
que o workflow roda.

### P1 — Provar o ramo ARM do `Dockerfile`

Nunca foi executado. A evidência que existe é indireta (o tamanho do wheel no
PyPI). A primeira build dentro da Ampere é o teste de verdade.

### P2 — Sobras

- Mergear a **PR #38** (4 commits, `MERGEABLE`, sem review).
- Apagar `C:\Users\dell08\lib\oracle-cli` e `C:\Users\dell08\bin`, restos do
  instalador que falhou.
- O container do ensaio segue de pé em `127.0.0.1:8010`. Derrubar com
  `docker compose -f <scratchpad>/ensaio/compose.yml down`.

---

## 5. O laço que pede a máquina

Roda como **processo destacado do Windows**, não como tarefa do Claude Code —
e essa diferença foi aprendida do jeito difícil: a primeira versão morreu aos
23 minutos porque o harness mata tarefa de background por tempo de vida, sem
que nada estivesse errado com o script.

| | |
|---|---|
| script | `<scratchpad>/pescar_ampere.ps1` |
| log | `<scratchpad>/ampere.log` |
| PID | gravado em `<scratchpad>/ampere.pid` |
| parar | `Stop-Process -Id <pid>` |
| alcance | 24 h, alternando 2/12 e 1/6, para na primeira que fisgar |

Ele sobrevive ao fechamento do Claude Code. **Não sobrevive a um reboot** — se
a máquina reiniciar, precisa ser religado à mão.

---

## 6. Armadilhas desta sessão, para não pagar de novo

1. **`not_in_nav` não exclui nada** (herdada de antes, mas repetida aqui):
   quem tira do build é `exclude_docs`.
2. **`shutil.which("bash")` no Windows acha o stub da WSL**, em `System32`, que
   não é um shell — e nesta máquina ele demora **75 segundos** para falhar.
   Sonda que confia no `which` reprova script correto e culpa o arquivo por
   defeito do ambiente. Teste o candidato antes de usá-lo.
3. **Lista de dependência escrita à mão envelhece em silêncio.** Ver §2.4.
4. **Medir CUDA por tamanho é palpite.** `torch.version.cuda` é o fato.
5. **A API de Security List substitui a lista inteira.** Ver §2.2.
6. **`openssl` existe no Git Bash, não no PowerShell.** Na VM (Linux) não é
   problema; em script que rode dos dois lados, é.
7. **Sonda que casa comentário mede a documentação, não o comportamento.** O
   teste do `rsync` lê só os blocos de comando — a prosa *explica* por que o
   rsync saiu, e casá-la faria o teste falhar contra o próprio texto que
   documenta a regra. Esse erro já foi cometido antes, em
   `test_documentacao.py`.
