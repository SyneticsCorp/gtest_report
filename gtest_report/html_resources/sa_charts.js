document.addEventListener('DOMContentLoaded', function() {
  Chart.register(ChartDataLabels);

  var commonOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      datalabels: {
        formatter: function(value) { return value; },
        color: '#000',
        font: { weight: 'bold', size: 12 },
        anchor: 'end',
        align: 'top',
        clamp: true,
        offset: 4
      },
      tooltip: { enabled: false }
    }
  };

  // Component Chart
  var compChart = document.getElementById('componentChart');
  if (compChart) {
    var compLabels = JSON.parse(compChart.dataset.labels || '[]');
    var compValues = JSON.parse(compChart.dataset.values || '[]');
    new Chart(compChart.getContext('2d'), {
      type: 'bar',
      data: {
        labels: compLabels,
        datasets: [{
          label: 'Violations',
          data: compValues,
          backgroundColor: 'rgba(54, 162, 235, 0.7)'
        }]
      },
      options: commonOptions
    });
  }

  // Severity Chart
  var sevChart = document.getElementById('severityChart');
  if (sevChart) {
    var sevLabels = JSON.parse(sevChart.dataset.labels || '[]');
    var sevValues = JSON.parse(sevChart.dataset.values || '[]');
    new Chart(sevChart.getContext('2d'), {
      type: 'bar',
      data: {
        labels: sevLabels,
        datasets: [{
          label: 'Violations',
          data: sevValues,
          backgroundColor: 'rgba(255, 99, 132, 0.7)'
        }]
      },
      options: commonOptions
    });
  }

  // Rule ID Chart
  var ruleChart = document.getElementById('ruleIdChart');
  if (ruleChart) {
    var ruleLabels = JSON.parse(ruleChart.dataset.labels || '[]');
    var ruleValues = JSON.parse(ruleChart.dataset.values || '[]');
    new Chart(ruleChart.getContext('2d'), {
      type: 'bar',
      data: {
        labels: ruleLabels,
        datasets: [{
          label: 'Violations',
          data: ruleValues,
          backgroundColor: 'rgba(153, 102, 255, 0.7)'
        }]
      },
      options: commonOptions
    });
  }
});
