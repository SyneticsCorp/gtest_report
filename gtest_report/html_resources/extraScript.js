// File: gtest_report/html_resources/extraScript.js

document.addEventListener('DOMContentLoaded', () => {
    const searchInput = document.getElementById('searchInput');
    const toggle      = document.getElementById('failOnlyToggle');
    const details     = document.querySelectorAll('#detailsContainer table.utests');
  
    function filterRows() {
      const keyword = searchInput.value.toLowerCase();
      const failOnly = toggle.checked;
  
      details.forEach(table => {
        // 헤더 및 각 행 검사
        const rows = table.querySelectorAll('tr');
        rows.forEach((row, idx) => {
          if (idx === 0) return; // 헤더는 항상 표시
          const nameCell = row.cells[1].textContent.toLowerCase();
          const resultCell = row.cells[2].innerHTML;
          const isFail = resultCell.includes('notok') || resultCell.includes('Failure');
  
          let show = true;
          if (keyword && !nameCell.includes(keyword)) show = false;
          if (failOnly && !isFail) show = false;
  
          row.style.display = show ? '' : 'none';
        });
      });
    }
  
    searchInput.addEventListener('input', filterRows);
    toggle.addEventListener('change', filterRows);
  });
  