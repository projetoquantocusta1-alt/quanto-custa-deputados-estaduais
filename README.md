# Projeto Quanto Custa — Deputados estaduais

Quanto custa cada deputado estadual: salário bruto (folha de pagamento nominal) e verba de gabinete,
nota a nota, com fornecedores e valores corrigidos pela inflação. Começa pelo **Ceará** (Assembleia
Legislativa do Ceará — Alece). Endereço: https://quantocustaum.com/quanto-custa-deputados-estaduais/

## Como funciona

- `atualizar.py` — robô diário (GitHub Actions). Baixa, mês a mês desde 2023:
  - a **verba de desempenho parlamentar (VDP)** — CSV do Portal da Transparência da Alece;
  - a **folha de pagamento** — CSV nominal (deputados nominalmente; demais categorias só em totais);
  - o **cadastro** dos deputados (nome parlamentar, nome completo, partido, foto) no site da Alece.
- `coletor/alece.py` — leitores da Alece. Atenção: o mês vai com dois dígitos (`mes=06`);
  com `mes=6` o portal devolve o arquivo vazio.
- Saídas em `SAIDA` (padrão `docs/dados`) e `BRUTOS` (padrão `dados_brutos`).

## Site

GitHub Pages a partir da pasta `docs/` (branch `main`). Endereço: https://quantocustaum.com/quanto-custa-deputados-estaduais/

Privacidade: CPF de pessoas físicas sempre mascarado (`***.456.789-**`); da folha, só deputados
aparecem com nome — servidores entram apenas em totais por categoria.
