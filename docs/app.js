// Mapa interativo: enchente de 2024 × voto para presidente na Grande Porto Alegre.
// Dados em dados/*.json, gerados por scripts/13_exportar_web.py. Sem build: Leaflet via cdnjs.
(() => {
  const PADRAO = { aba: "26", un: "pontos", mancha: "1", sim: "0", so: "0", mun: "", local: "" };
  const ABAS = {
    "26": { campo: "m26", tit: "Diferença Lula (PT) − Flávio Bolsonaro (PL) em 2026, em pontos percentuais" },
    "22": { campo: "m22", tit: "Diferença Lula (PT) − Jair Bolsonaro (PL) em 2022, em pontos percentuais" },
    "18": { campo: "m18", tit: "Diferença Haddad (PT) − Jair Bolsonaro (PSL) em 2018, em pontos percentuais" },
    mud: { campo: "mud", tit: "Mudança na diferença PT − PL de 2022 para 2026, em pontos" },
  };
  const COR_VAZIO = "#a9a59c", COR_FORA = "#c2beb5";
  const RMAX = 8; // raio do maior local no zoom 10, em px

  // ---------- estado na URL (#aba=mud&mun=4314902&local=812) ----------
  const estado = { ...PADRAO };
  const params = new URLSearchParams(location.hash.slice(1));
  for (const k of Object.keys(PADRAO)) if (params.has(k)) estado[k] = params.get(k);
  if (!ABAS[estado.aba]) estado.aba = PADRAO.aba;

  function gravarHash() {
    const p = new URLSearchParams();
    for (const [k, v] of Object.entries(estado)) if (v !== PADRAO[k]) p.set(k, v);
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
    const x = p[ABAS[estado.aba].campo];
    if (x == null) return null;
    const mud = estado.aba === "mud";
    const cl = mud ? meta.classes_mud : meta.classes;
    return cl[cl.length - 1 - classe(x, mud ? meta.cortes_mud : meta.cortes)].cor; // legenda vai da classe 4 à 0
  }
  function estilo(p) {
    const c = cor(p);
    if (estado.so === "1" && !p.ada) return { color: COR_FORA, weight: 0.8, fillOpacity: 0 };
    if (!c) return { color: COR_VAZIO, weight: 1.2, fillOpacity: 0 };
    return { color: meta.cor.fundo, weight: 0.6, fillColor: c, fillOpacity: 0.92 };
  }

  // ---------- mapa ----------
  const mapa = L.map("mapa", { zoomControl: false, minZoom: 8, maxZoom: 17 });
  L.control.zoom({ position: "topright" }).addTo(mapa);
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

  let pontos = [], vmax = 1, camMancha, camSim, camMun, camAreas, porPid = new Map(), munBounds = new Map();

  // cresce com o zoom, mas mais devagar que o mapa, para os locais do centro não se cobrirem
  const raio = (v) => Math.max(1.5, Math.min(20, Math.sqrt(v / vmax) * RMAX * Math.pow(1.3, mapa.getZoom() - 10)));

  function popup(p) {
    const tag = p.ada
      ? `<span class="tag ada">Dentro da área alagada${p.f > 0 ? ` · ${Math.round(100 * p.f)}% do entorno` : ""}</span>`
      : `<span class="tag">Fora da área alagada${p.f >= 0.05 ? ` · ${Math.round(100 * p.f)}% do entorno` : ""}</span>`;
    const lugar = [p.bairro, p.mun].filter(Boolean).map(esc).join(" · ");
    const sim = p.p530 ? '<p class="nota">Dentro da simulação do Guaíba a 5,30 m.</p>' : "";
    return `<div class="pop"><h3>${esc(p.nome)}</h3><p class="lugar">${lugar}</p>${tag}
      <table>
        <tr><th>PT − PSL, 2018</th><td>${sinal(p.m18)}</td></tr>
        <tr><th>PT − PL, 2022</th><td>${sinal(p.m22)}</td></tr>
        <tr><th>PT − PL, 2026</th><td>${sinal(p.m26)}</td></tr>
        <tr class="forte"><th>Mudança 2022 → 2026</th><td>${sinal(p.mud)}</td></tr>
      </table>
      <p>2026: Lula ${pct(p.lula)} · Flávio Bolsonaro ${pct(p.flavio)} · ${mil(p.v26)} votos válidos</p>
      ${p.a22 ? `<p>Eleitores aptos: ${mil(p.a22)} em 2022 → ${mil(p.a26)} em 2026</p>` : ""}
      ${sim}<p class="nota">Pontos percentuais dos votos válidos, nas mesmas seções eleitorais.</p></div>`;
  }

  function abrirLocal(pid, centralizar) {
    const m = porPid.get(pid);
    if (!m) return;
    if (centralizar) mapa.setView(m.getLatLng(), Math.max(mapa.getZoom(), 14));
    L.popup({ maxWidth: 290, autoPanPadding: [20, 20] }).setLatLng(m.getLatLng()).setContent(popup(m.p)).openOn(mapa);
    estado.local = String(pid);
    gravarHash();
  }
  mapa.on("popupclose", () => { estado.local = ""; gravarHash(); });

  function desenharPontos() {
    const visiveis = estado.un === "pontos";
    for (const m of pontos) {
      if (!visiveis) { m.remove(); continue; }
      m.setStyle(estilo(m.p));
      m.setRadius(raio(m.p.v26));
      if (!mapa.hasLayer(m)) m.addTo(mapa);
    }
  }
  mapa.on("zoomend", () => { if (estado.un === "pontos") for (const m of pontos) m.setRadius(raio(m.p.v26)); });

  async function garantirAreas() {
    if (camAreas) return camAreas;
    const g = await baixar("areas.json");
    camAreas = L.geoJSON(g, {
      pane: "areas", renderer: telaAreas,
      style: (f) => ({ ...estilo(porPid.get(f.properties.pid).p), weight: 0.3, fillOpacity: 0.85 }),
      onEachFeature: (f, l) => l.on("click", () => abrirLocal(f.properties.pid, false)),
    });
    return camAreas;
  }
  async function desenharAreas() {
    if (estado.un !== "areas") { if (camAreas) camAreas.remove(); return; }
    const c = await garantirAreas();
    c.setStyle((f) => {
      const s = estilo(porPid.get(f.properties.pid).p);
      return s.fillOpacity ? { ...s, weight: 0.3, fillOpacity: 0.85 } : { ...s, weight: 0.5 };
    });
    if (!mapa.hasLayer(c)) c.addTo(mapa);
  }

  async function desenharSim() {
    if (estado.sim !== "1") { if (camSim) camSim.remove(); return; }
    if (!camSim) camSim = L.geoJSON(await baixar("mancha_poa530.json"), {
      pane: "mancha", renderer: telaMancha, interactive: false,
      style: { color: "#075f6c", weight: 1, dashArray: "4 3", fillColor: "#0a8fa3", fillOpacity: 0.22 },
    });
    camSim.addTo(mapa);
  }

  // ---------- painel ----------
  function legenda() {
    const mud = estado.aba === "mud";
    const cl = mud ? meta.classes_mud : meta.classes;
    const lados = meta.lados[estado.aba];
    const vazio = mud ? "sem comparação (menos de 100 votos)" : estado.aba === "18" ? "sem seções em 2018" : "";
    document.getElementById("legenda").innerHTML = `
      <div class="tit">${ABAS[estado.aba].tit}</div>
      <div class="faixa">${cl.map((c) => `<span style="background:${c.cor}"></span>`).join("")}</div>
      <div class="rots">${cl.map((c) => `<div>${esc(c.rot)}</div>`).join("")}</div>
      ${mud ? "" : `<div class="lados"><span>← ${lados[0]}</span><span>${lados[1]} →</span></div>`}
      <div class="extras">
        ${estado.mancha === "1" ? '<span><i class="amostra-mancha"></i>área alagada em maio de 2024</span>' : ""}
        ${vazio ? `<span><i class="amostra-vazio"></i>${vazio}</span>` : ""}
        ${estado.so === "1" ? '<span><i class="amostra-fora"></i>locais fora da área alagada</span>' : ""}
      </div>`;
  }

  function quadroResumo() {
    const d = resumo.dentro, f = resumo.fora;
    const campo = ABAS[estado.aba].campo;
    const tit = {
      "26": "Diferença PT − PL em 2026", "22": "Diferença PT − PL em 2022",
      "18": "Diferença PT − PSL em 2018", mud: "Mudança na diferença PT − PL, 2022 → 2026",
    }[estado.aba];
    let nota = "";
    if (estado.aba === "mud") {
      const [a, b] = resumo.ic_mud;
      nota = `Diferença entre os dois: ${sinal(resumo.dif_mud)} ponto (intervalo de 95%: ${sinal(a)} a ${sinal(b)}). ` +
        "Dentro da margem de acaso: o voto andou igual dentro e fora da água.";
    } else if (estado.aba === "18") {
      nota = "2018: só as seções que existem nas três eleições.";
    }
    document.getElementById("resumo").innerHTML = `
      <div class="tit">${tit}, em pontos</div>
      <table>
        <tr><td><span class="ponto" style="background:var(--alagado)"></span>Locais dentro da área alagada
          <br><small>${d.locais} locais, ${mil(Math.round(d.aptos / 1000))} mil eleitores</small></td><td class="n">${sinal(d[campo])}</td></tr>
        <tr><td><span class="ponto" style="background:#b0761c"></span>Restante do mapa</td><td class="n">${sinal(f[campo])}</td></tr>
      </table>
      ${nota ? `<p class="nota">${nota}</p>` : ""}`;
  }

  function sincronizarControles() {
    for (const b of document.querySelectorAll("[data-aba]")) b.setAttribute("aria-selected", b.dataset.aba === estado.aba);
    for (const b of document.querySelectorAll("[data-un]")) b.setAttribute("aria-pressed", b.dataset.un === estado.un);
    document.getElementById("c-mancha").checked = estado.mancha === "1";
    document.getElementById("c-sim").checked = estado.sim === "1";
    document.getElementById("c-so").checked = estado.so === "1";
    document.getElementById("mun").value = estado.mun;
  }

  function redesenhar() {
    sincronizarControles();
    legenda();
    quadroResumo();
    if (estado.mancha === "1") camMancha.addTo(mapa); else camMancha.remove();
    desenharPontos();
    desenharAreas();
    desenharSim();
    gravarHash();
  }

  function enquadrar() {
    const celular = matchMedia("(max-width: 700px)").matches;
    const painel = document.getElementById("painel");
    const pad = celular ? { paddingTopLeft: [10, 30], paddingBottomRight: [10, painel.offsetHeight + 10] }
      : { paddingTopLeft: [painel.offsetWidth + 30, 20], paddingBottomRight: [20, 20] };
    mapa.fitBounds(munBounds.get(estado.mun) || L.featureGroup(pontos).getBounds(), pad);
  }

  function ligarControles() {
    for (const b of document.querySelectorAll("[data-aba]")) b.onclick = () => { estado.aba = b.dataset.aba; redesenhar(); };
    for (const b of document.querySelectorAll("[data-un]")) b.onclick = () => { estado.un = b.dataset.un; redesenhar(); };
    for (const [id, k] of [["c-mancha", "mancha"], ["c-sim", "sim"], ["c-so", "so"]])
      document.getElementById(id).onchange = (e) => { estado[k] = e.target.checked ? "1" : "0"; redesenhar(); };
    document.getElementById("mun").onchange = (e) => {
      estado.mun = e.target.value;
      camMun.setStyle((f) => estiloMun(f));
      enquadrar();
      gravarHash();
    };
    const painel = document.getElementById("painel"), botao = document.getElementById("recolher");
    botao.onclick = () => {
      const fechado = painel.classList.toggle("fechado");
      botao.textContent = fechado ? "+" : "−";
      botao.setAttribute("aria-expanded", !fechado);
      botao.title = fechado ? "Abrir painel" : "Recolher painel";
    };
    L.DomEvent.disableClickPropagation(painel);
    L.DomEvent.disableScrollPropagation(painel);
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
    document.getElementById("resumo").innerHTML = `<p class="nota">Não foi possível carregar os dados (${esc(e.message)}).</p>`;
    console.error(e);
  });
})();
