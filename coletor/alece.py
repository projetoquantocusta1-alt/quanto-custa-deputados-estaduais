"""Assembleia Legislativa do Ceará (Alece): verba de desempenho parlamentar (VDP),
folha de pagamento nominal e cadastro dos deputados.

Fontes (Portal da Transparência da Alece, robots.txt permite):
  - VDP por mês:   /despesas/verba-desempenho-parlamentar/csv?mes=MM&ano=AAAA
        colunas DEPUTADO;PERIODO;EMPENHO;DESCRICAO;CNPJ;CREDOR;VALOR (valor negativo = anulação)
  - Folha por mês: /gestao-de-pessoas/pessoal/csv?mes=MM&ano=AAAA
        MATRÍCULA;NOME;SITUAÇÃO;CATEGORIA;CARGO/FUNÇÃO;...;REMUNERAÇÃO BRUTA;...;REMUNERAÇÃO LÍQUIDA
  - Deputados:     www.al.ce.gov.br/deputados (nome parlamentar, partido, foto) e a página de cada um
        (nome completo).
O mês tem de ir com dois dígitos: com "6" o portal devolve o arquivo vazio.
"""
import csv
import html
import io
import re
import unicodedata

import config
from coletor import http
from coletor.privacidade import mascarar_cpf_no_texto

TITULOS = {"DEP", "DEPUTADO", "DEPUTADA", "DR", "DRA", "AP", "DELEGADO", "DELEGADA", "SOLDADO", "PASTOR",
           "PROFESSOR", "PROFESSORA", "PROF", "CAPITAO", "SARGENTO", "CORONEL", "VEREADOR"}


# ------------------------------------------------------------------ texto
def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Z0-9 ]+", " ", s.upper()).strip()


def palavras(nome: str) -> list[str]:
    return [p for p in norm(nome).split() if p not in TITULOS and len(p) > 1]


def chave(nome: str) -> str:
    """Chave de comparação de nomes parlamentares ("DEP AP. LUIZ HENRIQUE" == "Ap Luiz Henrique")."""
    return " ".join(palavras(nome))


def valor_br(s: str) -> float:
    s = (s or "").strip().replace(".", "").replace(",", ".")
    return float(s) if s not in ("", "-") else 0.0


def decodificar(conteudo: bytes) -> str:
    for enc in ("utf-8-sig", "cp1252"):
        try:
            return conteudo.decode(enc)
        except UnicodeDecodeError:
            continue
    return conteudo.decode("latin-1")


# ------------------------------------------------------------------ documento do credor
def _cnpj_valido(c: str) -> bool:
    if len(c) != 14 or len(set(c)) == 1:
        return False
    def dv(base, pesos):
        s = sum(int(a) * b for a, b in zip(base, pesos)) % 11
        return "0" if s < 2 else str(11 - s)
    p1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    d1 = dv(c[:12], p1)
    return c[12] == d1 and c[13] == dv(c[:12] + d1, [6] + p1)


def documento(bruto: str) -> tuple[str, str]:
    """(documento publicável, tipo). CNPJ fica inteiro; CPF sai mascarado (***.456.789-**)."""
    b = (bruto or "").strip()
    dig = re.sub(r"\D", "", b)
    if b.startswith("***"):
        return b, "PF"                      # já veio mascarado
    if len(dig) == 14 and _cnpj_valido(dig):
        return dig, "PJ"
    if len(dig) == 11 or (len(dig) == 14 and dig.startswith("000")):
        d = dig[-11:]
        return f"***.{d[3:6]}.{d[6:9]}-**", "PF"
    return (dig or b), ("PJ" if len(dig) == 14 else "?")


def categoria(descricao: str) -> str:
    d = norm(descricao)
    for nome, padrao in config.CATEGORIAS_VDP:
        if re.search(padrao, d):
            return nome
    return "Outras despesas"


# ------------------------------------------------------------------ VDP
_DEPUTADO_OK = re.compile(r"^(?:DEP\.?\s+)?[A-ZÀ-Ú][A-ZÀ-Ú.' ]{1,40}$")


def ler_vdp(texto: str, deputados_conhecidos: set[str] | None = None) -> tuple[list[dict], list[dict]]:
    """Separa as linhas de deputados das linhas estranhas (outras folhas misturadas no arquivo).
    Linha de deputado: 1ª coluna curta, só com letras (ex.: "DEP AGENOR NETO"), 7 colunas.
    Se deputados_conhecidos for dado, a chave do nome também tem de estar lá."""
    ok, recusadas = [], []
    for ln in csv.reader(io.StringIO(texto), delimiter=";"):
        if len(ln) != 7 or ln[0].strip().upper() == "DEPUTADO":
            continue
        dep, periodo, empenho, desc, doc, credor, valor = (x.strip() for x in ln)
        try:
            v = valor_br(valor)
        except ValueError:
            recusadas.append({"motivo": "valor ilegível", "linha": ln[:3]})
            continue
        nome = re.sub(r"^DEP\.?\s+", "", dep.upper()).strip()
        if not _DEPUTADO_OK.match(dep.upper()) or (deputados_conhecidos and chave(nome) not in deputados_conhecidos):
            recusadas.append({"deputado_coluna": mascarar_cpf_no_texto(dep[:120]), "valor": v})
            continue
        d, tipo = documento(doc)
        ok.append({
            "deputado": nome, "periodo": periodo, "empenho": empenho,
            "descricao": mascarar_cpf_no_texto(re.sub(r"\s+", " ", desc)),
            "doc": d, "tipo": tipo, "credor": mascarar_cpf_no_texto(re.sub(r"\s+", " ", credor)),
            "valor": round(v, 2), "categoria": categoria(desc),
        })
    return ok, recusadas


def baixar_vdp(ano: int, mes: int) -> str:
    r = http.get(config.ALECE["vdp_csv"].format(ano=ano, mes=mes), timeout=120)
    return decodificar(r.content)


# ------------------------------------------------------------------ folha
def ler_folha(texto: str) -> dict:
    """Deputados nominalmente; demais categorias só em totais (quantidade e remuneração bruta)."""
    linhas = list(csv.reader(io.StringIO(texto), delimiter=";"))
    cab = next((i for i, x in enumerate(linhas) if len(x) > 8 and "NOME" in norm(";".join(x))), None)
    if cab is None:
        return {"deputados": [], "categorias": {}}
    h = [norm(c) for c in linhas[cab]]
    def col(padrao):
        """Primeira coluna cujo cabeçalho (sem acentos) casa com o padrão; tolera acentos estragados."""
        for i, c in enumerate(h):
            if re.search(padrao, c):
                return i
        return None
    i_nome, i_sit, i_cat, i_cargo = col(r"^NOME$"), col(r"^SITUA"), col(r"^CATEGORIA"), col(r"^CARGO F")
    i_bruta, i_liq, i_teto, i_13 = col(r"BRUTA"), col(r"QUIDA$"), col(r"^ABATIMENTO"), col(r"^13")
    deps, cats = [], {}
    for x in linhas[cab + 1:]:
        if len(x) != len(h):
            continue
        cat = x[i_cat].strip()
        bruta = valor_br(x[i_bruta]) if i_bruta is not None else 0.0
        teto = valor_br(x[i_teto]) if i_teto is not None else 0.0
        dec = valor_br(x[i_13]) if i_13 is not None else 0.0
        c = cats.setdefault(cat, {"n": 0, "bruta": 0.0})
        c["n"] += 1
        c["bruta"] = round(c["bruta"] + bruta - teto + dec, 2)
        if norm(cat) == "DEPUTADOS":
            deps.append({"nome": x[i_nome].strip(), "situacao": x[i_sit].strip(), "cargo": x[i_cargo].strip(),
                         "bruta": round(bruta, 2), "teto": round(teto, 2), "decimo": round(dec, 2),
                         "liquida": round(valor_br(x[i_liq]), 2) if i_liq is not None else None})
    return {"deputados": deps, "categorias": cats}


def baixar_folha(ano: int, mes: int) -> str:
    r = http.get(config.ALECE["folha_csv"].format(ano=ano, mes=mes), timeout=180)
    return decodificar(r.content)


# ------------------------------------------------------------------ cadastro
_CARTAO = re.compile(r'<div\s+class="deputado_card[^"]*"[^>]*>(.*?)</div>', re.S)


def ler_lista(texto: str) -> list[dict]:
    """Cartões da página /deputados: slug, nome parlamentar, partido, foto, licenciado (vermelho)."""
    out = []
    for bloco in _CARTAO.findall(texto):
        m = re.search(r'deputados/([a-z0-9-]+)"[^>]*>\s*([^<]+?)\s*</a>', bloco)
        if not m or m.group(1) == "mesa-diretora":
            continue
        foto = re.search(r'src="([^"]+)"', bloco)
        part = re.search(r'deputado_card--partido[^>]*>\s*([^<]*?)\s*</p>', bloco)
        out.append({"slug": m.group(1), "nome": html.unescape(m.group(2)).strip(),
                    "partido": html.unescape(part.group(1)).strip() if part else "",
                    "foto": foto.group(1) if foto else ""})
    vistos, unicos = set(), []
    for d in out:
        if d["slug"] not in vistos:
            vistos.add(d["slug"])
            unicos.append(d)
    return unicos


def ler_perfil(texto: str) -> dict:
    def campo(rotulo):
        m = re.search(r">\s*" + rotulo + r"\s*</span>\s*<span[^>]*>\s*([^<]*?)\s*</span>", texto)
        return html.unescape(m.group(1)).strip() if m else ""
    return {"nome_completo": campo("Nome Completo"), "nome": campo("Nome Parlamentar"), "partido": campo("Partido")}


def baixar_lista() -> str:
    return http.get(config.ALECE["lista_deputados"], timeout=90).text


def baixar_perfil(slug: str) -> str:
    return http.get(config.ALECE["perfil"].format(slug=slug), timeout=90).text


# ------------------------------------------------------------------ casar nomes
def casar_folha(nome_vdp: str, nomes_folha: list[str], cadastro: dict[str, dict]) -> str | None:
    """Nome na folha (nome completo) de quem aparece na VDP (nome parlamentar).
    1) pelo cadastro do site (nome parlamentar -> nome completo);
    2) todas as palavras do nome parlamentar dentro de um único nome completo da folha."""
    k = chave(nome_vdp)
    cad = cadastro.get(k)
    if cad and cad.get("nome_completo"):
        alvo = norm(cad["nome_completo"])
        for n in nomes_folha:
            if norm(n) == alvo:
                return n
    pals = set(palavras(nome_vdp))
    if not pals:
        return None
    cand = [n for n in nomes_folha if pals <= set(palavras(n))]
    return cand[0] if len(cand) == 1 else None
