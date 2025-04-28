import asyncio
import logging
import datetime
from flask import Flask, render_template
from config import Config
from database.db import Database
from scraper.scraper import DjinniScraper
from web.routes import init_routes
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('scraper.log')
    ]
)

logger = logging.getLogger(__name__)

global_loop = asyncio.new_event_loop()
asyncio.set_event_loop(global_loop)

class DjinniApp:
    def __init__(self, config=None):
        self.config = config or Config()
        self.app = Flask(__name__, 
                         static_folder='static',
                         template_folder='web/templates')
        self.app.config['SECRET_KEY'] = self.config.SECRET_KEY
        self.app.config['DEBUG'] = self.config.DEBUG

        self.app.loop = global_loop

        self.db = Database(self.config.DATABASE_URL)
        self.db.init_db()

        self.scraper = DjinniScraper(self.db, self.config.MAX_CONCURRENT_REQUESTS)

        @self.app.context_processor
        def inject_now():
            return {'now': datetime.datetime.now()}

        init_routes(self.app, self.db, self.scraper)
        
        logger.info("Application initialized")

        uploads_dir = os.path.join(os.getcwd(), 'uploads')
        if not os.path.exists(uploads_dir):
            os.makedirs(uploads_dir)
            logger.info(f"Created uploads directory: {uploads_dir}")
    
    def run(self):
        """Run the Flask web application"""
        try:
            logger.info(f"Starting web server on {self.config.HOST}:{self.config.PORT}")
            self.app.run(
                host=self.config.HOST,
                port=self.config.PORT,
                debug=self.config.DEBUG
            )
        except Exception as e:
            logger.error(f"Error running application: {e}")
        finally:
            # Clean up
            if global_loop and global_loop.is_running():
                global_loop.close()

if __name__ == '__main__':
    app = DjinniApp()
    app.run()