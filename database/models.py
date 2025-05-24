from sqlalchemy import Column, Integer, String, Float, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class Job(Base):
    __tablename__ = 'jobs'
    
    id = Column(Integer, primary_key=True)
    job_id = Column(String(50), unique=True)
    title = Column(String(255))
    title_en = Column(String(255))
    company_name = Column(String(255))
    company_name_en = Column(String(255))
    salary_min = Column(Float, nullable=True)
    salary_max = Column(Float, nullable=True)
    currency = Column(String(3), default='USD')
    description = Column(Text)
    description_en = Column(Text)
    location = Column(String(255))
    location_en = Column(String(255))
    location_type = Column(String(50), nullable=True)
    experience_years = Column(Integer, nullable=True)
    english_level = Column(String(50), nullable=True)
    job_type = Column(String(50))  # Remote, Office, Hybrid
    employment_type = Column(String(50))  # Full-time, Part-time, Contract
    category = Column(String(100))
    category_en = Column(String(100))
    domain = Column(String(100), nullable=True)
    domain_en = Column(String(100), nullable=True)
    url = Column(String(255))
    posted_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'job_id': self.job_id,
            'title': self.title_en or self.title,
            'company_name': self.company_name_en or self.company_name,
            'salary_min': self.salary_min,
            'salary_max': self.salary_max,
            'currency': self.currency,
            'description': self.description_en or self.description,
            'location': self.location_en or self.location,
            'location_type': self.location_type,
            'experience_years': self.experience_years,
            'english_level': self.english_level,
            'job_type': self.job_type,
            'employment_type': self.employment_type,
            'category': self.category_en or self.category,
            'domain': self.domain_en or self.domain,
            'url': self.url,
            'posted_date': self.posted_date.isoformat() if self.posted_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_active': self.is_active
        }

    
class ScrapingProgress(Base):
    __tablename__ = 'scraping_progress'

    id = Column(Integer, primary_key=True)
    site = Column(String(50), unique=True)
    last_job_id = Column(Integer, default=0)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class ScrapingStatus(Base):
    __tablename__ = 'scraping_status'
    
    id = Column(Integer, primary_key=True)
    is_scraping = Column(Boolean, default=False)
    total_jobs = Column(Integer, default=0)
    completed_jobs = Column(Integer, default=0)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class JobUrl(Base):
    __tablename__ = 'job_urls'
    
    id = Column(Integer, primary_key=True)
    url = Column(String(255), unique=True, nullable=False)
    source = Column(String(50), nullable=False)
    job_id = Column(String(50), nullable=True)
    is_processed = Column(Boolean, default=False)
    status = Column(String(50), default='pending')  # 'pending', 'success', 'error'
    created_at = Column(DateTime, server_default=func.now())
    processed_at = Column(DateTime, nullable=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'url': self.url,
            'source': self.source,
            'job_id': self.job_id,
            'is_processed': self.is_processed,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'processed_at': self.processed_at.isoformat() if self.processed_at else None
        }


class RequirementsAnalysis(Base):
    __tablename__ = 'requirements_analysis'
    
    id = Column(Integer, primary_key=True)
    domains = Column(String(255), nullable=False)
    top_words = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    is_educational_analysis = Column(Boolean, default=False)
    education_program_file = Column(String(255), nullable=True)
    education_program_filename = Column(String(255), nullable=True)
    education_program_filetype = Column(String(50), nullable=True)
    education_program_text = Column(Text, nullable=True)
    education_program_analysis = Column(Text, nullable=True)

    
    def to_dict(self):
        return {
            'id': self.id,
            'domains': self.domains,
            'top_words': self.top_words,
            'summary': self.summary,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_educational_analysis': self.is_educational_analysis,
            'education_program_file': self.education_program_file,
            'education_program_filename': self.education_program_filename,
            'education_program_filetype': self.education_program_filetype,
            'education_program_text': self.education_program_text,
            'education_program_analysis': self.education_program_analysis
        }


class ScraperSettings(Base):
    __tablename__ = 'scraper_settings'
    
    id = Column(Integer, primary_key=True)
    schedule_type = Column(String(50), nullable=False)  # 'daily', 'weekly', 'custom'
    run_time = Column(String(8), nullable=True)  # HH:MM format
    cron_expression = Column(String(100), nullable=True)
    next_run = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    def to_dict(self):
        return {
            'id': self.id,
            'schedule_type': self.schedule_type,
            'run_time': self.run_time,
            'cron_expression': self.cron_expression,
            'next_run': self.next_run.isoformat() if self.next_run else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

