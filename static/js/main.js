// Main JavaScript file for Djinni Job Scraper

// Enable tooltips
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize popovers
    var popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Scraping form submission with progress indicator
    const scrapingForm = document.getElementById('scraping-form');
    if (scrapingForm) {
        scrapingForm.addEventListener('submit', function(e) {
            const submitButton = this.querySelector('button[type="submit"]');
            const buttonText = submitButton.innerHTML;
            
            // Change button to loading state
            submitButton.disabled = true;
            submitButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Scraping...';
            
            // Form will submit normally, this is just UI feedback
        });
    }
    
    // Job table sorting
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
    
    // Filter jobs by text input
    const jobFilter = document.getElementById('job-filter');
    if (jobFilter) {
        jobFilter.addEventListener('input', function() {
            const filterValue = this.value.toLowerCase();
            const rows = document.querySelectorAll('.job-row');
            
            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(filterValue) ? '' : 'none';
            });
            
            // Show or hide "no results" message
            const visibleRows = document.querySelectorAll('.job-row[style=""]').length;
            document.getElementById('no-results').style.display = visibleRows === 0 ? 'block' : 'none';
        });
    }
    
    // API-based scraping
    const apiScrapeButton = document.getElementById('api-scrape');
    if (apiScrapeButton) {
        apiScrapeButton.addEventListener('click', function(e) {
            e.preventDefault();
            
            const query = document.getElementById('query').value;
            const pages = document.getElementById('pages').value;
            
            // Change button to loading state
            this.disabled = true;
            this.innerHTML = '<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Scraping...';
            
            // Make API request
            fetch('/api/jobs/scrape', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ query, pages }),
            })
            .then(response => response.json())
            .then(data => {
                // Show success message
                const alertBox = document.createElement('div');
                alertBox.className = 'alert alert-success alert-dismissible fade show';
                alertBox.innerHTML = `
                    <strong>Success!</strong> ${data.message}
                    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                `;
                document.querySelector('.container').prepend(alertBox);
                
                // Restore button
                this.disabled = false;
                this.innerHTML = 'Start Scraping';
                
                // Auto-dismiss alert after 5 seconds
                setTimeout(() => {
                    const bsAlert = new bootstrap.Alert(alertBox);
                    bsAlert.close();
                }, 5000);
            })
            .catch(error => {
                // Show error message
                const alertBox = document.createElement('div');
                alertBox.className = 'alert alert-danger alert-dismissible fade show';
                alertBox.innerHTML = `
                    <strong>Error!</strong> Something went wrong.
                    <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
                `;
                document.querySelector('.container').prepend(alertBox);
                
                // Restore button
                this.disabled = false;
                this.innerHTML = 'Start Scraping';
                
                console.error('Error:', error);
            });
        });
    }
});