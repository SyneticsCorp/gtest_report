// Local Chart.js bootstrapper for Jenkins (no CDN / no inline script)
document.addEventListener('DOMContentLoaded', () => {
  if (typeof Chart === 'undefined') return;
  if (typeof ChartDataLabels !== 'undefined') {
    Chart.register(ChartDataLabels);
  }

  const commonOpts = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      datalabels: {
        formatter: v => v,
        color: '#fff',
        font: { weight: 'bold', size: 14 }
      },
      tooltip: { enabled: false }
    }
  };

  function renderFromCanvas(canvasId) {
    const el = document.getElementById(canvasId);
    if (!el) return;
    const labels = JSON.parse(el.getAttribute('data-labels') || '[]');
    const values = JSON.parse(el.getAttribute('data-values') || '[]');
    const ctx = el.getContext('2d');
    new Chart(ctx, {
      type: 'pie',
      data: { labels, datasets: [{ data: values }] },
      options: commonOpts,
    });
  }

  ['execChart', 'execNoSkipChart', 'passChart'].forEach(renderFromCanvas);
});


