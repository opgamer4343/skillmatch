(function () {

  /* ── Timer helpers ───────────────────────────────────────── */
  function formatSeconds(s) {
    const m = Math.floor(s / 60);
    const sec = s % 60;
    return String(m).padStart(2,'0') + ':' + String(sec).padStart(2,'0');
  }

  /* ── Cooldown timer ──────────────────────────────────────── */
  function initCooldownTimer() {
    const box = document.querySelector('[data-cooldown-seconds]');
    const out = document.getElementById('cooldownTimer');
    if (!box || !out) return;
    let secs = parseInt(box.dataset.cooldownSeconds || '0', 10);
    function tick() {
      if (secs <= 0) { out.textContent = 'Available now'; return; }
      const d = Math.floor(secs / 86400);
      const h = Math.floor((secs % 86400) / 3600);
      const m = Math.floor((secs % 3600) / 60);
      const s = secs % 60;
      const parts = [];
      if (d) parts.push(d + 'd');
      if (h || d) parts.push(h + 'h');
      if (m || h || d) parts.push(m + 'm');
      parts.push(s + 's');
      out.textContent = parts.join(' ');
      secs--;
      setTimeout(tick, 1000);
    }
    tick();
  }

  /* ── Score History Chart ─────────────────────────────────── */
  function initHistoryChart() {
    const canvas = document.getElementById('historyChart');
    if (!canvas || typeof Chart === 'undefined') return;

    const url = canvas.dataset.historyUrl;
    if (!url) return;

    const bandColors = {
      expert:       '#059669',
      strong:       '#4f46e5',
      intermediate: '#0891b2',
      foundation:   '#d97706',
      beginner:     '#dc2626',
    };

    fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
      .then(r => r.json())
      .then(data => {
        const labels          = data.labels          || [];
        const overall_scores  = data.overall_scores  || [];
        const technical_scores= data.technical_scores|| [];
        const soft_scores     = data.soft_scores     || [];
        const bands           = data.bands           || [];
        const dates           = data.dates           || [];
        const count           = data.count           || 0;

        /* Update "N attempts" counter in the heading */
        const counter = document.getElementById('attemptCount');
        if (counter) counter.textContent = count + ' attempt' + (count !== 1 ? 's' : '');

        if (count === 0) {
          /* Show empty-state message, hide canvas */
          canvas.style.display = 'none';
          const emptyEl = document.getElementById('chartEmpty');
          if (emptyEl) emptyEl.style.display = 'block';
          return;
        }

        /* Point colors per band */
        const ptColors = bands.map(b => bandColors[b] || '#4f46e5');

        new Chart(canvas, {
          type: 'line',
          data: {
            labels: labels,
            datasets: [
              {
                label: 'Overall',
                data: overall_scores,
                borderColor: '#4f46e5',
                backgroundColor: 'rgba(79,70,229,.08)',
                borderWidth: 2.5,
                pointBackgroundColor: ptColors,
                pointBorderColor: '#fff',
                pointBorderWidth: 2,
                pointRadius: 6,
                pointHoverRadius: 8,
                tension: 0.35,
                fill: true,
              },
              {
                label: 'Technical',
                data: technical_scores,
                borderColor: '#0891b2',
                backgroundColor: 'transparent',
                borderWidth: 2,
                pointBackgroundColor: '#0891b2',
                pointBorderColor: '#fff',
                pointBorderWidth: 2,
                pointRadius: 5,
                pointHoverRadius: 7,
                tension: 0.35,
                borderDash: [4, 3],
                fill: false,
              },
              {
                label: 'Soft Skills',
                data: soft_scores,
                borderColor: '#f59e0b',
                backgroundColor: 'transparent',
                borderWidth: 2,
                pointBackgroundColor: '#f59e0b',
                pointBorderColor: '#fff',
                pointBorderWidth: 2,
                pointRadius: 5,
                pointHoverRadius: 7,
                tension: 0.35,
                borderDash: [4, 3],
                fill: false,
              },
            ],
          },
          options: {
            responsive: true,
            maintainAspectRatio: true,
            interaction: { mode: 'index', intersect: false },
            plugins: {
              legend: {
                position: 'top',
                labels: {
                  usePointStyle: true,
                  pointStyle: 'circle',
                  padding: 20,
                  font: { size: 12, family: 'Inter, system-ui, sans-serif' },
                  color: '#64748b',
                },
              },
              tooltip: {
                backgroundColor: '#1e293b',
                titleColor: '#f1f5f9',
                bodyColor: '#cbd5e1',
                borderColor: '#334155',
                borderWidth: 1,
                cornerRadius: 10,
                padding: 12,
                callbacks: {
                  title: function(items) {
                    const idx = items[0].dataIndex;
                    return labels[idx] + (dates[idx] ? '  ·  ' + dates[idx] : '');
                  },
                  label: function(item) {
                    return '  ' + item.dataset.label + ': ' + item.raw.toFixed(1) + '%';
                  },
                  afterBody: function(items) {
                    const idx = items[0].dataIndex;
                    const band = bands[idx];
                    return band ? ['  Band: ' + band.charAt(0).toUpperCase() + band.slice(1)] : [];
                  },
                },
              },
            },
            scales: {
              x: {
                grid: { display: false },
                ticks: {
                  font: { size: 12, family: 'Inter, system-ui, sans-serif' },
                  color: '#94a3b8',
                },
              },
              y: {
                min: 0,
                max: 100,
                grid: {
                  color: 'rgba(0,0,0,.04)',
                  drawBorder: false,
                },
                ticks: {
                  stepSize: 20,
                  font: { size: 11, family: 'Inter, system-ui, sans-serif' },
                  color: '#94a3b8',
                  callback: v => v + '%',
                },
                border: { display: false },
              },
            },
            animation: {
              duration: 900,
              easing: 'easeInOutQuart',
            },
          },
        });
      })
      .catch(() => {
        canvas.style.display = 'none';
      });
  }

  /* ── Question timer ──────────────────────────────────────── */
  function initQuestionTimer() {
    const timerEl  = document.getElementById('questionTimer');
    const form     = document.getElementById('assessmentQuestionForm');
    const timeInput= document.getElementById('timeTakenInput');
    if (!timerEl || !form || !timeInput) return;

    let secs = parseInt(timerEl.dataset.seconds || '60', 10);
    timerEl.textContent = formatSeconds(secs);
    timeInput.value = secs;

    const bar   = document.getElementById('questionProgressBar');
    const total = secs;

    const iv = setInterval(() => {
      secs--;
      timerEl.textContent = formatSeconds(Math.max(secs, 0));
      timeInput.value     = Math.max(secs, 0);

      if (bar && total > 0) {
        const pct = (Math.max(secs, 0) / total) * 100;
        bar.style.width = pct + '%';
        if (pct < 25) bar.style.background = '#dc2626';
        else if (pct < 50) bar.style.background = '#f59e0b';
        else bar.style.background = '#4f46e5';
      }

      if (secs <= 0) { clearInterval(iv); form.submit(); }
    }, 1000);
  }

  /* ── Boot ────────────────────────────────────────────────── */
  document.addEventListener('DOMContentLoaded', function () {
    initCooldownTimer();
    initHistoryChart();
    initQuestionTimer();
  });

})();