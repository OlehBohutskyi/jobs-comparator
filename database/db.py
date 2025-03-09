from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base
from .models import Base, Job, ScrapingProgress, ScrapingStatus

class Database:
    def __init__(self, db_url='sqlite:///djinni_jobs.db'):
        self.engine = create_engine(db_url)
        self.session_factory = sessionmaker(bind=self.engine)
        self.Session = scoped_session(self.session_factory)
        
    def init_db(self):
        Base.metadata.create_all(self.engine)
        
    def get_session(self):
        return self.Session()
        
    def close_session(self):
        self.Session.remove()
        
    def add_job(self, job_data):
        session = self.get_session()
        try:
            existing_job = session.query(Job).filter_by(job_id=job_data['job_id']).first()
            
            if existing_job:
                # Update existing job
                for key, value in job_data.items():
                    setattr(existing_job, key, value)
                job = existing_job
            else:
                # Create new job
                job = Job(**job_data)
                session.add(job)
                
            session.commit()
            return job.id
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
            
    def get_job(self, job_id):
        session = self.get_session()
        try:
            job = session.query(Job).filter_by(job_id=job_id).first()
            return job.to_dict() if job else None
        finally:
            session.close()
            
    def get_all_jobs(self):
        session = self.get_session()
        try:
            jobs = session.query(Job).all()
            return [job.to_dict() for job in jobs]
        finally:
            session.close()
            
    def search_jobs(self, title):
        session = self.get_session()
        try:
            jobs = session.query(Job).filter(
                (Job.title.ilike(f'%{title}%')) | 
                (Job.title_en.ilike(f'%{title}%'))
            ).all()
            return [job.to_dict() for job in jobs]
        finally:
            session.close()

    def get_last_scraped_job_id(self, site='djinni'):
        session = self.get_session()
        try:
            progress = session.query(ScrapingProgress).filter_by(site=site).first()
            print(progress)
            return progress.last_job_id if progress else 0
        
        finally:
            session.close()

    def update_last_job_id(self, site, job_id):
        session = self.get_session()
        try:
            progress = session.query(ScrapingProgress).filter_by(site=site).first()
            if progress:
                progress.last_job_id = job_id
            else:
                progress = ScrapingProgress(site=site, last_job_id=job_id)
                session.add(progress)
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def start_scraping(self, total_jobs):
        session = self.get_session()
        try:
            # Check if there's an existing status
            status = session.query(ScrapingStatus).first()
            if status:
                status.is_scraping = True
                status.total_jobs = total_jobs
                status.completed_jobs = 0
            else:
                status = ScrapingStatus(
                    is_scraping=True,
                    total_jobs=total_jobs,
                    completed_jobs=0
                )
                session.add(status)
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def update_scraping_progress(self, completed_jobs=None):
        session = self.get_session()
        try:
            status = session.query(ScrapingStatus).first()
            if status:
                if completed_jobs is not None:
                    status.completed_jobs = completed_jobs
                else:
                    status.completed_jobs += 1
                session.commit()
                return status.completed_jobs
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
            
    def end_scraping(self):
        session = self.get_session()
        try:
            status = session.query(ScrapingStatus).first()
            if status:
                status.is_scraping = False
                session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
            
    def get_scraping_status(self):
        session = self.get_session()
        try:
            status = session.query(ScrapingStatus).first()
            if status:
                return {
                    'is_scraping': status.is_scraping,
                    'total_jobs': status.total_jobs,
                    'completed_jobs': status.completed_jobs
                }
            return {
                'is_scraping': False,
                'total_jobs': 0,
                'completed_jobs': 0
            }
        finally:
            session.close()
