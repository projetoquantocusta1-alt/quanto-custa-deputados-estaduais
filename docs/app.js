/* Projeto Quanto Custa — Deputados estaduais (Ceará / Alece) */
(() => {
"use strict";
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"];
const E = { meta: null, ano: null, pag: "inicio", res: {}, forn: {}, ord: ["total", -1], lim: 30, limF: 50, graf: {} };
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
  $("#i-total").textContent = brl(T);
  $("#i-ext").textContent = porExtenso(T);
  $("#i-nota").textContent = `${corrigir() ? "Em valores de hoje (IPCA). " : ""}Salário bruto (folha) + verba de desempenho parlamentar. Não inclui a equipe do gabinete${ult ? ` · dados até ${mesBR(ult)}` : ""}.`;
  const folha = soma(D.map((d) => d.folha)), verba = soma(D.map((d) => d.verba));
  const comVerba = D.filter((d) => d.meses_verba), mesesV = soma(comVerba.map((d) => d.meses_verba));
  kpis("#i-kpis", [["Salários (folha bruta)", curto(folha), porExtenso(folha)], ["Verba (VDP)", curto(verba), porExtenso(verba)],
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
const COLS = [["total", "Custo total"], ["folha", "Salário (folha)"], ["verba", "Verba (VDP)"], ["notas", "Notas"]];
async function rDeputados() {
  const D = (await dados()).filter(passa);
  const [k, s] = E.ord; D.sort((a, b) => (k === "nome" ? a.nome.localeCompare(b.nome) * -s : (a[k] - b[k]) * s));
  kpis("#d-kpis", [["Deputados", nf(D.length), rotAno()], ["Custo total", curto(soma(D.map((d) => d.total))), ""],
    ["Maior custo", D.length ? curto(Math.max(...D.map((d) => d.total))) : "—", ""], ["Mediana da verba", curto(mediana(D.map((d) => d.verba))), "por deputado no período"]]);
  const seta = (c) => (E.ord[0] === c ? (E.ord[1] < 0 ? " ▼" : " ▲") : "");
  $("#d-tab").innerHTML = `<thead><tr><th>#</th><th data-ord="nome">Deputado${seta("nome")}</th>${COLS.map(([c, t]) => `<th class="num" data-ord="${c}">${t}${seta(c)}</th>`).join("")}</tr></thead><tbody>${
    D.slice(0, E.lim).map((d, i) => `<tr><td>${i + 1}</td><td><a href="#" data-dep="${esc(d.id)}">${esc(d.nome)}</a> <span class="sub">${esc(d.partido || "")}${d.atual === false ? " · fora do mandato" : ""}</span></td>
      <td class="num"><b>${brl(d.total)}</b></td><td class="num">${brl(d.folha)}</td><td class="num">${brl(d.verba)}</td><td class="num">${nf(d.notas)}</td></tr>`).join("")}</tbody>`;
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

// ---------------------------------------------------------------- fichas
async function notasDe(id) {
  const anos = tot() ? E.meta.anos : [E.ano], out = [];
  for (const a of anos) { const r = await resumo(a), F = fatorDe(r);
    if (!r?.deputados.some((d) => d.id === id && d.notas > 0)) continue;   // quem não usou a verba não tem arquivo de notas
    (await getJSON(`dados/${a}/notas/${encodeURIComponent(id)}.json`).catch(() => [])).forEach((n) => out.push({ mes: n[0], emp: n[1], cat: n[2], doc: n[3], credor: n[4], valor: n[5] * F, desc: n[6] })); }
  return out;
}
async function fichaDeputado(id) {
  const d = (await dados()).find((x) => x.id === id); if (!d) return;
  const N = (await notasDe(id)).sort((a, b) => (a.mes < b.mes ? 1 : -1));
  const cats = Object.entries(d.categorias).filter(([, v]) => v > 0).sort((a, b) => b[1] - a[1]);
  const porForn = {}; N.forEach((n) => { const o = (porForn[n.doc] = porForn[n.doc] || { nome: n.credor, v: 0, n: 0 }); o.v += n.valor; o.n++; });
  const fs = Object.entries(porForn).sort((a, b) => b[1].v - a[1].v).slice(0, 10);
  $("#ficha-corpo").innerHTML = `<div class="ficha-cab">${foto(d)}<div><h2>${esc(d.nome)}</h2><p class="sub">${esc(d.partido || "")}${d.nome_completo ? " · " + esc(d.nome_completo) : ""}${d.situacao ? " · " + esc(d.situacao.toLowerCase()) : ""}</p>
    ${d.url ? `<p class="sub"><a href="${esc(d.url)}" target="_blank" rel="noopener">Página oficial na Alece</a></p>` : ""}</div></div>
    <div class="kpis">${[["Custo total", brl(d.total), rotAno()], ["Salário (folha bruta)", brl(d.folha), `${d.meses_folha} mês(es) na folha`], ["Verba (VDP)", brl(d.verba), `${d.meses_verba} mês(es) com notas`]]
      .map(([r, v, o]) => `<div class="kpi"><div class="rot">${r}</div><div class="val num">${v}</div><div class="obs">${o}</div></div>`).join("")}</div>
    <div class="d-grade2"><div><h3 class="d-sec">Para onde foi a verba</h3><table class="ranking">${cats.map(([k, v]) => `<tr><td>${esc(k)}</td><td class="num">${brl(v)}</td></tr>`).join("") || "<tr><td>Sem notas no período</td></tr>"}</table></div>
      <div><h3 class="d-sec">Quem mais recebeu</h3><table class="ranking">${fs.map(([doc, f]) => `<tr><td class="quebra"><a href="#" data-forn="${esc(doc)}">${esc(f.nome)}</a></td><td class="num">${brl(f.v)}</td></tr>`).join("") || "<tr><td>—</td></tr>"}</table></div></div>
    <h3 class="d-sec">Todas as notas da verba (${nf(N.length)})</h3>
    <div class="tabela-rolagem"><table class="ranking notas-tab"><thead><tr><th>Mês</th><th>Tipo</th><th>Fornecedor</th><th class="num">Valor</th><th>Detalhe</th></tr></thead><tbody>${
      N.map((n) => `<tr><td class="data">${mesBR(n.mes)}</td><td>${esc(n.cat)}</td><td class="quebra">${esc(n.credor)}<span class="sub"> ${esc(fmtDoc(n.doc))}</span></td><td class="num ${n.valor < 0 ? "neg" : ""}">${brl(n.valor, 2)}</td><td class="quebra sub">${esc(n.desc)} <span class="mono">${esc(n.emp)}</span></td></tr>`).join("")}</tbody></table></div>
    <p class="dica">Valores negativos são anulações de empenho (dinheiro que voltou). Fonte: Portal da Transparência da Alece.</p>`;
  $("#ficha").hidden = false; history.replaceState(null, "", "#dep-" + encodeURIComponent(id));
}
async function fichaFornecedor(doc) {
  const anos = tot() ? E.meta.anos : [E.ano], L = [];
  const D = await dados(), nomes = Object.fromEntries(D.map((d) => [d.id, d.nome]));
  for (const id of D.map((d) => d.id)) for (const n of await notasDe(id)) if (n.doc === doc) L.push({ ...n, dep: id });
  if (!L.length) return;
  L.sort((a, b) => (a.mes < b.mes ? 1 : -1));
  const porDep = {}; L.forEach((n) => (porDep[n.dep] = (porDep[n.dep] || 0) + n.valor));
  $("#ficha-corpo").innerHTML = `<div class="ficha-cab"><div><h2>${esc(L[0].credor)}</h2><p class="sub mono">${esc(fmtDoc(doc))}</p></div></div>
    <div class="kpis"><div class="kpi"><div class="rot">Recebido da verba</div><div class="val num">${brl(soma(L.map((n) => n.valor)))}</div><div class="obs">${rotAno()} · ${nf(L.length)} notas</div></div></div>
    <h3 class="d-sec">Por deputado</h3><table class="ranking">${Object.entries(porDep).sort((a, b) => b[1] - a[1]).map(([id, v]) => `<tr><td><a href="#" data-dep="${esc(id)}">${esc(nomes[id] || id)}</a></td><td class="num">${brl(v, 2)}</td></tr>`).join("")}</table>
    <h3 class="d-sec">Notas</h3><div class="tabela-rolagem"><table class="ranking notas-tab"><thead><tr><th>Mês</th><th>Deputado</th><th class="num">Valor</th><th>Detalhe</th></tr></thead><tbody>${
      L.map((n) => `<tr><td class="data">${mesBR(n.mes)}</td><td>${esc(nomes[n.dep] || n.dep)}</td><td class="num">${brl(n.valor, 2)}</td><td class="quebra sub">${esc(n.desc)}</td></tr>`).join("")}</tbody></table></div>`;
  $("#ficha").hidden = false; history.replaceState(null, "", "#forn-" + encodeURIComponent(doc));
}

// ---------------------------------------------------------------- navegação
async function render() {
  try { await ({ inicio: rInicio, deputados: rDeputados, fornecedores: rFornecedores, assembleia: rAssembleia, metodo: rMetodo })[E.pag](); }
  catch (e) { console.error(e); }
}
async function rMetodo() {
  const M = E.meta?.meses || {}, rec = Object.values(M), n = soma(rec.map((x) => x.recusadas)), v = soma(rec.map((x) => x.recusadas_valor));
  const vazios = Object.entries(M).filter(([, x]) => !x.verba).map(([k]) => mesBR(k));
  $("#m-recusadas").innerHTML = `<b>Conferência</b>: ${nf(n)} linha(s) recusadas no arquivo da verba (${brl(v, 2)}), de ${nf(rec.length)} mês(es) baixados.${vazios.length ? ` Meses ainda sem notas publicadas: ${esc(vazios.join(", "))}.` : ""}`;
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
  const d = e.target.closest("[data-dep]"); if (d) { e.preventDefault(); fichaDeputado(d.dataset.dep); return; }
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
