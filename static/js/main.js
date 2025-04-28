document.addEventListener('DOMContentLoaded', function() {
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    const scrapingForm = document.getElementById('scraping-form');
    if (scrapingForm) {
        scrapingForm.addEventListener('submit', function(e) {
            const submitButton = this.querySelector('button[type="submit"]');
            const buttonText = submitButton.innerHTML;
            
            submitButton.disabled = true;
            submitButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Scraping...';
        });
    }
    
    const jobTable = document.querySelector('.table');
    if (jobTable) {
        const getCellValue = (tr, idx) => tr.children[idx].innerText || tr.children[idx].textContent;
        
        const comparer = (idx, asc) => (a, b) => ((v1, v2) => 
            v1 !== '' && v2 !== '' && !isNaN(v1) && !isNaN(v2) ? v1 - v2 : v1.toString().localeCompare(v2)
        )(getCellValue(asc ? a : b, idx), getCellValue(asc ? b : a, idx));
        
        document.querySelectorAll('th').forEach(th => th.addEventListener('click', (() => {
            const table = th.closest('table');
            const tbody = table.querySelector('tbody');
            Array.from(tbody.querySelectorAll('tr'))
                .sort(comparer(Array.from(th.parentNode.children).indexOf(th), this.asc = !this.asc))
                .forEach(tr => tbody.appendChild(tr) );
        })));
    }
    
    const jobFilter = document.getElementById('job-filter');
    if (jobFilter) {
        jobFilter.addEventListener('input', function() {
            const filterValue = this.value.toLowerCase();
            const rows = document.querySelectorAll('.job-row');
            
            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(filterValue) ? '' : 'none';
            });
            
            const visibleRows = document.querySelectorAll('.job-row[style=""]').length;
            document.getElementById('no-results').style.display = visibleRows === 0 ? 'block' : 'none';
        });
    }

    const apiScrapeButton = document.getElementById('api-scrape');
    if (apiScrapeButton) {
        apiScrapeButton.addEventListener('click', function(e) {
            e.preventDefault();
            
            const query = document.getElementById('query').value;
            const pages = document.getElementById('pages').value;
            
            this.disabled = true;
            this.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Scraping...';

            fetch('/api/jobs/scrape', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ query, pages }),
            })
            .then(response => response.json())
            .then(data => {
                const alertBox = document.createElement('div');
                alertBox.className = 'alert alert-success alert-dismissible fade show';
                alertBox.innerHTML = `
                    <strong>Success!</strong> ${data.message}
                    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                `;
                document.querySelector('.container').prepend(alertBox);
                
                this.disabled = false;
                this.innerHTML = 'Start Scraping';
                
                setTimeout(() => {
                    const bsAlert = new bootstrap.Alert(alertBox);
                    bsAlert.close();
                }, 5000);
            })
            .catch(error => {
                const alertBox = document.createElement('div');
                alertBox.className = 'alert alert-danger alert-dismissible fade show';
                alertBox.innerHTML = `
                    <strong>Error!</strong> Something went wrong.
                    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                `;
                document.querySelector('.container').prepend(alertBox);
                
                this.disabled = false;
                this.innerHTML = 'Start Scraping';
                
                console.error('Error:', error);
            });
        });
    }
});