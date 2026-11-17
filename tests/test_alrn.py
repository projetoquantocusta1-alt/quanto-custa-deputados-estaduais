import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from coletor import alrn  # noqa: E402


def test_valor_rs():
    assert alrn.valor_rs("1600") == 1600.0
    assert alrn.valor_rs("1.234,56") == 1234.56
    assert alrn.valor_rs(1500.5) == 1500.5
    assert alrn.valor_rs(None) == 0.0
    assert alrn.valor_rs("") == 0.0
    assert alrn.valor_rs("R$ 2.000,00") == 2000.0


def test_nota_cnpj_fica_inteiro():
    d = {"cnpj": "04.958.139/0001-01", "cpf": None, "fornecedor": "PORTUGAL CENTER",
         "titulo": "LOCACAO", "numero": "NF1", "valor": "1600",
         "deputado": {"id": 100, "nome": "Hermano Morais"}, "nome_categoria": "Locação"}
    n = alrn.nota_despesa(d, "2026-06")
    assert n["doc"] == "04958139000101" and n["tipo"] == "PJ"
    assert n["valor"] == 1600.0 and n["deputado"] == "Hermano Morais"
    assert n["categoria"] == "Locação"


def test_nota_cpf_sai_mascarado():
    # CPF nunca é guardado inteiro, nem no documento nem no texto do fornecedor
    d = {"cnpj": None, "cpf": "123.456.789-09", "fornecedor": "JOAO (CPF 123.456.789-09)",
         "titulo": "Serviço de 123.456.789-09", "numero": "NF2", "valor": "300",
         "deputado": {"id": 110, "nome": "Galeno Torquato"}, "nome_categoria": "Serviços"}
    n = alrn.nota_despesa(d, "2026-06")
    assert n["doc"] == "***.456.789-**" and n["tipo"] == "PF"
    assert "123.456.789" not in n["credor"]
    assert "123.456.789" not in n["descricao"]


def test_categoria_vazia():
    assert alrn.categoria(None) == "Outras despesas"
    assert alrn.categoria("  ") == "Outras despesas"
