# API modular — quebrar `fraus/api/main.py` em módulos por domínio

Data: 2026-08-17

## O problema

`fraus/api/main.py` tem 1367 linhas. Dentro dele convivem sete coisas de
natureza diferente: os schemas de entrada, a classe `Motor` (domínio puro),
toda a autenticação, os helpers de validação de período e de caminho, os
derivados de leitura (`faixas_vigentes`, `categoria_de`), as constantes de
configuração e as ~30 rotas de oito domínios.

O que prende tudo junto não é acoplamento real — é que **cada rota é uma
closure** dentro de `criar_app(banco, motor, raiz_importacao, chave_mestra)`.
Enquanto a dependência chegar por fechamento léxico, nenhuma rota pode morar
em outro arquivo.

O núcleo do projeto já é modular (`sinais/`, `ingest/`, `db.py`,
`indicadores.py`, `fusor.py`). O que destoa é só a borda HTTP.

## Referência: wascer-watcher

O padrão que se quer espelhar, do repositório `soureiBR/wascer-watcher`
(NestJS):

- `apps/api/src/{auth,health,scan,admin}` — um módulo por domínio, cada um com
  controller (só HTTP) + `dto/`
- `libs/contracts/src/{dto,enums,events}` — contratos compartilhados
- `libs/database` — acesso a dado isolado
- `libs/tracking-core` — regra de negócio pura, longe do controller

A tradução para FastAPI não copia o framework, copia a **fronteira**: HTTP num
lugar, contrato noutro, domínio noutro.

## Escopo

Refactor **estritamente estrutural**. O contrato HTTP não muda: mesmos paths,
mesmos corpos de resposta, mesmos status, mesmos cabeçalhos. `criar_app`
mantém assinatura e comportamento. `scripts/api_demo.py` e a dashboard não são
tocados.

Fora de escopo: deploy/k8s, pendências funcionais do README (fusor de 30
features, retreino da ironia), camada de serviço por domínio.

## Arquitetura alvo

```
fraus/
  motor.py           # classe Motor — domínio, sai da borda HTTP
  api/
    main.py          # só criar_app: monta Contexto, middlewares, include_router
    contexto.py      # dataclass Contexto + obter_contexto (dependência FastAPI)
    esquemas.py      # os 7 BaseModel de entrada
    seguranca.py     # bearer, mestra, chave de acesso, chave de fonte, middleware
    periodo.py       # dia_ou_400, recorte_ou_400, no_recorte
    caminhos.py      # resolver_dentro_da_raiz, metricas_de, constantes de path
    rotas/
      saude.py          # GET /saude
      conversas.py      # /conversas, /conversas/{id}, /conversas/{id}/atribuicao,
                        # POST /conversas/importar
      indicadores.py    # /indicadores, /lexico, /serie-temporal
      configuracoes.py  # GET+PUT /configuracoes
      integracoes.py    # /integracoes/* (fontes, chave da fonte, tipos,
                        # arquivos, importacoes)
      acesso.py         # /acesso/chaves
      ingestao.py       # POST /ingestao
      modelo.py         # /modelo, /modelo/lexicon, /modelo/simular,
                        # /analisar, /analisar/arquivo
```

### Como a dependência deixa de ser closure

Um `Contexto` — dataclass com o que hoje é fechado por `criar_app`:

```python
@dataclass(frozen=True)
class Contexto:
    banco: Banco
    motor: Motor
    raiz: Path
    chave_mestra: str | None

    def faixas_vigentes(self) -> dict: ...
    def categoria_de(self, score: float | None, faixas: dict) -> str | None: ...
    def registros_do_recorte(self, de, ate) -> list: ...
```

`criar_app` guarda a instância em `app.state.contexto`; `obter_contexto(request)`
a devolve. Cada rota declara **um** parâmetro:

```python
@router.get("/indicadores")
def indicadores(de: str | None = None, ate: str | None = None,
                ctx: Contexto = Depends(obter_contexto)) -> dict:
```

Rotas viram funções de nível de módulo em `APIRouter`s importáveis e testáveis
isoladamente. `faixas_vigentes` e `categoria_de` — hoje redefinidas dentro do
`criar_app` e usadas por seis rotas — passam a ter um dono só.

**Contenção do god object:** o `Contexto` só carrega o que é usado por mais de
um domínio. O que é de um domínio só (`metricas_de`, a listagem de arquivos
importáveis, os tetos de `/analisar`) fica no módulo daquele domínio.

### Autenticação

`seguranca.py` concentra o que hoje está espalhado entre funções de módulo e
closures de `criar_app`:

- `chave_bearer`, `chave_do_cabecalho` — parsing do `Authorization`, com a
  normalização de esquema sem caixa que hoje já é ponto único
- `fonte_autorizada` — credencial de fonte para `POST /ingestao`
- `e_mestra`, `acesso_autorizado`, `exigir_mestra` — hoje closures sobre
  `chave_mestra`; viram funções que recebem o `Contexto`
- `middleware_de_acesso(app, contexto)` — registra o middleware só quando há
  chave mestra, preservando a isenção de `/ingestao` e de `OPTIONS`

**Ordem de middleware é comportamento, não estilo.** O CORS é registrado
DEPOIS do middleware de chave para ficar por fora dele (em Starlette o último
registrado é o mais externo) — sem isso o preflight, que não carrega
`Authorization` por definição, morre em 401. O comentário que documenta isso
acompanha o código para `main.py`.

### Motor

`Motor` sai para `fraus/motor.py` — é domínio puro (classificador + fusor),
equivalente ao `libs/tracking-core` do watcher. `fraus/api/main.py` reexporta o
nome, de modo que `from fraus.api.main import Motor` continua funcionando em
testes e scripts.

O `__getattr__` de módulo (PEP 562) que constrói `app` preguiçosamente
permanece em `main.py`, com o mesmo comportamento de falhar alto no boot
quando o modelo não existe.

## Rede de segurança

A suíte atual (`test_api.py`, `test_api_periodo.py`, `test_autenticacao.py`,
`test_acesso.py`) bate na API por `criar_app` e é o que prova o refactor. Como
ela precede o refactor, ela é **auditada antes**:

1. Levantar rota por rota (as ~30) o que a suíte hoje exerce — status feliz,
   status de erro, formato de resposta.
2. Escrever os testes que faltam para as rotas descobertas, **contra o código
   atual**, e vê-los passar. Teste escrito depois do refactor não prova nada:
   ele nasceria testando o código novo, não o comportamento antigo.
3. Só então mover código.

Nenhum teste existente é editado durante o refactor. Se um precisar mudar, o
contrato mudou — e isso é violação de escopo, não ajuste.

## Ordem de execução

Cada passo termina com a suíte verde. Nenhum passo mistura mover código com
mudar código.

0. Auditar cobertura; escrever os testes faltantes contra o código atual.
1. `esquemas.py` — mover os 7 `BaseModel`. Sem dependência, risco mínimo.
2. `motor.py` — mover a classe `Motor`; reexportar em `main.py`.
3. `periodo.py` e `caminhos.py` — helpers puros.
4. `contexto.py` — `Contexto` + `obter_contexto`; `criar_app` passa a montá-lo
   e a usá-lo internamente, ainda com as rotas no lugar.
5. `seguranca.py` — auth e middleware.
6. `rotas/` — um domínio por vez, do mais isolado para o mais entrelaçado:
   saúde → configurações → acesso → integrações → ingestão → modelo →
   indicadores → conversas.
7. `main.py` final: só montagem (~120 linhas).

## Critério de pronto

- `uv run pytest -q` verde, com a suíte auditada e **sem uma linha de teste
  existente editada**.
- Nenhum arquivo de `fraus/api/` acima de ~250 linhas.
- `criar_app` com a mesma assinatura; `from fraus.api.main import Motor` e
  `uvicorn fraus.api.main:app` seguem funcionando.
- `scripts/api_demo.py` sobe e a dashboard fala com a API sem alteração.
- Diff sem mudança de comportamento: toda linha movida é a mesma linha.
