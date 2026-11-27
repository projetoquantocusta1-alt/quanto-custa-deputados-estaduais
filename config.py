"""Quanto Custa — Deputados estaduais (configuração).

Um estado por vez. Cada Assembleia tem a sua entrada em CASAS (abaixo) e o seu módulo em
coletor/ (Ceará: alece.py; Bahia: alba.py). O site lê docs/dados/<uf>/ de cada estado.
"""

USER_AGENT = "ProjetoQuantoCusta/1.0 (painel de transparencia com dados abertos)"
PAUSA_ENTRE_REQUISICOES = 1.0   # o portal da Alece é lento: uma consulta por segundo, no máximo

# A legislatura atual começou em fevereiro de 2023. Antes disso, o arquivo da verba
# (sistema antigo S2GPR, até 2021) mistura folhas de aposentadoria/pensão e empenhos anuais
# globais nas linhas dos deputados; por isso começamos em 2023.
ANO_INICIAL = 2023

# Meses já fechados há mais que isso não são baixados de novo (a fonte quase não muda).
MESES_REBAIXAR = 3
# Bahia: notas de um mês continuam sendo lançadas por muitos meses depois; a lista é refeita por mais tempo.
MESES_REBAIXAR_BA = 12

IPCA_SGS = ("https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados"
            "?formato=json&dataInicial=01/01/{ano}")

# --- Ceará (Alece) ---
ALECE = {
    "uf": "CE",
    "nome": "Assembleia Legislativa do Ceará",
    "sigla": "Alece",
    # o mês PRECISA ter dois dígitos ("06"): com "6" o portal devolve o arquivo vazio
    "vdp_csv": "https://transparencia.al.ce.gov.br/despesas/verba-desempenho-parlamentar/csv?mes={mes:02d}&ano={ano}",
    "vdp_pagina": "https://transparencia.al.ce.gov.br/despesas/verba-desempenho-parlamentar",
    "folha_csv": "https://transparencia.al.ce.gov.br/gestao-de-pessoas/pessoal/csv?mes={mes:02d}&ano={ano}",
    "folha_pagina": "https://transparencia.al.ce.gov.br/gestao-de-pessoas/pessoal",
    "lista_deputados": "https://www.al.ce.gov.br/deputados",
    "perfil": "https://www.al.ce.gov.br/deputados/{slug}",
}

# Apelidos da verba que não aparecem no nome completo da folha (conferidos em fonte pública).
# Chave: nome na planilha da verba; valor: nome completo na folha da Alece.
APELIDOS = {
    "NIZO COSTA": "ANTONIO VALDENIZO DA COSTA",   # ficha oficial da Alece
    "GORDIM ARAUJO": "ELVILO ARAUJO DE OLIVEIRA",  # "Gordim" é o apelido de Elvilo Araújo (imprensa)
}

# Categorias da verba (VDP), pela descrição do empenho. A primeira regra que casar vale.
CATEGORIAS_VDP = [
    ("Combustível", r"COMBUST|ABASTECIMENTO"),
    ("Alimentação (vale)", r"ALIMENTACAO|REFEICAO"),
    ("Consultoria e assessoria", r"CONSULTORIA|ASSESSORIA|ADVOCACIA|JURIDIC|CONTABI|PRESTACAO DE SERVICOS PROFISSIONAIS"),
    ("Divulgação do mandato", r"DIVULGACAO|PUBLICIDADE|RADIO|PROGRAMA|JORNAL|REDES SOCIAIS|MIDIA|SITE|IMPRESS|GRAFIC"),
    ("Locação de veículos", r"LOCACAO D[EOA]S? ?(?:\d+ )?(?:UM |DOIS |TRES )?VEICULO|LOCACAO DE VEICULO|RENT A CAR|LOCADORA"),
    ("Telefonia e internet", r"TELEFON|INTERNET|CELULAR|DADOS MOVEIS"),
    ("Fretamento de aeronave", r"FRETAMENTO|AERONAVE|TAXI AEREO"),
    ("Passagens e locomoção", r"PASSAGE|LOCOMOCAO|AEREA|TRANSPORTE"),
    ("Seguro de vida", r"SEGURO"),
    ("Aluguel de imóvel / escritório", r"ALUGUEL|LOCACAO DE (?:IMOVEL|SALA|ESCRITORIO)|CONDOMINIO"),
    ("Correios", r"POSTA|CORREIO"),
    ("Sistemas e informática", r"SISTEMA|SOFTWARE|INFORMATICA|PROGRAMACAO"),
    ("Saúde (plano)", r"SAUDE|PLANO DE ASSISTENCIA|ODONTO"),
    ("Reembolso de despesas", r"REEMBOLSO"),
]


# --- Bahia (ALBA) ---
# Sem robots.txt no site (resposta 404): nenhuma restrição. A lista mensal tem 20 notas por página
# (a página começa em 0) e cada nota tem uma página de detalhe com CPF/CNPJ, fornecedor e glosa.
# A ALBA não publica a folha de pagamento nominal: só o subsídio fixado em lei.
ALBA = {
    "uf": "BA",
    "nome": "Assembleia Legislativa da Bahia",
    "sigla": "ALBA",
    "lista_mes": "https://www.al.ba.gov.br/transparencia/verbas-idenizatorias?ano={ano}&mes={mes}&page={pagina}&size=20",
    "detalhe": "https://www.al.ba.gov.br/transparencia/verbas-idenizatorias/{id}/",
    "verba_pagina": "https://www.al.ba.gov.br/transparencia/verbas-idenizatorias",
    "legislatura": "https://www.al.ba.gov.br/deputados/legislatura-atual",
    "em_exercicio": "https://www.al.ba.gov.br/deputados/deputados-estaduais",
    "perfil": "https://www.al.ba.gov.br/deputados/deputado-legislatura-atual/{codigo}",
    "site": "https://www.al.ba.gov.br",
    "subsidio_pdf": "https://portalrh.alba.ba.gov.br/pdf/transparencia/ALBA_ECV_Deputados.pdf",
}

# Categorias da verba da ALBA (nome oficial, sem acentos, em maiúsculas -> nome curto). A primeira que casar vale.
CATEGORIAS_ALBA = [
    ("Aluguel de imóvel / escritório", r"ALUGUEL"),
    ("Material de expediente", r"MATERIAL DE EXPEDIENTE"),
    ("Software, internet, telefone e correios", r"SOFTWARE|INTERNET|TELEFONE|POSTAIS"),
    ("Divulgação em redes sociais", r"DIVULGACAO.*REDES SOCIAIS"),
    ("Divulgação do mandato", r"DIVULGACAO"),
    ("Fretamento", r"FRETAMENTO"),
    ("Cursos e eventos (inscrições)", r"INSCRIC"),
    ("Locação de veículos", r"LOCACAO DE VEICULO"),
    ("Locomoção e hospedagem", r"LOCOMOCAO|HOSPEDAGEM"),
    ("Consultoria e assessoria", r"CONSULTORIAS\s+ASSESSORIAS"),
    ("Assessorias", r"^ASSESSORIA"),
    ("Consultorias", r"^CONSULTORIA"),
    ("Pesquisas", r"^PESQUISA"),
    ("Trabalhos técnicos", r"TRABALHOS TECNICOS"),
]


# --- Rio Grande do Norte (ALRN) ---
# O portal de transparência (um aplicativo que lê a API api-transparencia.al.rn.leg.br) exige um token de
# acesso embutido no próprio código entregue ao navegador. O robô lê esse token público do portal a cada
# execução (coletor/alrn.py), em vez de guardá-lo aqui. A ALRN publica a cota parlamentar nota a nota, mas
# não a folha de pagamento nominal dos deputados.
ALRN = {
    "uf": "RN",
    "nome": "Assembleia Legislativa do Rio Grande do Norte",
    "sigla": "ALRN",
    "portal": "https://transparencia.al.rn.leg.br/",
    "api": "https://api-transparencia.al.rn.leg.br",
    "verba_pagina": "https://transparencia.al.rn.leg.br/verbas",
    "deputados": "https://www.al.rn.leg.br/deputados",
    "perfil": "https://www.al.rn.leg.br/deputado/{codigo}/{slug}",
}

# --- Minas Gerais (ALMG) ---
# A API de dados abertos da ALMG não traz a verba; ela fica no portal almg.gov.br, com uma página de detalhe por
# deputado (nota a nota: fornecedor, CNPJ/CPF, data, número e valor reembolsável). O portal responde aos robôs do
# GitHub (ao contrário do de São Paulo). A folha nominal não é usada; o subsídio é o teto constitucional (75% do
# subsídio do deputado federal, hoje R$ 34.774,64).
ALMG = {
    "uf": "MG",
    "nome": "Assembleia Legislativa de Minas Gerais",
    "sigla": "ALMG",
    "legislatura": 20,   # 20ª legislatura: 2023-2027
    "lista": "https://www.almg.gov.br/transparencia/prestacao-de-contas/deputados/verba-indenizatoria/?leg={leg}",
    "detalhe": "https://www.almg.gov.br/transparencia/prestacao-de-contas/deputados/verba-indenizatoria/detalhe.html?id={id}&periodo={periodo}",
    "verba_pagina": "https://www.almg.gov.br/transparencia/prestacao-de-contas/deputados/verba-indenizatoria/",
    "deputados_pagina": "https://www.almg.gov.br/a-assembleia/deputados/inicial/",
    "perfil": "https://www.almg.gov.br/transparencia/prestacao-de-contas/deputados/verba-indenizatoria/detalhe.html?id={slug}",
}


# Estados publicados no site (ordem do seletor). "limite" explica por que os dados começam no ano "desde".
CASAS = {
    "ce": {
        "uf": "CE", "estado": "Ceará", "do_estado": "do Ceará", "nome": ALECE["nome"], "sigla": "Alece", "vagas": 46,
        "desde": 2023, "salario": True,
        "verba": "Verba de desempenho parlamentar", "verba_curta": "Verba (VDP)",
        "perfil": ALECE["perfil"],
        "fontes": {"verba": ALECE["vdp_pagina"], "folha": ALECE["folha_pagina"], "deputados": ALECE["lista_deputados"]},
        "limite": ("Dados desde janeiro de 2023, início da legislatura atual. Os anos anteriores ficaram de fora porque, "
                   "no sistema antigo da Assembleia, o arquivo da verba mistura aposentadorias, pensões e empenhos anuais "
                   "globais nas linhas dos deputados. Com isso, não dá para separar com segurança o que foi gasto de cada "
                   "deputado, e preferimos não publicar números que não conseguimos conferir."),
    },
    "ba": {
        "uf": "BA", "estado": "Bahia", "do_estado": "da Bahia", "nome": ALBA["nome"], "sigla": "ALBA", "vagas": 63,
        "desde": 2023, "salario": False, "subsidio": 34774.64, "subsidio_lei": "Lei estadual nº 14.532, de 16/01/2023",
        "verba": "Verba indenizatória", "verba_curta": "Verba indenizatória",
        "perfil": ALBA["perfil"],
        "fontes": {"verba": ALBA["verba_pagina"], "deputados": ALBA["legislatura"], "subsidio": ALBA["subsidio_pdf"]},
        "limite": ("Dados desde janeiro de 2023, início da legislatura atual, para comparar com os outros estados no mesmo "
                   "período. A Assembleia da Bahia não publica a folha de pagamento com o nome de cada deputado, só o "
                   "subsídio fixado em lei (hoje, R$ 34.774,64 por mês). Por isso, na Bahia, o custo mostrado é só o da verba "
                   "indenizatória, sem o salário."),
    },
    "rn": {
        "uf": "RN", "estado": "Rio Grande do Norte", "do_estado": "do Rio Grande do Norte", "nome": ALRN["nome"],
        "sigla": "ALRN", "vagas": 24, "desde": 2023, "salario": False,
        "verba": "Cota parlamentar (verba de gabinete)", "verba_curta": "Cota parlamentar",
        "perfil": ALRN["perfil"],
        "fontes": {"verba": ALRN["verba_pagina"], "deputados": ALRN["deputados"]},
        "limite": ("Dados desde janeiro de 2023, início da legislatura atual, para comparar com os outros estados no "
                   "mesmo período (o portal da ALRN tem a cota desde 2009). A Assembleia do Rio Grande do Norte publica "
                   "a cota parlamentar nota a nota, com fornecedor e valor, mas não a folha de pagamento com o salário de "
                   "cada deputado; por isso mostramos só a cota. Os números vêm do portal de transparência da ALRN, que "
                   "exige uma chave de acesso embutida no próprio código do site; o robô usa essa mesma chave pública "
                   "para ler os dados abertos."),
    },
    "mg": {
        "uf": "MG", "estado": "Minas Gerais", "do_estado": "de Minas Gerais", "nome": ALMG["nome"], "sigla": "ALMG",
        "vagas": 77, "desde": 2023, "salario": False, "subsidio": 34774.64,
        "subsidio_lei": "teto constitucional (art. 27, §2º): 75% do subsídio do deputado federal",
        "verba": "Verba indenizatória", "verba_curta": "Verba indenizatória",
        "perfil": ALMG["perfil"],
        "fontes": {"verba": ALMG["verba_pagina"], "deputados": ALMG["deputados_pagina"]},
        "limite": ("Dados desde janeiro de 2023, início da legislatura atual, para comparar com os outros estados no "
                   "mesmo período. A Assembleia de Minas publica a verba indenizatória nota a nota, com fornecedor e "
                   "valor, mas não a folha de pagamento com o salário de cada deputado; por isso mostramos a verba e o "
                   "subsídio fixado em lei (hoje, R$ 34.774,64 por mês, o teto de 75% do salário do deputado federal)."),
    },
}
