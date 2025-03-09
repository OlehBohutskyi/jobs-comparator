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
