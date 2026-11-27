"""Assembleia Legislativa de Minas Gerais (ALMG): verba indenizatória nota a nota e cadastro dos deputados.

A API de dados abertos da ALMG (dadosabertos.almg.gov.br) NÃO traz a verba dos deputados; ela fica no portal
institucional (www.almg.gov.br), que responde aos computadores do GitHub.

Fontes:
  - lista da legislatura: /transparencia/prestacao-de-contas/deputados/verba-indenizatoria/?leg=20
        traz um link "detalhe.html?id=<codigo>" por deputado, com o nome ("Dep. Fulano").
  - detalhe por deputado/ano: .../verba-indenizatoria/detalhe.html?id=<codigo>&ano=AAAA
        tabela nota a nota: Emitente | CNPJ/CPF | Data | Número | Valor | Reembolsável.
Salário: a ALMG não publica a folha nominal; o subsídio é o teto constitucional (75% do deputado federal).
CPF de pessoa física sai sempre mascarado; nunca é guardado inteiro.
"""
import html
import re

import config
from coletor import http
from coletor.alece import documento          # documento(): mascara CPF e devolve (doc, tipo)
from coletor.privacidade import mascarar_cpf_no_texto


def _txt(s: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def valor_rs(s: str) -> float:
    s = _txt(s).replace("R$", "").replace("\xa0", "").replace(".", "").replace(",", ".").strip()
    try:
        return float(s)
    except ValueError:
        return 0.0


# ------------------------------------------------------------------ lista de deputados
def baixar_lista(leg: int | None = None) -> str:
    return http.get(config.ALMG["lista"].format(leg=leg or config.ALMG["legislatura"]), timeout=90).text


def ler_deputados(texto: str) -> list[dict]:
    """[{codigo, nome}] a partir dos links 'detalhe.html?id=<codigo>'>'Dep. Nome'. Cada código aparece uma vez."""
    out, vistos = [], set()
    for cod, bruto in re.findall(r'detalhe\.html\?id=(\d+)[^>]*>\s*([^<]{3,80})', texto):
        nome = re.sub(r"^Dep\.\s*", "", _txt(bruto)).strip()
        if not nome or cod in vistos:
            continue
        vistos.add(cod)
        out.append({"codigo": cod, "nome": nome})
    return out


# ------------------------------------------------------------------ detalhe (verba nota a nota)
_TAB = re.compile(r"<table.*?</table>", re.S)
_TR = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S)
_TD = re.compile(r"<td[^>]*>(.*?)</td>", re.S)


def baixar_detalhe(codigo: str, periodo: str) -> str:
    """periodo no formato MMAAAA (ex.: '102023' = outubro de 2023), como o seletor do portal."""
    return http.get(config.ALMG["detalhe"].format(id=codigo, periodo=periodo), timeout=90).text


def ler_detalhe(texto: str) -> list[dict]:
    """Notas de um deputado num ano: [{data(AAAA-MM-DD), mes, ano, nota, doc, tipo, fornecedor, valor}].
    Valor = o reembolsável (o que a verba de fato pagou); se faltar, usa o valor da nota."""
    itens = []
    for tab in _TAB.findall(texto):
        if "Emitente" not in tab or "CNPJ" not in tab:
            continue
        for tr in _TR.findall(tab):
            tds = [_txt(x) for x in _TD.findall(tr)]
            if len(tds) < 5:
                continue
            emitente, doc_bruto, data, numero = tds[0], tds[1], tds[2], tds[3]
            m = re.match(r"(\d{2})/(\d{2})/(\d{4})", data)
            if not m:
                continue
            d, mo, y = m.groups()
            valor = valor_rs(tds[5]) if len(tds) > 5 else 0.0
            if not valor:
                valor = valor_rs(tds[4])
            doc, tipo = documento(doc_bruto)
            itens.append({"data": f"{y}-{mo}-{d}", "mes": int(mo), "ano": int(y),
                          "nota": mascarar_cpf_no_texto(_txt(numero)),
                          "doc": doc, "tipo": tipo,
                          "fornecedor": mascarar_cpf_no_texto(_txt(emitente)),
                          "valor": round(valor, 2)})
    return itens
