from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base
from .models import Base, Job, ScrapingProgress, ScrapingStatus, JobUrl, RequirementsAnalysis
import datetime, re

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
            job_data_copy = job_data.copy()
            
            location_type = job_data_copy.pop('location_type', None)
    
            if location_type:
                print(f"Location type for job {job_data_copy.get('job_id')}: {location_type}")
            
            existing_job = session.query(Job).filter_by(job_id=job_data_copy['job_id']).first()
            
            if existing_job:
                # Update existing job
                for key, value in job_data_copy.items():
                    setattr(existing_job, key, value)
                job = existing_job
            else:
                # Create new job
                job = Job(**job_data_copy)
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

    def add_job_url(self, url, source):
        session = self.get_session()
        try:
            existing_url = session.query(JobUrl).filter_by(url=url).first()
            if not existing_url:
                job_id = None
                if source == 'djinni':
                    match = re.search(r'/jobs/(\d+)-', url)
                    if match:
                        job_id = match.group(1)
                elif source == 'dou':
                    match = re.search(r'/vacancies/(\d+)/', url)
                    if match:
                        job_id = match.group(1)
                    
                job_url = JobUrl(url=url, source=source, job_id=job_id)
                session.add(job_url)
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def mark_job_url_processed(self, url, success=True):
        session = self.get_session()
        try:
            job_url = session.query(JobUrl).filter_by(url=url).first()
            if job_url:
                job_url.is_processed = True
                job_url.processed_at = datetime.datetime.now()
                job_url.status = 'success' if success else 'error'
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def get_next_job_urls(self):
        session = self.get_session()
        try:
            djinni_url = session.query(JobUrl).filter_by(
                source='djinni', is_processed=False
            ).first()
            
            dou_url = session.query(JobUrl).filter_by(
                source='dou', is_processed=False
            ).first()
            
            result = []
            if djinni_url:
                result.append(djinni_url.to_dict())
            if dou_url:
                result.append(dou_url.to_dict())
            
            return result
        finally:
            session.close()

    def count_unprocessed_job_urls(self):
        session = self.get_session()
        try:
            djinni_count = session.query(JobUrl).filter_by(
                source='djinni', is_processed=False
            ).count()
            
            dou_count = session.query(JobUrl).filter_by(
                source='dou', is_processed=False
            ).count()
            
            return {
                'djinni': djinni_count,
                'dou': dou_count,
                'total': djinni_count + dou_count
            }
        finally:
            session.close()


    def add_requirements_analysis(self, domains, top_words=None, summary=None, 
                                is_educational_analysis=False, education_program_file=None,
                                education_program_filename=None, education_program_filetype=None,
                                education_program_text=None, education_program_analysis=None):
        """Add a new requirements analysis record"""
        session = self.get_session()
        try:
            analysis = RequirementsAnalysis(
                domains=domains,
                top_words=top_words,
                summary=summary,
                is_educational_analysis=is_educational_analysis,
                education_program_file=education_program_file,
                education_program_filename=education_program_filename,
                education_program_filetype=education_program_filetype,
                education_program_text=education_program_text,
                education_program_analysis=education_program_analysis
            )
            session.add(analysis)
            session.commit()
            return analysis.id
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()


    def update_requirements_analysis(self, analysis_id, top_words=None, summary=None,
                                    education_program_analysis=None):
        """Update an existing requirements analysis record"""
        session = self.get_session()
        try:
            analysis = session.query(RequirementsAnalysis).filter_by(id=analysis_id).first()
            if analysis:
                if top_words is not None:
                    analysis.top_words = top_words
                if summary is not None:
                    analysis.summary = summary
                if education_program_analysis is not None:
                    analysis.education_program_analysis = education_program_analysis
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def get_educational_analyses(self):
        """Get all requirements analyses that include educational program analysis"""
        session = self.get_session()
        try:
            analyses = session.query(RequirementsAnalysis).filter_by(
                is_educational_analysis=True
            ).order_by(RequirementsAnalysis.created_at.desc()).all()
            return [analysis.to_dict() for analysis in analyses]
        finally:
            session.close()


    def get_regular_analyses(self):
        """Get all requirements analyses that don't include educational program analysis"""
        session = self.get_session()
        try:
            analyses = session.query(RequirementsAnalysis).filter_by(
                is_educational_analysis=False
            ).order_by(RequirementsAnalysis.created_at.desc()).all()
            return [analysis.to_dict() for analysis in analyses]
        finally:
            session.close()


    def get_requirements_analysis(self, analysis_id):
        """Get a requirements analysis by ID"""
        session = self.get_session()
        try:
            analysis = session.query(RequirementsAnalysis).filter_by(id=analysis_id).first()
            return analysis.to_dict() if analysis else None
        finally:
            session.close()

    def get_all_requirements_analyses(self):
        """Get all requirements analyses"""
        session = self.get_session()
        try:
            analyses = session.query(RequirementsAnalysis).order_by(RequirementsAnalysis.created_at.desc()).all()
            return [analysis.to_dict() for analysis in analyses]
        finally:
            session.close()

    def get_jobs_by_domains(self, domains, limit=100):
        """Get jobs filtered by domain"""
        session = self.get_session()
        try:
            jobs = []
            for domain in domains:
                domain_jobs = session.query(Job).filter(
                    Job.domain.ilike(f'%{domain}%') | Job.domain_en.ilike(f'%{domain}%')
                ).limit(limit).all()
                
                jobs.extend([job.to_dict() for job in domain_jobs])
            
            return jobs
        finally:
            session.close()

    
    
    def delete_requirements_analysis(self, analysis_id):
        """Delete a requirements analysis by ID"""
        session = self.get_session()
        try:
            analysis = session.query(RequirementsAnalysis).filter_by(id=analysis_id).first()
            if analysis:
                session.delete(analysis)
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
