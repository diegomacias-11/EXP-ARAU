(() => {
  if (window.ChartDataLabels && window.Chart) {
    Chart.register(window.ChartDataLabels);
  }

  const form = document.getElementById('form-filtros');
  const selCliente = document.getElementById('cliente_id');
  const desde = document.getElementById('fecha_desde');
  const hasta = document.getElementById('fecha_hasta');
  const btnLimpiar = document.getElementById('btn-limpiar');

  const msg = document.getElementById('msg-seleccione');
  const chartsWrap = document.getElementById('charts');
  const tbody = document.getElementById('tbody-eventos');
  const eventosWrap = document.getElementById('eventos_qas');

  const kpiWrap = document.getElementById('kpi');
  const kpiAvg = document.getElementById('kpi_avg_ticket');
  const kpiNum = document.getElementById('kpi_num');
  const kpiTotal = document.getElementById('kpi_total');
  const perPreguntaWrap = document.getElementById('per_pregunta');
  const preguntasCharts = document.getElementById('preguntas-charts');
  const btnPrint = document.getElementById('btn-print');
  const phTitle = document.getElementById('ph-title');
  const phSubtitle = document.getElementById('ph-subtitle');

  let chartEventos = null;
  let chartEncuestas = null;
  let lastEventos = [];
  let selectedDay = null;      // barra seleccionada (YYYY-MM-DD)
  let selectedStatus = null;   // 'Completadas' | 'Pendientes'
  let selectedQA = null;       // {pid:number|string, ans:string}

  // Utilidad global: color de alto contraste
  function getContrast(hex) {
    if (!hex || typeof hex !== 'string') return '#2b313f';
    const h = hex.replace('#','');
    const v = h.length === 3 ? h.split('').map(c=>c+c).join('') : h;
    const num = parseInt(v,16);
    const r = (num>>16)&255, g=(num>>8)&255, b=num&255;
    const lum = 0.299*r + 0.587*g + 0.114*b;
    return lum < 140 ? '#d2dee3' : '#2b313f';
  }

  function makePalette(n) {
    const base = ['#2b313f', '#59b9c7', '#aebed2', '#294369', '#4aa5b3', '#d2dee3', '#003b71', '#808b98'];
    const out = [];
    for (let i = 0; i < n; i++) out.push(base[i % base.length]);
    return out;
  }

  function renderPerPregunta(per_pregunta) {
    if (!perPreguntaWrap || !preguntasCharts) return;
    preguntasCharts.innerHTML = '';
    if (!per_pregunta || !per_pregunta.length) { perPreguntaWrap.style.display = 'none'; return; }
    perPreguntaWrap.style.display = '';

    for (const item of per_pregunta) {
      const box = document.createElement('div');
      box.style.flex = '1 1 420px';
      box.style.minWidth = '320px';
      box.style.border = '1px solid #aebed2';
      box.style.borderRadius = '6px';
      box.style.padding = '0.5rem';
      box.style.background = '#ffffff';

      const title = document.createElement('div');
      title.textContent = item.pregunta;
      title.style.fontWeight = '700';
      title.style.color = '#2b313f';
      title.style.marginBottom = '0.25rem';

      const wrap = document.createElement('div');
      wrap.style.position = 'relative';
      wrap.style.width = '100%';
      wrap.style.height = '300px';

      const canvas = document.createElement('canvas');
      canvas.style.width = '100%';
      canvas.style.height = '100%';

      box.appendChild(title);
      wrap.appendChild(canvas);
      box.appendChild(wrap);
      preguntasCharts.appendChild(box);

      const colors = makePalette(item.labels.length || 1);
      const chart = new Chart(canvas, {
        type: 'doughnut',
        data: { labels: item.labels, datasets: [{ data: item.data, backgroundColor: colors, borderColor: '#232833' }] },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { position: 'bottom' },
            datalabels: {
              anchor: 'center', align: 'center', clamp: true,
              font: { size: 11, weight: '600' },
              color: (ctx) => {
                const bg = (ctx.dataset.backgroundColor || [])[ctx.dataIndex] || '#2b313f';
                return getContrast(bg);
              },
              formatter: (v, ctx) => {
                const data = ctx.chart.data.datasets[0].data || [];
                const total = data.reduce((a,b)=>a + (typeof b==='number'?b:parseFloat(b)||0),0) || 1;
                const pct = (v/total)*100;
                if (pct < 1 && v === 0) return '';
                const pctStr = pct < 10 ? pct.toFixed(1) : pct.toFixed(0);
                return `${v} (${pctStr}%)`;
              },
              display: (ctx) => (ctx.dataset.data[ctx.dataIndex] > 0),
            }
          },
          onClick: (evt, elements, chart) => {
            if (!elements || !elements.length) return;
            const idx = elements[0].index;
            const label = chart.data.labels[idx];
            const pid = item.pregunta_id;
            // toggle
            if (selectedQA && String(selectedQA.pid) === String(pid) && String(selectedQA.ans) === String(label)) {
              selectedQA = null;
            } else {
              selectedQA = { pid: pid, ans: label };
            }
            applyTableFilters();
          }
        }
      });
    }
  }

  function resetUI() {
    if (chartEventos) { chartEventos.destroy(); chartEventos = null; }
    if (chartEncuestas) { chartEncuestas.destroy(); chartEncuestas = null; }
    tbody.innerHTML = '';
    chartsWrap.style.display = 'none';
    eventosWrap.style.display = 'none';
    if (kpiWrap) kpiWrap.style.display = 'none';
    msg.style.display = '';
  }

  function renderCharts(series) {
    const ctx1 = document.getElementById('chart_eventos');
    const ctx2 = document.getElementById('chart_encuestas');
    const ed = series?.eventos_por_dia || { labels: [], data: [] };
    const en = series?.encuestas || { labels: [], data: [] };

    // Utilidad: color de alto contraste según fondo
    const contrastColor = (hex) => {
      if (!hex || typeof hex !== 'string') return '#2b313f';
      const h = hex.replace('#','');
      const v = h.length === 3 ? h.split('').map(c=>c+c).join('') : h;
      const num = parseInt(v,16);
      const r = (num>>16)&255, g=(num>>8)&255, b=num&255;
      const lum = 0.299*r + 0.587*g + 0.114*b; // percepción
      return lum < 140 ? '#d2dee3' : '#2b313f';
    };

    const barBg = '#59b9c7';
    chartEventos = new Chart(ctx1, {
      type: 'bar',
      data: {
        labels: ed.labels,
        datasets: [{ label: 'Eventos por día', data: ed.data, backgroundColor: barBg, borderColor: '#2b313f', borderWidth: 1 }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          title: { display: true, text: 'Eventos por día', color: '#2b313f', font: { weight: 'bold' } },
          legend: { display: false },
          datalabels: {
            anchor: 'center',
            align: 'center',
            clamp: true,
            color: (ctx) => contrastColor(ctx.dataset.backgroundColor || barBg),
            formatter: (v) => (Number.isFinite(v) && v > 0 ? Math.round(v) : ''),
            display: (ctx) => (ctx.dataset.data[ctx.dataIndex] > 0)
          },
        },
        scales: {
          y: { beginAtZero: true, ticks: { stepSize: 1, callback: (v) => Number.isInteger(v) ? v : '' } }
        },
        onClick: (evt, elements, chart) => {
          if (!elements || !elements.length) return;
          const idx = elements[0].index;
          const label = chart.data.labels[idx];
          selectedDay = (selectedDay === label ? null : label);
          applyTableFilters();
        }
      }
    });

    chartEncuestas = new Chart(ctx2, {
      type: 'doughnut',
      data: { labels: en.labels, datasets: [{ data: en.data, backgroundColor: ['#2b313f', '#aebed2'], borderColor: '#232833' }] },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          title: { display: true, text: 'Encuestas (Completadas vs Pendientes)', color: '#2b313f', font: { weight: 'bold' } },
          legend: { position: 'bottom' },
          datalabels: {
            anchor: 'center',
            align: 'center',
            clamp: true,
            font: { size: 11, weight: '600' },
            color: (ctx) => {
              const bg = (ctx.dataset.backgroundColor || ['#2b313f','#aebed2'])[ctx.dataIndex] || '#2b313f';
              return contrastColor(bg);
            },
            formatter: (v, ctx) => {
              const data = ctx.chart.data.datasets[0].data || [];
              const total = data.reduce((a, b) => a + (typeof b === 'number' ? b : parseFloat(b) || 0), 0) || 1;
              const pct = ((v / total) * 100);
              if (pct < 1 && v === 0) return '';
              const pctStr = pct < 10 ? pct.toFixed(1) : pct.toFixed(0);
              return `${v} (${pctStr}%)`;
            },
            display: (ctx) => (ctx.dataset.data[ctx.dataIndex] > 0)
          },
        },
        onClick: (evt, elements, chart) => {
          if (!elements || !elements.length) return;
          const idx = elements[0].index;
          const label = chart.data.labels[idx]; // 'Completadas' | 'Pendientes'
          selectedStatus = (selectedStatus === label ? null : label);
          applyTableFilters();
        }
      }
    });
  }

  function renderEventos(eventos) {
    tbody.innerHTML = '';
    for (const ev of (eventos || [])) {
      const tr = document.createElement('tr');
      const qas = (ev.qa || []).map(q => `${q.pregunta || ''}: ${q.respuesta || ''}`).join('<br/>');
      tr.innerHTML = `
        <td>${ev.nombre}</td>
        <td>${ev.telefono || ''}</td>
        <td>${ev.ticket}</td>
        <td>${(ev.fecha_registro || '').slice(0,10)}</td>
        <td style="text-align:left">${qas}</td>
      `;
      tbody.appendChild(tr);
    }
  }

  function renderKpi(kpi) {
    if (!kpiWrap) return;
    try {
      const fmt = new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN', maximumFractionDigits: 2 });
      const avg = parseFloat(kpi?.avg_ticket || '0') || 0;
      const total = parseFloat(kpi?.total_ticket || '0') || 0;
      kpiAvg.textContent = fmt.format(avg);
      kpiTotal.textContent = fmt.format(total);
      kpiNum.textContent = String(kpi?.num_eventos ?? 0);
    } catch (_) {
      kpiAvg.textContent = kpi?.avg_ticket || '0';
      kpiTotal.textContent = kpi?.total_ticket || '0';
      kpiNum.textContent = String(kpi?.num_eventos ?? 0);
    }
  }

  function updateKpiFromEvents(evs) {
    if (!kpiWrap) return;
    const n = evs.length;
    let total = 0;
    for (const e of evs) {
      const t = parseFloat(e.ticket);
      if (!isNaN(t)) total += t;
    }
    const avg = n ? total / n : 0;
    try {
      const fmt = new Intl.NumberFormat('es-MX', { style: 'currency', currency: 'MXN', maximumFractionDigits: 2 });
      kpiAvg.textContent = fmt.format(avg);
      kpiTotal.textContent = fmt.format(total);
    } catch (_) {
      kpiAvg.textContent = String(avg.toFixed(2));
      kpiTotal.textContent = String(total.toFixed(2));
    }
    kpiNum.textContent = String(n);
  }

  function applyTableFilters() {
    let evs = lastEventos.slice();
    if (selectedDay) {
      evs = evs.filter(e => (e.fecha_registro || '').slice(0,10) === selectedDay);
    }
    if (selectedStatus) {
      const wantCompleted = (selectedStatus === 'Completadas');
      evs = evs.filter(e => !!e.completada === wantCompleted);
    }
    if (selectedQA) {
      const pid = String(selectedQA.pid || '');
      const ans = String(selectedQA.ans || '');
      const isSin = ans.toLowerCase() === 'sin respuesta' || ans === '__sinrespuesta__';
      evs = evs.filter(e => {
        const list = e.qa || [];
        const hasForPid = list.filter(q => String(q.pregunta_id || '') === pid);
        if (isSin) {
          // no hay respuesta no vacía para esta pregunta
          return !hasForPid.some(q => (q.respuesta || '').trim().length > 0);
        }
        return hasForPid.some(q => (q.respuesta || '') === ans);
      });
    }
    renderEventos(evs);
    updateKpiFromEvents(evs);
  }

  async function fetchData() {
    const clienteId = selCliente.value;
    if (!clienteId) { resetUI(); return; }

    const params = new URLSearchParams();
    params.set('cliente_id', clienteId);
    if (desde.value) params.set('fecha_desde', desde.value);
    if (hasta.value) params.set('fecha_hasta', hasta.value);

    const url = `${window.REPORTES_DATA_URL}?${params.toString()}`;
    const res = await fetch(url, { headers: { 'Accept': 'application/json' } });
    if (!res.ok) { resetUI(); return; }
    const data = await res.json();

    // Mostrar secciones
    msg.style.display = 'none';
    chartsWrap.style.display = '';
    eventosWrap.style.display = '';
    if (kpiWrap) kpiWrap.style.display = '';

    // Render
    renderCharts(data.series);
    lastEventos = data.eventos || [];
    selectedDay = null;
    selectedStatus = null;
    selectedQA = null;
    renderEventos(lastEventos);
    renderKpi(data.kpi || null);
    renderPerPregunta(data.per_pregunta || []);
  }

  form.addEventListener('submit', (e) => { e.preventDefault(); fetchData(); });
  selCliente.addEventListener('change', fetchData);
  btnLimpiar.addEventListener('click', (e) => { e.preventDefault(); selCliente.value=''; desde.value=''; hasta.value=''; resetUI(); });

  // Impresión literal del dashboard: oculta filtros y muestra encabezado con cliente/fechas
  if (btnPrint) {
    btnPrint.addEventListener('click', (e) => {
      e.preventDefault();
      try {
        // Título = Cliente; Subtítulo = fechas
        const opt = selCliente.options[selCliente.selectedIndex];
        const clienteTxt = opt && opt.value ? opt.text : '';
        const desdeTxt = desde.value ? `Desde: ${desde.value}` : '';
        const hastaTxt = hasta.value ? `Hasta: ${hasta.value}` : '';
        const rango = [desdeTxt, hastaTxt].filter(Boolean).join('  ');

        if (phTitle) phTitle.textContent = clienteTxt ? `Cliente: ${clienteTxt}` : 'Cliente: —';
        if (phSubtitle) phSubtitle.textContent = rango || 'Rango: Todos';

        // Mostrar encabezado de impresión; el CSS @media print ocultará los filtros.
        const ph = document.getElementById('print-header');
        if (ph) ph.style.display = '';

        // Disparar diálogo de impresión (usuario puede Guardar como PDF)
        window.print();

        // Revertir estado visual tras impresión
        window.setTimeout(() => { if (ph) ph.style.display = 'none'; }, 300);
      } catch (err) {
        console.error('Error al preparar impresión', err);
      }
    });
  }

  // (PDF eliminado)

  resetUI();
})();
