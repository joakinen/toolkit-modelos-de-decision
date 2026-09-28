// Pinta los resultados de la prueba del apartado del BOE (resultados/boe.json, generado por boe/exportar.py).
// Lo usan la pestaña BOE del laboratorio y la página estática de docs/: una sola fuente para las dos.
// Necesita en la página los elementos #boe-marcador, #boe-lectura, #boe-tabla, #boe-confusiones, #boe-ajuste, #boe-olvido,
// #boe-control y #boe-calibracion (los que falten se saltan).
function pintarBoe(d) {
  const $ = s => document.querySelector(s);
  const esc = s => String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const pct = p => (p * 100).toFixed(0) + " %";
  const signo = x => (x >= 0 ? "+" : "−") + Math.abs(x * 100).toFixed(0) + " %";
  const coma = (x, n = 2) => x.toFixed(n).replace(".", ",");
  const cuota = x => x.seguras ? x.fallos_seguras / x.seguras : 0;
  const fallos = x => `${x.fallos_seguras} de ${x.seguras} (${(100 * cuota(x)).toFixed(1).replace(".", ",")} %)`;
  const sigla = a => a.split(". ")[0] + ".";                        // «II.A.», «III.»…
  const resto = a => a.split(". ").slice(1).join(". ");
  const corto = n => n.replace("Jev-style ", "J").replace("Kev · ", "K").replace("Qwen3.5 · ", "Q").replace(" (letras)", "")
    .replace(" · 2B", "").replace(" · 0.8B", "").replace(" ajustado", " aj.");
  const ap = d.apartados, M = d.modelos;                            // modelos ya ordenados de mejor a peor
  if (!M.length) { $("#boe-marcador").innerHTML = `<div class="card sub">Aún no hay resultados.</div>`; return; }

  $("#boe-marcador").innerHTML = M.map((m, i) => `<div class="card">
      <div class="sub">${esc(m.nombre)}${m.ajustado ? "" : " (sin ajustar)"}</div>
      <div class="n" ${i === 0 ? 'style="color:var(--ok)"' : ""}>${pct(m.media)}</div>
      <div class="sub">log-loss ${coma(m.logloss)}${m.ms != null ? ` · ${m.ms} ms` : ""}</div></div>`).join("");

  const sin = M.filter(m => !m.ajustado), aj = M.filter(m => m.ajustado);
  const I = ap.findIndex(a => a.startsWith("I. ")), IIA = ap.findIndex(a => a.startsWith("II.A"));
  const comp = (a, b) => (d.comparaciones || []).find(c => c.a === a && c.b === b);
  const orig = { ajustado08b: "base08b", ajustado4b: "base4b" };
  const base = { ajustado08b: "kev-08b", ajustado4b: "kev-4b" };
  const tam = { ajustado08b: 0.8, ajustado4b: 4, "kev-08b": 0.8, "kev-4b": 4, "jev-v1": 2, "jev-v3": 0.8, "llm-9b": 9 };   // miles de millones de parámetros
  $("#boe-lectura").innerHTML = `<ul class="plain">
    ${aj.map(m => { const c = comp(m.id, orig[m.id]), b = M.find(x => x.id === base[m.id]);
      return c && b ? `<li><b>${esc(m.nombre)}:</b> del ${pct(b.media)} sin ajustar al ${pct(m.media)} (${signo(c.diferencia)}; intervalo de confianza del 95 %: ${signo(c.ic95[0])} a ${signo(c.ic95[1])}).</li>` : ""; }).join("")}
    <li><b>Sin ajustar, nadie reconoce las disposiciones generales:</b> ${sin.map(m => `${esc(m.nombre)} ${m.clases[I][0]}`).join(", ")} de ${sin[0]?.clases[I][1] ?? 50}. Casi todas acaban en «Otras disposiciones». Distinguir una norma de alcance general de un acto concreto es una convención del BOE que no se deduce del texto sin ejemplos.</li>
    ${aj.length ? `<li><b>Los ajustados aprenden esas convenciones:</b> ${aj.map(m => `${esc(m.nombre)}, ${m.clases[I][0]} disposiciones generales y ${m.clases[IIA][0]} nombramientos de 50`).join("; ")}. Los nombramientos son la otra frontera difícil: se confunden con oposiciones y concursos.</li>` : ""}
    ${aj.map(m => { const c = (d.comparaciones || []).find(x => x.a === m.id && !Object.values(orig).includes(x.b));
      return c ? `<li><b>${tam[c.a] < tam[c.b] ? "Pequeño y ajustado gana a grande sin ajustar." : "Ajustado gana al mejor sin ajustar."}</b> ${esc(c.texto)}: ${signo(c.diferencia)} (intervalo ${signo(c.ic95[0])} a ${signo(c.ic95[1])}).</li>` : ""; }).join("")}
    ${aj.filter(m => m.olvido?.ampliado).map(m => { const o = m.olvido.ampliado;
      return `<li><b>${esc(m.nombre)}, fuera del BOE:</b> acierta lo mismo (${signo(o.diferencia)}; intervalo ${signo(o.ic95[0])} a ${signo(o.ic95[1])}), pero su seguridad deja de ser de fiar: de las respuestas que da con un 90 % o más, fallan ${fallos(o.ajustado)}, frente a ${fallos(o.original)} antes del ajuste.${o.recalibrado ? ` Recalibrado: ${fallos(o.recalibrado)}.` : ""}</li>`; }).join("")}
    <li><b>Cómo se mide:</b> los modelos sin ajustar, con el laboratorio; los Kev ajustados y sus originales, con el evaluador de Kev y el mismo límite de contexto que en el entrenamiento.</li></ul>`;

  $("#boe-tabla").innerHTML = `<tr><th>Apartado</th>${M.map(m => `<th>${esc(corto(m.nombre))}</th>`).join("")}</tr>` +
    ap.map((a, k) => { const top = Math.max(...M.map(m => m.clases[k][0]));
      return `<tr><td title="${esc(a)}"><b>${esc(sigla(a))}</b> <span class="sub">${esc(resto(a).slice(0, 40))}</span></td>${M.map(m =>
        `<td class="${m.clases[k][0] === top ? "ok" : ""}">${m.clases[k][0]}</td>`).join("")}</tr>`; }).join("") +
    `<tr><td><b>Media</b></td>${M.map(m => `<td><b>${pct(m.media)}</b></td>`).join("")}</tr>`;

  $("#boe-confusiones").innerHTML = `<tr><th>Modelo</th><th>Confusiones más frecuentes (real → dicho)</th></tr>` + M.map(m =>
    `<tr><td>${esc(m.nombre)}</td><td style="text-align:left" class="sub">${m.confusiones.map(([r, p, n]) => `${esc(sigla(r))} → ${esc(sigla(p))} ×${n}`).join(" · ") || "ninguna"}</td></tr>`).join("");

  const conAjuste = M.filter(m => m.ajuste), cel = $("#boe-ajuste");
  const hm = s => `${Math.floor(s / 3600)} h ${String(Math.round(s % 3600 / 60)).padStart(2, "0")} min`;
  if (cel) cel.innerHTML = conAjuste.length ? `<table class="matrix"><tr><th></th>${conAjuste.map(m => `<th>${esc(m.nombre)}</th>`).join("")}</tr>
    ${[["Tiempo de ajuste", a => `<b>${hm(a.segundos)}</b>`],
       ["Ejemplos propios", a => a.ejemplos_propios ? a.ejemplos_propios.toLocaleString("es-ES") : "–"],
       ["Ejemplos generales de repaso", a => a.ejemplos_repaso],
       ["Pasadas por los datos", a => a.epocas],
       ["Ejemplos procesados en total", a => a.ejemplos_procesados.toLocaleString("es-ES")],
       ["Segundos por ejemplo", a => coma(a.s_por_ejemplo)],
       ["Memoria de GPU, máximo", a => `${coma(a.memoria_gpu_gb, 1)} GB`],
       ["Memoria del proceso, máximo", a => `${coma(a.memoria_proceso_gb, 1)} GB`],
       ["Qué se entrena", a => a.parametros_entrenados + (a.base_en_media_precision ? ", base en media precisión" : "")]]
      .map(([t, f]) => `<tr><td>${t}</td>${conAjuste.map(m => `<td>${f(m.ajuste)}</td>`).join("")}</tr>`).join("")}</table>
    <p class="sub" style="margin-top:8px">Equipo: ${esc(conAjuste[0].ajuste.equipo)}, sin conexión a servicios externos. El tiempo crece en proporción a los ejemplos y a las pasadas: el doble de ejemplos, el doble de tiempo.</p>`
    : `<span class="sub">Sin datos de ajuste.</span>`;

  const conCtrl = M.filter(m => m.control);
  $("#boe-control").innerHTML = conCtrl.length ? conCtrl.map(m => `${esc(m.nombre)}: ${m.control[0]}/${m.control[1]}`).join(" · ") : `<span class="sub">Sin datos de control.</span>`;

  const nombreControl = { ampliado: "Inglés", es: "Español" };
  const conOlvido = aj.filter(m => m.olvido), olv = $("#boe-olvido");
  if (olv) olv.innerHTML = conOlvido.length ? `<table class="matrix"><tr><th>Modelo</th><th>Control</th><th>Acierto antes → después</th><th>Diferencia (IC 95 %)</th>
      <th>Fallan con ≥ 90 %: antes</th><th>después</th><th>recalibrado</th></tr>
    ${conOlvido.flatMap(m => Object.entries(m.olvido).map(([k, o]) => `<tr><td>${esc(m.nombre)}</td><td>${nombreControl[k] || k} (${o.preguntas})</td>
      <td>${pct(o.original.acierto)} → ${pct(o.ajustado.acierto)}</td><td>${signo(o.diferencia)} (${signo(o.ic95[0])} a ${signo(o.ic95[1])})</td>
      <td>${fallos(o.original)}</td><td class="${cuota(o.ajustado) > cuota(o.original) + 0.03 ? "bad" : ""}">${fallos(o.ajustado)}</td>
      <td>${o.recalibrado ? fallos(o.recalibrado) : "–"}</td></tr>`)).join("")}</table>`
    : `<span class="sub">Sin datos del control ampliado.</span>`;

  const conCal = aj.filter(m => m.calibracion), cal = $("#boe-calibracion");
  if (cal) cal.innerHTML = conCal.length ? `<table class="matrix"><tr><th></th>${conCal.map(m => `<th>${esc(m.nombre)}</th>`).join("")}</tr>
    ${[["Temperatura ajustada (tope 4)", c => `<b>${coma(c.temperatura)}</b>`],
       ["Sin tope", c => coma(c.temperatura_sin_tope)],
       ["Por parte: BOE · generales · español", c => ["BOE", "generales", "español"].map(p => coma(c.temperatura_por_parte[p], 1)).join(" · ")],
       ["Prueba del BOE: fallan con ≥ 90 %, sin recalibrar", c => c.prueba ? fallos(c.prueba.ajustado) : "–"],
       ["Prueba del BOE: fallan con ≥ 90 %, recalibrado", c => c.prueba ? fallos(c.prueba.recalibrado) : "–"],
       ["¿Basta una temperatura?", c => (c.nll_con_temperatura - c.nll_sin_tope) / c.nll_sin_tope > 0.02
         ? `<span style="color:var(--bad)">No: el tope le cuesta un ${Math.round(100 * (c.nll_con_temperatura / c.nll_sin_tope - 1))} % de log-loss</span>` : "Sí"]]
      .map(([t, f]) => `<tr><td>${t}</td>${conCal.map(m => `<td>${f(m.calibracion)}</td>`).join("")}</tr>`).join("")}</table>`
    : `<span class="sub">Sin datos de calibración.</span>`;
}
