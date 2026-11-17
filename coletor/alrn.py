"""Assembleia Legislativa do Rio Grande do Norte (ALRN): cota parlamentar pela API pública do portal.

Fonte: o portal de transparência (transparencia.al.rn.leg.br) é um aplicativo que lê a API
api-transparencia.al.rn.leg.br. A API pede um "token" de acesso que o PRÓPRIO portal embute no código
entregue a qualquer visitante — não é segredo: todo navegador que abre a página o usa sem saber. Para não
republicar esse token (ele carrega, embutidos, um usuário e uma senha) no nosso repositório, o robô o lê do
código público do portal a cada execução.

A ALRN publica a cota desde 2009, por mês, com fornecedor, CNPJ/CPF, categoria e valor. Usamos de 2023 em
diante, como nos outros estados, para comparar no mesmo período. Não há folha de pagamento nominal (só a cota).
CPF de pessoa física é mascarado antes de ser guardado.
"""
import re

import requests

import config
from coletor import http
from coletor.alece import documento

_MES = {"janeiro": 1, "fevereiro": 2, "março": 3, "marco": 3, "abril": 4, "maio": 5, "junho": 6,
        "julho": 7, "agosto": 8, "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12}

_token = None


# ------------------------------------------------------------------ token (lido do código público do portal)
def _buscar_token() -> str:
    """Procura tokenBearer:"..." no código do portal (index + chunks do aplicativo Angular)."""
    base = config.ALRN["portal"]
    try:
        html = http.get(base, timeout=60).text
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"portal da ALRN indisponível ({e})") from e
    arquivos = re.findall(r'(?:chunk|main|polyfills)-[A-Z0-9]+\.js', html)
    # o main costuma importar outros chunks; o token está no chunk do ambiente (environment)
    vistos, fila = set(), sorted(arquivos, key=lambda n: (not n.startswith("main"), n))
    while fila:
        nome = fila.pop(0)
        if nome in vistos:
            continue
        vistos.add(nome)
        if len(vistos) > 45:
            break
        try:
            js = http.get(base + nome, timeout=60).text
        except Exception:  # noqa: BLE001
            continue
        m = re.search(r'tokenBearer:"([^"]+)"', js)
        if m:
            return m.group(1)
        if nome.startswith("main"):
            fila += [x for x in re.findall(r'chunk-[A-Z0-9]+\.js', js) if x not in vistos]
    raise RuntimeError("não encontrei o token no código do portal da ALRN")


def token() -> str:
    global _token
    if _token is None:
        _token = _buscar_token()
    return _token


def _cabecalhos() -> dict:
    return {"Authorization": f"Bearer {token()}", "Accept": "application/json, text/plain, */*",
            "Origin": config.ALRN["portal"].rstrip("/"), "Referer": config.ALRN["portal"]}


def _api(caminho: str, params=None):
    url = config.ALRN["api"] + caminho
    global _token
    for tentativa in (1, 2):
        try:
            return http.get(url, params=params, timeout=90, headers=_cabecalhos()).json()
        except requests.HTTPError as e:
            # 401: o token mudou (novo deploy do portal); pega de novo e tenta mais uma vez
            if tentativa == 1 and e.response is not None and e.response.status_code == 401:
                _token = None
                continue
            raise


# ------------------------------------------------------------------ dados
def anos() -> list[int]:
    d = _api("/verbas/meses/anos")
    return sorted(int(a) for a in (d.get("anos") or []))


def meses_do_ano(ano: int) -> list[tuple[int, int]]:
    """[(número do mês, mes_id), ...] apenas dos meses que já têm dados no ano."""
    d = _api(f"/verbas/meses/{ano}")
    out = []
    for m in d.get("meses") or []:
        n = _MES.get((m.get("mes") or "").strip().lower())
        if n and m.get("mes_id") is not None:
            out.append((n, int(m["mes_id"])))
    return sorted(out)


def despesas_do_mes(mes_id: int) -> list[dict]:
    d = _api("/verbas/despesas/", params={"mes_id": mes_id})
    return d.get("data") or []


def valor_rs(v) -> float:
    if v is None:
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace("R$", "").strip()
    if "," in s:                      # formato brasileiro: 1.234,56
        s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return 0.0


def categoria(nome_oficial) -> str:
    s = re.sub(r"\s+", " ", str(nome_oficial or "")).strip()
    return s[:70] if s else "Outras despesas"


def nota_despesa(d: dict, periodo: str) -> dict:
    """Uma despesa da API no mesmo formato das notas do Ceará/Bahia (CPF mascarado, CNPJ inteiro)."""
    cnpj = (d.get("cnpj") or "").strip()
    cpf = (d.get("cpf") or "").strip()
    if cnpj:
        doc, tipo = documento(cnpj)
    elif cpf:
        doc, tipo = documento(cpf)       # CPF sai mascarado aqui; nunca é guardado inteiro
    else:
        doc, tipo = "", "?"
    dep = (d.get("deputado") or {}).get("nome") or ""
    return {"deputado": re.sub(r"\s+", " ", dep).strip() or "—", "periodo": periodo,
            "empenho": str(d.get("numero") or d.get("id") or ""),
            "descricao": _mascarar(d.get("titulo") or ""),
            "doc": doc, "tipo": tipo, "credor": _mascarar((d.get("fornecedor") or "").strip()),
            "valor": round(valor_rs(d.get("valor")), 2), "categoria": categoria(d.get("nome_categoria"))}


def _mascarar(s: str) -> str:
    from coletor.privacidade import mascarar_cpf_no_texto
    return mascarar_cpf_no_texto(re.sub(r"\s+", " ", s).strip())
