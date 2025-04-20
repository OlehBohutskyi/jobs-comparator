import asyncio
import aiohttp
import logging
from .dou_parser import DouParser
from .translator import Translator

class DouScraper:
    """Scraper for DOU job vacancies"""
    BASE_URL = 'https://jobs.dou.ua'
    
    def __init__(self, db, max_concurrent=5):
        self.parser = DouParser()
        self.translator = Translator()
        self.db = db
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.logger = logging.getLogger(__name__)
        self.session = None
    
    async def init_session(self):
        """Initialize HTTP session with appropriate headers"""
        if self.session is None:
            self.session = aiohttp.ClientSession(headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9,uk;q=0.8',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Cache-Control': 'max-age=0',
            })
    
    async def close_session(self):
        """Close HTTP session if open"""
        if self.session:
            await self.session.close()
            self.session = None
    
    async def get_job_detail(self, job_url):
        """Get and parse job details from URL"""
        await self.init_session()
        
        try:
            self.logger.info(f"Fetching DOU job: {job_url}")
            async with self.semaphore, self.session.get(job_url) as response:
                if response.status != 200:
                    self.logger.error(f"Failed to get DOU job details: {response.status}")
                    return None
                
                html_content = await response.text()
                job_data = self.parser.parse_job_detail(html_content)
                
                if job_data:
                    self.logger.info(f"Successfully parsed DOU job: {job_data.get('title', 'Unknown title')}")
                else:
                    self.logger.warning(f"No data extracted from DOU job page: {job_url}")
                
                return job_data
        except Exception as e:
            self.logger.error(f"Error getting DOU job details: {str(e)}")
            return None
        finally:
            await self.close_session()
    
    async def process_job(self, job_url):
        """Process a single job: get details, translate, and save to DB"""
        try:
            # Get detailed job information
            job_data = await self.get_job_detail(job_url)
            
            if not job_data:
                self.logger.error(f"Failed to extract data from {job_url}")
                return None
            
            # Translate fields
            translated_job_data = await self.translator.translate_job_data(job_data)
            
            # Save to database
            self.db.add_job(translated_job_data)
            
            # Mark URL as processed
            self.db.mark_job_url_processed(job_url, True)
            
            return translated_job_data.get('job_id')
        except Exception as e:
            self.logger.error(f"Error processing DOU job {job_url}: {str(e)}")
            # Mark URL as processed with error
            self.db.mark_job_url_processed(job_url, False)
            return None