"""Projeto Quanto Custa — Deputados estaduais (configuração).

Começa pelo Ceará (Assembleia Legislativa do Ceará — Alece). Outros estados entram
como novas entradas em ASSEMBLEIAS, cada uma com o seu módulo em coletor/.
"""

USER_AGENT = "ProjetoQuantoCusta/1.0 (painel de transparencia com dados abertos)"
PAUSA_ENTRE_REQUISICOES = 1.0   # o portal da Alece é lento: uma consulta por segundo, no máximo

# A legislatura atual começou em fevereiro de 2023. Antes disso, o arquivo da verba
# (sistema antigo S2GPR, até 2021) mistura folhas de aposentadoria/pensão e empenhos anuais
# globais nas linhas dos deputados; por isso começamos em 2023.
ANO_INICIAL = 2023

# Meses já fechados há mais que isso não são baixados de novo (a fonte quase não muda).
MESES_REBAIXAR = 3

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
