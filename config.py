import os
from dotenv import load_dotenv

# Load .env file if it exists
load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev_key_change_in_production')
    DEBUG = os.getenv('DEBUG', 'False').lower() in ('true', '1', 't')
    
    # Database settings
    DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///djinni_jobs.db')
    
    # Scraper settings
    MAX_CONCURRENT_REQUESTS = int(os.getenv('MAX_CONCURRENT_REQUESTS', 5))
    DEFAULT_PAGES_TO_SCRAPE = int(os.getenv('DEFAULT_PAGES_TO_SCRAPE', 1))
    
    # Web server settings
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', 5000))