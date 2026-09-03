from fraus.seguranca.pii import censurar_pii


def test_mascara_cpf_valido():
    # 529.982.247-25 e um CPF com digito verificador valido.
    assert censurar_pii("meu cpf e 529.982.247-25") == "meu cpf e [CPF]"
    assert censurar_pii("cpf 52998224725 ok") == "cpf [CPF] ok"


def test_sequencia_de_11_digitos_que_nao_e_cpf_cai_como_telefone():
    """Decisao do Joao em 03/09/2026: privacidade vence sinal.

    "12345678901" tem digito verificador de CPF invalido, entao nao e CPF --
    mas e indistinguivel de um celular com DDD digitado corrido. Mascarar
    apaga numero de protocolo do texto que alimenta os sinais; nao mascarar
    deixa passar telefone de cliente. A escolha foi mascarar.
    """
    assert censurar_pii("protocolo 12345678901") == "protocolo [TELEFONE]"
    assert censurar_pii("meu fone 11987654321") == "meu fone [TELEFONE]"


def test_mascara_email():
    assert censurar_pii("manda pra joao@exemplo.com") == "manda pra [EMAIL]"


def test_mascara_telefone_com_ddd():
    assert censurar_pii("liga (11) 98765-4321") == "liga [TELEFONE]"
    assert censurar_pii("meu numero e +55 11 98765-4321") == "meu numero e [TELEFONE]"


def test_mascara_cartao_com_luhn_valido():
    # 4539578763621486 passa no Luhn.
    assert censurar_pii("cartao 4539578763621486") == "cartao [CARTAO]"


def test_nao_mascara_numero_longo_que_falha_no_luhn():
    assert censurar_pii("pedido 4539578763621487") == "pedido 4539578763621487"


def test_mascara_endereco_com_tipo_de_logradouro_e_numero():
    assert censurar_pii("moro na Rua das Flores 123") == "moro na [ENDERECO]"
    assert censurar_pii("Av Paulista 1000 hoje") == "[ENDERECO] hoje"


def test_texto_sem_pii_fica_intacto():
    texto = "o atendimento foi pessimo e demorou tres horas"
    assert censurar_pii(texto) == texto


def test_mistura_de_tipos_na_mesma_mensagem():
    resultado = censurar_pii("cpf 529.982.247-25 e email joao@exemplo.com")
    assert resultado == "cpf [CPF] e email [EMAIL]"
