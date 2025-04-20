import asyncio
import re
import logging
from flask import jsonify, Blueprint
from concurrent.futures import ThreadPoolExecutor
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
import json
from collections import defaultdict
import datetime
from scraper.sitemap_processor import SitemapProcessor
import re

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
        # Pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # Search query
        query = request.args.get('query', '')
        
        # Filter parameters
        experience_min = request.args.get('experience_min', '', type=str)
        experience_max = request.args.get('experience_max', '', type=str)
        salary_min = request.args.get('salary_min', '', type=str)
        salary_max = request.args.get('salary_max', '', type=str)
        english_level = request.args.get('english_level', '')
        location = request.args.get('location', '')
        job_type = request.args.get('job_type', '')
        domain = request.args.get('domain', '')
        
        # Get jobs from database
        if query:
            all_jobs = db.search_jobs(query)
        else:
            all_jobs = db.get_all_jobs()
        
        # Apply filters
        filtered_jobs = []
        for job in all_jobs:
            # Experience filter
            if experience_min and (not job.get('experience_years') or job['experience_years'] < int(experience_min)):
                continue
            if experience_max and (not job.get('experience_years') or job['experience_years'] > int(experience_max)):
                continue
            
            # Salary filter
            if salary_min and (not job.get('salary_min') or job['salary_min'] < float(salary_min)):
                continue
            if salary_max and (not job.get('salary_max') or job['salary_max'] > float(salary_max)):
                continue
            
            # English level filter
            if english_level and job.get('english_level') != english_level:
                continue
            
            # Location filter
            if location and (not job.get('location') or location.lower() not in job['location'].lower()):
                continue
            
            # Job type filter
            if job_type and job.get('job_type') != job_type:
                continue
            
            # Domain filter
            if domain and job.get('domain') != domain:
                continue
            
            filtered_jobs.append(job)
        
        # Get metadata for filters
        filter_metadata = {
            'english_levels': sorted(list(set(job.get('english_level') for job in all_jobs if job.get('english_level')))),
            'locations': sorted(list(set(job.get('location') for job in all_jobs if job.get('location')))),
            'job_types': sorted(list(set(job.get('job_type') for job in all_jobs if job.get('job_type')))),
            'domains': sorted(list(set(job.get('domain') for job in all_jobs if job.get('domain')))),
        }
        
        # Pagination
        total_jobs = len(filtered_jobs)
        total_pages = (total_jobs + per_page - 1) // per_page
        start_index = (page - 1) * per_page
        end_index = min(start_index + per_page, total_jobs)
        paginated_jobs = filtered_jobs[start_index:end_index]
        
        return render_template(
            'jobs.html',
            jobs=paginated_jobs,
            query=query,
            page=page,
            per_page=per_page,
            total_jobs=total_jobs,
            total_pages=total_pages,
            experience_min=experience_min,
            experience_max=experience_max,
            salary_min=salary_min,
            salary_max=salary_max,
            english_level=english_level,
            location=location,
            job_type=job_type,
            domain=domain,
            filter_metadata=filter_metadata
        )
    
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
    

    @web_bp.route('/api/scrape/refresh', methods=['POST'])
    def api_refresh_job_urls():
        """Эндпоинт для принудительного обновления списка вакансий из карт сайтов"""
        try:
            sitemap_processor = SitemapProcessor(db)
            results = sitemap_processor.refresh_job_urls()
            
            return jsonify({
                'success': True,
                'added': results,
                'remaining': db.count_unprocessed_job_urls()
            })
        
        except Exception as e:
            logging.error(f"Error refreshing job URLs: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @web_bp.route('/api/scrape/next', methods=['GET'])
    def api_scrape_next():
        """Эндпоинт для скрапинга следующей пары вакансий (одна из Djinni, одна из DOU)"""
        try:
            # Проверяем количество непрошедших URL
            unprocessed_count = db.count_unprocessed_job_urls()
            
            # Если осталось мало вакансий, обновляем список
            if unprocessed_count['total'] < 10:
                sitemap_processor = SitemapProcessor(db)
                refresh_result = sitemap_processor.refresh_job_urls()
                logging.info(f"Refreshed job URLs: {refresh_result}")
                
            # Получаем следующие вакансии для обработки
            next_urls = db.get_next_job_urls()
            
            results = []
            for job_url_data in next_urls:
                source = job_url_data['source']
                url = job_url_data['url']
                
                if source == 'djinni':
                    # Используем существующий скрапер для Djinni
                    try:
                        # Извлекаем ID вакансии из URL
                        job_id_match = re.search(r'/jobs/(\d+)-', url)
                        if job_id_match:
                            job_id = job_id_match.group(1)
                            
                            # Создаём функцию для асинхронного скрапинга
                            async def process_djinni_job():
                                try:
                                    # Инициализируем сессию скрапера
                                    await scraper.init_session()
                                    
                                    # Получаем детали вакансии
                                    job_detail = await scraper.get_job_detail(url)
                                    
                                    if job_detail:
                                        # Добавляем job_id, если его нет
                                        job_detail['job_id'] = job_id
                                        
                                        # Переводим данные
                                        job_detail = await scraper.translator.translate_job_data(job_detail)
                                        
                                        # Сохраняем в БД
                                        db.add_job(job_detail)
                                        db.mark_job_url_processed(url, True)
                                        return {
                                            'source': 'djinni',
                                            'url': url,
                                            'status': 'success',
                                            'job_id': job_id
                                        }
                                    else:
                                        # Если не удалось получить детали, отмечаем как обработанную с ошибкой
                                        db.mark_job_url_processed(url, False)
                                        return {
                                            'source': 'djinni',
                                            'url': url,
                                            'status': 'error',
                                            'message': 'Failed to get job details'
                                        }
                                except Exception as e:
                                    logging.error(f"Error processing Djinni job {job_id}: {e}")
                                    # При любой ошибке отмечаем URL как обработанный с ошибкой
                                    db.mark_job_url_processed(url, False)
                                    return {
                                        'source': 'djinni',
                                        'url': url,
                                        'status': 'error',
                                        'message': str(e)
                                    }
                                finally:
                                    # Закрываем сессию скрапера
                                    await scraper.close_session()
                            
                            # Запускаем асинхронную задачу в текущем event loop или создаем новый
                            try:
                                # Используем app.loop, который определен в app.py
                                result = app.loop.run_until_complete(process_djinni_job())
                            except RuntimeError:
                                # Если текущий loop уже работает, создаем новый
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                result = loop.run_until_complete(process_djinni_job())
                                loop.close()
                            
                            results.append(result)
                        else:
                            # Если не удалось извлечь ID, отмечаем как обработанную с ошибкой
                            db.mark_job_url_processed(url, False)
                            results.append({
                                'source': 'djinni',
                                'url': url,
                                'status': 'error',
                                'message': 'Failed to extract job ID from URL'
                            })
                    except Exception as e:
                        logging.error(f"General error processing Djinni URL {url}: {e}")
                        # При любой ошибке отмечаем URL как обработанный с ошибкой
                        db.mark_job_url_processed(url, False)
                        results.append({
                            'source': 'djinni',
                            'url': url,
                            'status': 'error',
                            'message': str(e)
                        })
                
                elif source == 'dou':
                    # Для DOU пока только отмечаем URL как обработанный
                    # В будущем здесь будет логика скрапинга DOU
                    db.mark_job_url_processed(url, True)
                    results.append({
                        'source': 'dou',
                        'url': url,
                        'status': 'skipped',
                        'message': 'DOU scraper not implemented yet'
                    })
            
            # Возвращаем результаты
            return jsonify({
                'success': True,
                'processed': len(results),
                'results': results,
                'remaining': db.count_unprocessed_job_urls()
            })
        
        except Exception as e:
            logging.error(f"Error in scrape next endpoint: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    

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