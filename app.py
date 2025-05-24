import asyncio
import logging
import datetime
from flask import Flask, render_template
from config import Config
from database.db import Database
from scraper.scraper import DjinniScraper
from web.routes import init_routes
import os
from scheduler import ScraperScheduler

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('scraper.log')
    ]
)

logger = logging.getLogger(__name__)

class DjinniApp:
    def __init__(self, config=None):
        self.config = config or Config()
        self.app = Flask(__name__, 
                         static_folder='static',
                         template_folder='web/templates')
        self.app.config['SECRET_KEY'] = self.config.SECRET_KEY
        self.app.config['DEBUG'] = self.config.DEBUG

        # Remove global loop reference
        self.app.loop = None

        self.db = Database(self.config.DATABASE_URL)
        self.db.init_db()

        self.scraper = DjinniScraper(self.db, self.config.MAX_CONCURRENT_REQUESTS)
        
        # Initialize scheduler
        self.scheduler = ScraperScheduler(self.app)
        
        # Load existing settings and update scheduler
        settings = self.db.get_scraper_settings()
        if settings:
            self.scheduler.update_schedule(settings)

        @self.app.context_processor
        def inject_now():
            return {'now': datetime.datetime.now()}

        # Pass the scheduler instance to init_routes
        init_routes(self.app, self.db, self.scraper, self.scheduler)
        
        logger.info("Application initialized")

        uploads_dir = os.path.join(os.getcwd(), 'uploads')
        if not os.path.exists(uploads_dir):
            os.makedirs(uploads_dir)
            logger.info(f"Created uploads directory: {uploads_dir}")
            
    def run(self, host=None, port=None):
        """Run the application"""
        try:
            self.app.run(
                host=host or self.config.HOST,
                port=port or self.config.PORT
            )
        finally:
            self.scheduler.shutdown()

if __name__ == '__main__':
    app = DjinniApp()
    app.run()