/* Projeto Quanto Custa — Deputados estaduais (Ceará / Alece) */
(() => {
"use strict";
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"];
const E = { tick: 0, meta: null, ano: null, pag: "inicio", res: {}, forn: {}, ord: ["total", -1], lim: 30, limF: 50, graf: {} };
const brl = (v, d = 0) => (v || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL", minimumFractionDigits: d, maximumFractionDigits: d });
const curto = (v) => { const a = Math.abs(v || 0);
  if (a >= 1e9) return "R$ " + (v / 1e9).toLocaleString("pt-BR", { maximumFractionDigits: 2 }) + " bi";
  if (a >= 999_500) return "R$ " + (v / 1e6).toLocaleString("pt-BR", { maximumFractionDigits: 2 }) + " mi";
  if (a >= 1e3) return "R$ " + (v / 1e3).toLocaleString("pt-BR", { maximumFractionDigits: 0 }) + " mil";
  return brl(v); };
const nf = (v, d = 0) => (v || 0).toLocaleString("pt-BR", { minimumFractionDigits: d, maximumFractionDigits: d });
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const semAcento = (s) => (s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
const soma = (a) => a.reduce((s, x) => s + (x || 0), 0);
const getJSON = async (u) => { const r = await fetch(u, { cache: "no-cache" }); if (!r.ok) throw new Error(u + " " + r.status); return r.json(); };
const porExtenso = (v) => { const a = Math.abs(v || 0);
  for (const [b, um, varios] of [[1e12, "trilhão", "trilhões"], [1e9, "bilhão", "bilhões"], [1e6, "milhão", "milhões"], [1e3, "mil", "mil"]]) {
    if (a < b) continue;
    const x = v / b, t = x.toLocaleString("pt-BR", { maximumFractionDigits: Math.abs(x) < 10 ? 2 : Math.abs(x) < 100 ? 1 : 0 });
    return b === 1e3 ? `≈ ${t} mil reais` : `≈ ${t} ${Math.abs(x) < 2 ? um : varios} de reais`; }
  return ""; };
const mesBR = (k) => { const [a, m] = String(k).split("-"); return `${MESES[+m - 1]}/${a}`; };
const tot = () => E.ano === "total";
const corrigir = () => $("#f-ipca").checked;
const fatorDe = (r) => (corrigir() ? r?.fator_ipca || 1 : 1);
const iniciais = (n) => (n || "?").split(/\s+/).filter(Boolean).slice(0, 2).map((p) => p[0]).join("").toUpperCase();
const foto = (d, cls = "") => d.foto ? `<img class="${cls}" src="${esc(d.foto)}" alt="" loading="lazy" referrerpolicy="no-referrer" onerror="this.style.visibility='hidden'">` : `<span class="foto sem ${cls}">${esc(iniciais(d.nome))}</span>`;

async function resumo(a) {
  if (E.res[a]) return E.res[a];
  return (E.res[a] = await getJSON(`dados/${a}/resumo.json`).catch(() => null));
}
// ano escolhido ou soma de todos os anos (cada ano corrigido pelo próprio IPCA)
async function dados() {
  const anos = tot() ? E.meta.anos : [E.ano];
  const rs = (await Promise.all(anos.map(resumo))).filter(Boolean), m = new Map();
  rs.forEach((r) => { const F = fatorDe(r); r.deputados.forEach((d) => {
    let o = m.get(d.id);
    if (!o) m.set(d.id, (o = { ...d, folha: 0, verba: 0, total: 0, notas: 0, meses_folha: 0, meses_verba: 0, categorias: {}, anos: [] }));
    o.folha += d.folha * F; o.verba += d.verba * F; o.total += d.total * F; o.notas += d.notas;
    o.meses_folha += d.meses_folha; o.meses_verba += d.meses_verba; o.anos.push(r.ano);
    Object.assign(o, { nome: d.nome, partido: d.partido || o.partido, foto: d.foto || o.foto, url: d.url || o.url, atual: d.atual, situacao: d.situacao });
    o.prev = anos.length === 1 && d.previsao?.ativo ? d.previsao.restante * F : 0;
    Object.entries(d.categorias || {}).forEach(([k, v]) => (o.categorias[k] = (o.categorias[k] || 0) + v * F));
  }); });
  return [...m.values()];
}
const passa = (d) => { const p = $("#f-partido").value, q = semAcento($("#f-busca").value.trim());
  return (!p || d.partido === p) && (!q || semAcento(d.nome + " " + (d.nome_completo || "")).includes(q)); };
const rotAno = () => (tot() ? `${E.meta.anos[0]}–${E.meta.anos[E.meta.anos.length - 1]}` : E.ano);
function kpis(el, itens) { $(el).innerHTML = itens.map(([r, v, o]) => `<div class="kpi"><div class="rot">${r}</div><div class="val num">${v}</div><div class="obs">${o || ""}</div></div>`).join(""); }
function grafico(id, cfg) { E.graf[id]?.destroy(); E.graf[id] = new Chart($("#" + id), cfg); }
const tipBRL = { callbacks: { label: (c) => `${c.dataset.label ? c.dataset.label + ": " : ""}${brl(c.parsed.x ?? c.parsed.y ?? c.parsed)}` } };
const ultimoMes = async () => { const r = await resumo(E.meta.anos[E.meta.anos.length - 1]); return r?.ultimo_mes; };

// ---------------------------------------------------------------- início
async function rInicio() {
  const D = (await dados()).filter(passa), T = soma(D.map((d) => d.total)), ult = await ultimoMes();
  $("#i-rot").textContent = tot() ? `Os deputados estaduais do Ceará já custaram, de ${rotAno()},` : `Os deputados estaduais do Ceará custaram em ${E.ano}`;
  const r = tot() ? null : E.res[E.ano], prev = r?.previsao, rest = prev ? soma(D.map((d) => d.prev || 0)) : 0;
  cancelAnimationFrame(E.tick);
  const nota = `${corrigir() ? "Em valores de hoje (IPCA). " : ""}Salário bruto (folha) + verba de desempenho parlamentar. Não inclui a equipe do gabinete${ult ? ` · dados até ${mesBR(ult)}` : ""}.`;
  if (prev && rest > 0) {
    // corre em tempo real: do 1º dia depois da última folha publicada até 31/12, no ritmo da previsão
    const ini = new Date(r.ano, prev.ult_folha, 1).getTime(), fim = new Date(r.ano + 1, 0, 1).getTime();
    const porSeg = rest / ((fim - ini) / 1000);
    const passo = () => { const v = Math.min(T + rest, T + Math.max(0, (Date.now() - ini) / 1000) * porSeg);
      $("#i-total").textContent = brl(v); $("#i-ext").textContent = porExtenso(v);
      if (E.pag === "inicio") E.tick = requestAnimationFrame(passo); };
    passo();
    $("#i-nota").innerHTML = `${esc(nota)}<br><span class="ritmo">O valor avança em tempo real, no ritmo previsto: <b>+${brl(porSeg, 2)} por segundo</b> · ${curto(porSeg * 86400)} por dia · previsão para ${r.ano}: <b>${curto(T + rest)}</b> (estimativa)</span>`;
  } else {
    $("#i-total").textContent = brl(T); $("#i-ext").textContent = porExtenso(T); $("#i-nota").textContent = nota;
  }
  const folha = soma(D.map((d) => d.folha)), verba = soma(D.map((d) => d.verba));
  const comVerba = D.filter((d) => d.meses_verba), mesesV = soma(comVerba.map((d) => d.meses_verba));
  kpis("#i-kpis", [...(prev && rest > 0 ? [["Previsão até dezembro", "+" + curto(rest), `${E.ano} deve fechar em ${curto(T + rest)} (estimativa)`]] : []),
    ["Salários (folha bruta)", curto(folha), porExtenso(folha)], ["Verba (VDP)", curto(verba), porExtenso(verba)],
    ["Verba média por deputado, por mês", brl(mesesV ? verba / mesesV : 0), `${comVerba.length} deputados usaram a verba`],
    ["Deputados no período", nf(D.length), "inclui suplentes que assumiram"]]);
  const top = D.slice().sort((a, b) => b.total - a.total).slice(0, 5);
  $("#i-top-dica").textContent = rotAno();
  $("#i-top").innerHTML = top.map((d) => `<li>${foto(d)}<div><a href="#" data-dep="${esc(d.id)}">${esc(d.nome)}</a><span class="s">${esc(d.partido || "—")}</span></div><span class="v">${curto(d.total)}</span></li>`).join("");
  const cats = {}; D.forEach((d) => Object.entries(d.categorias).forEach(([k, v]) => (cats[k] = (cats[k] || 0) + v)));
  const cs = Object.entries(cats).filter(([, v]) => v > 0).sort((a, b) => b[1] - a[1]);
  grafico("g-cat", { type: "bar", data: { labels: cs.map((c) => c[0]), datasets: [{ data: cs.map((c) => c[1]), backgroundColor: "#2475B8" }] },
    options: { indexAxis: "y", maintainAspectRatio: false, plugins: { legend: { display: false }, tooltip: tipBRL }, scales: { x: { ticks: { callback: (v) => curto(v) } } } } });
  // mês a mês: notas por mês vêm do próprio resumo (soma das categorias não tem mês); usa meta.meses para a verba e a folha média
  const anos = tot() ? E.meta.anos : [E.ano], labels = [], vf = [], vv = [];
  for (const a of anos) { const r = await resumo(a); if (!r?.por_mes) continue; const F = fatorDe(r);
    Object.entries(r.por_mes).forEach(([k, x]) => { labels.push(mesBR(k)); vf.push(x.folha * F); vv.push(x.verba * F); }); }
  grafico("g-mes", { type: "bar", data: { labels, datasets: [{ label: "Salários (folha)", data: vf, backgroundColor: "#14283F", stack: "s" }, { label: "Verba (VDP)", data: vv, backgroundColor: "#2475B8", stack: "s" }] },
    options: { maintainAspectRatio: false, plugins: { tooltip: tipBRL }, scales: { x: { stacked: true }, y: { stacked: true, ticks: { callback: (v) => curto(v) } } } } });
}

// ---------------------------------------------------------------- ranking
const COLS = [["total", "Custo total"], ["folha", "Salário (folha)"], ["verba", "Verba (VDP)"], ["prev", "Previsão até dez."], ["notas", "Notas"]];
async function rDeputados() {
  const D = (await dados()).filter(passa);
  const [k, s] = E.ord; D.sort((a, b) => (k === "nome" ? a.nome.localeCompare(b.nome) * -s : (a[k] - b[k]) * s));
  kpis("#d-kpis", [["Deputados", nf(D.length), rotAno()], ["Custo total", curto(soma(D.map((d) => d.total))), ""],
    ["Maior custo", D.length ? curto(Math.max(...D.map((d) => d.total))) : "—", ""], ["Mediana da verba", curto(mediana(D.map((d) => d.verba))), "por deputado no período"]]);
  const seta = (c) => (E.ord[0] === c ? (E.ord[1] < 0 ? " ▼" : " ▲") : "");
  $("#d-tab").innerHTML = `<thead><tr><th>#</th><th data-ord="nome">Deputado${seta("nome")}</th>${COLS.map(([c, t]) => `<th class="num" data-ord="${c}">${t}${seta(c)}</th>`).join("")}</tr></thead><tbody>${
    D.slice(0, E.lim).map((d, i) => `<tr><td>${i + 1}</td><td><a href="#" data-dep="${esc(d.id)}">${esc(d.nome)}</a> <span class="sub">${esc(d.partido || "")}${d.atual === false ? " · fora do mandato" : ""}</span></td>
      <td class="num"><b>${brl(d.total)}</b></td><td class="num">${brl(d.folha)}</td><td class="num">${brl(d.verba)}</td><td class="num prev">${d.prev ? "+" + brl(d.prev) : "—"}</td><td class="num">${nf(d.notas)}</td></tr>`).join("")}</tbody>`;
  $("#d-mais").hidden = D.length <= E.lim;
}
const mediana = (a) => { const s = a.filter((x) => x > 0).sort((x, y) => x - y); return s.length ? s[Math.floor(s.length / 2)] : 0; };

// ---------------------------------------------------------------- fornecedores
async function fornecedores(a) { return (E.forn[a] = E.forn[a] || (await getJSON(`dados/${a}/fornecedores.json`).catch(() => ({ linhas: [] })))); }
async function rFornecedores() {
  const anos = tot() ? E.meta.anos : [E.ano], m = new Map();
  for (const a of anos) { const r = await resumo(a), F = fatorDe(r), f = await fornecedores(a);
    f.linhas.forEach(([doc, nome, tipo, total, notas, deps]) => { const o = m.get(doc) || { doc, nome, tipo, total: 0, notas: 0, deps: 0 };
      o.total += total * F; o.notas += notas; o.deps = Math.max(o.deps, deps); m.set(doc, o); }); }
  const q = semAcento($("#f-q").value.trim());
  const L = [...m.values()].filter((f) => !q || semAcento(f.nome + " " + f.doc).includes(q)).sort((a, b) => b.total - a.total);
  kpis("#f-kpis", [["Fornecedores", nf(L.length), rotAno()], ["Recebido", curto(soma(L.map((f) => f.total))), ""],
    ["Os 10 maiores", L.length ? Math.round(100 * soma(L.slice(0, 10).map((f) => f.total)) / (soma(L.map((f) => f.total)) || 1)) + "%" : "—", "do total da verba"]]);
  $("#f-tab").innerHTML = `<thead><tr><th>#</th><th>Fornecedor</th><th>CNPJ / CPF</th><th class="num">Recebido</th><th class="num">Notas</th><th class="num">Deputados</th></tr></thead><tbody>${
    L.slice(0, E.limF).map((f, i) => `<tr><td>${i + 1}</td><td class="quebra"><a href="#" data-forn="${esc(f.doc)}">${esc(f.nome)}</a></td><td class="mono">${esc(fmtDoc(f.doc))}</td>
      <td class="num"><b>${brl(f.total)}</b></td><td class="num">${nf(f.notas)}</td><td class="num">${nf(f.deps)}</td></tr>`).join("")}</tbody>`;
  $("#f-mais").hidden = L.length <= E.limF;
}
const fmtDoc = (d) => (/^\d{14}$/.test(d) ? d.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})$/, "$1.$2.$3/$4-$5") : d);

// ---------------------------------------------------------------- Assembleia
async function rAssembleia() {
  const anos = tot() ? E.meta.anos : [E.ano], cats = {};
  for (const a of anos) { const r = await resumo(a), F = fatorDe(r), p = E.meta.pessoal_assembleia?.[a] || {};
    Object.entries(p).forEach(([c, x]) => { const o = (cats[c] = cats[c] || { bruta: 0, pessoas: 0 }); o.bruta += x.bruta * F; o.pessoas = Math.max(o.pessoas, x.media_pessoas); }); }
  const L = Object.entries(cats).sort((a, b) => b[1].bruta - a[1].bruta), T = soma(L.map(([, x]) => x.bruta));
  kpis("#a-kpis", [["Folha da Assembleia", curto(T), porExtenso(T)], ["Pessoas na folha (média mensal)", nf(soma(L.map(([, x]) => x.pessoas))), "inclui aposentados e pensionistas"]]);
  const rot = (c) => c.charAt(0) + c.slice(1).toLowerCase();
  $("#a-tab").innerHTML = `<thead><tr><th>Categoria</th><th class="num">Pessoas (média por mês)</th><th class="num">Remuneração bruta</th><th class="num">%</th></tr></thead><tbody>${
    L.map(([c, x]) => `<tr><td class="quebra">${esc(rot(c))}</td><td class="num">${nf(x.pessoas)}</td><td class="num"><b>${brl(x.bruta)}</b></td><td class="num">${nf(100 * x.bruta / (T || 1), 1)}%</td></tr>`).join("")}</tbody>`;
}

// ---------------------------------------------------------------- fichas (mesmo formato das fichas dos deputados federais)
const etqTipo = (t) => (t === "PJ" ? `<span class="etq pj">Empresa</span>` : t === "PF" ? `<span class="etq pf">Pessoa física</span>` : `<span class="etq">sem documento</span>`);
const grupoForn = (doc) => { const d = String(doc || "").replace(/\D/g, ""); return d.length === 14 ? d.slice(0, 2) : "pf"; };
const cacheJ = {};
const jsonC = (u) => (cacheJ[u] = cacheJ[u] || getJSON(u).catch(() => null));
// notas do deputado nos anos pedidos (em paralelo; só anos em que ele usou a verba)
async function notasDe(id, anos) {
  const lotes = await Promise.all(anos.map(async (a) => { const r = await resumo(a), F = fatorDe(r);
    if (!r?.deputados.some((d) => d.id === id && d.notas > 0)) return [];
    return ((await jsonC(`dados/${a}/notas/${encodeURIComponent(id)}.json`)) || []).map((n) => ({ ano: a, mes: n[0], emp: n[1], cat: n[2], doc: n[3], credor: n[4], valor: n[5] * F, desc: n[6] })); }));
  return lotes.flat();
}
function abrirFicha(html) { $("#ficha-corpo").innerHTML = html; $("#ficha").hidden = false; $("#ficha-corpo").scrollTop = 0; $(".ficha-caixa").scrollTop = 0; }
const tabelaNotas = (N, comDep, nomes) => `<div class="tabela-rolagem"><table class="ranking notas-tab"><thead><tr><th>Mês</th>${comDep ? "<th>Deputado</th>" : ""}<th>Tipo</th>${comDep ? "" : "<th>Fornecedor</th>"}<th class="num">Valor</th><th>Detalhe</th></tr></thead><tbody>${
  N.map((n) => `<tr><td class="data">${mesBR(n.mes)}</td>${comDep ? `<td><a href="#" data-dep="${esc(n.dep)}" data-ano="${n.ano}">${esc(nomes[n.dep] || n.dep)}</a></td>` : ""}<td class="quebra sub">${esc(n.cat)}</td>${comDep ? "" : `<td class="quebra">${n.doc ? `<a href="#" data-forn="${esc(n.doc)}">${esc(n.credor)}</a>` : esc(n.credor)}<span class="sub"> ${esc(fmtDoc(n.doc))}</span></td>`}<td class="num ${n.valor < 0 ? "neg" : ""}">${brl(n.valor, 2)}</td><td class="quebra sub">${esc(n.desc)} <span class="mono">${esc(n.emp)}</span></td></tr>`).join("")}</tbody></table></div>`;

async function fichaDeputado(id, anoPedido) {
  const todos = anoPedido == null && tot(), anos = todos ? E.meta.anos : [anoPedido ?? E.ano], rot = todos ? rotAno() : String(anos[0]);
  const rs = await Promise.all(anos.map(resumo));
  // custo de cada ano (para o gráfico e a tabela) e posição no período
  const porAno = rs.filter(Boolean).map((r) => { const F = fatorDe(r), L = r.deputados.filter((x) => x.id !== "nao-identificado").slice().sort((a, b) => b.total - a.total);
    const x = r.deputados.find((y) => y.id === id); return x ? { ano: r.ano, x, F, pos: L.findIndex((y) => y.id === id) + 1, de: L.length } : null; }).filter(Boolean);
  if (!porAno.length) return;
  const D = todos ? await dados() : porAno[0].x ? [{ ...porAno[0].x }] : [];
  const d = todos ? D.find((x) => x.id === id) : (() => { const { x, F } = porAno[0]; return { ...x, folha: x.folha * F, verba: x.verba * F, total: x.total * F, prev: x.previsao?.ativo ? x.previsao.restante * F : 0,
    categorias: Object.fromEntries(Object.entries(x.categorias || {}).map(([k, v]) => [k, v * F])) }; })();
  if (!d) return;
  const Lp = todos ? (await dados()).filter((x) => x.id !== "nao-identificado").sort((a, b) => b.total - a.total) : null;
  const pos = todos ? Lp.findIndex((x) => x.id === id) + 1 : porAno[0].pos, de = todos ? Lp.length : porAno[0].de, caro = pos && pos <= Math.ceil(de / 2);
  const meses = todos ? soma(porAno.map((p) => Math.max(p.x.meses_folha, p.x.meses_verba))) : Math.max(d.meses_folha, d.meses_verba);
  const N = (await notasDe(id, anos)).sort((a, b) => (a.ano * 100 + +String(a.mes).slice(5) < b.ano * 100 + +String(b.mes).slice(5) ? 1 : -1));
  const porForn = {}; N.forEach((n) => { const o = (porForn[n.doc] = porForn[n.doc] || { nome: n.credor, v: 0, n: 0 }); o.v += n.valor; o.n++; });
  const fs = Object.entries(porForn).filter(([k]) => k).sort((a, b) => b[1].v - a[1].v);
  const cats = Object.entries(d.categorias || {}).filter(([, v]) => v > 0).sort((a, b) => b[1] - a[1]);
  const aviso = d.id === "nao-identificado" ? `<p class="aviso-div">A planilha da verba da Assembleia traz estas notas com um nome que não é de nenhum deputado (por exemplo “${esc(Object.values(E.meta?.sem_casar || {}).flat().slice(0, 3).join("”, “"))}”). Mostramos para o dinheiro não sumir da conta; a correção cabe à Assembleia.</p>`
    : d.verba > 0 && !d.folha ? `<p class="aviso-div">Este nome aparece na planilha da verba, mas não encontramos o mesmo nome na folha de pagamento da Assembleia. Por isso o salário não está somado aqui.</p>` : "";
  abrirFicha(`<div class="d-cab">${d.id !== "nao-identificado" ? `<img src="dados/fotos/${esc(d.id)}.jpg" data-alt="${esc(d.foto || "")}" alt="" onerror="if(this.dataset.alt){this.src=this.dataset.alt;this.dataset.alt=''}else{this.style.visibility='hidden'}">` : ""}
      <div><h2>${esc(d.nome)}</h2><div class="sub">${esc(d.partido || "")}${d.nome_completo ? " · " + esc(d.nome_completo) : ""} · ${todos ? `${porAno.length} ano(s) com dados entre ${rot}` : `${meses} ${meses === 1 ? "mês" : "meses"} com dados em ${rot}`}</div>
        ${pos ? `<div class="selo-pos ${caro ? "" : "barato"}">${pos === 1 ? "Deputado estadual mais caro" : caro ? `${pos}º mais caro` : `${de - pos + 1}º mais econômico`} entre ${de} deputados estaduais do Ceará ${todos ? "(soma de todos os anos)" : "em " + rot}</div>` : ""}</div></div>
    ${aviso}
    <div class="sub">${todos ? "Custo somado de todos os anos" : "Custo do mandato em " + rot}${corrigir() ? " (valores de hoje)" : ""}</div>
    <div class="d-total">${brl(d.total, 2)}</div>
    <div class="sub">${meses ? brl(d.total / meses) + " por mês, em média · " : ""}${porExtenso(d.total)}${d.url ? ` · <a href="${esc(d.url)}" target="_blank" rel="noopener">página oficial na Alece</a>` : ""}</div>
    <div class="pecas"><div class="peca" style="--c:#14283F"><div class="rot">Salário (folha bruta)</div><div class="val num">${brl(d.folha)}</div></div>
      <div class="peca" style="--c:#2475B8"><div class="rot">Verba de desempenho parlamentar</div><div class="val num">${brl(d.verba)}</div></div>
      ${d.prev ? `<div class="peca" style="--c:#9c2a6f"><div class="rot">Previsão até dezembro</div><div class="val num">+${brl(d.prev)}</div></div>` : ""}</div>
    <p class="sub"><button class="btn" id="card-dep" type="button">Gerar imagem para compartilhar</button></p>
    <h3 class="d-sec">${todos ? "Custo em cada ano" : "Gasto por mês em " + rot}</h3><div class="canvas-box"><canvas id="g-ficha"></canvas></div>
    ${todos ? `<div class="tabela-rolagem"><table class="ranking"><thead><tr><th>Ano</th><th>Partido</th><th class="num">Custo</th><th class="num">Posição</th><th></th></tr></thead><tbody>${porAno.slice().reverse().map((p) =>
      `<tr><td>${p.ano}</td><td>${esc(p.x.partido || "")}</td><td class="num">${brl(p.x.total * p.F)}</td><td class="num">${p.pos ? `${p.pos}º de ${p.de}` : "—"}</td><td><a href="#" data-dep="${esc(id)}" data-ano="${p.ano}">ver ficha do ano</a></td></tr>`).join("")}</tbody></table></div>` : ""}
    <div class="d-grade2"><div><h3 class="d-sec">Para onde foi a verba</h3><table class="ranking">${cats.map(([k, v]) => `<tr><td class="quebra">${esc(k)}</td><td class="num">${brl(v)}</td></tr>`).join("") || "<tr><td>Sem notas no período</td></tr>"}</table></div>
      <div><h3 class="d-sec">Quem mais recebeu</h3><table class="ranking">${fs.slice(0, 10).map(([doc, f]) => `<tr><td class="quebra"><a href="#" data-forn="${esc(doc)}">${esc(f.nome)}</a><div class="sub">${esc(fmtDoc(doc))}</div></td><td class="num">${brl(f.v)}</td></tr>`).join("") || "<tr><td>—</td></tr>"}</table></div></div>
    <h3 class="d-sec">Todas as notas da verba (${nf(N.length)})</h3>
    ${N.length > 200 ? `<p class="sub"><button class="btn-sec" id="ver-notas" type="button">Mostrar as ${nf(N.length)} notas</button></p><div id="notas-box"></div>` : tabelaNotas(N, false)}
    <p class="dica">Valores negativos são anulações de empenho (dinheiro que voltou). Fonte: Portal da Transparência da Alece.</p>`);
  history.replaceState(null, "", "#dep-" + encodeURIComponent(id));
  if ($("#ver-notas")) $("#ver-notas").onclick = (e) => { e.target.remove(); $("#notas-box").innerHTML = tabelaNotas(N, false); };
  if (todos) grafico("g-ficha", { type: "bar", data: { labels: porAno.map((p) => p.ano), datasets: [{ label: "Salário", data: porAno.map((p) => p.x.folha * p.F), backgroundColor: "#14283F", stack: "s" }, { label: "Verba", data: porAno.map((p) => p.x.verba * p.F), backgroundColor: "#2475B8", stack: "s" }] },
    options: { maintainAspectRatio: false, plugins: { tooltip: tipBRL }, scales: { x: { stacked: true }, y: { stacked: true, ticks: { callback: (v) => curto(v) } } } } });
  else { const x = porAno[0].x, F = porAno[0].F;
    grafico("g-ficha", { type: "bar", data: { labels: MESES, datasets: [{ label: "Salário", data: (x.mensal_folha || []).map((v) => v * F), backgroundColor: "#14283F", stack: "s" }, { label: "Verba", data: (x.mensal_verba || []).map((v) => v * F), backgroundColor: "#2475B8", stack: "s" }] },
      options: { maintainAspectRatio: false, plugins: { tooltip: tipBRL }, scales: { x: { stacked: true }, y: { stacked: true, ticks: { callback: (v) => curto(v) } } } } }); }
  $("#card-dep").onclick = () => {
    const destaques = [];
    if (fs[0]) destaques.push([`Quem mais recebeu da verba: ${fs[0][1].nome}`, `${brl(fs[0][1].v)} · ${fmtDoc(fs[0][0])}`, "#118dff"]);
    if (cats[0]) destaques.push([`Maior gasto da verba: ${cats[0][0]}`, brl(cats[0][1]), "#107c41"]);
    CartaoQC.abrir({
      titulo: `${todos ? `Custo de todos os anos (${rot})` : `Custo do mandato em ${rot}`} · Deputado estadual`,
      nome: d.nome, foto: d.id !== "nao-identificado" ? `dados/fotos/${d.id}.jpg` : "", semFoto: d.id === "nao-identificado",
      linhas: [[d.partido, "Assembleia Legislativa do Ceará"].filter(Boolean).join(" · "), meses ? `${meses} mês(es) com dados${todos ? "" : " em " + rot}` : ""],
      faixa: pos ? { titulo: pos === 1 ? "Deputado estadual mais caro" : caro ? `${pos}º mais caro` : `${de - pos + 1}º mais econômico`, sub: `entre ${de} deputados estaduais do Ceará · ${todos ? "todos os anos" : "em " + rot}`, cor: caro ? "#c4161c" : "#107c41" } : null,
      valorRot: "Custou aos cofres públicos", valor: d.total, valorSub: meses ? `${brl(d.total / meses)} por mês, em média` : "",
      destaques: [...(d.prev ? [[`Previsão: mais ${CartaoQC.compacto(d.prev)} até dezembro`, "salário dos meses que faltam, 13º e verba no ritmo do ano (estimativa)", "#9c2a6f"]] : []), ...destaques],
      composicao: [["Salário (folha)", d.folha, "#14283F"], ["Verba de desempenho parlamentar", d.verba, "#2475B8"]],
      fonte: `Fonte: Assembleia Legislativa do Ceará${corrigir() ? " · valores corrigidos pelo IPCA" : ""} · sem a equipe do gabinete`,
      arquivo: `${semAcento(d.nome).replace(/\W+/g, "-")}-${todos ? "todos-os-anos" : rot}`,
    });
  };
}

async function fichaFornecedor(doc, anoPedido) {
  const todos = anoPedido == null && tot(), anos = todos ? E.meta.anos : [anoPedido ?? E.ano], rot = todos ? rotAno() : String(anos[0]), g = grupoForn(doc);
  abrirFicha(`<p class="sub">Carregando…</p>`);
  const lotes = await Promise.all(anos.map(async (a) => { const r = await resumo(a), F = fatorDe(r), G = await jsonC(`dados/${a}/forn/${g}.json`), f = G?.[doc];
    return f ? { ano: a, F, f } : null; }));
  const L = lotes.filter(Boolean);
  if (!L.length) { abrirFicha(`<p class="sub">Este fornecedor não recebeu da verba em ${rot}.</p>`); return; }
  const D = await Promise.all(anos.map(resumo)), nomes = {}; D.filter(Boolean).forEach((r) => r.deputados.forEach((x) => (nomes[x.id] = x.nome)));
  const N = L.flatMap(({ ano, F, f }) => f.notas.map(([mes, dep, emp, cat, valor, desc]) => ({ ano, mes, dep, emp, cat, valor: valor * F, desc, doc })));
  const info = L[L.length - 1].f, total = soma(N.map((n) => n.valor));
  const porDep = {}; N.forEach((n) => { const o = (porDep[n.dep] = porDep[n.dep] || { v: 0, n: 0 }); o.v += n.valor; o.n++; });
  const cats = {}; N.forEach((n) => (cats[n.cat] = (cats[n.cat] || 0) + n.valor)); const catP = Object.entries(cats).sort((a, b) => b[1] - a[1])[0];
  abrirFicha(`<div class="d-cab"><div><h2>${esc(info.nome)}</h2><div class="sub">${etqTipo(info.tipo)} ${esc(fmtDoc(doc))}${catP ? " · " + esc(catP[0]) : ""}</div></div></div>
    <div class="sub">Recebeu da verba de desempenho parlamentar em ${rot}${corrigir() ? " (valores de hoje)" : ""}</div>
    <div class="d-total">${brl(total, 2)}</div><div class="sub">${porExtenso(total)}</div>
    <div class="percentis" style="margin-top:12px"><div><b>${nf(N.length)}</b>notas</div><div><b>${nf(Object.keys(porDep).length)}</b>deputado(s)</div><div><b>${todos ? nf(L.length) : nf(new Set(N.map((n) => n.mes)).size)}</b>${todos ? "ano(s) recebendo" : "mês(es) recebendo"}</div></div>
    <h3 class="d-sec">${todos ? "Recebido em cada ano" : "Recebido por mês em " + rot}</h3><div class="canvas-box"><canvas id="g-forn"></canvas></div>
    <h3 class="d-sec">Por deputado</h3><div class="tabela-rolagem"><table class="ranking"><thead><tr><th>Deputado</th><th class="num">Recebido</th><th class="num">%</th><th class="num">Notas</th></tr></thead><tbody>${
      Object.entries(porDep).sort((a, b) => b[1].v - a[1].v).map(([id, o]) => `<tr><td><a href="#" data-dep="${esc(id)}">${esc(nomes[id] || id)}</a></td><td class="num"><b>${brl(o.v)}</b></td><td class="num">${nf(100 * o.v / (total || 1), 1)}%</td><td class="num">${o.n}</td></tr>`).join("")}</tbody></table></div>
    <h3 class="d-sec">Notas (${nf(N.length)})</h3>${tabelaNotas(N, true, nomes)}
    <p class="dica">${info.tipo === "PF" ? "Pessoa física: o CPF aparece mascarado. " : ""}Valores negativos são anulações de empenho. Fonte: Portal da Transparência da Alece.</p>`);
  history.replaceState(null, "", "#forn-" + encodeURIComponent(doc));
  const serie = todos ? L.map(({ ano, F, f }) => [String(ano), soma(f.notas.map((n) => n[4])) * F])
    : MESES.map((m, i) => [m, soma(N.filter((n) => +String(n.mes).slice(5) === i + 1).map((n) => n.valor))]);
  grafico("g-forn", { type: "bar", data: { labels: serie.map((s) => s[0]), datasets: [{ data: serie.map((s) => s[1]), backgroundColor: "#2475B8" }] },
    options: { maintainAspectRatio: false, plugins: { legend: { display: false }, tooltip: tipBRL }, scales: { y: { ticks: { callback: (v) => curto(v) } } } } });
}

// ---------------------------------------------------------------- navegação
async function render() {
  try { await ({ inicio: rInicio, deputados: rDeputados, fornecedores: rFornecedores, assembleia: rAssembleia, metodo: rMetodo })[E.pag](); }
  catch (e) { console.error(e); }
}
async function rMetodo() {
  const M = E.meta?.meses || {}, rec = Object.values(M), n = soma(rec.map((x) => x.recusadas)), v = soma(rec.map((x) => x.recusadas_valor));
  const vazios = Object.entries(M).filter(([, x]) => !x.verba).map(([k]) => mesBR(k));
  const semCasar = Object.entries(E.meta?.sem_casar || {}).filter(([, l]) => l.length).map(([a, l]) => `${a}: ${l.map((x) => `“${x}”`).join(", ")}`);
  const soVerba = [];
  for (const a of E.meta?.anos || []) { const r = await resumo(a); (r?.deputados || []).forEach((d) => { if (d.verba > 0 && !d.folha && d.id !== "nao-identificado") soVerba.push(`${d.nome} (${a})`); }); }
  $("#m-recusadas").innerHTML = `<b>Divergências encontradas nos dados da Assembleia</b> (avisamos sempre que a informação falta ou não fecha):<ul>
    <li>${nf(n)} linha(s) do arquivo da verba não eram de um deputado e ficaram de fora (${brl(v, 2)}), em ${nf(rec.length)} mês(es) baixados.</li>
    ${semCasar.length ? `<li>Nomes na planilha da verba que não são de nenhum deputado identificável, somados em “Nome não identificado na planilha”: ${esc(semCasar.join(" · "))}.</li>` : ""}
    ${soVerba.length ? `<li>Aparecem na verba com um nome que não encontramos na folha de pagamento, por isso sem salário ligado: ${esc(soVerba.join(", "))}.</li>` : ""}
    ${vazios.length ? `<li>Meses ainda sem notas da verba publicadas pela Assembleia: ${esc(vazios.join(", "))}.</li>` : ""}</ul>`;
}
function irPara(p) {
  E.pag = p; $$(".pagina").forEach((s) => s.classList.toggle("ativa", s.dataset.pag === p));
  $$(".menu nav button").forEach((b) => (b.dataset.pag === p ? b.setAttribute("aria-current", "page") : b.removeAttribute("aria-current")));
  $("#menu").classList.remove("aberto"); $("#veu").hidden = true;
  const u = new URL(location); u.searchParams.set("ano", E.ano); u.hash = p; history.replaceState(null, "", u);
  render(); window.scrollTo(0, 0);
}
async function iniciar() {
  try { E.meta = await getJSON("dados/meta.json"); } catch { $("#aviso").hidden = false; $("#aviso").textContent = "Os dados ainda estão sendo coletados pelo robô. Volte em algumas horas."; irPara("metodo"); return; }
  const anos = E.meta.anos.slice().reverse();
  const pedido = new URL(location).searchParams.get("ano");
  E.ano = pedido && (pedido === "total" || anos.includes(+pedido)) ? (pedido === "total" ? "total" : +pedido) : anos[0];
  $("#f-ano").innerHTML = `<option value="total">Todos os anos</option>` + anos.map((a) => `<option value="${a}">${a}</option>`).join("");
  $("#f-ano").value = E.ano;
  if (E.meta.ipca?.referencia) $("#ipca-ref").textContent = `IPCA até ${E.meta.ipca.referencia}`;
  $("#atualizado").textContent = `Atualizado em ${new Date(E.meta.gerado_em).toLocaleString("pt-BR")}`;
  const todos = (await Promise.all(anos.map(resumo))).filter(Boolean).flatMap((r) => r.deputados);
  $("#f-partido").innerHTML = `<option value="">Todos</option>` + [...new Set(todos.map((d) => d.partido).filter(Boolean))].sort().map((u) => `<option>${esc(u)}</option>`).join("");
  const h = location.hash.slice(1), md = h.match(/^dep-(.+)$/), mf = h.match(/^forn-(.+)$/);
  irPara(md ? "deputados" : mf ? "fornecedores" : ["inicio", "deputados", "fornecedores", "assembleia", "metodo"].includes(h) ? h : "inicio");
  if (md) fichaDeputado(decodeURIComponent(md[1]));
  if (mf) fichaFornecedor(decodeURIComponent(mf[1]));
}
document.addEventListener("click", (e) => {
  const d = e.target.closest("[data-dep]"); if (d) { e.preventDefault(); fichaDeputado(d.dataset.dep, d.dataset.ano ? +d.dataset.ano : undefined); return; }
  const f = e.target.closest("[data-forn]"); if (f) { e.preventDefault(); fichaFornecedor(f.dataset.forn); return; }
  const o = e.target.closest("#d-tab th[data-ord]"); if (o) { const k = o.dataset.ord; E.ord = [k, E.ord[0] === k ? -E.ord[1] : -1]; rDeputados(); return; }
  const b = e.target.closest(".menu nav button"); if (b) irPara(b.dataset.pag);
});
$("#f-ano").onchange = (e) => { E.ano = e.target.value === "total" ? "total" : +e.target.value; irPara(E.pag); };
["#f-partido", "#f-ipca"].forEach((k) => ($(k).onchange = () => { E.lim = 30; E.limF = 50; render(); }));
$("#f-busca").oninput = () => { E.lim = 30; render(); };
$("#f-q").oninput = () => { E.limF = 50; rFornecedores(); };
$("#d-mais").onclick = () => { E.lim += 50; rDeputados(); };
$("#f-mais").onclick = () => { E.limF += 100; rFornecedores(); };
$("#ficha-fechar").onclick = () => ($("#ficha").hidden = true);
$("#ficha").onclick = (e) => { if (e.target.id === "ficha") $("#ficha").hidden = true; };
$("#abrir-menu").onclick = () => { $("#menu").classList.add("aberto"); $("#veu").hidden = false; };
$("#veu").onclick = () => { $("#menu").classList.remove("aberto"); $("#veu").hidden = true; };
iniciar();
})();
