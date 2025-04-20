import re
import requests
import logging
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

class SitemapProcessor:
    def __init__(self, db):
        self.db = db
        
    def process_djinni_sitemap(self, sitemap_url="https://djinni.co/sitemap.xml"):
        try:
            logger.info(f"Processing Djinni sitemap: {sitemap_url}")
            
            # Добавляем заголовки, имитирующие обычный браузер
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Cache-Control': 'max-age=0',
            }
            
            # Создаем сессию и устанавливаем заголовки
            session = requests.Session()
            response = session.get(sitemap_url, headers=headers)
            response.raise_for_status()
            
            root = ET.fromstring(response.content)
            urls = []
            
            ns = {'sm': 'https://www.sitemaps.org/schemas/sitemap/0.9'}
            
            for url_element in root.findall(".//sm:url", ns):
                loc_element = url_element.find("sm:loc", ns)
                if loc_element is not None:
                    url = loc_element.text
                    
                    job_id_match = re.search(r'/jobs/(\d+)-', url)
                    if job_id_match:
                        urls.append(url)
                        self.db.add_job_url(url, 'djinni')
            
            logger.info(f"Added {len(urls)} Djinni job URLs to the database")
            return len(urls)
        except Exception as e:
            logger.error(f"Error processing Djinni sitemap: {e}")
            return 0
    
    def process_dou_sitemap(self, sitemap_url="https://jobs.dou.ua/sitemap-vacancies.xml"):
        """Обрабатывает карту сайта DOU и добавляет все URL вакансий в базу данных"""
        try:
            logger.info(f"Processing DOU sitemap: {sitemap_url}")
            
            # Добавляем заголовки, имитирующие обычный браузер
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Cache-Control': 'max-age=0',
            }
            
            # Создаем сессию и устанавливаем заголовки
            session = requests.Session()
            response = session.get(sitemap_url, headers=headers)
            response.raise_for_status()
            
            # Парсим XML
            root = ET.fromstring(response.content)
            # Находим все URLs в карте сайта
            urls = []
            
            # Определяем namespace из XML
            ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
            
            for url_element in root.findall(".//sm:url", ns):
                loc_element = url_element.find("sm:loc", ns)
                if loc_element is not None:
                    url = loc_element.text
                    urls.append(url)
                    # Добавляем URL в базу данных
                    self.db.add_job_url(url, 'dou')
            
            logger.info(f"Added {len(urls)} DOU job URLs to the database")
            return len(urls)
        except Exception as e:
            logger.error(f"Error processing DOU sitemap: {e}")
            return 0
    
    def refresh_job_urls(self):
        djinni_count = self.process_djinni_sitemap()
        dou_count = self.process_dou_sitemap()
        
        return {
            'djinni': djinni_count,
            'dou': dou_count,
            'total': dou_count + djinni_count
        }