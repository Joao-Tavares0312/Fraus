# E2 — Calibração, abstenção e conformal: plano de implementação

> **Para quem executa:** SUB-SKILL OBRIGATÓRIA: superpowers:subagent-driven-development. Passos em checkbox (`- [ ]`).

**Objetivo:** dizer quando a nota merece confiança, com garantia estatística declarada:
- um conjunto de classes por conversa (conformal Mondrian por classe), calculado a partir do **score gravado**;
- abstenção ("leitura sem confiança suficiente") que marca, mas não remove a conversa do NPS;
- instrumentos que medem calibração (ECE/MCE) e cobertura.

**Arquitetura:**
- **`fraus/conformal.py` (puro):** ajuste dos limites por classe, conjunto, divisão estratificada, artefato.
- **`fraus/calibracao.py` (puro):** ECE, MCE, ECE por classe e bootstrap.
- **Artefato `fraus/dados/conformal_fusor.json`:** chaveado pela **régua** (`regua_do_fusor`).
- **Duas rotas de leitura**, com 503 explícito sem artefato ou com régua diferente.
- **Três scripts no estilo de `scripts/medir_faixas.py`:** só leem e imprimem.
- **Um selo na tela do atendimento.** Nada é gravado no banco.

**Stack:** Python 3.11, numpy e scikit-learn (já instalados), FastAPI, Next.js/vitest. O matplotlib só entra na execução do PNG, via `uv run --with matplotlib`, e **nunca** como dependência do projeto.

**Spec:** `docs/superpowers/specs/2026-10-14-e2-calibracao-abstencao-design.md`. Decisão do João em 14/10: o conformal sai do score gravado, sem schema novo.

## Restrições globais

- `score`, nota e categoria gravados **não mudam**. A abstenção marca e informa, e a conversa **continua no NPS e no CSAT**.
- Nada novo é persistido no banco. O artefato é um arquivo versionado em `fraus/dados/`, fora de `modelos/`, que não pode ser tocado.
- Sem artefato, ou com a régua do artefato diferente da vigente, as rotas novas respondem **503 com o motivo**. Nunca devolvem conjunto vazio fingindo confiança (mesmo espírito da invariante 7). Indicadores e rotas existentes não dependem do artefato.
- `None` nunca vira 0. Conversa sem score não tem conjunto (`null`) e não entra em contagem de abstenção.
- **Garantia declarada** em toda saída: "cobertura ≥ alvo **por classe**, sob permutabilidade com o conjunto de calibração; **não vale** sob mudança de distribuição (atendimento real ≠ holdout sintético); o sinal de tempo do fusor é sintético".
- Não retreinar nada. Não tocar `modelos/`, `NOMES_FEATURES`, `PESO_NEUTRO_NO_SCORE`, `FEATURES_EM_LOG` nem a cabeça de ironia. Nenhuma dependência nova.
- Identificadores em português sem acento; texto de tela com acento; fonte mínima de 11 px; tokens de `dashboard/DESIGN.md`.
- Commit por tarefa, com o trailer `Co-Authored-By: Neuro <neuro.chan.dev@gmail.com>`. O controlador junta tudo no commit único da entrega.

## Pontos de revisão

1. **Score fora de todos os intervalos (conjunto vazio).** Conta como abstenção, com o critério `conjunto_vazio`. Nunca vira "confiante".
2. **Score nas bordas 0 e 100** (o score é limitado a esse intervalo). Os limites infinitos viram 0,0 e 100,0, e a comparação usa `≤`.
3. **Classe sem exemplo na calibração.** `ajustar` levanta `ValueError`, porque não existe garantia para ela.
4. **Conversa de outra régua.** No detalhe responde 409 (o score histórico não tem garantia com o artefato atual). No agregado, a conversa fica fora e é contada em `defasadas`.
5. **Artefato malformado** (JSON inválido ou chave faltando). Vira 503 com o motivo, nunca 500.

---

### Tarefa 1: `fraus/conformal.py` (ajuste, conjunto, divisão, artefato)

**Arquivos:**
- Criar `fraus/conformal.py`.
- Teste: `tests/test_conformal.py`.

**Interfaces produzidas:**
- `ajustar(scores_por_classe: dict[int, list[float]], alvo: float) -> dict[int, dict]`, em que cada classe vira `{"inferior": float, "superior": float, "n": int}`.
- `conjunto(score: float, limites: dict[int, dict]) -> list[int]`, ordenado.
- `abstencao(conj: list[int]) -> str | None`. Devolve `"conjunto_vazio"`, `"conjunto_multiplo"` ou `None`.
- `dividir_estratificado(rotulos: list[int], fracao_calibracao: float, semente: int) -> tuple[list[int], list[int]]`. Devolve índices disjuntos.
- `class ConformalIndisponivel(RuntimeError)`.
- `carregar_conformal(caminho: Path, regua_vigente: str | None) -> dict`.
- `serializar(limites, alvo, regua, semente, origem) -> dict`.
- `GARANTIA: str`.

**Método** (deve ficar na docstring do módulo). Para cada classe `y`:
1. Ordenar os `n` scores de calibração dessa classe.
2. `k_inf = floor((n + 1) * (1 - alvo) / 2)` e `k_sup = ceil((n + 1) * (1 - (1 - alvo) / 2))`.
3. `inferior = s_(k_inf)` se `k_inf ≥ 1`, senão `0.0`. `superior = s_(k_sup)` se `k_sup ≤ n`, senão `100.0`.

Sob permutabilidade, `P(S < inferior) ≤ (1 - alvo)/2` e `P(S > superior) ≤ (1 - alvo)/2`, então a cobertura por classe é de pelo menos `alvo`. Referência: Vovk et al., *Algorithmic Learning in a Random World* (Mondrian/label-conditional), e Angelopoulos & Bates (2021), *A Gentle Introduction to Conformal Prediction*.

- [ ] **Passo 1: testes vermelhos.**

```python
# tests/test_conformal.py
import json
import random

import pytest

from fraus.conformal import (ConformalIndisponivel, abstencao, ajustar, carregar_conformal,
                             conjunto, dividir_estratificado, serializar)


def test_limites_por_ordem_com_correcao_de_amostra_finita():
    # n = 19, alvo 0.9: k_inf = floor(20*0.05) = 1, k_sup = ceil(20*0.95) = 19
    scores = list(range(1, 20))  # 1..19
    limites = ajustar({0: scores, 1: scores, 2: scores}, alvo=0.9)
    assert limites[0] == {"inferior": 1.0, "superior": 19.0, "n": 19}


def test_amostra_pequena_abre_para_os_extremos():
    # n = 5, alvo 0.9: k_inf = floor(6*0.05) = 0 -> 0.0 ; k_sup = ceil(6*0.95) = 6 > 5 -> 100.0
    limites = ajustar({0: [10, 20, 30, 40, 50], 1: [1], 2: [99]}, alvo=0.9)
    assert limites[0]["inferior"] == 0.0 and limites[0]["superior"] == 100.0


def test_classe_sem_exemplo_e_erro():
    with pytest.raises(ValueError, match="1"):
        ajustar({0: [1.0], 1: [], 2: [3.0]}, alvo=0.9)


def test_alvo_fora_de_0_1_e_erro():
    with pytest.raises(ValueError):
        ajustar({0: [1.0]}, alvo=1.0)


def test_conjunto_inclui_borda_e_pode_ser_vazio_ou_multiplo():
    limites = {0: {"inferior": 0.0, "superior": 30.0, "n": 9},
               1: {"inferior": 25.0, "superior": 70.0, "n": 9},
               2: {"inferior": 80.0, "superior": 100.0, "n": 9}}
    assert conjunto(30.0, limites) == [0, 1]
    assert conjunto(75.0, limites) == []
    assert conjunto(100.0, limites) == [2]
    assert abstencao([0, 1]) == "conjunto_multiplo"
    assert abstencao([]) == "conjunto_vazio"
    assert abstencao([2]) is None


def test_cobertura_empirica_por_classe_em_dado_permutavel():
    """Simulacao: calibracao e avaliacao da MESMA distribuicao; cobertura media >= alvo - 0.02."""
    sorteio = random.Random(20261014)
    medias = {0: 15.0, 1: 55.0, 2: 85.0}
    coberturas = {c: [] for c in medias}
    for _ in range(200):
        calib = {c: [sorteio.gauss(m, 12) for _ in range(50)] for c, m in medias.items()}
        limites = ajustar(calib, alvo=0.9)
        for c, m in medias.items():
            novos = [sorteio.gauss(m, 12) for _ in range(50)]
            coberturas[c].append(sum(c in conjunto(s, limites) for s in novos) / 50)
    for c in medias:
        assert sum(coberturas[c]) / 200 >= 0.88


def test_divisao_estratificada_disjunta_e_reprodutivel():
    rotulos = [0] * 100 + [1] * 100 + [2] * 100
    a1, b1 = dividir_estratificado(rotulos, 0.5, semente=7)
    a2, b2 = dividir_estratificado(rotulos, 0.5, semente=7)
    assert (a1, b1) == (a2, b2)
    assert set(a1).isdisjoint(b1) and sorted(a1 + b1) == list(range(300))
    assert [rotulos[i] for i in a1].count(0) == 50


def test_artefato_com_regua_diferente_e_indisponivel(tmp_path):
    caminho = tmp_path / "c.json"
    limites = ajustar({0: [1.0, 2.0], 1: [50.0, 51.0], 2: [90.0, 99.0]}, alvo=0.9)
    caminho.write_text(json.dumps(serializar(limites, 0.9, "regua-a", 1, "teste")))
    assert carregar_conformal(caminho, "regua-a")["alvo"] == 0.9
    with pytest.raises(ConformalIndisponivel, match="regua"):
        carregar_conformal(caminho, "regua-b")


def test_artefato_ausente_ou_malformado_e_indisponivel(tmp_path):
    with pytest.raises(ConformalIndisponivel):
        carregar_conformal(tmp_path / "nao-existe.json", "r")
    ruim = tmp_path / "ruim.json"
    ruim.write_text("{nao e json")
    with pytest.raises(ConformalIndisponivel):
        carregar_conformal(ruim, "r")
```

- [ ] **Passo 2:** `uv run pytest -q tests/test_conformal.py` falha com ImportError.
- [ ] **Passo 3: implementar `fraus/conformal.py`.**
  - `ajustar` aplica as fórmulas acima, com `math.floor`/`math.ceil` e índices 1-based.
  - `serializar` devolve `{"versao": 1, "metodo": "conformal Mondrian por classe sobre o score 0-100", "alvo", "regua", "semente", "origem", "limites": {str(classe): {...}}, "garantia": GARANTIA}`.
  - `carregar_conformal` lê o JSON e confere a `regua`. Converte as chaves de volta para `int`. Qualquer `OSError`, `json.JSONDecodeError`, `KeyError` ou `TypeError` vira `ConformalIndisponivel` com o motivo.
  - `dividir_estratificado` usa `random.Random(semente)` por classe, com a fração arredondada por classe.
  - Texto de `GARANTIA`: "cobertura de pelo menos {alvo} por classe, sob permutabilidade com o conjunto de calibração; não vale sob mudança de distribuição, e atendimento real é mudança de distribuição em relação ao holdout sintético; o sinal de tempo do fusor foi treinado em dados sintéticos". O `{alvo}` é formatado na leitura.
  - **Armadilha de ponto flutuante (obrigatório):** `1 - 0.9` vale `0.09999999999999998`, então `20 * (1 - (1 - 0.9)/2)` dá `19.000000000000004` e `ceil` daria 20. Usar `math.floor(x + 1e-9)` e `math.ceil(x - 1e-9)` e comentar o motivo no código. O teste de n = 19 só passa com essa guarda.
- [ ] **Passo 4:** os testes ficam verdes.
- [ ] **Passo 5: commit**, `feat(conformal): conjunto por classe sobre o score gravado`.

---

### Tarefa 2: `fraus/calibracao.py` (ECE, MCE, por classe, bootstrap)

**Arquivos:**
- Criar `fraus/calibracao.py`.
- Teste: `tests/test_calibracao.py`.

**Interfaces produzidas:**
- `faixas(probs: list[list[float]], rotulos: list[int], n_faixas: int = 10) -> list[dict]`. Cada faixa é `{"inferior", "superior", "n", "confianca_media", "acuracia"}`. Faixa vazia tem `n = 0` e médias `None`.
- `ece(probs, rotulos, n_faixas=10) -> float`, sobre a confiança máxima.
- `mce(probs, rotulos, n_faixas=10) -> float`.
- `ece_por_classe(probs, rotulos, n_faixas=10) -> dict[int, float]`, classwise: a prob da classe `c` contra a indicadora `rotulo == c`.
- `bootstrap(funcao, probs, rotulos, reamostras=1000, semente=20261014) -> tuple[float, float]`, com IC de 95%.

- [ ] **Passo 1: testes vermelhos.**

```python
# tests/test_calibracao.py
import pytest

from fraus.calibracao import bootstrap, ece, ece_por_classe, faixas, mce


def test_perfeitamente_calibrado_tem_ece_zero():
    # confianca 1.0 e sempre acerta
    probs = [[1.0, 0.0, 0.0]] * 10 + [[0.0, 0.0, 1.0]] * 10
    rotulos = [0] * 10 + [2] * 10
    assert ece(probs, rotulos) == pytest.approx(0.0)


def test_superconfiante_mede_a_distancia():
    # confianca 0.9, acerta metade -> ECE = |0.9 - 0.5| = 0.4 (uma faixa so)
    probs = [[0.9, 0.05, 0.05]] * 10
    rotulos = [0] * 5 + [1] * 5
    assert ece(probs, rotulos) == pytest.approx(0.4)
    assert mce(probs, rotulos) == pytest.approx(0.4)


def test_faixa_vazia_e_none_e_nao_zero():
    f = faixas([[0.95, 0.05, 0.0]], [0], n_faixas=10)
    vazias = [x for x in f if x["n"] == 0]
    assert vazias and all(x["acuracia"] is None and x["confianca_media"] is None for x in vazias)


def test_ece_por_classe_tem_as_tres_classes():
    probs = [[0.7, 0.2, 0.1], [0.1, 0.8, 0.1], [0.2, 0.2, 0.6]]
    assert set(ece_por_classe(probs, [0, 1, 2])) == {0, 1, 2}


def test_bootstrap_reprodutivel_e_contem_o_ponto():
    probs = [[0.9, 0.05, 0.05]] * 20 + [[0.6, 0.3, 0.1]] * 20
    rotulos = [0] * 15 + [1] * 5 + [0] * 12 + [2] * 8
    a = bootstrap(ece, probs, rotulos)
    assert a == bootstrap(ece, probs, rotulos)
    assert a[0] <= ece(probs, rotulos) <= a[1]
```

- [ ] **Passo 2:** os testes falham.
- [ ] **Passo 3: implementar** com numpy.
  - Faixas de largura igual em [0, 1]. A última faixa inclui 1,0.
  - `ece = Σ (n_b/N) |acc_b − conf_b|`; `mce = max_b |acc_b − conf_b|`, só sobre as faixas não vazias.
  - Bootstrap com `np.random.default_rng(semente)` e percentis 2,5/97,5.
- [ ] **Passo 4:** verde.
- [ ] **Passo 5: commit**, `feat(calibracao): ECE, MCE e por classe com bootstrap`.

---

### Tarefa 3: rotas de confiança (detalhe e agregado)

**Arquivos:**
- Modificar `fraus/api/contexto.py`: método `conformal_vigente()`.
- Criar `fraus/api/rotas/confianca.py`.
- Registrar em `fraus/api/main.py`.
- Teste: `tests/test_confianca_api.py`.

**Caminho do artefato:** `fraus/api/caminhos.py` ganha `CAMINHO_CONFORMAL = RAIZ / "fraus" / "dados" / "conformal_fusor.json"`. Seguir o padrão dos outros caminhos, que podem ser sobrescritos por variável de ambiente; se esse padrão existir, a variável é `FRAUS_CONFORMAL`.

**Interfaces produzidas:**
- `Contexto.conformal_vigente() -> dict`. Levanta `ConformalIndisponivel`. Lê `CAMINHO_CONFORMAL` (ou o caminho injetado pelos testes) e confere contra `self.regua_vigente()`. O contexto/app deve permitir injetar o caminho, para os testes não dependerem do arquivo real.
- `GET /conversas/{conversa_id:path}/confianca`. Responde `{"conversa_id", "score", "conjunto": [classes] | null, "rotulos_conjunto": ["insatisfeito", ...], "abstencao": bool | null, "criterios": [...], "features_fora_da_faixa": [...], "alvo", "garantia", "metodo"}`.
  - Sem score: `conjunto`, `abstencao` e `rotulos` saem `null`, com 200.
  - Régua diferente: 409, reaproveitando `_exigir_regua_vigente` de `fraus/api/rotas/conversas.py` (importar a função existente; não duplicar).
  - Artefato indisponível: 503 com o motivo.
  - O critério de deriva sai de `ctx.motor.deriva_da_amostra([conversa], curadoria)`: as features com `dentro_da_faixa is False` entram em `features_fora_da_faixa`, e `"deriva"` entra nos critérios.
  - Com motor dublê, o critério de deriva fica indisponível. Nesse caso responder `features_fora_da_faixa: null` e `criterios` só com o do conjunto. Não usar 503 inteiro, porque o conjunto não depende do motor.
  - `abstencao = bool(criterios)`.
- `GET /indicadores/confianca?de&ate`. Responde `{"recorte", "com_sinal", "defasadas", "avaliadas", "abstencoes", "fracao_abstencao", "ic_fracao": [lo, hi] | null, "por_criterio": {"conjunto_vazio": n, "conjunto_multiplo": n}, "tamanho_conjunto": {"0": n, "1": n, "2": n, "3": n}, "alvo", "garantia", "metodo"}`.
  - Só o critério do conjunto entra (sem passagem de modelo), e o `metodo` diz isso explicitamente.
  - O IC é de Wilson 95%; se já houver função de Wilson no repositório (`grep -rn wilson fraus`), reaproveitar.
  - `avaliadas == 0` dá `fracao_abstencao: null` e `ic: null`.
  - Escopo via `ctx.registros_do_recorte`. As defasadas saem de `ctx.banco.ids_defasadas(...)`, como na rota `/indicadores/drivers`.
- Nenhuma das duas rotas é administrativa: GET em `/conversas/...` e `/indicadores/...`.

- [ ] **Passo 1: testes vermelhos.** Montar um `Banco` temporário com conversas pontuadas pelo `_motor()` de `tests/test_motor.py`. Seguir o padrão de `tests/test_drivers.py`: `banco.migrar()` e `lexico_versao=banco.lexico_versao()`. Gerar um artefato com `serializar(..., regua=motor.regua())` em `tmp_path` e injetá-lo no app.

  Casos de teste:
  - Com artefato: o detalhe devolve `conjunto` coerente com `conjunto(score, limites)` calculado no teste.
  - Abstenção por conjunto múltiplo e por conjunto vazio.
  - Conversa sem score responde 200 com `conjunto: null`.
  - Artefato ausente dá 503 nas duas rotas e o `/conversas` antigo continua 200.
  - Artefato de outra régua dá 503.
  - Conversa de outra régua dá 409 no detalhe e é contada em `defasadas` no agregado.
  - Escopo: canal fora do escopo dá 404 no detalhe e fica fora do agregado (molde: `tests/test_drivers.py`).
  - O score gravado fica idêntico depois das chamadas.
  - O NPS de `GET /indicadores` é idêntico com e sem artefato. É o teste de que a abstenção não remove a conversa do agregado.
- [ ] **Passo 2:** vermelho.
- [ ] **Passo 3:** implementar.
- [ ] **Passo 4:** `uv run pytest -q tests/test_confianca_api.py tests/test_api.py tests/test_drivers.py`, depois a suíte inteira.
- [ ] **Passo 5: commit**, `feat(confianca): rotas de conjunto conformal e abstencao`.

---

### Tarefa 4: scripts de calibração, abstenção e geração do artefato

**Arquivos:**
- Criar `scripts/calibrar_conformal.py`, `scripts/medir_calibracao.py` e `scripts/medir_abstencao.py`.
- Teste: `tests/test_scripts_confianca.py`.

**Comum aos três:**
- Entram `--cache` (o JSON `{xt, yt, xe, ye}` de `scripts/retreinar_fusor_local.py --cache`) e o fusor vigente de `modelos/fusor.joblib`, carregado por `Fusor.carregar`.
- **Falham alto** se o fusor estiver ausente ou incompatível. Nunca há fusor substituto.
- O holdout é `xe`/`ye` (300). A divisão é `dividir_estratificado(ye, 0.5, semente=20261014)` em calibração e avaliação. **Nada de `xt` entra** (é o treino).
- **Instrumentos, não botões:** só imprimem, exceto `calibrar_conformal.py --gravar`.
- Lógica pura e testável em funções, com o `main()` fino, como em `medir_faixas.py`.

**Cada script:**
- **`calibrar_conformal.py`:** ajusta os limites (`alvo` padrão 0,9, via `--alvo`) na metade de calibração. Imprime limites, `n` por classe, cobertura e tamanho médio na metade de avaliação. Só grava `fraus/dados/conformal_fusor.json` com `--gravar`, usando `serializar(..., regua=regua_do_fusor(fusor), origem="holdout B2W semente 999, metade de calibracao semente 20261014")`.
- **`medir_calibracao.py`:**
  - Na metade de avaliação e no holdout inteiro (as duas linhas rotuladas), imprime ECE e MCE da confiança máxima e ECE por classe, todos com IC por bootstrap.
  - Imprime a tabela de faixas.
  - Imprime uma tabela por fatia, reaproveitando `fraus/fatias.py` `fatias_de` sobre as features.
  - Com `--png CAMINHO`, gera o reliability diagram. O `matplotlib` é importado **dentro** da função, com mensagem clara: "rode com `uv run --with matplotlib`".
  - Se ECE > 0,05 e o IC não cruzar 0,05, imprime uma **proposta** de temperatura: ajusta `T` minimizando a log-loss na metade de calibração, aplicada aos logits `l_c = log P_c`, e mostra o ECE resultante na avaliação. Imprime o aviso "PROPOSTA — não aplicada; aplicar mudaria a régua e exigiria repontuar". Nada é gravado.
- **`medir_abstencao.py`:**
  - Para `alvo` em 0,80, 0,85, 0,90 e 0,95, ajusta na calibração e mede na avaliação: cobertura geral e por classe, tamanho médio do conjunto, fração de abstenção, acurácia das conversas não abstidas (`argmax` das probabilidades do fusor contra o rótulo) e a curva risco × cobertura.
  - Declara a tolerância binomial `2·sqrt(alvo(1−alvo)/n)`.
  - Marca o ponto de operação em 0,90.

- [ ] **Passo 1: testes vermelhos** das funções puras dos scripts, com fusor sintético treinado em memória (molde: `tests/test_contrafactual.py` `_fusor_com_tempo_variando`) e um cache sintético pequeno em `tmp_path`.
  - A cobertura medida fica perto do alvo.
  - `--gravar` ausente não cria arquivo.
  - Fusor ausente gera erro (`SystemExit` diferente de zero ou exceção).
  - O PNG sem matplotlib dá mensagem clara. Esse caso é pulado se o matplotlib estiver instalado.
- [ ] **Passo 2:** vermelho.
- [ ] **Passo 3:** implementar.
- [ ] **Passo 4:** verde, mais a suíte inteira.
- [ ] **Passo 5: commit**, `feat(confianca): instrumentos de calibracao, abstencao e geracao do artefato`.

---

### Tarefa 5: selo de confiança na tela do atendimento

**Arquivos:**
- Em `dashboard/lib/api.ts`: tipo `Confianca` e `obterConfianca(id)`, que é uma leitura do servidor no molde de `obterAtribuicao`.
- Criar `dashboard/components/SeloConfianca.tsx` e o teste `SeloConfianca.test.tsx` (`renderToStaticMarkup`).
- Em `dashboard/app/dashboard/atendimentos/[id]/page.tsx`, incluir `obterConfianca` no `Promise.all` e renderizar perto do cartão da nota.

**Comportamento:**
- **Abstenção:** "Leitura sem confiança suficiente", com os critérios em linguagem simples:
  - conjunto com mais de uma classe: "a nota é compatível com mais de uma categoria";
  - conjunto vazio: "a nota não se parece com nenhuma categoria calibrada";
  - deriva: "fora da faixa de treino em: …".

  Logo abaixo: "Continua contando no NPS."
- **Sem abstenção:** "Conjunto de {alvo·100}%: {rótulo}", em uma linha discreta.
- **Rodapé:** a `garantia` do servidor em texto pequeno.
- **503:** estado vazio "Calibração conformal ainda não gerada para este modelo", com o `detail` do servidor. O texto não pode dizer "confiante".
- **409:** "pontuada com outra régua; repontue para ver a confiança".
- **Score nulo:** não renderiza nada. A tela já diz "sem sinal".
- **Proibido:** calcular conjunto ou abstenção no cliente, e `?? 0` / `|| 0`.

- [ ] **Passos:** teste vermelho, implementação, `npx vitest run`, `npx tsc --noEmit`, `npm test` e `npm run build`. Se o build regenerar `dashboard/AGENTS.md`, restaurar o arquivo. Commit `feat(dashboard): selo de confianca conformal no atendimento`.

---

### Tarefa 6: documentação, cartão do modelo e verificação

**Arquivos:** `docs/limitacoes.md`, `docs/cartao-do-modelo.md`, `docs/arquitetura.md`, README (rotas), `CLAUDE.md` (linhas do mapa para `fraus/conformal.py` e `fraus/calibracao.py`) e a seção "Desvios aceitos" do spec do E2.

- [ ] **`docs/limitacoes.md`:** a seção do IC ganha um parágrafo.
  - Diz que a calibração **do fusor** agora tem instrumento, mas os números ainda não foram medidos com o fusor vigente. Só onde for verdade: "não verificado: fusor log1p ausente na máquina de desenvolvimento em 14/10/2026".
  - Explica o conjunto conformal, a garantia e o limite da permutabilidade.
  - Diz que a abstenção não remove a conversa do NPS.
- [ ] **`docs/cartao-do-modelo.md`:** seção "Calibração e conformal do fusor", com os comandos exatos e a marca **"não verificado"** nas células de número.
- [ ] **Desvios aceitos no spec:**
  - exposição por duas rotas próprias (detalhe e agregado), e não na lista;
  - o agregado usa só o critério de conjunto;
  - artefato chaveado pela régua;
  - conjunto vazio conta como abstenção.
- [ ] **Verificação, com a saída colada no relatório:**
  - `uv run pytest -q`;
  - `cd dashboard && npm test && npx tsc --noEmit && npm run build`;
  - diff do OpenAPI contra a linha de base em `…/scratchpad/baseline/openapi.json`: só aparecem `/conversas/{conversa_id}/confianca` e `/indicadores/confianca`, além das do E1;
  - `git diff --stat cdaa9e2 -- modelos/ requirements.txt` vazio;
  - constantes intactas;
  - `uv run pytest -q tests/test_documentacao.py`;
  - mkdocs público `--strict`.
- [ ] **Commit:** `docs(confianca): limitacoes, cartao e desvios do E2`.
