# Landing page e autenticação de usuário — plano de implementação

> Spec: `docs/superpowers/specs/2026-08-31-lp-e-autenticacao-design.md`.
> TDD em cada task de código: teste que falha, implementação mínima, verde,
> commit. Commits em conventional commits, assunto sem acento.

## Constraints globais

- Segredos (`FRAUS_JWT_SEGREDO`, `FRAUS_CODIGO_DEV`) moram no ambiente, nunca
  no banco.
- Papel decidido no servidor, sempre — a interface só esconde.
- Nenhuma mensagem de erro distingue "e-mail não existe" de "senha errada".
- `str(ValidationError)` nunca vai para log nem para `detail` (armadilha 10).
- Rotas antigas da dashboard redirecionam para `/dashboard/*`.

---

### Task 1: usuários no banco e o módulo de senha — `feat(usuarios)`

- `fraus/usuarios.py`: `gerar_hash(senha)` (scrypt, salt 16B, `n=2**14, r=8,
  p=1`, formato `scrypt$<salt_b64>$<hash_b64>`), `confere(senha, guardado)`
  em tempo constante, tolerante a `None` e a formato inválido.
- `fraus/db.py`: tabela `usuarios` (`id`, `nome`, `email` UNIQUE COLLATE
  NOCASE, `senha_hash`, `papel` CHECK IN ('dev','usuario'), `criado_em`,
  `ativo`), com `criar_usuario`, `buscar_usuario_por_email`,
  `buscar_usuario` — o hash **nunca** sai nos dicionários de leitura
  (mesmo desenho de `_fonte()`).
- Testes: `tests/test_usuarios.py` (hash ≠ senha, salt diferente a cada
  chamada, confere/recusa, tempo constante por API, e-mail duplicado é
  recusado no banco, leitura não expõe hash).

### Task 2: o token — `feat(auth)` parte 1

- Dependência nova: `pyjwt` no `pyproject.toml` (motivo na spec §2.4).
- `fraus/token_acesso.py`: `emitir(usuario_id, papel, segredo, agora)` e
  `conferir(token, segredo, agora)` → dict ou `None`. HS256 **fixo** —
  qualquer outro `alg` é recusado por construção; `exp` de 12h conferido.
- Testes: `tests/test_token_acesso.py` (ida e volta, expirado recusa,
  assinatura errada recusa, `alg: none` recusa, payload carrega `sub`/`papel`).

### Task 3: as rotas de auth — `feat(api)`

- `fraus/api/rotas/auth.py`: `POST /auth/registrar` (papel `dev` só com
  `codigo_dev` igual a `FRAUS_CODIGO_DEV`; sem a variável, dev não nasce),
  `POST /auth/entrar` (mensagem única para e-mail/senha errados; 503 se
  `FRAUS_JWT_SEGREDO` ausente — mesmo contrato do webhook sem segredo),
  `GET /auth/eu` (quem sou, do token).
- `Contexto` ganha `jwt_segredo` e `codigo_dev` por parâmetro (injeção, como
  `chave_mestra`).
- Isentas: `/auth/entrar` e `/auth/registrar` no middleware.
- Testes: `tests/test_auth.py` (cadastro, papel por código, entrar devolve
  token válido, mensagem uniforme, isenção com mestra ligada, `/auth/eu`).

### Task 4: JWT como credencial e o portão de papel — `feat(api)`

- `seguranca.py`: `acesso_autorizado` aceita JWT válido como terceira
  credencial (mestra ligada).
- `exigir_dev(ctx, authorization)`: JWT de `usuario` → 403 nas rotas
  administrativas (integrações, configurações PUT, léxico escrita, chaves,
  importar, modelo); credencial técnica passa.
- Testes: matriz papel × rota em `tests/test_auth.py`.

### Task 5: sessão no Next — `feat(dashboard)`

- Rotas Next `app/api/sessao/entrar|sair/route.ts`: chamam a API, gravam/
  apagam cookie httpOnly `SameSite=Lax`.
- `middleware.ts`: `/dashboard/*` sem cookie válido redireciona à LP; telas
  administrativas exigem `papel === 'dev'` (o papel sai do token conferido —
  no proxy, nunca no navegador).
- Proxy `[...caminho]` repassa o token como `Authorization: Bearer`.

### Task 6: a migração de rotas — `feat(dashboard)`

- Telas atuais movem para `app/dashboard/*`; layout da dashboard (sidebar,
  ateliê) desce junto para esse segmento.
- Redirects das rotas antigas em `next.config`.
- `npx tsc --noEmit`, `npm run build`, `npm run contraste` verdes.

### Task 7: telas de entrar e cadastrar — `feat(dashboard)`

- `/entrar` e `/cadastrar` no mundo Pauta; cadastro com campo opcional de
  código de convite (é ele que diferencia dev — a spec §2.3 diz por quê).
  Erro de credencial exibe a mensagem única do servidor.

### Task 8: a LP — `feat(lp)`

- `app/page.tsx` vira a página pública: tese, sete sinais → fusor → score,
  honestidade metodológica, entrada. Sem número inventado (spec §2.8).
  Sessão ativa mostra "ir para a dashboard" no lugar de "entrar".

### Task 9: documentação — `docs`

- README (rotas novas, papéis, variáveis `FRAUS_JWT_SEGREDO` e
  `FRAUS_CODIGO_DEV`), `docs/hospedagem.md`, handoff.
