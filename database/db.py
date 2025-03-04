from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base
from .models import Base, Job

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