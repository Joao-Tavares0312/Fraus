#!/usr/bin/env bash
#
# Sobe a API do Fraus numa VM Ubuntu recem-criada (Oracle Ampere A1).
#
# Uso:   scripts/provisionar_oracle.sh SEU_IP [dominio.com]
#
# O passo a passo em prosa esta em docs/hospedagem.md, e ele continua sendo a
# fonte do PORQUE de cada decisao. Este arquivo e o MESMO roteiro executavel --
# existe porque digitar vinte comandos a mao numa sessao ssh erra, e porque o
# erro mais caro daqui (recriar a chave mestra) e invisivel no momento em que
# acontece.
#
# IDEMPOTENTE DE PROPOSITO. Rodar de novo depois de uma falha no meio nao pode
# refazer o que ja deu certo -- em particular NAO regera segredo: um `.env` que
# ja existe e lido, nunca reescrito. Regerar a FRAUS_CHAVE_MESTRA invalidaria
# em silencio a FRAUS_CHAVE_ACESSO que a dashboard na Vercel usa, e o sintoma
# apareceria como "401 em tudo" horas depois, longe da causa.
#
# POR QUE `tar | ssh` E NAO `rsync`: o Git Bash do Windows nao traz rsync. O
# roteiro em prosa pedia rsync e falharia na maquina de quem escreveu o
# projeto. `tar` e `ssh` existem nos dois lados.

set -euo pipefail

IP="${1:-}"
DOMINIO="${2:-}"
REMOTO="ubuntu@${IP}"
RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ -z "$IP" ]; then
    echo "uso: $0 SEU_IP [dominio.com]" >&2
    exit 64
fi

passo() { printf '\n\033[1m== %s\033[0m\n' "$*"; }
erro()  { printf '\033[31mERRO: %s\033[0m\n' "$*" >&2; exit 1; }
nota()  { printf '   %s\n' "$*"; }

# `ssh -T` com heredoc: o comando remoto vem por stdin, entao nada de aspas
# aninhadas. `bash -se` propaga a falha de cada linha para o exit do ssh, que o
# `set -e` daqui transforma em parada -- sem isso o script seguiria alegre
# depois de um passo remoto quebrado.
remoto() { ssh -T -o StrictHostKeyChecking=accept-new "$REMOTO" bash -se; }

# ---------------------------------------------------------------------------
passo "0. A VM responde?"

if ! ssh -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15 \
         -o BatchMode=yes "$REMOTO" true 2>/dev/null; then
    erro "sem ssh em $REMOTO.
   Se a instancia acabou de nascer, espere ~60s pelo primeiro boot.
   Se demora e expira sem recusar, a Security List da VCN nao liberou a 22."
fi
nota "ok"

# ---------------------------------------------------------------------------
passo "1. iptables (o firewall DENTRO da maquina)"
# A imagem Ubuntu da Oracle descarta tudo menos a 22, e isso nao aparece em
# lugar nenhum do assistente de criacao. Abrir so a Security List deixa a
# conexao PENDURADA -- sem recusa, sem erro, sem pista.
#
# `-C` antes de `-I`: checa se a regra ja existe. Rodar o script duas vezes nao
# pode empilhar duplicata na cadeia.
remoto <<'FIM'
set -euo pipefail
for porta in 80 443 ; do
    if sudo iptables -C INPUT -m state --state NEW -p tcp --dport "$porta" -j ACCEPT 2>/dev/null ; then
        echo "   porta $porta ja estava aberta no iptables"
    else
        sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport "$porta" -j ACCEPT
        echo "   porta $porta aberta"
    fi
done
sudo netfilter-persistent save >/dev/null
FIM

# ---------------------------------------------------------------------------
passo "2. Docker"
remoto <<'FIM'
set -euo pipefail
if command -v docker >/dev/null ; then
    echo "   docker ja instalado: $(docker --version)"
else
    curl -fsSL https://get.docker.com | sudo sh >/dev/null
    sudo usermod -aG docker ubuntu
    echo "   docker instalado"
fi
sudo systemctl enable --now docker >/dev/null 2>&1
mkdir -p ~/fraus ~/fraus-modelos ~/fraus-dados
FIM

# ---------------------------------------------------------------------------
passo "3. Mandar o codigo"
# Sem .git: o repositorio e privado, e um clone na VM significaria credencial
# do GitHub morando num host exposto a internet. Sem dashboard/: ela roda na
# Vercel, nao aqui.
tar -czf - -C "$RAIZ" \
    --exclude=.git --exclude=modelos --exclude=dashboard \
    --exclude=node_modules --exclude=site --exclude=.venv \
    --exclude='__pycache__' \
    . | ssh "$REMOTO" "tar -xzf - -C ~/fraus"
nota "codigo em ~/fraus"

# ---------------------------------------------------------------------------
passo "4. Mandar os modelos (1,3 GB -- e aqui que o tempo vai)"
[ -d "$RAIZ/modelos" ] || erro "nao achei $RAIZ/modelos. Sem os pesos a API nao sobe (invariante 7)."

# `-h` resolve link simbolico: o `modelos/` local pode apontar para fora.
tar -czhf - -C "$RAIZ/modelos" . | ssh "$REMOTO" "tar -xzf - -C ~/fraus-modelos"
remoto <<'FIM'
set -euo pipefail
echo "   $(du -sh ~/fraus-modelos | cut -f1) em ~/fraus-modelos"
for exigido in bertimbau-satisfacao bertimbau-emocao bertimbau-ironia fusor.joblib ; do
    [ -e "$HOME/fraus-modelos/$exigido" ] || { echo "FALTA: $exigido" >&2 ; exit 1 ; }
done
FIM

# ---------------------------------------------------------------------------
passo "5. Segredos -- gerados UMA vez, nunca reescritos"
remoto <<FIM
set -euo pipefail
if [ -f ~/fraus/.env ] ; then
    echo "   .env ja existe -- preservado (regerar a mestra quebraria a Vercel em silencio)"
else
    umask 077
    cat > ~/fraus/.env <<ENV
FRAUS_CHAVE_MESTRA=\$(openssl rand -hex 32)
FRAUS_JWT_SEGREDO=\$(openssl rand -hex 32)
FRAUS_CODIGO_CONVITE=troque-esta-frase-agora
FRAUS_ORIGENS=${DOMINIO:+https://}${DOMINIO:-http://localhost:3000}
ENV
    echo "   .env criado (modo 600)"
fi
FIM

# ---------------------------------------------------------------------------
passo "6. Construir a imagem"
remoto <<'FIM'
set -euo pipefail
cd ~/fraus
docker build -t fraus-api . 2>&1 | tail -5

# O torch com CUDA num host sem GPU nao QUEBRA -- so faz a imagem crescer
# alguns GB. Falha silenciosa merece sonda explicita.
#
# A sonda pergunta a PROPRIA BIBLIOTECA, e nao mede megabyte: em 11/09/2026 o
# torch 2.14.0+cpu media 769 MB de CPU puro, sem um pacote nvidia sequer, e um
# limiar de tamanho acusaria CUDA onde nao ha. `torch.version.cuda` e o fato.
versao=$(docker run --rm fraus-api python -c "import torch; print(torch.__version__, torch.version.cuda)")
echo "   torch: $versao"
case "$versao" in
    *" None") : ;;
    *) echo "veio CUDA junto ($versao) -- ver o comentario de arquitetura no Dockerfile" >&2 ; exit 1 ;;
esac
FIM

# ---------------------------------------------------------------------------
passo "7. Subir"
remoto <<'FIM'
set -euo pipefail
cd ~/fraus
cat > compose.yml <<'YML'
services:
  api:
    image: fraus-api
    restart: always
    env_file: .env
    ports:
      # SO em 127.0.0.1: quem conversa com a internet e o Caddy, com TLS.
      # Publicar 0.0.0.0:8000 exporia a API em texto claro na porta 8000,
      # contornando o proxy sem que nada reclamasse.
      - "127.0.0.1:8000:8000"
    volumes:
      - /home/ubuntu/fraus-modelos:/modelos:ro
      - /home/ubuntu/fraus-dados:/dados
YML
docker compose up -d
FIM

# ---------------------------------------------------------------------------
passo "8. Conferir que o motor e REAL"
# Invariante 7: servir predicao sem modelo carregado e pior do que estar fora
# do ar. `"motor":"duble"` aqui e falha, nao aviso -- o duble devolve numero
# sintetico com cara de predicao.
remoto <<'FIM'
set -euo pipefail
for tentativa in $(seq 1 30) ; do
    resposta=$(curl -s --max-time 5 localhost:8000/saude || true)
    case "$resposta" in
        *'"motor":"real"'*)  echo "   $resposta" ; exit 0 ;;
        *'"motor":"duble"'*) echo "MOTOR DUBLE: os modelos nao foram encontrados no volume." >&2 ; exit 1 ;;
    esac
    sleep 5
done
echo "a API nao respondeu em 150s. Log:" >&2
cd ~/fraus && docker compose logs --tail 40 >&2
exit 1
FIM

# A porta destrancada: mestra + jwt SEM codigo de convite deixa qualquer um
# fazer registrar -> entrar e ler tudo. A API grita no boot; o script repete,
# porque o log da primeira subida e exatamente o que ninguem le.
if remoto <<<'grep -q "^FRAUS_CODIGO_CONVITE=troque-esta-frase-agora" ~/fraus/.env' ; then
    printf '\n\033[33mAVISO: FRAUS_CODIGO_CONVITE ainda esta no valor de fabrica.\033[0m\n'
    nota "Com mestra e JWT ligados e o convite no padrao, o cadastro fica ABERTO."
    nota "Troque em ~/fraus/.env e rode: cd ~/fraus && docker compose up -d"
fi

# ---------------------------------------------------------------------------
if [ -n "$DOMINIO" ]; then
    passo "9. HTTPS com o Caddy ($DOMINIO)"
    # A dashboard esta em https://, e o navegador RECUSA chamar api em http://
    # (mixed content). TLS nao e opcional aqui.
    remoto <<FIM
set -euo pipefail
command -v caddy >/dev/null || { sudo apt-get update -qq && sudo apt-get install -y -qq caddy ; }
echo "${DOMINIO} {
    reverse_proxy 127.0.0.1:8000
}" | sudo tee /etc/caddy/Caddyfile >/dev/null
sudo systemctl enable caddy >/dev/null 2>&1
sudo systemctl restart caddy
FIM
    nota "conferindo o certificado (o Let's Encrypt leva alguns segundos)..."
    sleep 20
    curl -sS --max-time 20 "https://${DOMINIO}/saude" || \
        nota "ainda nao respondeu -- confira se o DNS de ${DOMINIO} aponta para ${IP}"
else
    passo "9. HTTPS -- PULADO"
    nota "Sem dominio, a API so responde em localhost:8000 DENTRO da VM."
    nota "O Let's Encrypt nao emite certificado para IP; um subdominio gratuito"
    nota "(DuckDNS) resolve. Depois rode de novo: $0 $IP seu-dominio.com"
fi

# ---------------------------------------------------------------------------
passo "Pronto"
nota "Chave de acesso para a Vercel (a mestra fica na VM, nunca no Next):"
nota "  ssh $REMOTO"
nota "  source ~/fraus/.env && curl -X POST localhost:8000/acesso/chaves \\"
nota "       -H \"Authorization: Bearer \$FRAUS_CHAVE_MESTRA\" \\"
nota "       -H 'Content-Type: application/json' -d '{\"nome\":\"dashboard\"}'"
nota ""
nota "GUARDE a FRAUS_CHAVE_MESTRA fora da VM -- ela nao e recuperavel."
