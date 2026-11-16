import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from coletor import alba  # noqa: E402

LISTA = """
<tr class="table-itens cinza">
  <div>
  <td width="150" style="text-align: center;">204167</td>
  <td style="text-align: center;">20235148</td>
  <td style="text-align: center;">01/2023</td>
  <td width="150">Maria del Carmen</td>
  <td>Aquisição ou locação de software; serviços postais  e de segurança; assinaturas de publicações; TV a cabo ou similar; acesso à Internet; e locação de móveis e equipamentos. Telefones.</td>
  <td width="150">R$ 1.180,50</td>
  <td width="150"><a href="/transparencia/verbas-idenizatorias/80856/"><button><span>DETALHES</span></button></a></td>
  </div>
</tr>
<tr class="table-itens cinza"><td>204136</td><td>57</td><td>01/2023</td><td>Alan Sanches</td><td>Consultorias</td>
  <td>R$ 4.750,00</td><td><a href="/transparencia/verbas-idenizatorias/80857/">DETALHES</a></td></tr>
<a class="paginate-button-next" href="?ano=2023&amp;inicio=1&amp;mes=1&amp;quantidade=20&amp;page=12&amp;size=20" title="Última Página">Último</a>
"""

DETALHE = """
<div class="titulo-presidente">
    DEPUTADO (A):
    <span>CLÁUDIA OLIVEIRA (PT do B)</span>
</div>
<div class="titulo-bloco-lista no-margin">DESPESAS REFERÊNCIA:
    <span>216583 - 11/2026</span></div>
<table><thead><tr><th>CATEGORIA</th><th>Nº NOTA/RECIBO</th><th>CPF/CNPJ</th><th>NOME DO FORNECEDOR</th><th>VALOR</th><th>GLOSA</th><th>ANEXO NF</th></tr></thead>
<tbody>
<tr class="table-itens cinza">
    <td><span>Assessorias</span></td><td width="100"><span>7</span></td>
    <td width="200"><span>65.073.990/0001-33</span></td><td><span>LB CONTABILIDADE LTDA</span></td>
    <td width="150"><span>R$ 11.100,00</span></td><td width="150">R$ 100,00</td><td><a href="/fserver/:anexo:NFE1.pdf"><span>7</span></a></td>
</tr>
<tr class="table-itens cinza">
    <td><span>Assessorias</span></td><td><span>8</span></td>
    <td><span>123.456.789-09</span></td><td><span>FULANO DE TAL</span></td>
    <td><span>R$ 500,00</span></td><td>R$ 0,00</td><td></td>
</tr>
</tbody></table>
"""

DEPUTADOS = """
<div class="col-md-3">
  <li class="list-item"><a href="/deputados/deputado-legislatura-atual/910629"><div class="cnt-img-deputado">
    <img src="/fserver/:imagensAlbanet:fotos:AdolfoMenezes.jpg/static:images:shared:avatar.jpg" class="deputado-img" alt=""/></div></a></li>
  <div class="campo-dados"><div class="deputado-nome"><a href="/deputados/deputado-legislatura-atual/910629">
    <span>Adolfo Menezes</span></a></div><div class="partido-nome">PSD</div></div>
  <div style="border: 1px solid red;"></div>
</div>
"""


def test_lista_mes_le_notas_e_ultima_pagina():
    linhas, ult = alba.ler_lista_mes(LISTA)
    assert ult == 12
    assert [x["id"] for x in linhas] == ["80856", "80857"]
    assert linhas[0]["valor"] == 1180.5 and linhas[0]["competencia"] == "2023-01"
    assert linhas[0]["deputado"] == "Maria del Carmen"


def test_detalhe_mascara_cpf_e_le_glosa():
    d = alba.ler_detalhe(DETALHE)
    assert d["deputado"].startswith("CLÁUDIA OLIVEIRA")
    pj, pf = d["itens"]
    assert pj["doc"] == "65073990000133" and pj["tipo"] == "PJ" and pj["glosa"] == 100.0
    assert pf["doc"] == "***.456.789-**" and pf["tipo"] == "PF"
    assert "123.456.789-09" not in str(d)


def test_deputados_codigo_partido_foto():
    (d,) = alba.ler_deputados(DEPUTADOS)
    assert d["codigo"] == "910629" and d["nome"] == "Adolfo Menezes" and d["partido"] == "PSD"
    assert d["foto"].startswith("https://www.al.ba.gov.br/fserver/")


def test_categorias_curtas():
    assert alba.categoria("Aquisição ou locação de software; serviços postais  e de segurança; Telefones.") == "Software, internet, telefone e correios"
    assert alba.categoria("Divulgação da atividade parlamentar em redes sociais") == "Divulgação em redes sociais"
    assert alba.categoria("Divulgação da  atividade parlamentar") == "Divulgação do mandato"
    assert alba.categoria("Consultorias, assessorias, pesquisas  e trabalhos técnicos") == "Consultoria e assessoria"
    assert alba.categoria("Assessorias") == "Assessorias"
