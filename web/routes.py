import asyncio
import re
import logging
from flask import jsonify, Blueprint, send_from_directory
from concurrent.futures import ThreadPoolExecutor
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
import json
from collections import defaultdict
import datetime
from scraper.sitemap_processor import SitemapProcessor
from scraper.dou_scraper import DouScraper
from text_processor import TextProcessor
from chatgpt_api import ChatGPTAPI
from file_processor import FileProcessor
from werkzeug.utils import secure_filename
import os
from flask import send_from_directory, send_file



web_bp = Blueprint('web', __name__)
executor = ThreadPoolExecutor(max_workers=5)
file_processor = FileProcessor(upload_folder='uploads')

def init_routes(app, db, scraper):

    @app.context_processor
    def inject_db():
        return {'db': db}

    @web_bp.route('/', methods=['GET', 'POST'])
    def index():

        return redirect(url_for('web.jobs'))
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
                    # Для DOU используем наш новый скрапер
                    try:
                        # Извлекаем ID вакансии из URL
                        job_id_match = re.search(r'/vacancies/(\d+)/', url)
                        if job_id_match:
                            job_id = job_id_match.group(1)
                            
                            # Создаём функцию для асинхронного скрапинга
                            async def process_dou_job():
                                try:
                                    # Создаем экземпляр скрапера DOU
                                    dou_scraper = DouScraper(db)
                                    
                                    # Обрабатываем вакансию
                                    result = await dou_scraper.process_job(url)
                                    
                                    if result:
                                        return {
                                            'source': 'dou',
                                            'url': url,
                                            'status': 'success',
                                            'job_id': job_id
                                        }
                                    else:
                                        return {
                                            'source': 'dou',
                                            'url': url,
                                            'status': 'error',
                                            'message': 'Failed to process DOU job'
                                        }
                                except Exception as e:
                                    logging.error(f"Error processing DOU job {job_id}: {e}")
                                    db.mark_job_url_processed(url, False)
                                    return {
                                        'source': 'dou',
                                        'url': url,
                                        'status': 'error',
                                        'message': str(e)
                                    }
                            
                            # Запускаем асинхронную задачу
                            try:
                                result = app.loop.run_until_complete(process_dou_job())
                            except RuntimeError:
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                result = loop.run_until_complete(process_dou_job())
                                loop.close()
                            
                            results.append(result)
                        else:
                            db.mark_job_url_processed(url, False)
                            results.append({
                                'source': 'dou',
                                'url': url,
                                'status': 'error',
                                'message': 'Failed to extract job ID from URL'
                            })
                    except Exception as e:
                        logging.error(f"General error processing DOU URL {url}: {e}")
                        db.mark_job_url_processed(url, False)
                        results.append({
                            'source': 'dou',
                            'url': url,
                            'status': 'error',
                            'message': str(e)
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
    

    @web_bp.route('/requirements')
    def requirements_analysis():
        """Render the requirements analysis page"""
        # Get filter type
        filter_type = request.args.get('type', 'all')
        
        # Get analyses based on filter
        if filter_type == 'educational':
            analyses = db.get_educational_analyses()
        elif filter_type == 'regular':
            analyses = db.get_regular_analyses()
        else:
            # Default to all analyses
            analyses = db.get_all_requirements_analyses()
        
        # Get unique domains for the dropdown
        all_jobs = db.get_all_jobs()
        domains = set()
        for job in all_jobs:
            if job.get('domain') and job['domain'] not in ('Not specified', ''):
                domains.add(job['domain'])
        
        return render_template(
            'requirements.html',
            analyses=analyses,
            domains=sorted(list(domains)),
            filter_type=filter_type
        )

    @web_bp.route('/api/requirements/analyze', methods=['POST'])
    def api_analyze_requirements():
        """API endpoint for analyzing job requirements"""
        try:
            # Get basic parameters
            selected_domains = request.form.getlist('domains[]')
            is_educational_analysis = 'education_analysis' in request.form
            
            if not selected_domains:
                return jsonify({
                    'success': False,
                    'error': 'No domains selected'
                }), 400
            
            # Convert to list if it's a string
            if isinstance(selected_domains, str):
                selected_domains = [selected_domains]
            
            # Create a comma-separated string of domains for DB storage
            domains_str = ','.join(selected_domains)
            
            # Get educational program file if provided
            education_program_file = None
            education_program_filename = None
            education_program_filetype = None
            education_program_text = None
            
            if is_educational_analysis:
                if 'program_file' not in request.files:
                    return jsonify({
                        'success': False,
                        'error': 'No educational program file provided'
                    }), 400
                    
                program_file = request.files['program_file']
                
                if program_file.filename == '':
                    return jsonify({
                        'success': False,
                        'error': 'No selected file'
                    }), 400
                    
                # Process the file
                file_info = file_processor.save_file(program_file)
                education_program_file = file_info['path']
                education_program_filename = file_info['filename']
                education_program_filetype = file_info['file_type']
                
                # Extract text from file
                education_program_text = file_processor.extract_text(
                    file_info['path'], 
                    file_info['file_type']
                )
            
            # Check if we already have an analysis for these domains
            existing_analyses = db.get_all_requirements_analyses()
            for analysis in existing_analyses:
                if analysis['domains'] == domains_str and analysis['is_educational_analysis'] == is_educational_analysis:
                    # For educational analysis, we don't consider it a duplicate unless filenames match
                    if is_educational_analysis and analysis['education_program_filename'] != education_program_filename:
                        continue
                    return jsonify({
                        'success': True,
                        'analysis': analysis,
                        'message': 'Found existing analysis'
                    })
            
            # Create a new analysis record
            analysis_id = db.add_requirements_analysis(
                domains=domains_str,
                is_educational_analysis=is_educational_analysis,
                education_program_file=education_program_file,
                education_program_filename=education_program_filename,
                education_program_filetype=education_program_filetype,
                education_program_text=education_program_text
            )
            
            # Get jobs for the selected domains
            jobs = db.get_jobs_by_domains(selected_domains, limit=100)
            
            if not jobs:
                return jsonify({
                    'success': False,
                    'error': 'No jobs found for the selected domains'
                }), 404
            
            # Initialize text processor and analyze job requirements
            text_processor = TextProcessor()
            frequency_data = text_processor.analyze_frequency(jobs, top_n=50)
            
            # Save the frequency analysis
            db.update_requirements_analysis(analysis_id, top_words=json.dumps(frequency_data))
            
            # Initialize ChatGPT API and generate summary
            chatgpt = ChatGPTAPI()
            summary = chatgpt.generate_job_requirements_summary(
                selected_domains, 
                frequency_data['top_words']
            )
            
            # Save the summary
            db.update_requirements_analysis(analysis_id, summary=summary)
            
            # If this is an educational program analysis, compare with the program
            if is_educational_analysis and education_program_text:
                education_analysis = chatgpt.analyze_educational_program(
                    selected_domains,
                    summary,
                    education_program_text
                )
                
                # Save the educational program analysis
                db.update_requirements_analysis(analysis_id, education_program_analysis=education_analysis)
            
            # Get the updated analysis
            analysis = db.get_requirements_analysis(analysis_id)
            
            return jsonify({
                'success': True,
                'analysis': analysis,
                'message': 'Analysis completed successfully'
            })
            
        except Exception as e:
            logging.error(f"Error analyzing requirements: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    # Add route to serve the uploaded files
    @web_bp.route('/uploads/<path:filename>')
    def serve_upload(filename):
        """Serve uploaded files"""
        try:
            # Ensure the uploads directory exists
            uploads_dir = os.path.join(os.getcwd(), 'uploads')
            if not os.path.exists(uploads_dir):
                os.makedirs(uploads_dir)
            
            # Get file extension
            _, ext = os.path.splitext(filename)
            
            # Set the correct MIME type based on extension
            mimetype = None
            if ext.lower() == '.pdf':
                mimetype = 'application/pdf'
            elif ext.lower() in ['.doc', '.docx']:
                mimetype = 'application/msword'
            elif ext.lower() == '.txt':
                mimetype = 'text/plain'
            
            # Log for debugging
            logging.info(f"Serving file: {filename} with mimetype: {mimetype}")
            
            # Force download by setting as_attachment=True for non-text files
            as_attachment = ext.lower() != '.txt'
            
            return send_from_directory(
                'uploads', 
                filename, 
                mimetype=mimetype,
                as_attachment=as_attachment
            )
        except Exception as e:
            logging.error(f"Error serving file {filename}: {e}")
            return f"Error: Could not retrieve file: {str(e)}", 404

    @web_bp.route('/api/requirements/<int:analysis_id>', methods=['GET'])
    def api_get_requirements_analysis(analysis_id):
        """Get a specific requirements analysis by ID"""
        try:
            analysis = db.get_requirements_analysis(analysis_id)
            if not analysis:
                return jsonify({
                    'success': False,
                    'error': 'Analysis not found'
                }), 404
                
            return jsonify({
                'success': True,
                'analysis': analysis
            })
            
        except Exception as e:
            logging.error(f"Error getting analysis: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
        
    @web_bp.route('/api/requirements/<int:analysis_id>', methods=['DELETE'])
    def api_delete_requirements_analysis(analysis_id):
        """Delete a specific requirements analysis by ID"""
        try:
            success = db.delete_requirements_analysis(analysis_id)
            if not success:
                return jsonify({
                    'success': False,
                    'error': 'Analysis not found'
                }), 404
                
            return jsonify({
                'success': True,
                'message': f'Analysis {analysis_id} deleted successfully'
            })
            
        except Exception as e:
            logging.error(f"Error deleting analysis: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @web_bp.route('/api/requirements/filter', methods=['GET'])
    def api_filter_requirements_analyses():
        """Filter requirements analyses by domain"""
        try:
            # Get filter parameter
            filter_domain = request.args.get('domain', '').strip()
            
            if not filter_domain:
                # If no filter is provided, return all analyses
                analyses = db.get_all_requirements_analyses()
                return jsonify({
                    'success': True,
                    'analyses': analyses
                })
            
            # Get all analyses and filter them
            all_analyses = db.get_all_requirements_analyses()
            
            # Filter analyses that contain the specified domain
            filtered_analyses = []
            for analysis in all_analyses:
                domains = analysis['domains'].split(',')
                if any(filter_domain.lower() in domain.lower() for domain in domains):
                    filtered_analyses.append(analysis)
            
            return jsonify({
                'success': True,
                'analyses': filtered_analyses,
                'filter': filter_domain,
                'count': len(filtered_analyses)
            })
            
        except Exception as e:
            logging.error(f"Error filtering analyses: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
        
    @web_bp.route('/api/preview/<path:filename>')
    def preview_file(filename):
        """Preview text-based files"""
        try:
            # Ensure the uploads directory exists
            uploads_dir = os.path.join(os.getcwd(), 'uploads')
            file_path = os.path.join(uploads_dir, filename)
            
            if not os.path.exists(file_path):
                return jsonify({
                    'success': False,
                    'error': 'File not found'
                }), 404
            
            # Get file extension
            _, ext = os.path.splitext(filename)
            
            # For text files, return the content directly
            if ext.lower() == '.txt':
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                return jsonify({
                    'success': True,
                    'content': content,
                    'format': 'text'
                })
            
            # For other files, extract text using file processor
            from file_processor import FileProcessor
            processor = FileProcessor()
            
            if ext.lower() == '.pdf':
                content = processor.extract_text(file_path, 'pdf')
                return jsonify({
                    'success': True,
                    'content': content,
                    'format': 'pdf'
                })
            elif ext.lower() in ['.doc', '.docx']:
                content = processor.extract_text(file_path, 'docx')
                return jsonify({
                    'success': True,
                    'content': content,
                    'format': 'docx'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': 'Unsupported file format for preview'
                }), 400
        
        except Exception as e:
            logging.error(f"Error previewing file {filename}: {e}")
            return jsonify({
                'success': False,
                'error': f"Could not preview file: {str(e)}"
            }), 500
    
    # Add this route to web/routes.py

    @web_bp.route('/api/test/openai', methods=['GET'])
    def test_openai_api():
        """Test the OpenAI API connection"""
        try:
            from chatgpt_api import ChatGPTAPI
            import os
            from dotenv import load_dotenv
            
            # Reload environment variables
            load_dotenv()
            
            # Get API key
            api_key = os.getenv('OPENAI_API_KEY', '')
            
            if not api_key:
                return jsonify({
                    'success': False,
                    'error': 'API key is not configured in .env file'
                })
            
            # Test with a simple prompt
            api = ChatGPTAPI()
            test_response = api.generate_job_requirements_summary(
                ['Test'], 
                {'python': 100, 'javascript': 90, 'sql': 80, 'html': 70, 'css': 60}
            )
            
            # Check if we got an error response
            if test_response.startswith('Error:'):
                return jsonify({
                    'success': False,
                    'error': test_response,
                    'api_key_preview': f"{api_key[:3]}...{api_key[-3:]}" if len(api_key) > 6 else "Too short"
                })
            
            return jsonify({
                'success': True,
                'message': 'Successfully connected to OpenAI API',
                'response_preview': test_response[:200] + '...' if len(test_response) > 200 else test_response
            })
        
        except Exception as e:
            logging.error(f"Error testing OpenAI API: {e}")
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500
    
    app.register_blueprint(web_bp)