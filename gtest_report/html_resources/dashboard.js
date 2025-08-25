// Dashboard JavaScript Functions
document.addEventListener('DOMContentLoaded', () => {
    // Initialize mini chart if element exists
    const ctx = document.getElementById('miniChart');
    if (ctx) {
        // Get data from data attributes
        const passedCount = parseInt(ctx.dataset.passed || '0');
        const failedCount = parseInt(ctx.dataset.failed || '0');
        const skippedCount = parseInt(ctx.dataset.skipped || '0');
        
        new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Passed', 'Failed', 'Skipped'],
                datasets: [{
                    data: [passedCount, failedCount, skippedCount],
                    backgroundColor: ['#27ae60', '#e74c3c', '#f39c12'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            padding: 10,
                            font: { size: 11 }
                        }
                    }
                }
            }
        });
    }
});