import asyncio
from concurrent.futures import ThreadPoolExecutor
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
import json
from collections import defaultdict
import datetime

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
    

    @web_bp.route('/analytics')
    def analytics():
        # Отримати всі вакансії
        jobs_data = db.get_all_jobs()
        
        # Загальна статистика
        stats = {
            'total_jobs': len(jobs_data),
            'active_jobs': sum(1 for job in jobs_data if job.get('is_active', False)),
            'avg_salary': 0,
            'min_salary': 0,
            'max_salary': 0,
        }
        
        # Зарплатна статистика
        salaries = [job['salary_min'] for job in jobs_data if job.get('salary_min')]
        if salaries:
            stats['min_salary'] = min(salaries)
            stats['avg_salary'] = sum(salaries) / len(salaries)
        
        max_salaries = [job['salary_max'] for job in jobs_data if job.get('salary_max')]
        if max_salaries:
            stats['max_salary'] = max(max_salaries)
        
        # Дані для діаграм
        job_types_data = defaultdict(int)
        experience_data = defaultdict(int)
        english_levels_data = defaultdict(int)
        location_data = defaultdict(int)
        employment_types_data = defaultdict(int)
        categories_data = defaultdict(int)
        salary_ranges = {
            '0-1000': 0, 
            '1000-2000': 0, 
            '2000-3000': 0, 
            '3000-4000': 0, 
            '4000-5000': 0, 
            '5000+': 0
        }
        
        for job in jobs_data:
            # Тип роботи (Remote, Office, Hybrid)
            job_type = job.get('job_type', 'Not specified')
            job_types_data[job_type] += 1
            
            # Досвід роботи
            exp = job.get('experience_years')
            exp_key = f"{exp} years" if exp else "Not specified"
            experience_data[exp_key] += 1
            
            # Рівень англійської
            english = job.get('english_level', 'Not specified')
            english_levels_data[english] += 1
            
            # Локація
            location = job.get('location', 'Not specified')
            location_data[location] += 1
            
            # Тип зайнятості
            employment = job.get('employment_type', 'Not specified')
            employment_types_data[employment] += 1
            
            # Категорія
            category = job.get('category', 'Not specified')
            categories_data[category] += 1
            
            # Діапазони зарплат
            salary_min = job.get('salary_min', 0)
            if salary_min:
                if salary_min < 1000:
                    salary_ranges['0-1000'] += 1
                elif salary_min < 2000:
                    salary_ranges['1000-2000'] += 1
                elif salary_min < 3000:
                    salary_ranges['2000-3000'] += 1
                elif salary_min < 4000:
                    salary_ranges['3000-4000'] += 1
                elif salary_min < 5000:
                    salary_ranges['4000-5000'] += 1
                else:
                    salary_ranges['5000+'] += 1
        
        # Перетворення даних для Chart.js
        chart_data = {
            'job_types': {
                'labels': list(job_types_data.keys()),
                'data': list(job_types_data.values())
            },
            'experience': {
                'labels': list(experience_data.keys()),
                'data': list(experience_data.values())
            },
            'english_levels': {
                'labels': list(english_levels_data.keys()),
                'data': list(english_levels_data.values())
            },
            'locations': {
                'labels': list(location_data.keys())[:10],  # Top 10 locations
                'data': list(location_data.values())[:10]
            },
            'employment_types': {
                'labels': list(employment_types_data.keys()),
                'data': list(employment_types_data.values())
            },
            'categories': {
                'labels': list(categories_data.keys())[:10],  # Top 10 categories
                'data': list(categories_data.values())[:10]
            },
            'salary_ranges': {
                'labels': list(salary_ranges.keys()),
                'data': list(salary_ranges.values())
            }
        }
        
        return render_template('analytics.html', 
                              stats=stats, 
                              chart_data=json.dumps(chart_data), 
                              jobs_data=jobs_data)
    
    @web_bp.route('/api/analytics/filter', methods=['POST'])
    def api_filter_analytics():
        # Отримуємо параметри фільтрації з запиту
        filters = request.json
        time_range = filters.get('timeRange', 'all')
        job_type = filters.get('jobType', 'all')
        experience = filters.get('experience', 'all')
        category = filters.get('category', 'all')
        
        # Отримуємо всі вакансії
        jobs_data = db.get_all_jobs()
        
        # Фільтруємо вакансії
        filtered_jobs = []
        for job in jobs_data:
            # Фільтр за часовим діапазоном
            if time_range != 'all':
                # Конвертуємо posted_date у дату, якщо це можливо
                posted_date = job.get('posted_date')
                if not posted_date:
                    continue
                
                try:
                    posted_date = datetime.datetime.fromisoformat(posted_date) if isinstance(posted_date, str) else posted_date
                    now = datetime.datetime.now()
                    
                    if time_range == 'month' and (now - posted_date).days > 30:
                        continue
                    elif time_range == 'quarter' and (now - posted_date).days > 90:
                        continue
                    elif time_range == 'year' and (now - posted_date).days > 365:
                        continue
                except (ValueError, TypeError):
                    # Якщо не вдалося конвертувати дату, пропускаємо фільтрацію за часом
                    pass
            
            # Фільтр за типом роботи
            if job_type != 'all' and job.get('job_type') != job_type:
                continue
                
            # Фільтр за досвідом
            if experience != 'all':
                exp_years = job.get('experience_years')
                if exp_years is None:
                    continue
                    
                if experience == '0-1' and exp_years > 1:
                    continue
                elif experience == '1-3' and (exp_years < 1 or exp_years > 3):
                    continue
                elif experience == '3-5' and (exp_years < 3 or exp_years > 5):
                    continue
                elif experience == '5+' and exp_years < 5:
                    continue
                    
            # Фільтр за категорією
            if category != 'all' and job.get('category') != category:
                continue
                
            # Якщо вакансія пройшла всі фільтри, додаємо її
            filtered_jobs.append(job)
            
        # Статистика
        stats = {
            'total_jobs': len(filtered_jobs),
            'active_jobs': sum(1 for job in filtered_jobs if job.get('is_active', False)),
            'avg_salary': 0,
            'min_salary': 0,
            'max_salary': 0,
        }
        
        # Зарплатна статистика
        salaries = [job['salary_min'] for job in filtered_jobs if job.get('salary_min')]
        if salaries:
            stats['min_salary'] = min(salaries)
            stats['avg_salary'] = sum(salaries) / len(salaries)
        
        max_salaries = [job['salary_max'] for job in filtered_jobs if job.get('salary_max')]
        if max_salaries:
            stats['max_salary'] = max(max_salaries)
        
        # Дані для діаграм
        job_types_data = defaultdict(int)
        experience_data = defaultdict(int)
        english_levels_data = defaultdict(int)
        location_data = defaultdict(int)
        employment_types_data = defaultdict(int)
        categories_data = defaultdict(int)
        salary_ranges = {
            '0-1000': 0, 
            '1000-2000': 0, 
            '2000-3000': 0, 
            '3000-4000': 0, 
            '4000-5000': 0, 
            '5000+': 0
        }
        
        for job in filtered_jobs:
            # Тип роботи (Remote, Office, Hybrid)
            job_type = job.get('job_type', 'Not specified')
            job_types_data[job_type] += 1
            
            # Досвід роботи
            exp = job.get('experience_years')
            exp_key = f"{exp} years" if exp else "Not specified"
            experience_data[exp_key] += 1
            
            # Рівень англійської
            english = job.get('english_level', 'Not specified')
            english_levels_data[english] += 1
            
            # Локація
            location = job.get('location', 'Not specified')
            location_data[location] += 1
            
            # Тип зайнятості
            employment = job.get('employment_type', 'Not specified')
            employment_types_data[employment] += 1
            
            # Категорія
            category = job.get('category', 'Not specified')
            categories_data[category] += 1
            
            # Діапазони зарплат
            salary_min = job.get('salary_min', 0)
            if salary_min:
                if salary_min < 1000:
                    salary_ranges['0-1000'] += 1
                elif salary_min < 2000:
                    salary_ranges['1000-2000'] += 1
                elif salary_min < 3000:
                    salary_ranges['2000-3000'] += 1
                elif salary_min < 4000:
                    salary_ranges['3000-4000'] += 1
                elif salary_min < 5000:
                    salary_ranges['4000-5000'] += 1
                else:
                    salary_ranges['5000+'] += 1
        
        # Сортування для отримання топ-10
        sorted_locations = sorted(location_data.items(), key=lambda x: x[1], reverse=True)
        sorted_categories = sorted(categories_data.items(), key=lambda x: x[1], reverse=True)
        
        # Перетворення даних для Chart.js
        chart_data = {
            'job_types': {
                'labels': list(job_types_data.keys()),
                'data': list(job_types_data.values())
            },
            'experience': {
                'labels': list(experience_data.keys()),
                'data': list(experience_data.values())
            },
            'english_levels': {
                'labels': list(english_levels_data.keys()),
                'data': list(english_levels_data.values())
            },
            'locations': {
                'labels': [loc for loc, count in sorted_locations[:10]],
                'data': [count for loc, count in sorted_locations[:10]]
            },
            'employment_types': {
                'labels': list(employment_types_data.keys()),
                'data': list(employment_types_data.values())
            },
            'categories': {
                'labels': [cat for cat, count in sorted_categories[:10]],
                'data': [count for cat, count in sorted_categories[:10]]
            },
            'salary_ranges': {
                'labels': list(salary_ranges.keys()),
                'data': list(salary_ranges.values())
            }
        }
        
        return jsonify({
            'stats': stats,
            'chart_data': chart_data
        })
    
    app.register_blueprint(web_bp)