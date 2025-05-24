import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta
import requests
import pytz
from apscheduler.job import Job

logger = logging.getLogger(__name__)

class ScraperScheduler:
    def __init__(self, app=None):
        self.app = app
        self.scheduler = BackgroundScheduler(timezone=pytz.UTC)
        self.scheduler.start()
        self.job = None
        self.is_running = False
        self.is_paused = False
        
    def init_app(self, app):
        self.app = app

    def _run_scraper(self):
        """Execute the scraper job"""
        if self.is_running:
            logger.info("Skipping scheduled run as previous job is still running")
            return
            
        with self.app.app_context():
            try:
                logger.info("Running scheduled scraper job")
                self.is_running = True
                host = self.app.config.get('HOST', 'localhost')
                port = self.app.config.get('PORT', 5000)
                url = f'http://{host}:{port}/api/scrape/next'
                
                response = requests.get(url)
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"Scraping completed. Results: {data}")
                else:
                    logger.error(f"Scraping failed with status code: {response.status_code}")
            except Exception as e:
                logger.error(f"Error running scraper: {e}")
            finally:
                self.is_running = False

    def update_schedule(self, settings):
        """Update the scraper schedule based on settings"""
        if self.job:
            self.job.remove()
            self.job = None
            self.is_paused = False

        if not settings:
            logger.info("No settings provided, scraper not scheduled")
            return

        schedule_type = settings.get('schedule_type')
        if not schedule_type:
            return

        try:
            if schedule_type == 'interval':
                interval_seconds = settings.get('interval_seconds', 300)  # Default 5 minutes
                self.job = self.scheduler.add_job(
                    self._run_scraper,
                    trigger=IntervalTrigger(seconds=interval_seconds),
                    id='scraper_job'
                )
                logger.info(f"Scheduled scraper with {interval_seconds} seconds interval")
            elif schedule_type == 'daily':
                run_time = settings.get('run_time')
                if run_time:
                    hour, minute = map(int, run_time.split(':'))
                    self.job = self.scheduler.add_job(
                        self._run_scraper,
                        trigger='cron',
                        hour=hour,
                        minute=minute,
                        id='scraper_job'
                    )
                    logger.info(f"Scheduled daily scraper at {run_time}")
            elif schedule_type == 'weekly':
                run_time = settings.get('run_time')
                if run_time:
                    hour, minute = map(int, run_time.split(':'))
                    self.job = self.scheduler.add_job(
                        self._run_scraper,
                        trigger='cron',
                        day_of_week='mon',
                        hour=hour,
                        minute=minute,
                        id='scraper_job'
                    )
                    logger.info(f"Scheduled weekly scraper at {run_time}")

        except Exception as e:
            logger.error(f"Error scheduling scraper: {e}")

    def stop_scraping(self):
        """Stop the current scraping job"""
        if self.job:
            self.scheduler.pause_job('scraper_job')
            self.is_paused = True
            self.is_running = False
        logger.info("Scraping stopped")

    def resume_scraping(self):
        """Resume the scraping job"""
        if self.job:
            self.scheduler.resume_job('scraper_job')
            self.is_paused = False
        logger.info("Scraping resumed")

    def get_status(self):
        """Get current scraping status"""
        status = {
            'is_running': self.is_running,
            'has_job': self.job is not None,
            'is_paused': self.is_paused
        }

        if self.job:
            next_run = self.job.next_run_time
            if next_run:
                status['next_run'] = next_run.timestamp()

        return status

    def shutdown(self):
        """Shutdown the scheduler"""
        if self.scheduler:
            self.scheduler.shutdown() 