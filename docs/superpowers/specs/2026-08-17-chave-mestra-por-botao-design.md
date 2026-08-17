# Ligar a autenticação por um botão — chave mestra sem terminal

Data: 2026-08-17

## O problema

Hoje ligar a autenticação exige três passos fora da interface: inventar um
segredo no terminal, subir a API com `FRAUS_CHAVE_MESTRA` no ambiente e emitir
uma chave de acesso por `curl`. Cada passo é uma chance de a banca ver a API
aberta por esquecimento — e "sem autenticação" é o primeiro item das limitações
conhecidas do README.

O pedido é um botão na tela de Configurações. O que ele precisa entregar:
gerar a mestra, ligar a exigência de chave e **deixar a dashboard funcionando
depois do clique**.

## O que NÃO é feito, e por quê

- **Botão que sobe ou reinicia o servidor.** A dashboard é uma página web que
  pode rodar em outra máquina; uma rota que executa processo no servidor é uma
  porta pior do que a ausência de autenticação que ela viria consertar. E ficou
  desnecessária: como as dependências chegam por `app.state.contexto`
  (refactor de 2026-08-17), ligar a autenticação vale na requisição seguinte,
  sem reiniciar nada.
- **Desligar a autenticação pela web.** Um botão que *baixa* a defesa não tem
  contrapartida de risco aceitável. Desligar continua sendo trabalho de
  ambiente: apagar a linha do banco e a variável.

## A mudança que sustenta tudo

`registrar_middleware_de_acesso` só registra o middleware **quando há mestra no
boot**. Ligar em runtime nesse desenho não protegeria nada — o middleware não
existiria, e o botão apenas *pareceria* funcionar.

O middleware passa a ser **sempre registrado** e decide **por requisição**,
consultando o estado vigente. Sem mestra ele libera, exatamente como hoje. O
custo é uma consulta por requisição; o ganho é que a decisão deixa de ser um
retrato do boot.

## Onde a mestra vive

Uma tabela com uma linha só:

```sql
CREATE TABLE IF NOT EXISTS chave_mestra (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    chave_hash TEXT NOT NULL,
    dica TEXT NOT NULL,
    criada_em TEXT NOT NULL
)
```

`CHECK (id = 1)` é a garantia estrutural de que não existem duas mestras: o
banco recusa a segunda em vez de a aplicação precisar lembrar de conferir.

A mestra em claro continua **nunca tocando o disco** — o banco guarda o hash
SHA-256 (mesma decisão de `fraus/credencial.py`: o segredo tem 256 bits
sorteados, não é senha, e um KDF lento se pagaria em toda requisição sem
comprar nada).

**Precedência:** `FRAUS_CHAVE_MESTRA` no ambiente vence o banco. Quem já usa a
variável não muda nada, e a variável continua sendo a saída para quem perdeu a
chave gerada pelo botão.

## As rotas

### `GET /acesso/estado` — pública

```json
{"ligada": true, "origem": "banco"}
```

`origem` é `"ambiente"`, `"banco"` ou `null`. Não devolve dica, hash nem data:
a tela só precisa saber o que desenhar. É pública por necessidade — a tela
precisa dela justamente quando ainda não há credencial nenhuma.

### `POST /acesso/mestra`

Dois caminhos, decididos pelo estado:

1. **Sem mestra (primeiro uso).** Gera o segredo (`frm_` + 32 bytes
   sorteados), grava o hash e **emite junto uma chave de acesso `dashboard`**.
   Devolve as duas em claro, uma única vez, com o aviso. `201`.
2. **Já ligada.** Exige a mestra atual no `Authorization` e **rotaciona**: a
   antiga deixa de valer no mesmo instante. Sem a mestra atual, `409` — nunca
   um `201` que sobrescreveria a credencial de quem está dentro.

A emissão da chave de acesso junto não é conveniência: sem ela, o clique
deixaria a própria dashboard em `401`, e o passo seguinte seria o terminal que
o botão veio eliminar.

### `GET /acesso/chaves` e as demais

Inalteradas. O privilégio da mestra continua sendo `exigir_mestra`, que agora
consulta a mestra vigente (ambiente ou banco) em vez da capturada no boot.

## A dashboard depois do clique

O proxy do Next lê a chave de acesso de `FRAUS_CHAVE_ACESSO`. Variável de
ambiente não muda em processo vivo, então o clique precisa de outro caminho:

- **Rota própria** `POST /api/fraus/ligar-autenticacao` no Next: chama
  `POST /acesso/mestra`, e quando vem `201` grava a chave de acesso num cookie
  `httpOnly` (`SameSite=Lax`, `Secure` fora de desenvolvimento). Devolve à tela
  as duas chaves em claro — a única vez que elas existem.
- **O proxy geral** passa a montar o header com `env ?? cookie`. Ele continua
  bobo: repassa bytes e não inspeciona corpo de resposta. Quem sabe o
  significado de uma rota específica é a rota específica.
- `httpOnly` mantém a promessa atual: a chave não toca o JS do navegador.

Efeito colateral desejável: outro navegador que abrir a dashboard publicada
sem o cookie cai em `401` em vez de ler os dados. A dashboard não tinha login
nenhum — isto é o primeiro passo de um, e o README precisa parar de dizer que
"quem alcança a URL lê os dados pelo proxy" sem ressalva.

## A tela

Painel novo em `/configuracoes`, acima das faixas:

- **Desligada:** explica em uma frase o que o botão faz e o botão "Ligar
  autenticação".
- **Ligando:** as duas chaves em claro, com aviso de que não voltam a
  aparecer, e um botão de copiar cada uma.
- **Ligada:** o estado, a origem (ambiente ou banco) e a instrução de como
  rotacionar. Sem botão de desligar.

## Testes

- **API (pytest):** estado desligado/ligado por ambiente/ligado por banco;
  primeiro uso devolve as duas chaves e passa a exigir chave na requisição
  seguinte **no mesmo processo** (é o teste que prova o middleware por
  requisição); segunda chamada sem a mestra atual é 409; rotação com a mestra
  atual invalida a antiga; a chave de acesso emitida no primeiro uso autentica
  de fato; `CHECK (id = 1)` recusa segunda linha; nada de hash nas respostas.
- **Dashboard:** `npm run build` verde e verificação manual contra
  `scripts/api_demo.py` — a suíte de testes do front não existe hoje e criá-la
  não é escopo desta feature.

## Critério de pronto

- Ligar a autenticação sem abrir terminal, e a dashboard continua navegando.
- `uv run pytest -q` verde, com os testes novos acima.
- Reiniciar a API mantém a autenticação ligada.
- README atualizado: o botão como caminho principal, a variável como override.
