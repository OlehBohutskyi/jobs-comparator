import asyncio
import aiohttp
import logging
from urllib.parse import urljoin, quote
from .parser import DjinniParser
from .translator import Translator

class DjinniScraper:
    BASE_URL = 'https://djinni.co'
    JOB_LIST_URL = 'https://djinni.co/jobs/'
    
    def __init__(self, db, max_concurrent=5):
        self.parser = DjinniParser()
        self.translator = Translator()
        self.db = db
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.logger = logging.getLogger(__name__)
        self.session = None
        
    async def init_session(self):
        if self.session is None:
            self.session = aiohttp.ClientSession(headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9,uk;q=0.8'
            })
        
    async def close_session(self):
        if self.session:
            await self.session.close()
            self.session = None
            
    async def search_jobs(self, query=None, pages=1):
        """Search jobs with optional query and scrape multiple pages"""
        await self.init_session()
        self.logger.info(f"Starting job search with query: {query}, pages: {pages}")
        
        # Build search URL
        search_url = self.JOB_LIST_URL
        if query:
            search_url = f"{self.JOB_LIST_URL}?all_keywords={quote(query)}"
        
        job_ids = []
        
        try:
            # Scrape multiple pages if requested
            for page in range(1, pages + 1):
                page_url = f"{search_url}&page={page}" if "?" in search_url else f"{search_url}?page={page}"
                
                # Get job listing page
                async with self.semaphore, self.session.get(page_url) as response:
                    if response.status != 200:
                        self.logger.error(f"Failed to get job listing page: {response.status}")
                        continue
                    
                    html_content = await response.text()
                    job_items = self.parser.parse_job_list(html_content)
                    
                    # Process each job
                    tasks = []
                    for job_item in job_items:
                        if job_item and 'job_id' in job_item:
                            job_ids.append(job_item['job_id'])
                            tasks.append(self.process_job(job_item))
                    
                    # Process jobs concurrently
                    await asyncio.gather(*tasks)
        except Exception as e:
            self.logger.error(f"Error during job search: {e}")
        finally:
            await self.close_session()
            
        return job_ids
        
    async def process_job(self, job_list_data):
        """Process a single job: get details, translate, and save to DB"""
        try:
            # Get detailed job information
            job_detail = await self.get_job_detail(job_list_data['url'])
            
            # Merge listing and detail data
            job_data = {**job_list_data, **(job_detail or {})}
            
            # Translate fields
            job_data = await self.translator.translate_job_data(job_data)
            
            # Save to database
            self.db.add_job(job_data)
            
            return job_data['job_id']
        except Exception as e:
            self.logger.error(f"Error processing job {job_list_data.get('job_id', 'unknown')}: {e}")
            return None
            
    async def get_job_detail(self, job_url):
        """Get and parse detailed job information"""
        await self.init_session()
        
        try:
            async with self.semaphore, self.session.get(job_url) as response:
                if response.status != 200:
                    self.logger.error(f"Failed to get job details: {response.status}")
                    return None
                
                html_content = await response.text()
                return self.parser.parse_job_detail(html_content)
        except Exception as e:
            self.logger.error(f"Error getting job details: {e}")
            return None
    
    async def scrape_sequential_jobs(self, start_id, count):
        """Scrape jobs sequentially by ID"""
        await self.init_session()
        self.logger.info(f"Starting sequential job scraping from ID {start_id}, count: {count}")
        
        job_ids = []
        
        try:
            for job_id in range(start_id, start_id + count):
                job_url = f"{self.BASE_URL}/jobs/{job_id}"
                
                try:
                    async with self.semaphore, self.session.get(job_url) as response:
                        if response.status != 200:
                            self.logger.error(f"Failed to get job at ID {job_id}: {response.status}")
                            continue
                        
                        html_content = await response.text()
                        job_data = self.parser.parse_job_detail(html_content)
                        
                        if job_data:
                            # Ensure job_id is set
                            job_data['job_id'] = str(job_id)
                            
                            # Skip translation
                            self.db.add_job(job_data)
                            job_ids.append(str(job_id))
                            
                            # Update progress
                            self.db.update_scraping_progress('djinni', job_id)
                except Exception as e:
                    self.logger.error(f"Error processing job at ID {job_id}: {e}")
        except Exception as e:
            self.logger.error(f"Error during sequential job scraping: {e}")
        finally:
            await self.close_session()
            
        return job_ids
