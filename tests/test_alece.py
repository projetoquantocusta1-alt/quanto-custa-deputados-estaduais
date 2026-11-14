"""Testes dos leitores da Alece com dados de exemplo (CPFs e nomes fictícios)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from coletor import alece  # noqa: E402

VDP = """﻿;;;
DEPUTADO;PERIODO;EMPENHO;DESCRICAO;CNPJ;CREDOR;VALOR
DEP FULANO DE TAL;06/2026;2026NE000001;REFERE-SE AO CONTRATO DE CARTOES PARA ABASTECIMENTO DE COMBUSTIVEIS;03506307000157;TICKET SOLUCOES HDFGT S/A;2.855,70
DEP FULANO DE TAL;06/2026;2026NE000002;REEMBOLSO DE DESPESAS INDENIZATORIAS LOCOMOCAO;123.456.789-09;FULANO DE TAL SILVA;1.000,00
DEP AP. CICLANO;06/2026;2026NE000003;ANULACAO PARCIAL DA NE 2026NE000009 DIVULGACAO DAS ATIVIDADES;11222333000181;RADIO EXEMPLO LTDA;-250,00
FOLHA DE PAGAMENTO 0015 - PROVENTOS DE APOSENTADORIA PARLAMENTAR REF AO MES DE MARCO;03/2021;000000001;X;11222333000181;ALGUEM;4.349.606,80
"""


def test_ler_vdp_separa_linhas_estranhas_e_mascara_cpf():
    ok, rec = alece.ler_vdp(VDP)
    assert len(ok) == 3 and len(rec) == 1
    assert ok[0]["deputado"] == "FULANO DE TAL" and ok[0]["valor"] == 2855.70 and ok[0]["categoria"] == "Combustível"
    assert ok[1]["doc"] == "***.456.789-**" and ok[1]["tipo"] == "PF"
    assert ok[2]["valor"] == -250.0 and ok[2]["categoria"] == "Divulgação do mandato"
    assert rec[0]["valor"] == 4349606.80


def test_chave_ignora_titulos_e_pontuacao():
    assert alece.chave("DEP AP. LUIZ HENRIQUE") == alece.chave("Ap Luiz Henrique") == "LUIZ HENRIQUE"


def test_documento_cnpj_valido_e_cpf_com_zeros():
    assert alece.documento("03506307000157") == ("03506307000157", "PJ")
    assert alece.documento("00012345678909") == ("***.456.789-**", "PF")


FOLHA = """MATRÍCULA;NOME;SITUAÇÃO;CATEGORIA;CARGO/FUNÇÃO;"AREA DE ATUAÇÃO";"CARGO COMISSIONADO";"NÍVEL DO CARGO COMISSIONADO";"REMUNERAÇÃO BRUTA";"DESCONTOS LEGAIS";"ABATIMENTO EM FUNÇÃO DO ""TETO"" CONSTITUCIONAL";"13º SAL / ADTO 13º SAL";"DESCONTOS ADTO 13º SAL";"REMUNERAÇÃO LÍQUIDA"
000001;"FULANO DE TAL SILVA";"EM EXERCICIO";DEPUTADOS;DEPUTADO;"NAO SE APLICA";"NAO SE APLICA";"NAO SE APLICA";39.993,14;9.371,21;0,00;0,00;0,00;30.621,93
000002;"BELTRANA SOUZA";"EM EXERCICIO";"SERVIDORES ATIVOS - FUNÇÃO DE NATUREZA COMISSIONADA - ASSESSOR PARLAMENTAR";ASSESSOR;X;Y;Z;5.000,00;500,00;0,00;0,00;0,00;4.500,00
"""


def test_ler_folha_deputados_nominais_e_totais():
    f = alece.ler_folha(FOLHA)
    assert f["deputados"] == [{"nome": "FULANO DE TAL SILVA", "situacao": "EM EXERCICIO", "cargo": "DEPUTADO",
                               "bruta": 39993.14, "teto": 0.0, "decimo": 0.0, "liquida": 30621.93}]
    assert f["categorias"]["DEPUTADOS"] == {"n": 1, "bruta": 39993.14}
    assert sum(c["n"] for c in f["categorias"].values()) == 2


def test_decodificar_cp1252():
    assert alece.decodificar("REMUNERAÇÃO".encode("cp1252")) == "REMUNERAÇÃO"


def test_casar_folha_por_palavras():
    assert alece.casar_folha("DEP SALMITO", ["JOAO SALMITO FILHO", "OUTRO NOME"], {}) == "JOAO SALMITO FILHO"
    assert alece.casar_folha("DEP SILVA", ["JOAO SILVA", "MARIA SILVA"], {}) is None


LISTA = """<div class="deputado_card " style="max-width: 300px">
<img width="100%" src="https://www.al.ce.gov.br/image/1" alt="Foto">
<p class="deputado_card--nome s-font-1"><a href="https://www.al.ce.gov.br/deputados/fulano-de-tal">  Fulano de Tal </a></p>
<p class="deputado_card--partido s-font-1"> XYZ </p>
</div>"""


def test_ler_lista():
    assert alece.ler_lista(LISTA) == [{"slug": "fulano-de-tal", "nome": "Fulano de Tal", "partido": "XYZ",
                                       "foto": "https://www.al.ce.gov.br/image/1"}]
