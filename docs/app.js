// Mapa interativo: enchente de 2024 × voto para presidente na Grande Porto Alegre.
// Dados em dados/*.json, gerados por scripts/13_exportar_web.py. Sem build: Leaflet via cdnjs.
// O painel conta a história em cinco passos (2018, 2022, a enchente, 2026, o que mudou); um cartão à parte, com o
// gráfico das duas linhas, alagados × restante, avança junto com o mapa e carrega a comparação.
(() => {
  const PADRAO = { passo: "1", un: "pontos", mancha: null, sim: "0", dest: "1", mun: "", local: "" };
  const ABAS = {
    "26": { campo: "m26", tit: "Diferença Lula (PT) − Flávio Bolsonaro (PL) em 2026, em pontos percentuais" },
    "22": { campo: "m22", tit: "Diferença Lula (PT) − Jair Bolsonaro (PL) em 2022, em pontos percentuais" },
    "18": { campo: "m18", tit: "Diferença Haddad (PT) − Jair Bolsonaro (PSL) em 2018, em pontos percentuais" },
    mud: { campo: "mud", tit: "Mudança na diferença PT − PL de 2022 para 2026, em pontos" },
  };
  // anos: quantas eleições o gráfico já mostra; mancha: se a área alagada começa ligada
  const PASSOS = {
    "1": { aba: "18", anos: 1, mancha: "0" },
    "2": { aba: "22", anos: 2, mancha: "0" },
    "3": { aba: "22", anos: 2, mancha: "1" },
    "4": { aba: "26", anos: 3, mancha: "1" },
    "5": { aba: "mud", anos: 3, mancha: "1" },
  };
  const COR_VAZIO = "#a9a59c";
  const RMAX = 8; // raio do maior local no zoom 10, em px

  // ---------- estado na URL (#passo=5&mun=4314902&local=812) ----------
  const estado = { ...PADRAO };
  const params = new URLSearchParams(location.hash.slice(1));
  for (const k of Object.keys(PADRAO)) if (params.has(k)) estado[k] = params.get(k);
  if (!params.has("passo") && params.has("aba")) estado.passo = { 18: "1", 22: "2", 26: "4", mud: "5" }[params.get("aba")] || "1";
  if (!PASSOS[estado.passo]) estado.passo = PADRAO.passo;
  if (estado.mancha == null) estado.mancha = PASSOS[estado.passo].mancha;
  const aba = () => PASSOS[estado.passo].aba;
  const padrao = (k) => (k === "mancha" ? PASSOS[estado.passo].mancha : PADRAO[k]);

  function gravarHash() {
    const p = new URLSearchParams();
    for (const [k, v] of Object.entries(estado)) if (v !== padrao(k)) p.set(k, v);
    history.replaceState(null, "", p.toString() ? "#" + p : location.pathname + location.search);
  }

  // ---------- números ----------
  const fmt1 = (x) => x.toLocaleString("pt-BR", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  const sinal = (x) => (x == null ? "—" : (x > 0 ? "+" : x < 0 ? "−" : "") + fmt1(Math.abs(x)));
  const pct = (x) => fmt1(x) + "%";
  const mil = (n) => n.toLocaleString("pt-BR");
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);

  let meta, resumo;
  const classe = (x, cortes) => cortes.filter((c) => x >= c).length; // = np.digitize
  function cor(p) {
    const x = p[ABAS[aba()].campo];
    if (x == null) return null;
    const mud = aba() === "mud";
    const cl = mud ? meta.classes_mud : meta.classes;
    return cl[cl.length - 1 - classe(x, mud ? meta.cortes_mud : meta.cortes)].cor; // legenda vai da classe 4 à 0
  }
  // destaque: os locais alagados ganham contorno escuro e os outros só ficam apagados, nunca somem, para os dois
  // lados da comparação continuarem no mapa
  function estilo(p, area = false) {
    const c = cor(p);
    const s = c ? { color: meta.cor.fundo, weight: area ? 0.3 : 0.6, opacity: 1, fillColor: c, fillOpacity: area ? 0.85 : 0.92 }
      : { color: COR_VAZIO, weight: area ? 0.5 : 1.2, opacity: 1, fillOpacity: 0 };
    if (estado.dest !== "1") return s;
    if (!p.ada) return { ...s, opacity: 0.5, fillOpacity: s.fillOpacity && 0.5 };
    return { ...s, color: meta.cor.texto, weight: area ? 1.2 : 1.6 };
  }

  // ---------- mapa ----------
  const mapa = L.map("mapa", { zoomControl: false, minZoom: 8, maxZoom: 17 });
  L.control.zoom({ position: "topright" }).addTo(mapa);
  // volta à área de interesse: limpa o município escolhido e enquadra os locais de votação
  const Centralizar = L.Control.extend({
    options: { position: "topright" },
    onAdd() {
      const b = L.DomUtil.create("button", "btn-centro");
      b.type = "button";
      b.title = "Centralizar na Grande Porto Alegre";
      b.innerHTML = '<svg viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="5" fill="none" stroke="currentColor" ' +
        'stroke-width="1.6"/><circle cx="8" cy="8" r="1.8" fill="currentColor"/><path d="M8 0v3M8 13v3M0 8h3M13 8h3" ' +
        'stroke="currentColor" stroke-width="1.6"/></svg><span>Grande Porto Alegre</span>';
      L.DomEvent.disableClickPropagation(b);
      b.onclick = () => {
        if (!camMun) return;
        estado.mun = "";
        document.getElementById("mun").value = "";
        camMun.setStyle(estiloMun);
        mapa.closePopup();
        enquadrar();
        gravarHash();
      };
      return b;
    },
  });
  new Centralizar().addTo(mapa);
  mapa.attributionControl.setPrefix('<a href="https://leafletjs.com" target="_blank" rel="noopener">Leaflet</a>');
  const ESRI = "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/";
  L.tileLayer(ESRI + "World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}", {
    maxZoom: 16, maxNativeZoom: 16,
    attribution: "Mapa-base © Esri, HERE, Garmin, © OpenStreetMap · Votos: TSE · Área alagada: UFRGS/IPH (CC BY 4.0, simplificada)",
  }).addTo(mapa);
  mapa.createPane("rotulos").style.zIndex = 450;
  mapa.getPane("rotulos").style.pointerEvents = "none";
  L.tileLayer(ESRI + "World_Light_Gray_Reference/MapServer/tile/{z}/{y}/{x}", { maxZoom: 16, maxNativeZoom: 16, pane: "rotulos" })
    .addTo(mapa);

  for (const [nome, z] of [["areas", 405], ["mun", 410], ["mancha", 415], ["pontos", 420]]) mapa.createPane(nome).style.zIndex = z;
  const tela = (pane) => L.canvas({ pane, padding: 0.5, tolerance: pane === "pontos" ? 6 : 0 });
  const telaPontos = tela("pontos"), telaAreas = tela("areas"), telaMancha = tela("mancha"), telaMun = tela("mun");

  let pontos = [], vmax = 1, balao, camMancha, camSim, camMun, camAreas, porPid = new Map(), munBounds = new Map();

  // cresce com o zoom, mas mais devagar que o mapa, para os locais do centro não se cobrirem
  const raio = (v) => Math.max(1.5, Math.min(20, Math.sqrt(v / vmax) * RMAX * Math.pow(1.3, mapa.getZoom() - 10)));

  function popup(p) {
    const tag = p.ada
      ? `<span class="tag ada">Dentro da área alagada${p.f > 0 ? ` · ${Math.round(100 * p.f)}% do entorno` : ""}</span>`
      : `<span class="tag">Fora da área alagada${p.f >= 0.05 ? ` · ${Math.round(100 * p.f)}% do entorno` : ""}</span>`;
    const lugar = [p.bairro, p.mun].filter(Boolean).map(esc).join(" · ");
    const sim = p.p530 ? '<p class="nota">Dentro da simulação do Guaíba a 5,30 m.</p>' : "";
    // a linha do valor que está pintado no mapa agora (no passo da enchente, o mapa ainda é 2022)
    const linha = (chave, rot, val, cls = "") => {
      const agora = aba() === chave;
      return `<tr class="${cls}${agora ? " agora" : ""}"><th>${rot}${agora ? ' <span class="no-mapa">no mapa</span>' : ""}</th>
        <td>${sinal(val)}</td></tr>`;
    };
    return `<div class="pop"><h3>${esc(p.nome)}</h3><p class="lugar">${lugar}</p>${tag}
      <table>
        ${linha("18", "PT − PSL, 2018", p.m18)}
        ${linha("22", "PT − PL, 2022", p.m22)}
        ${linha("26", "PT − PL, 2026", p.m26)}
        ${linha("mud", "Mudança 2022 → 2026", p.mud, "soma")}
      </table>
      <p>2026: Lula ${pct(p.lula)} · Flávio Bolsonaro ${pct(p.flavio)} · ${mil(p.v26)} votos válidos</p>
      ${sim}<p class="nota">Pontos percentuais dos votos válidos, nas mesmas seções eleitorais.</p></div>`;
  }

  function abrirLocal(pid, centralizar) {
    const m = porPid.get(pid);
    if (!m) return;
    if (centralizar) mapa.setView(m.getLatLng(), Math.max(mapa.getZoom(), 14));
    balao = L.popup({ maxWidth: 290, autoPanPadding: [20, 20] }).setLatLng(m.getLatLng()).setContent(popup(m.p)).openOn(mapa);
    estado.local = String(pid);
    gravarHash();
  }
  mapa.on("popupclose", () => { estado.local = ""; gravarHash(); });

  function desenharPontos() {
    const setas = aba() === "mud";
    if (setas) desenharSetas(); else esconderSetas();
    const visiveis = estado.un === "pontos" && !setas;
    for (const m of pontos) m.remove(); // readiciona na ordem original: do maior para o menor
    if (!visiveis) return;
    for (const m of pontos) {
      m.setStyle(estilo(m.p));
      m.setRadius(raio(m.p.v26));
      m.addTo(mapa);
    }
    if (estado.dest === "1") for (const m of pontos) if (m.p.ada) m.bringToFront();
  }
  mapa.on("zoomend", () => { if (estado.un === "pontos") for (const m of pontos) m.setRadius(raio(m.p.v26)); });

  // ---------- passo "Mudança": setas de deslocamento ----------
  // Na mudança, cor de partido parecia dizer quem ganhou. Cada local vira uma seta que aponta para onde o voto andou
  // (→ PL, ← PT): três tamanhos só e uma cor por direção; com o destaque, alagados fortes e o resto apagado.
  // Escolhida em protótipo (branch prototipo/setas-mudanca) contra setas de comprimento contínuo e transição de cor.
  const SETA = { incl: (35 * Math.PI) / 180, tam: [7, 13, 21], pt: "#d4574a", pl: "#3f74c2", celula: 14, tudo: 10 };
  const faixaSeta = (v) => (Math.abs(v) < 4 ? 0 : Math.abs(v) < 10 ? 1 : 2); // até 4, 4 a 10, mais de 10 pontos
  let telaSetas, ctxSetas, setasNoMapa = [];

  // Com o zoom baixo (celular) os 1.239 locais não cabem: as setas viram uma mancha. Abaixo do zoom SETA.tudo a tela só
  // comporta uma seta por célula de SETA.celula px, e a grade se desfaz até o zoom SETA.tudo, de onde todas aparecem.
  // A célula é por grupo (alagado ou não, com o destaque ligado) e por direção, então nenhum dos dois grupos some e o
  // PT, que é pouco e concentrado no centro, não é engolido pelos vizinhos azuis. A seta de cada célula é a do maior
  // local (uma seta real, com popup); a média ponderada da célula foi testada e ficava praticamente igual.

  function agruparSetas() {
    const c = SETA.celula * Math.max(0, Math.min(1, SETA.tudo - mapa.getZoom()));
    const dest = estado.dest === "1", celulas = new Map(), lista = [];
    for (const m of pontos) { // do maior para o menor: o primeiro de cada célula é o de mais votos
      const p = m.p, { x, y } = mapa.latLngToContainerPoint(m.getLatLng()), seta = { x, y, mud: p.mud, ada: p.ada, p };
      if (c < 3) { lista.push(seta); continue; }
      const q = mapa.project(m.getLatLng()); // pixels do mundo: a grade fica parada quando o mapa é arrastado
      const dir = p.mud == null ? 2 : p.mud < 0 ? 1 : 0;
      const chave = `${Math.floor(q.x / c)},${Math.floor(q.y / c)},${dest && p.ada ? 1 : 0},${dir}`;
      if (!celulas.has(chave)) { celulas.set(chave, seta); lista.push(seta); }
    }
    return lista;
  }

  function caminhoSeta(x, y, dir, L) {
    const x2 = x + dir * L * Math.cos(SETA.incl), y2 = y - L * Math.sin(SETA.incl);
    const ang = Math.atan2(y2 - y, x2 - x), cab = Math.min(7, 2.5 + L * 0.3);
    return [[x, y, x2, y2], ...[-0.5, 0.5].map((a) => [x2, y2, x2 - cab * Math.cos(ang + a), y2 - cab * Math.sin(ang + a)])];
  }

  function desenharSetas() {
    if (!telaSetas) {
      telaSetas = L.DomUtil.create("canvas", "", mapa.getPane("pontos"));
      telaSetas.style.pointerEvents = "none";
      ctxSetas = telaSetas.getContext("2d");
    }
    const tam = mapa.getSize(), dpr = window.devicePixelRatio || 1, ctx = ctxSetas;
    L.DomUtil.setPosition(telaSetas, mapa.containerPointToLayerPoint([0, 0]));
    telaSetas.width = tam.x * dpr; telaSetas.height = tam.y * dpr;
    telaSetas.style.width = tam.x + "px"; telaSetas.style.height = tam.y + "px";
    telaSetas.style.display = "";
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.lineCap = "round";
    const esc = Math.max(0.8, Math.min(2.2, Math.pow(1.25, mapa.getZoom() - 10)));
    const dest = estado.dest === "1";
    setasNoMapa = agruparSetas();
    for (const alagado of [false, true]) { // os de fora primeiro, os alagados por cima
      for (const { x, y, mud, ada } of setasNoMapa) {
        if (ada !== alagado) continue;
        ctx.globalAlpha = dest && !ada ? 0.3 : 1;
        if (mud == null) { // sem comparação: um círculo vazio, como nos outros passos
          ctx.strokeStyle = COR_VAZIO; ctx.lineWidth = 1.2;
          ctx.beginPath(); ctx.arc(x, y, 3, 0, 2 * Math.PI); ctx.stroke();
          continue;
        }
        ctx.strokeStyle = mud < 0 ? SETA.pl : SETA.pt; // PT − PL caiu → andou para o PL → seta para a direita
        ctx.lineWidth = dest && ada ? 2.2 : 1.5;
        ctx.beginPath();
        for (const [a, b, c, d] of caminhoSeta(x, y, mud < 0 ? 1 : -1, SETA.tam[faixaSeta(mud)] * esc)) {
          ctx.moveTo(a, b); ctx.lineTo(c, d);
        }
        ctx.stroke();
      }
    }
    ctx.globalAlpha = 1;
  }
  const esconderSetas = () => { if (telaSetas) telaSetas.style.display = "none"; };
  mapa.on("moveend zoomend resize", () => { if (aba() === "mud") desenharSetas(); });
  mapa.on("zoomstart", esconderSetas);
  // as setas ficam num canvas sem clique: o clique perto da base de uma abre o popup do local
  mapa.on("click", (e) => {
    if (aba() !== "mud") return;
    let melhor = null, dmin = 12;
    for (const s of setasNoMapa) { // só as que estão desenhadas
      const d = L.point(s.x, s.y).distanceTo(e.containerPoint);
      if (d < dmin) { dmin = d; melhor = s; }
    }
    if (melhor) abrirLocal(melhor.p.pid, false);
  });

  // seta pequena em SVG para a legenda, com o mesmo desenho do mapa
  function svgSeta(dir, cor, L, opac = 1, larg = 2) {
    const d = caminhoSeta(dir > 0 ? 4 : 30, 18, dir, L).map(([a, b, c, e]) => `M${a},${b}L${c},${e}`).join("");
    return `<svg width="34" height="22" viewBox="0 0 34 22" aria-hidden="true" style="opacity:${opac}">` +
      `<path d="${d}" stroke="${cor}" stroke-width="${larg}" fill="none" stroke-linecap="round"/></svg>`;
  }

  async function garantirAreas() {
    if (camAreas) return camAreas;
    const g = await baixar("areas.json");
    camAreas = L.geoJSON(g, {
      pane: "areas", renderer: telaAreas,
      style: (f) => estilo(porPid.get(f.properties.pid).p, true),
      onEachFeature: (f, l) => l.on("click", () => abrirLocal(f.properties.pid, false)),
    });
    return camAreas;
  }
  async function desenharAreas() {
    if (estado.un !== "areas" || aba() === "mud") { if (camAreas) camAreas.remove(); return; }
    const c = await garantirAreas();
    c.setStyle((f) => estilo(porPid.get(f.properties.pid).p, true));
    if (!mapa.hasLayer(c)) c.addTo(mapa);
    if (estado.dest === "1") c.eachLayer((l) => { if (porPid.get(l.feature.properties.pid).p.ada) l.bringToFront(); });
  }

  async function desenharSim() {
    if (estado.sim !== "1") { if (camSim) camSim.remove(); return; }
    if (!camSim) camSim = L.geoJSON(await baixar("mancha_poa530.json"), {
      pane: "mancha", renderer: telaMancha, interactive: false,
      style: { color: "#075f6c", weight: 1, dashArray: "4 3", fillColor: "#0a8fa3", fillOpacity: 0.22 },
    });
    camSim.addTo(mapa);
  }

  // ---------- os cinco passos ----------
  function textoPasso() {
    const [d, f] = [resumo.linhas.dentro, resumo.linhas.fora];
    const dist = (i) => sinal(d[i] - f[i]);
    const D = resumo.dentro, F = resumo.fora, [a, b] = resumo.ic_mud;
    return {
      "1": ["2018, antes da enchente",
        `Haddad (PT) contra Jair Bolsonaro (PSL). Os locais que a água atingiria em 2024 (contorno escuro) já votavam
        um pouco mais no PT que o resto: ${dist(0)} pontos de distância.`],
      "2": ["2022, antes da enchente",
        `Lula (PT) contra Jair Bolsonaro (PL). A região inteira foi para o PT, e as duas linhas subiram juntas.
        A distância ficou em ${dist(1)} pontos.`],
      "3": ["Maio de 2024: a enchente",
        `A água cobre ${D.locais} locais de votação, onde votam ${mil(Math.round(D.aptos / 1000))} mil eleitores.
        No mapa, o voto de 2022, a última eleição antes dela.`],
      "4": ["2026, depois da enchente",
        `Lula (PT) contra Flávio Bolsonaro (PL). A região inteira foi para o PL, e as linhas desceram juntas.
        A distância ficou em ${dist(2)} pontos, perto da de antes da água.`],
      "5": ["O que mudou de 2022 para 2026",
        `A diferença PT − PL caiu ${fmt1(-D.mud)} pontos nos locais alagados e ${fmt1(-F.mud)} no resto.
        A diferença entre os dois (${sinal(resumo.dif_mud)}) fica dentro da margem de acaso (${sinal(a)} a ${sinal(b)}):
        o voto andou igual dentro e fora da água.`],
    }[estado.passo];
  }

  // duas linhas, alagados × restante, nas três eleições; mostra só as eleições que o passo já alcançou.
  // Sem cor de partido nem bolinhas nas linhas, para não lembrarem os pontos do mapa: alagados em preto contínuo
  // (o contorno escuro dos locais alagados), o resto em cinza tracejado; o fundo diz quem venceu
  const LINHAS = {
    dentro: { classe: "g-alagados", rot: "Locais de votação dentro da área alagada" },
    fora: { classe: "g-resto", rot: "Todos os outros locais da Grande Porto Alegre" },
  };
  function grafico() {
    const { anos } = PASSOS[estado.passo];
    const L18 = resumo.linhas;
    const x0 = 6, x1 = 290, xs = [40, 150, 260], topo = 62, base = 162;
    const y = (v) => topo + ((8 - v) / 44) * (base - topo); // de +8 a −36 pontos
    const xEnchente = xs[1] + 0.6 * (xs[2] - xs[1]);
    const serie = (g) => {
      const v = L18[g].slice(0, anos);
      const pts = v.length > 1 ? v.map((val, i) => `${xs[i]},${y(val).toFixed(1)}`)
        : [xs[0] - 16, xs[0] + 16].map((x) => `${x},${y(v[0]).toFixed(1)}`); // um ano só: um traço curto
      return `<polyline points="${pts.join(" ")}" class="${LINHAS[g].classe}"/>`;
    };
    const amostra = (g, yy) => `<line x1="0" x2="28" y1="${yy - 4}" y2="${yy - 4}" class="${LINHAS[g].classe}"/>
      <text x="36" y="${yy}" class="g-leg">${LINHAS[g].rot}</text>`;
    const anosRot = ["2018", "2022", "2026"].map((t, i) => `<text x="${xs[i]}" y="${base + 14}" class="g-ano${i < anos ? "" : " g-futuro"}">${t}</text>`);
    const dists = L18.dentro.slice(0, anos).map((v, i) => `<text x="${xs[i]}" y="${base + 32}" class="g-dist">${fmt1(Math.abs(v - L18.fora[i]))}</text>`);
    const enchente = estado.passo >= "3"
      ? `<line x1="${xEnchente}" x2="${xEnchente}" y1="${topo - 2}" y2="${base}" class="g-enchente${estado.passo === "3" ? " g-agora" : ""}"/>
         <text x="${xEnchente}" y="${topo - 5}" class="g-enchente-rot">enchente</text>` : "";
    document.getElementById("grafico").innerHTML = `
      <text x="0" y="11" class="g-tit">Vantagem do PT sobre o PSL/PL, em pontos</text>
      ${amostra("dentro", 30)}
      ${amostra("fora", 46)}
      <rect x="${x0}" y="${topo}" width="${x1 - x0}" height="${y(0) - topo}" class="g-fundo-pt"/>
      <rect x="${x0}" y="${y(0)}" width="${x1 - x0}" height="${base - y(0)}" class="g-fundo-pl"/>
      ${xs.map((x) => `<line x1="${x}" x2="${x}" y1="${topo}" y2="${base}" class="g-grade"/>`).join("")}
      <text x="${x0 + 4}" y="${topo + 11}" class="g-venceu g-pt">PT venceu</text>
      <text x="${x1 - 4}" y="${base - 5}" class="g-venceu g-pl">PSL/PL venceu</text>
      <line x1="${x0}" x2="${x1}" y1="${y(0)}" y2="${y(0)}" class="g-zero"/>
      <text x="${x1 + 3}" y="${y(0) + 3}" class="g-eixo">empate</text>
      ${enchente}
      ${serie("fora")}
      ${serie("dentro")}
      ${anosRot.join("")}
      ${dists.join("")}
      <text x="${xs[1]}" y="${base + 46}" class="g-dist-rot">↑ distância entre as duas linhas, em pontos</text>`;
  }

  function narrativa() {
    const [tit, txt] = textoPasso();
    document.getElementById("passo-tit").textContent = tit;
    document.getElementById("passo-txt").textContent = txt.replace(/\s+/g, " ");
    grafico();
    document.getElementById("ant").disabled = estado.passo === "1";
    document.getElementById("prox").disabled = estado.passo === "5";
  }

  function irPara(passo) {
    if (!PASSOS[passo] || passo === estado.passo) return;
    estado.passo = passo;
    estado.mancha = PASSOS[passo].mancha;
    redesenhar();
  }

  // ---------- painel ----------
  function legenda() {
    const mud = aba() === "mud";
    if (mud) return legendaSetas();
    const cl = mud ? meta.classes_mud : meta.classes;
    const lados = meta.lados[aba()];
    const vazio = mud ? "sem comparação (menos de 100 votos)" : aba() === "18" ? "sem seções em 2018" : "";
    const quem = estado.passo < "3" ? "locais que a enchente atingiria em 2024" : "locais dentro da área alagada";
    document.getElementById("legenda").innerHTML = `
      <div class="tit">${estado.passo === "3" ? "<b>Cores: o voto de 2022</b>, a última eleição antes da enchente. " : ""}${ABAS[aba()].tit}</div>
      <div class="faixa">${cl.map((c) => `<span style="background:${c.cor}"></span>`).join("")}</div>
      <div class="rots">${cl.map((c) => `<div>${esc(c.rot)}</div>`).join("")}</div>
      ${mud ? "" : `<div class="lados"><span>← ${lados[0]}</span><span>${lados[1]} →</span></div>`}
      <div class="extras">
        ${estado.dest === "1" ? `<span><i class="amostra-destaque"></i>${quem}</span>` : ""}
        ${estado.mancha === "1" ? '<span><i class="amostra-mancha"></i>área alagada em maio de 2024</span>' : ""}
        ${vazio ? `<span><i class="amostra-vazio"></i>${vazio}</span>` : ""}
      </div>`;
  }

  function legendaSetas() {
    const dest = estado.dest === "1";
    document.getElementById("legenda").innerHTML = `
      <div class="tit">Para onde o voto andou de 2022 para 2026 (diferença PT − PL, em pontos)</div>
      <div class="leg-setas"><span>${svgSeta(-1, SETA.pt, 18)}para o PT</span><span>para o PL${svgSeta(1, SETA.pl, 18)}</span></div>
      <div class="leg-setas">${SETA.tam.map((L, i) => `<span>${svgSeta(1, SETA.pl, L)}${["até 4", "4 a 10", "mais de 10"][i]}</span>`).join("")}</div>
      ${dest ? `<div class="leg-setas"><span>${svgSeta(1, SETA.pl, 16, 1, 2.2)}locais dentro da área alagada</span>
        <span>${svgSeta(1, SETA.pl, 16, 0.3)}resto</span></div>` : ""}
      <div class="extras">
        ${estado.mancha === "1" ? '<span><i class="amostra-mancha"></i>área alagada em maio de 2024</span>' : ""}
        <span><i class="amostra-vazio redonda"></i>sem comparação (menos de 100 votos)</span>
      </div>`;
  }

  function sincronizarControles() {
    for (const b of document.querySelectorAll("[data-passo]")) {
      if (b.dataset.passo === estado.passo) b.setAttribute("aria-current", "step"); else b.removeAttribute("aria-current");
    }
    for (const b of document.querySelectorAll("[data-un]")) {
      b.setAttribute("aria-pressed", b.dataset.un === estado.un);
      b.disabled = aba() === "mud"; // na mudança são sempre setas, que partem do ponto do local
      b.title = b.disabled ? "Na mudança, cada local é uma seta" : "";
    }
    document.getElementById("c-mancha").checked = estado.mancha === "1";
    document.getElementById("c-sim").checked = estado.sim === "1";
    document.getElementById("c-dest").checked = estado.dest === "1";
    document.getElementById("mun").value = estado.mun;
  }

  function redesenhar() {
    sincronizarControles();
    narrativa();
    legenda();
    if (estado.mancha === "1") camMancha.addTo(mapa); else camMancha.remove();
    desenharPontos();
    desenharAreas();
    desenharSim();
    if (estado.local && balao && mapa.hasLayer(balao)) balao.setContent(popup(porPid.get(Number(estado.local)).p));
    gravarHash();
  }

  const celular = () => matchMedia("(max-width: 700px)").matches;
  // se o leitor ainda não arrastou nem deu zoom, recolher o cartão no celular reenquadra o mapa no espaço que sobrou
  let enquadrando = false, mexeu = false;
  mapa.on("dragstart zoomstart", () => { if (!enquadrando) mexeu = true; });

  function enquadrar() {
    const painel = document.getElementById("painel"), comp = document.getElementById("comparacao");
    // no celular o cartão da comparação fica no topo e o painel embaixo; no computador, painel à esquerda e cartão à direita
    const pad = celular() ? { paddingTopLeft: [10, comp.offsetHeight + 20], paddingBottomRight: [10, painel.offsetHeight + 10] }
      : { paddingTopLeft: [painel.offsetWidth + 30, 20],
          paddingBottomRight: [innerWidth - painel.offsetWidth - comp.offsetWidth > 560 ? comp.offsetWidth + 30 : 20, 20] };
    // no celular o zoom inteiro desperdiça até metade do espaço (o 8,9 ideal cai para 8): ali o enquadramento é fracionário
    const snap = mapa.options.zoomSnap;
    if (celular()) mapa.options.zoomSnap = 0;
    enquadrando = true;
    mapa.fitBounds(munBounds.get(estado.mun) || L.featureGroup(pontos).getBounds(), pad);
    enquadrando = mexeu = false;
    mapa.options.zoomSnap = snap;
  }

  function ligarControles() {
    for (const b of document.querySelectorAll("[data-passo]")) b.onclick = () => irPara(b.dataset.passo);
    document.getElementById("ant").onclick = () => irPara(String(+estado.passo - 1));
    document.getElementById("prox").onclick = () => irPara(String(+estado.passo + 1));
    document.addEventListener("keydown", (e) => {
      if (e.target.closest("select, input")) return;
      if (e.key === "ArrowRight") irPara(String(+estado.passo + 1));
      if (e.key === "ArrowLeft") irPara(String(+estado.passo - 1));
    });
    for (const b of document.querySelectorAll("[data-un]")) b.onclick = () => { estado.un = b.dataset.un; redesenhar(); };
    for (const [id, k] of [["c-mancha", "mancha"], ["c-sim", "sim"], ["c-dest", "dest"]])
      document.getElementById(id).onchange = (e) => { estado[k] = e.target.checked ? "1" : "0"; redesenhar(); };
    document.getElementById("mun").onchange = (e) => {
      estado.mun = e.target.value;
      camMun.setStyle((f) => estiloMun(f));
      enquadrar();
      gravarHash();
    };
    // no celular o painel começa recolhido: só o passo, a linha do tempo e a legenda das cores
    const painel = document.getElementById("painel");
    recolhivel(painel, document.getElementById("recolher"), "painel", celular());
    recolhivel(document.getElementById("comparacao"), document.getElementById("comp-recolher"), "gráfico", false,
      () => { if (celular() && !mexeu) enquadrar(); });
    // a altura do painel posiciona os controles do mapa no celular (estilo.css)
    new ResizeObserver(() => document.documentElement.style.setProperty("--alt-painel", painel.offsetHeight + "px"))
      .observe(painel);
  }

  function recolhivel(caixa, botao, nome, fechado, depois) {
    const aplicar = (f) => {
      caixa.classList.toggle("fechado", f);
      botao.textContent = f ? "+" : "−";
      botao.setAttribute("aria-expanded", !f);
      botao.title = (f ? "Abrir " : "Recolher ") + nome;
    };
    aplicar(fechado);
    botao.onclick = () => { aplicar(!caixa.classList.contains("fechado")); if (depois) depois(); };
    L.DomEvent.disableClickPropagation(caixa);
    L.DomEvent.disableScrollPropagation(caixa);
  }

  const estiloMun = (f) => ({
    color: f.properties.cd === estado.mun ? "#0b0b0b" : "#8a8880",
    weight: f.properties.cd === estado.mun ? 2 : 0.7, fill: false,
  });

  // ---------- carga ----------
  const baixar = (nome) => fetch("dados/" + nome).then((r) => {
    if (!r.ok) throw new Error(nome + ": " + r.status);
    return r.json();
  });

  async function iniciar() {
    const [m, r, loc, man, mun] = await Promise.all(
      ["meta.json", "resumo.json", "locais.json", "mancha.json", "municipios.json"].map(baixar));
    meta = m; resumo = r;
    document.getElementById("fonte-ada").textContent = meta.fontes.ada.replace(" (CC BY 4.0)", "");
    document.getElementById("gerado").textContent = "dados de " + meta.gerado.split("-").reverse().join("/");

    camMun = L.geoJSON(mun, { pane: "mun", renderer: telaMun, interactive: false, style: estiloMun }).addTo(mapa);
    camMun.eachLayer((l) => munBounds.set(l.feature.properties.cd, l.getBounds()));
    const sel = document.getElementById("mun");
    for (const f of [...mun.features].sort((a, b) => a.properties.nome.localeCompare(b.properties.nome, "pt-BR")))
      sel.add(new Option(f.properties.nome, f.properties.cd));

    camMancha = L.geoJSON(man, {
      pane: "mancha", renderer: telaMancha, interactive: false,
      style: { color: meta.cor.contorno, weight: 0.6, opacity: 0.7, fillColor: meta.cor.mancha, fillOpacity: 0.22 },
    });

    vmax = Math.max(...loc.features.map((f) => f.properties.v26));
    pontos = loc.features.map((f) => { // já vêm do maior para o menor: os pequenos ficam por cima
      const [lon, lat] = f.geometry.coordinates;
      const mk = L.circleMarker([lat, lon], { renderer: telaPontos });
      mk.p = f.properties;
      mk.on("click", () => abrirLocal(mk.p.pid, false));
      porPid.set(mk.p.pid, mk);
      return mk;
    });

    ligarControles();
    enquadrar();
    redesenhar();
    if (estado.local) abrirLocal(Number(estado.local), true);
  }

  iniciar().catch((e) => {
    document.getElementById("passo-txt").textContent = `Não foi possível carregar os dados (${e.message}).`;
    console.error(e);
  });
})();
