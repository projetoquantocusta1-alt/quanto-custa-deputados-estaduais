"""Robô dos deputados estaduais (um estado por vez: Ceará / Alece, Bahia / ALBA).

Uso:
    python atualizar.py                 # baixa o que falta e monta o site, todos os estados
    python atualizar.py --uf ba         # só um estado
    python atualizar.py --so-montar     # só remonta o site com o que já está salvo
    python atualizar.py --minutos 60    # tempo máximo de coleta (somando os estados)

Saídas (pastas configuráveis por variáveis de ambiente SAIDA e BRUTOS), <uf> = ce, ba...:
    BRUTOS/ipca.json                     fatores do IPCA (comum a todos os estados)
    BRUTOS/<uf>/cadastro.json            nome parlamentar, nome completo, partido, foto (site da Assembleia)
    BRUTOS/ce/meses/AAAA-MM.json         Ceará: linhas da verba (VDP) e deputados da folha, por mês
    BRUTOS/ba/listas/AAAA-MM.json        Bahia: notas da lista mensal da verba
    BRUTOS/ba/detalhes/AAAA-MM.json      Bahia: detalhe de cada nota (CPF/CNPJ mascarado, fornecedor, glosa)
    SAIDA/estados.json                   estados publicados (para o seletor do site)
    SAIDA/<uf>/meta.json                 data, anos, IPCA, situação de cada mês, totais da Assembleia
    SAIDA/<uf>/AAAA/resumo.json          um registro por deputado no ano
    SAIDA/<uf>/AAAA/notas/<id>.json      notas da verba de cada deputado
    SAIDA/<uf>/AAAA/fornecedores.json    quem recebeu da verba no ano
"""
import argparse
import difflib
import json
import logging
import os
import re
import sys
import time
import traceback
from collections import defaultdict
from datetime import date, datetime, timezone
from pathlib import Path

import config
from coletor import alba, alece, http, ipca
from coletor.privacidade import limpar_json

RAIZ = Path(__file__).parent
SAIDA_RAIZ = Path(os.environ.get("SAIDA") or RAIZ / "docs" / "dados")
BRUTOS_RAIZ = Path(os.environ.get("BRUTOS") or RAIZ / "dados_brutos")
# pastas do Ceará (o coletor original); a Bahia usa BRUTOS_RAIZ / "ba" e SAIDA_RAIZ / "ba"
SAIDA = SAIDA_RAIZ / "ce"
BRUTOS = BRUTOS_RAIZ / "ce"
VERSAO = 1
log = logging.getLogger("qce")


def ler(p: Path, padrao=None):
    try:
        return json.loads(p.read_text("utf-8")) if p.exists() else padrao
    except json.JSONDecodeError:
        return padrao


def gravar(p: Path, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(limpar_json(obj), ensure_ascii=False, separators=(",", ":")), "utf-8")


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", alece.norm(s).lower()).strip("-")


def meses(ini: int, hoje: date):
    for a in range(ini, hoje.year + 1):
        for m in range(1, 13):
            if (a, m) <= (hoje.year, hoje.month):
                yield a, m


def idade_meses(a: int, m: int, hoje: date) -> int:
    return (hoje.year - a) * 12 + hoje.month - m


# ------------------------------------------------------------------ coleta
def atualizar_ipca():
    try:
        serie = ipca.baixar_ipca(config.ANO_INICIAL)
        gravar(BRUTOS_RAIZ / "ipca.json", ipca.fatores_por_ano(serie))
    except Exception as e:  # noqa: BLE001
        log.warning("IPCA indisponível (%s); mantém o anterior", e)


def atualizar_cadastro_ce():
    cad = ler(BRUTOS / "cadastro.json", {}) or {}
    try:
        lista = alece.ler_lista(alece.baixar_lista())
    except Exception as e:  # noqa: BLE001
        log.warning("lista de deputados indisponível (%s); mantém a anterior", e)
        return cad
    for d in lista:
        k = alece.chave(d["nome"])
        x = cad.get(k, {})
        x.update({k2: v for k2, v in d.items() if v})
        if not x.get("nome_completo"):
            try:
                p = alece.ler_perfil(alece.baixar_perfil(d["slug"]))
                x["nome_completo"] = p.get("nome_completo") or ""
                if p.get("partido"):
                    x["partido"] = p["partido"]
            except Exception as e:  # noqa: BLE001
                log.warning("perfil %s: %s", d["slug"], e)
        x["atual"] = True
        x["visto_em"] = date.today().isoformat()
        cad[k] = x
    atuais = {alece.chave(d["nome"]) for d in lista}
    for k, x in cad.items():
        if k not in atuais:
            x["atual"] = False
    gravar(BRUTOS / "cadastro.json", cad)
    try:   # fotos oficiais no próprio site (para a imagem de compartilhar)
        from coletor.fotos import baixar_fotos
        baixar_fotos([(x["slug"], x.get("foto")) for x in cad.values() if x.get("slug")], SAIDA / "fotos", BRUTOS / "fotos_sem.json")
    except Exception as e:  # noqa: BLE001
        log.warning("fotos: %s", e)
    log.info("cadastro: %d deputados no site da Alece (%d no total guardado)", len(lista), len(cad))
    return cad


def coletar_ce(hoje: date, limite_s: float, forcar: bool = False) -> int:
    t0, feitos = time.time(), 0
    for a, m in meses(config.ANO_INICIAL, hoje):
        if time.time() - t0 > limite_s:
            log.warning("tempo esgotado; o resto fica para a próxima execução")
            break
        arq = BRUTOS / "meses" / f"{a}-{m:02d}.json"
        velho = ler(arq)
        if velho and not forcar and not velho.get("vazio") and idade_meses(a, m, hoje) > config.MESES_REBAIXAR:
            continue
        try:
            vdp, recusadas = alece.ler_vdp(alece.baixar_vdp(a, m))
            folha = alece.ler_folha(alece.baixar_folha(a, m))
        except http.SiteForaDoAr as e:
            log.error("%s", e)
            break
        except Exception as e:  # noqa: BLE001
            log.warning("%d-%02d: falhou (%s)", a, m, e)
            continue
        vazio = not vdp and not folha["deputados"]
        if vazio and velho and not velho.get("vazio"):
            log.warning("%d-%02d: veio vazio agora, mas já tinha dados; mantém os antigos", a, m)
            continue
        gravar(arq, {"ano": a, "mes": m, "baixado_em": hoje.isoformat(), "vazio": vazio,
                     "vdp": vdp, "recusadas": recusadas, "folha": folha})
        feitos += 1
        log.info("%d-%02d: %d notas da verba (R$ %.2f), %d recusadas, %d deputados na folha",
                 a, m, len(vdp), sum(x["valor"] for x in vdp), len(recusadas), len(folha["deputados"]))
    return feitos


# ------------------------------------------------------------------ nomes
NAO_IDENTIFICADO = "nao-identificado"
_NAO_E_NOME = re.compile(r"\b(PLANO|SAUDE|FOLHA|PAGAMENTO|EMPENHO|ANULACAO|REFERENTE|CONTRATO)\b")


def _parecido(a: str, b: str, minimo: float) -> bool:
    return difflib.SequenceMatcher(None, a, b).ratio() >= minimo


def _melhor(alvo: str, opcoes, minimo: float):
    """Opção mais parecida com o alvo, se for bem parecida e sem empate próximo."""
    notas = sorted(((difflib.SequenceMatcher(None, alvo, o).ratio(), o) for o in opcoes), reverse=True)
    if notas and notas[0][0] >= minimo and (len(notas) == 1 or notas[0][0] - notas[1][0] >= 0.05):
        return notas[0][1]
    return None


def _palavras_contidas(pals: list[str], nome_folha: str) -> bool:
    """Cada palavra do nome parlamentar está no nome completo (aceita erro de digitação em palavras longas)."""
    alvo = alece.palavras(nome_folha)
    def bate(p, q):
        return (p == q or (len(p) >= 5 and _parecido(p, q, 0.8))
                or (len(p) >= 4 and len(q) >= 4 and p[:4] == q[:4]))   # apelido abreviado: Martinha/Marta, Keivia/Keivilanny
    return bool(pals) and all(any(bate(p, q) for q in alvo) for p in pals)


def resolver_nomes(meses_brutos: list[dict], cad: dict) -> tuple[dict, dict]:
    """Liga, de uma vez para todos os meses, os nomes da verba (nome parlamentar, às vezes digitado com erro)
    e os nomes da folha (nome completo) a um mesmo identificador.
    Ordem: cadastro do site da Alece (exato ou quase igual) -> tabela de apelidos conferidos -> palavras do
    nome parlamentar dentro de um único nome completo da folha -> nome quase igual a outro já resolvido.
    Devolve (nome na verba -> id, nome na folha -> id)."""
    folha_nomes = sorted({f["nome"] for m in meses_brutos for f in (m.get("folha") or {}).get("deputados") or []})
    vdp_nomes = sorted({r["deputado"] for m in meses_brutos for r in m.get("vdp") or []})
    por_parl = {k: x["slug"] for k, x in cad.items() if x.get("slug")}
    completo_de = {x["slug"]: alece.norm(x["nome_completo"]) for x in cad.values() if x.get("slug") and x.get("nome_completo")}
    folha_norm = {alece.norm(n): n for n in folha_nomes}
    apelidos = {alece.chave(k): alece.norm(v) for k, v in config.APELIDOS.items()}

    id_folha: dict[str, str] = {}
    for i, comp in completo_de.items():                      # cadastro: nome completo idêntico ou quase (Filho/Júnior)
        n = folha_norm.get(comp) or folha_norm.get(_melhor(comp, folha_norm, 0.85) or "")
        if n and n not in id_folha:
            id_folha[n] = i

    def folha_por_palavras(k: str):
        # prefere nomes da folha ainda sem dono (ex.: "Felipe Aguiar" não é Felipe Mota); se o único que bate já tem dono,
        # é outro apelido da mesma pessoa (ex.: "Luana Ribeiro" e "Luana Régia")
        cand = [n for n in folha_nomes if _palavras_contidas(k.split(), n)]
        livres = [n for n in cand if n not in id_folha]
        if len(livres) == 1:
            return livres[0]
        return cand[0] if len(cand) == 1 else None

    id_vdp: dict[str, str] = {}
    pendentes = []
    for v in vdp_nomes:
        k = re.sub(r" POR SOLICITACAO.*$", "", alece.chave(v))
        if not k or _NAO_E_NOME.search(k):
            continue
        prefixo = [c for c in por_parl if c.startswith(k + " ")] if len(k) >= 4 else []   # "ALMIR B" -> "ALMIR BIE"
        i = (por_parl.get(k) or por_parl.get(_melhor(k, por_parl, 0.85) or "")
             or (por_parl[prefixo[0]] if len(prefixo) == 1 else None))
        if not i and k in apelidos:
            n = folha_norm.get(apelidos[k])
            i = id_folha.get(n) or (slug(n) if n else None)
            if n:
                id_folha.setdefault(n, i)
        if not i:
            n = folha_por_palavras(k)
            if n:
                i = id_folha.get(n) or slug(n)
                id_folha.setdefault(n, i)
        if i:
            id_vdp[v] = i
        else:
            pendentes.append((v, k))
    # nomes digitados com erro de quem não está no cadastro: quase igual a outro nome já resolvido
    chaves_ok = {alece.chave(v): i for v, i in id_vdp.items()}
    # reembolso ao próprio deputado: a verba de "Leo Suricate" paga, como pessoa física, "LEONARDO DE SOUSA XAVIER",
    # que é deputado na folha ("...SOUZA XAVIER") -> é a mesma pessoa
    credores_pf = defaultdict(set)
    for m in meses_brutos:
        for r in m.get("vdp") or []:
            if r.get("tipo") == "PF" and r.get("credor"):
                credores_pf[r["deputado"]].add(alece.norm(r["credor"]))
    for v, k in pendentes:
        m = _melhor(k, chaves_ok, 0.86)
        achado = None
        if not m:
            cands = {folha_norm[f] for c in credores_pf.get(v, ()) for f in folha_norm if _parecido(c, f, 0.9)}
            achado = cands.pop() if len(cands) == 1 else None
        if m:
            id_vdp[v] = chaves_ok[m]
        elif achado:
            id_vdp[v] = id_folha.get(achado) or slug(achado)
            id_folha.setdefault(achado, id_vdp[v])
            chaves_ok[k] = id_vdp[v]
        elif len(k.split()) >= 2:
            id_vdp[v] = slug(k)                                  # pessoa sem salário ligado: aparece só com a verba
            chaves_ok[k] = id_vdp[v]
    # deputados do cadastro sem nome completo casado: palavras do nome parlamentar na folha
    usados = set(id_folha.values())
    for k, i in por_parl.items():
        if i in usados:
            continue
        n = folha_por_palavras(k)
        if n and n not in id_folha:
            id_folha[n] = i
            usados.add(i)
    return id_vdp, id_folha


def grupo_forn(doc: str) -> str:
    """Arquivo do índice de fornecedores (o site calcula igual): 2 primeiros dígitos do CNPJ; CPF mascarado em "pf"."""
    d = re.sub(r"\D", "", doc or "")
    return d[:2] if len(d) == 14 else "pf"


# ------------------------------------------------------------------ previsão
def prever(folha_mes: dict, verba_mes: dict, decimo_pago: float, ult_folha: int, ult_verba: int) -> dict:
    """Quanto o deputado ainda deve custar até 31/12 (estimativa).
    Só para quem estava na folha do último mês publicado. Salário: o último salário bruto × meses que faltam,
    mais o 13º se ainda não foi pago. Verba: ritmo médio dos meses fechados (o último mês publicado costuma
    vir incompleto) para os meses que faltam e para completar o último mês."""
    if not ult_folha or ult_folha not in folha_mes:
        return {"ativo": False, "restante": 0.0, "folha": 0.0, "verba": 0.0}
    sal = folha_mes[ult_folha]
    folha_rest = sal * (12 - ult_folha) + (sal if decimo_pago <= 0 else 0.0)
    fechados = [v for m, v in verba_mes.items() if m < ult_verba]
    ritmo = sum(fechados) / len(fechados) if fechados else 0.0
    verba_rest = ritmo * (12 - ult_verba) + max(0.0, ritmo - verba_mes.get(ult_verba, 0.0)) if ult_verba else 0.0
    return {"ativo": True, "restante": round(folha_rest + verba_rest, 2), "folha": round(folha_rest, 2), "verba": round(verba_rest, 2)}


def prever_so_verba(verba_mes: dict, ult_verba: int) -> dict:
    """Estado sem folha nominal publicada (Bahia): só a verba, no ritmo médio dos meses fechados,
    para quem usou a verba em algum dos 3 últimos meses com notas."""
    if not ult_verba or not any(verba_mes.get(m) for m in range(max(1, ult_verba - 2), ult_verba + 1)):
        return {"ativo": False, "restante": 0.0, "folha": 0.0, "verba": 0.0}
    fechados = [v for m, v in verba_mes.items() if m < ult_verba]
    ritmo = sum(fechados) / len(fechados) if fechados else 0.0
    rest = ritmo * (12 - ult_verba) + max(0.0, ritmo - verba_mes.get(ult_verba, 0.0))
    return {"ativo": True, "restante": round(rest, 2), "folha": 0.0, "verba": round(rest, 2)}


# ------------------------------------------------------------------ Bahia (ALBA)
B_BA = BRUTOS_RAIZ / "ba"


def atualizar_cadastro_ba() -> dict:
    """Deputados da legislatura (com suplentes) e quem está em exercício hoje. Chave: nome parlamentar (alece.chave)."""
    cad = ler(B_BA / "cadastro.json", {}) or {}
    try:
        todos = alba.ler_deputados(alba.baixar_legislatura())
        atuais = {d["codigo"] for d in alba.ler_deputados(alba.baixar_em_exercicio())}
    except Exception as e:  # noqa: BLE001
        log.warning("BA: lista de deputados indisponível (%s); mantém a anterior", e)
        return cad
    if not todos:
        log.warning("BA: lista de deputados veio vazia; mantém a anterior")
        return cad
    for d in todos:
        k = alece.chave(d["nome"])
        x = cad.get(k, {})
        x.update({k2: v for k2, v in d.items() if v})
        x["slug"] = x.get("slug") or slug(d["nome"])
        x["url"] = config.ALBA["perfil"].format(codigo=d["codigo"])
        x["atual"] = d["codigo"] in atuais
        x["visto_em"] = date.today().isoformat()
        cad[k] = x
    gravar(B_BA / "cadastro.json", cad)
    try:
        from coletor.fotos import baixar_fotos
        baixar_fotos([(x["slug"], x.get("foto")) for x in cad.values() if x.get("slug")], SAIDA_RAIZ / "ba" / "fotos", B_BA / "fotos_sem.json")
    except Exception as e:  # noqa: BLE001
        log.warning("BA fotos: %s", e)
    log.info("BA: %d deputados na legislatura, %d em exercício", len(todos), len(atuais))
    return cad


def coletar_ba(hoje: date, limite_s: float, forcar: bool = False) -> int:
    """1) lista de cada mês (notas lançadas com atraso: refaz os últimos MESES_REBAIXAR_BA meses);
    2) detalhe de cada nota ainda sem detalhe, do mês mais recente para o mais antigo (fica salvo para sempre)."""
    t0, feitos = time.time(), 0
    for a, m in meses(config.CASAS["ba"]["desde"], hoje):
        if time.time() - t0 > limite_s * 0.4:
            log.warning("BA: tempo das listas esgotado; o resto fica para a próxima execução")
            break
        arq = B_BA / "listas" / f"{a}-{m:02d}.json"
        velho = ler(arq)
        if velho and not forcar and idade_meses(a, m, hoje) > config.MESES_REBAIXAR_BA:
            continue
        try:
            linhas = alba.lista_do_mes(a, m)
        except http.SiteForaDoAr as e:
            log.error("BA: %s", e)
            return feitos
        except Exception as e:  # noqa: BLE001
            log.warning("BA %d-%02d: lista falhou (%s)", a, m, e)
            continue
        if not linhas and velho and velho.get("linhas"):
            log.warning("BA %d-%02d: lista veio vazia agora, mas já tinha notas; mantém a antiga", a, m)
            continue
        gravar(arq, {"ano": a, "mes": m, "baixado_em": hoje.isoformat(), "linhas": linhas})
        feitos += 1
        log.info("BA %d-%02d: %d notas na lista (R$ %.2f)", a, m, len(linhas), sum(x["valor"] for x in linhas))
    # detalhes
    novos = 0
    for arq in sorted((B_BA / "listas").glob("*.json"), reverse=True):
        lista = ler(arq) or {}
        arq_d = B_BA / "detalhes" / arq.name
        det = ler(arq_d, {}) or {}
        falta = [x["id"] for x in lista.get("linhas", []) if x["id"] not in det
                 or (det[x["id"]].get("falhou") and hoje.toordinal() - date.fromisoformat(det[x["id"]]["falhou"]).toordinal() > 30)]
        mudou = 0
        for i in falta:
            if time.time() - t0 > limite_s:
                break
            try:
                det[i] = alba.ler_detalhe(alba.baixar_detalhe(i))
            except http.SiteForaDoAr as e:
                log.error("BA: %s", e)
                gravar(arq_d, det)
                return feitos
            except Exception as e:  # noqa: BLE001
                det[i] = {"itens": [], "falhou": hoje.isoformat()}
                log.warning("BA detalhe %s: %s", i, e)
            mudou += 1
            novos += 1
            if mudou % 100 == 0:
                gravar(arq_d, det)
        if mudou:
            gravar(arq_d, det)
            log.info("BA %s: %d detalhes novos (%d de %d)", arq.stem, mudou, len(det), len(lista.get("linhas", [])))
        if time.time() - t0 > limite_s:
            log.warning("BA: tempo esgotado nos detalhes; o resto fica para a próxima execução")
            break
    log.info("BA: %d listas, %d detalhes novos", feitos, novos)
    return feitos + novos


def _item_da_nota(nota: dict, det: dict | None) -> dict | None:
    itens = (det or {}).get("itens") or []
    if len(itens) == 1:
        return itens[0]
    for it in itens:
        if it["nota"] == nota["nota"]:
            return it
    for it in itens:
        if abs(it["valor"] - nota["valor"]) < 0.01:
            return it
    return itens[0] if itens else None


def meses_ba() -> list[dict]:
    """Notas da Bahia no mesmo formato dos meses do Ceará (sem folha: a ALBA não publica a folha nominal).
    Valor = valor da nota menos a glosa (parte que a Assembleia recusou)."""
    out = []
    for arq in sorted((B_BA / "listas").glob("*.json")):
        lista = ler(arq) or {}
        det = ler(B_BA / "detalhes" / arq.name, {}) or {}
        vdp = []
        for n in lista.get("linhas", []):
            it = _item_da_nota(n, det.get(n["id"]))
            glosa = (it or {}).get("glosa") or 0.0
            desc = f"Nota {n['nota']}" if n["nota"] else "Nota sem número"
            if glosa:
                desc += f" · glosa de R$ {glosa:,.2f} (valor recusado pela Assembleia, já descontado)".replace(",", "X").replace(".", ",").replace("X", ".")
            if not it:
                desc += " · fornecedor ainda não coletado"
            vdp.append({"deputado": n["deputado"], "periodo": n["competencia"], "empenho": n["processo"],
                        "descricao": desc, "doc": (it or {}).get("doc", ""), "tipo": (it or {}).get("tipo", "?"),
                        "credor": (it or {}).get("fornecedor", ""), "valor": round(n["valor"] - glosa, 2),
                        "categoria": alba.categoria(n["categoria_oficial"])})
        out.append({"ano": lista["ano"], "mes": lista["mes"], "vdp": vdp, "recusadas": [],
                    "folha": {"deputados": [], "categorias": {}}})
    return out


# ------------------------------------------------------------------ montagem
def meses_ce() -> list[dict]:
    return [d for p in sorted((BRUTOS / "meses").glob("*.json")) if (d := ler(p))]


def montar(hoje: date, uf: str = "ce", meses_brutos: list[dict] | None = None):
    casa = config.CASAS[uf]
    saida, brutos = SAIDA_RAIZ / uf, BRUTOS_RAIZ / uf
    cad = ler(brutos / "cadastro.json", {}) or {}
    ip = ler(BRUTOS_RAIZ / "ipca.json", {"fatores": {}, "referencia": None})
    por_ano: dict[int, list[dict]] = defaultdict(list)
    for d in (meses_ce() if meses_brutos is None else meses_brutos):
        if d["ano"] >= casa["desde"]:
            por_ano[d["ano"]].append(d)

    # nome completo (folha) -> id; nome parlamentar (verba) -> id
    id_por_completo = {alece.norm(x["nome_completo"]): x["slug"] for x in cad.values() if x.get("nome_completo") and x.get("slug")}
    id_por_parlamentar = {k: x["slug"] for k, x in cad.items() if x.get("slug")}
    info_por_id = {x["slug"]: x for x in cad.values() if x.get("slug")}
    situacao_meses, sem_casar, assembleia = {}, defaultdict(set), {}
    todos = [m for ms in por_ano.values() for m in ms]
    id_vdp, id_folha = resolver_nomes(todos, cad)
    anos = sorted(por_ano)
    for ano in anos:
        deps: dict[str, dict] = {}
        notas: dict[str, list] = defaultdict(list)
        forn: dict[str, dict] = {}
        pessoal = defaultdict(lambda: {"bruta": 0.0, "n_meses": 0, "n_soma": 0})
        por_mes: dict[str, dict] = {}

        def dep(i, nome, completo=""):
            x = deps.get(i)
            if not x:
                inf = info_por_id.get(i, {})
                rot = "Nome não identificado na planilha" if i == NAO_IDENTIFICADO else nome.title()
                x = deps[i] = {"id": i, "nome": inf.get("nome") or rot, "nome_completo": inf.get("nome_completo") or completo,
                               "partido": inf.get("partido", ""), "foto": inf.get("foto", ""), "atual": bool(inf.get("atual")),
                               "url": inf.get("url") or (casa["perfil"].format(slug=i) if i in info_por_id and "{slug}" in casa["perfil"] else ""),
                               "folha": 0.0, "meses_folha": 0, "verba": 0.0, "meses_verba": 0, "notas": 0,
                               "categorias": defaultdict(float), "situacao": "",
                               "_verba_mes": defaultdict(float), "_folha_mes": {}, "_decimo": 0.0}
            return x

        for mes in sorted(por_ano[ano], key=lambda d: d["mes"]):
            chave_mes = f"{ano}-{mes['mes']:02d}"
            situacao_meses[chave_mes] = {"verba": len(mes.get("vdp") or []), "folha": len((mes.get("folha") or {}).get("deputados") or []),
                                         "recusadas": len(mes.get("recusadas") or []),
                                         "recusadas_valor": round(sum(r.get("valor") or 0 for r in mes.get("recusadas") or []), 2)}
            folha = (mes.get("folha") or {}).get("deputados") or []
            por_mes[chave_mes] = {"folha": round(sum(f["bruta"] - f.get("teto", 0) + f.get("decimo", 0) for f in folha), 2),
                                  "verba": round(sum(r["valor"] for r in mes.get("vdp") or []), 2)}
            # verba
            vistos = set()
            for r in mes.get("vdp") or []:
                i = id_vdp.get(r["deputado"]) or NAO_IDENTIFICADO
                if i == NAO_IDENTIFICADO:
                    sem_casar[ano].add(r["deputado"])
                x = dep(i, r["deputado"])
                if x.pop("_nome_da_folha", False):   # fora do cadastro: mostra o nome parlamentar, não o da folha
                    x["nome"] = r["deputado"].title()
                x["verba"] += r["valor"]
                x["_verba_mes"][mes["mes"]] += r["valor"]
                x["notas"] += 1
                x["categorias"][r["categoria"]] += r["valor"]
                vistos.add(i)
                notas[i].append([chave_mes, r["empenho"], r["categoria"], r["doc"], r["credor"], r["valor"], r["descricao"]])
                if r["doc"]:
                    fo = forn.setdefault(r["doc"], {"nome": r["credor"], "tipo": r["tipo"], "total": 0.0, "notas": 0, "deps": set()})
                    fo["total"] += r["valor"]
                    fo["notas"] += 1
                    fo["deps"].add(i)
            for i in vistos:
                deps[i]["meses_verba"] += 1
            # folha
            for f in folha:
                i = id_folha.get(f["nome"]) or slug(f["nome"])
                novo = i not in deps
                x = dep(i, f["nome"], f["nome"])
                if novo and i not in info_por_id:
                    x["_nome_da_folha"] = True
                if not x["nome_completo"]:
                    x["nome_completo"] = f["nome"]
                x["folha"] += f["bruta"] - f.get("teto", 0) + f.get("decimo", 0)
                x["_folha_mes"][mes["mes"]] = f["bruta"] - f.get("teto", 0)
                x["_decimo"] += f.get("decimo", 0)
                x["meses_folha"] += 1
                x["situacao"] = f["situacao"]
            for cat, c in ((mes.get("folha") or {}).get("categorias") or {}).items():
                pa = pessoal[cat]
                pa["bruta"] += c["bruta"]
                pa["n_meses"] += 1
                pa["n_soma"] += c["n"]

        fator = (ip.get("fatores") or {}).get(str(ano)) or (ip.get("fatores") or {}).get(ano) or 1.0
        # previsão até dezembro (estimativa), só no ano em andamento
        ult_folha = max((m for x in deps.values() for m in x["_folha_mes"]), default=0)
        ult_verba = max((m for x in deps.values() for m in x["_verba_mes"]), default=0)
        if not casa["salario"]:
            ult_folha = ult_verba          # sem folha publicada: a previsão é só da verba, a partir do último mês com notas
        em_andamento = ano == hoje.year and 0 < ult_folha < 12
        lista = []
        for x in deps.values():
            vm, fm, dec = x.pop("_verba_mes"), x.pop("_folha_mes"), x.pop("_decimo")
            x["mensal_verba"] = [round(vm.get(m, 0.0), 2) for m in range(1, 13)]
            x["mensal_folha"] = [round(fm.get(m, 0.0), 2) for m in range(1, 13)]
            if not em_andamento:
                x["previsao"] = None
            elif casa["salario"]:
                x["previsao"] = prever(fm, vm, dec, ult_folha, ult_verba)
            else:
                x["previsao"] = prever_so_verba(vm, ult_verba)
            x.pop("_nome_da_folha", None)
            x["folha"], x["verba"] = round(x["folha"], 2), round(x["verba"], 2)
            x["total"] = round(x["folha"] + x["verba"], 2)
            x["categorias"] = {k: round(v, 2) for k, v in sorted(x["categorias"].items(), key=lambda kv: -kv[1])}
            lista.append(x)
        lista.sort(key=lambda x: -x["total"])
        cats = defaultdict(float)
        for x in lista:
            for k, v in x["categorias"].items():
                cats[k] += v
        fornecedores = sorted(([doc, f["nome"], f["tipo"], round(f["total"], 2), f["notas"], len(f["deps"])] for doc, f in forn.items()),
                              key=lambda r: -r[3])
        meses_com_verba = sorted(k for k, v in situacao_meses.items() if k.startswith(str(ano)) and v["verba"])
        resumo = {
            "versao": VERSAO, "ano": ano, "fator_ipca": fator, "meses_com_verba": meses_com_verba,
            "ultimo_mes": meses_com_verba[-1] if meses_com_verba else None,
            "totais": {"folha": round(sum(x["folha"] for x in lista), 2), "verba": round(sum(x["verba"] for x in lista), 2),
                       "total": round(sum(x["total"] for x in lista), 2), "deputados": len(lista)},
            "categorias": {k: round(v, 2) for k, v in sorted(cats.items(), key=lambda kv: -kv[1])},
            "por_mes": por_mes,
            "fechado": not em_andamento,
            "sem_fornecedor": sum(1 for ns in notas.values() for n in ns if not n[3]),
            "previsao": {"ult_folha": ult_folha, "ult_verba": ult_verba,
                         "restante": round(sum((x["previsao"] or {}).get("restante", 0) for x in lista), 2),
                         "folha": round(sum((x["previsao"] or {}).get("folha", 0) for x in lista), 2),
                         "verba": round(sum((x["previsao"] or {}).get("verba", 0) for x in lista), 2)} if em_andamento else None,
            "deputados": lista,
        }
        gravar(saida / str(ano) / "resumo.json", resumo)
        pasta_notas = saida / str(ano) / "notas"
        for velho in pasta_notas.glob("*.json"):
            if velho.stem not in notas:
                velho.unlink()
        for i, ns in notas.items():
            gravar(pasta_notas / f"{i}.json", sorted(ns, key=lambda n: (n[0], n[1])))
        # índice por fornecedor (a ficha do fornecedor lê um arquivo pequeno, e não as notas de todos os deputados)
        grupos: dict[str, dict] = defaultdict(dict)
        for i, ns in notas.items():
            for mes_n, emp, cat, doc, credor, valor, desc in ns:
                if not doc:
                    continue
                g = grupo_forn(doc)
                f = grupos[g].setdefault(doc, {"nome": credor, "tipo": forn.get(doc, {}).get("tipo", ""), "notas": []})
                f["notas"].append([mes_n, i, emp, cat, valor, desc])
        pasta_f = saida / str(ano) / "forn"
        for velho in pasta_f.glob("*.json"):
            if velho.stem not in grupos:
                velho.unlink()
        for g, conteudo in grupos.items():
            for f in conteudo.values():
                f["notas"].sort(key=lambda n: (n[0], n[2]), reverse=True)
            gravar(pasta_f / f"{g}.json", conteudo)
        gravar(saida / str(ano) / "fornecedores.json", {"campos": ["doc", "nome", "tipo", "total", "notas", "deputados"], "linhas": fornecedores})
        assembleia[str(ano)] = {cat: {"bruta": round(p["bruta"], 2), "media_pessoas": round(p["n_soma"] / p["n_meses"]) if p["n_meses"] else 0,
                                      "meses": p["n_meses"]} for cat, p in sorted(pessoal.items(), key=lambda kv: -kv[1]["bruta"])}
        log.info("%d: %d deputados, folha R$ %.2f, verba R$ %.2f", ano, len(lista), resumo["totais"]["folha"], resumo["totais"]["verba"])

    gerado = datetime.now(timezone.utc).isoformat(timespec="minutes")
    gravar(saida / "meta.json", {
        "gerado_em": gerado,
        "versao": VERSAO, "uf": casa["uf"], "casa": casa["nome"], "sigla": casa["sigla"],
        "estado": casa["estado"], "do_estado": casa["do_estado"], "salario": casa["salario"],
        "subsidio": casa.get("subsidio"), "subsidio_lei": casa.get("subsidio_lei"),
        "verba": casa["verba"], "verba_curta": casa["verba_curta"], "limite": casa["limite"], "desde": casa["desde"],
        "anos": anos, "ipca": ip, "meses": situacao_meses,
        "pessoal_assembleia": assembleia,
        "sem_casar": {str(a): sorted(v) for a, v in sem_casar.items()},
        "fontes": casa["fontes"],
    })
    gravar_estados(uf, gerado, anos)


def gravar_estados(uf: str, gerado: str, anos: list[int]):
    """Lista dos estados publicados, para o seletor do site (só entra quem já tem dados montados)."""
    atual = {e["id"]: e for e in (ler(SAIDA_RAIZ / "estados.json", {}) or {}).get("estados", [])}
    c = config.CASAS[uf]
    atual[uf] = {"id": uf, "uf": c["uf"], "estado": c["estado"], "do_estado": c["do_estado"], "casa": c["nome"],
                 "sigla": c["sigla"], "vagas": c["vagas"], "desde": c["desde"], "salario": c["salario"],
                 "anos": anos, "gerado_em": gerado}
    ordem = list(config.CASAS)
    gravar(SAIDA_RAIZ / "estados.json", {"estados": sorted(atual.values(), key=lambda e: ordem.index(e["id"]) if e["id"] in ordem else 99)})


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--so-montar", action="store_true")
    ap.add_argument("--forcar", action="store_true", help="baixa de novo todos os meses")
    ap.add_argument("--minutos", type=float, default=90)
    ap.add_argument("--uf", default="todas", help="ce, ba ou todas")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    hoje = date.today()
    ufs = list(config.CASAS) if args.uf == "todas" else [args.uf]
    t0, limite = time.time(), args.minutos * 60
    if not args.so_montar:
        atualizar_ipca()
    for uf in ufs:
        resta = limite - (time.time() - t0)
        try:
            if uf == "ce":
                if not args.so_montar:
                    atualizar_cadastro_ce()
                    coletar_ce(hoje, resta, args.forcar)
                montar(hoje, "ce")
            elif uf == "ba":
                if not args.so_montar:
                    atualizar_cadastro_ba()
                    coletar_ba(hoje, resta, args.forcar)
                montar(hoje, "ba", meses_ba())
        except Exception:  # noqa: BLE001
            log.error("%s: falhou; os outros estados seguem", uf.upper())
            traceback.print_exc()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        sys.exit(1)
