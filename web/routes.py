import asyncio
from concurrent.futures import ThreadPoolExecutor
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify

web_bp = Blueprint('web', __name__)
executor = ThreadPoolExecutor(max_workers=5)

def init_routes(app, db, scraper):

    @app.context_processor
    def inject_db():
        return {'db': db}

    @web_bp.route('/', methods=['GET', 'POST'])
    def index():
        if request.method == 'POST':
            site = request.form.get('site', 'djinni')
            count = int(request.form.get('count', 10))
            
            # Get the last scraped job ID for this site
            last_job_id = db.get_last_scraped_job_id(site)
            start_id = last_job_id + 1
            
            # Start scraping in background using the executor
            def run_scraper():
                async_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(async_loop)
                try:
                    async_loop.run_until_complete(scraper.scrape_sequential_jobs(start_id, count))
                finally:
                    async_loop.close()
            
            executor.submit(run_scraper)
            
            flash(f'Started scraping {count} jobs starting from ID {start_id}.')
            return redirect(url_for('web.jobs'))
        
        return render_template('index.html')
    
    @web_bp.route('/jobs', methods=['GET'])
    def jobs():
        query = request.args.get('query', '')
        
        # Get jobs from database
        if query:
            jobs_data = db.search_jobs(query)
        else:
            jobs_data = db.get_all_jobs()
        
        return render_template('jobs.html', jobs=jobs_data, query=query)
    
    @web_bp.route('/jobs/<job_id>', methods=['GET'])
    def job_detail(job_id):
        job = db.get_job(job_id)
        if not job:
            flash('Job not found')
            return redirect(url_for('web.jobs'))
        
        return render_template('job_detail.html', job=job)
    
    @web_bp.route('/api/jobs/scrape', methods=['POST'])
    def api_scrape_jobs():
        query = request.json.get('query', '')
        pages = int(request.json.get('pages', 1))
        
        # Start scraping in background
        def run_scraper():
            async_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(async_loop)
            try:
                async_loop.run_until_complete(scraper.search_jobs(query, pages))
            finally:
                async_loop.close()
        
        executor.submit(run_scraper)
        
        return jsonify({'status': 'success', 'message': 'Scraping started in background'})
    
    @web_bp.route('/api/jobs', methods=['GET'])
    def api_get_jobs():
        query = request.args.get('query', '')
        
        if query:
            jobs_data = db.search_jobs(query)
        else:
            jobs_data = db.get_all_jobs()
        
        return jsonify({'jobs': jobs_data})
    
    @web_bp.route('/api/jobs/<job_id>', methods=['GET'])
    def api_get_job(job_id):
        job = db.get_job(job_id)
        if not job:
            return jsonify({'error': 'Job not found'}), 404
        
        return jsonify({'job': job})
    
    

    @web_bp.route('/api/scraping/status', methods=['GET'])
    def api_scraping_status():
        status = db.get_scraping_status()
        return jsonify(status)
    
    app.register_blueprint(web_bp)