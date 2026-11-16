"""Assembleia Legislativa da Bahia (ALBA): verba indenizatória e cadastro dos deputados.

Fontes (site da ALBA; não há robots.txt, ou seja, nenhuma restrição):
  - lista mensal: /transparencia/verbas-idenizatorias?ano=AAAA&mes=M&page=P&size=20
        20 notas por página; a PRIMEIRA página é a 0. Colunas: processo, nº da nota, competência,
        deputado, categoria, valor e o link para o detalhe.
  - detalhe:      /transparencia/verbas-idenizatorias/<id>/
        categoria, nº da nota, CPF/CNPJ, fornecedor, valor e glosa (parte recusada pela Assembleia).
  - deputados:    /deputados/legislatura-atual (todos desta legislatura, com suplentes) e
                  /deputados/deputados-estaduais (em exercício): código, nome, partido e foto.
Salário: a ALBA não publica a folha nominal, só o subsídio fixado em lei.
Dados pessoais da página do deputado (filiação, cônjuge, filhos) NÃO são lidos.
"""
import html
import re

import config
from coletor import http
from coletor.alece import documento, norm
from coletor.privacidade import mascarar_cpf_no_texto


def _txt(s: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", s or ""))).strip()


def valor_rs(s: str) -> float:
    s = _txt(s).replace("R$", "").replace(".", "").replace(",", ".").strip()
    return float(s) if s and s not in ("-",) else 0.0


def categoria(nome_oficial: str) -> str:
    d = norm(nome_oficial)
    for curto, padrao in config.CATEGORIAS_ALBA:
        if re.search(padrao, d):
            return curto
    return _txt(nome_oficial)[:60] or "Outras despesas"


# ------------------------------------------------------------------ lista mensal
_LINHA = re.compile(r'<tr class="table-itens[^"]*">(.*?)</tr>', re.S)
_TD = re.compile(r"<td[^>]*>(.*?)</td>", re.S)


def ler_lista_mes(texto: str) -> tuple[list[dict], int]:
    """(notas da página, número da última página). A última página vem do link "Última Página" (0 se não houver)."""
    linhas = []
    for bloco in _LINHA.findall(texto):
        m = re.search(r"verbas-idenizatorias/(\d+)/", bloco)
        tds = [_txt(t) for t in _TD.findall(bloco)]
        if not m or len(tds) < 6:
            continue
        processo, nota, comp, dep, cat, valor = tds[:6]
        mm = re.match(r"(\d{1,2})/(\d{4})", comp)
        linhas.append({"id": m.group(1), "processo": processo, "nota": mascarar_cpf_no_texto(nota),
                       "competencia": f"{mm.group(2)}-{int(mm.group(1)):02d}" if mm else comp,
                       "deputado": dep, "categoria_oficial": cat, "valor": round(valor_rs(valor), 2)})
    ult = re.search(r'page=(\d+)&(?:amp;)?size=\d+"\s+title="[ÚU]ltima', texto)
    return linhas, int(ult.group(1)) if ult else 0


def baixar_lista_mes(ano: int, mes: int, pagina: int) -> str:
    return http.get(config.ALBA["lista_mes"].format(ano=ano, mes=mes, pagina=pagina), timeout=90).text


def lista_do_mes(ano: int, mes: int) -> list[dict]:
    """Todas as páginas do mês. Se uma página falhar, levanta o erro (o mês fica com a lista antiga)."""
    linhas, ult = ler_lista_mes(baixar_lista_mes(ano, mes, 0))
    for p in range(1, ult + 1):
        mais, _ = ler_lista_mes(baixar_lista_mes(ano, mes, p))
        linhas += mais
    vistos, unicas = set(), []
    for x in linhas:                      # a mesma nota não pode entrar duas vezes (páginas que mudam durante a leitura)
        if x["id"] not in vistos:
            vistos.add(x["id"])
            unicas.append(x)
    return unicas


# ------------------------------------------------------------------ detalhe
def ler_detalhe(texto: str) -> dict:
    dep = re.search(r"DEPUTADO \(A\):\s*<span>(.*?)</span>", texto, re.S)
    ref = re.search(r"DESPESAS REFER[ÊE]NCIA:\s*<span>(.*?)</span>", texto, re.S)
    corpo = texto[texto.find("NOME DO FORNECEDOR"):] if "NOME DO FORNECEDOR" in texto else ""
    itens = []
    for bloco in _LINHA.findall(corpo.split("</table>")[0]):
        tds = [_txt(t) for t in _TD.findall(bloco)]
        if len(tds) < 6:
            continue
        cat, nota, doc_bruto, forn, valor, glosa = tds[:6]
        doc, tipo = documento(doc_bruto)          # CPF sai mascarado aqui; nunca é guardado inteiro
        itens.append({"categoria_oficial": cat, "nota": mascarar_cpf_no_texto(nota), "doc": doc, "tipo": tipo,
                      "fornecedor": mascarar_cpf_no_texto(forn), "valor": round(valor_rs(valor), 2),
                      "glosa": round(valor_rs(glosa), 2)})
    return {"deputado": _txt(dep.group(1)) if dep else "", "referencia": _txt(ref.group(1)) if ref else "", "itens": itens}


def baixar_detalhe(i: str) -> str:
    return http.get(config.ALBA["detalhe"].format(id=i), timeout=60).text


# ------------------------------------------------------------------ deputados
_CARTAO = re.compile(r'<div class="col-md-3">(.*?)<div style="border', re.S)


def ler_deputados(texto: str) -> list[dict]:
    """Cartões das páginas de deputados: código, nome parlamentar, partido e foto (endereço completo)."""
    out, vistos = [], set()
    for bloco in _CARTAO.findall(texto):
        m = re.search(r'deputado-(?:estadual|legislatura-atual)/(\d+)"[^>]*>\s*<span>([^<]+)</span>', bloco)
        if not m or m.group(1) in vistos:
            continue
        vistos.add(m.group(1))
        foto = re.search(r'<img src="([^"]+)"', bloco)
        part = re.search(r'class="partido-nome">\s*([^<]*?)\s*<', bloco)
        # "/fserver/:imagensAlbanet:fotos:Nome.jpg/static:images:shared:avatar.jpg": o servidor devolve a foto
        # ou, se ela faltar, a imagem reserva (avatar) indicada no fim do endereço
        url_foto = foto.group(1) if foto else ""
        if url_foto.startswith("/"):
            url_foto = config.ALBA["site"] + url_foto
        out.append({"codigo": m.group(1), "nome": html.unescape(m.group(2)).strip(),
                    "partido": html.unescape(part.group(1)).strip() if part else "", "foto": url_foto})
    return out


def baixar_legislatura() -> str:
    return http.get(config.ALBA["legislatura"], timeout=90).text


def baixar_em_exercicio() -> str:
    return http.get(config.ALBA["em_exercicio"], timeout=90).text
