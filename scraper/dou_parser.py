import re
import json
import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import logging

logger = logging.getLogger(__name__)

class DouParser:
    """Parser for DOU job vacancies"""
    BASE_URL = 'https://jobs.dou.ua'
    
    def __init__(self):
        pass
    
    def parse_job_detail(self, html_content):
        """Parse job details from DOU vacancy page"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            job_data = {}
            
            # Extract job ID from canonical URL
            canonical_url = soup.select_one('link[rel="canonical"]')
            if canonical_url:
                job_data['url'] = canonical_url['href']
                job_id = self._extract_job_id(job_data['url'])
                job_data['job_id'] = job_id
            
            # Check if job is active (assumption: all scraped jobs are active)
            job_data['is_active'] = True
            
            # Get job title
            job_title = soup.select_one('h1.g-h2')
            if job_title:
                job_data['title'] = job_title.text.strip()
            
            # Get company name
            company_element = soup.select_one('.l-n a')
            if company_element:
                job_data['company_name'] = company_element.text.strip()
            
            # Get location
            location_element = soup.select_one('.place')
            if location_element:
                location_text = location_element.text.strip()
                job_data['location'] = location_text
                
                # Determine job type (Remote, Office, Hybrid)
                if 'віддалено' in location_text.lower():
                    job_data['job_type'] = 'Remote'
                elif 'офіс' in location_text.lower():
                    job_data['job_type'] = 'Office'
                else:
                    job_data['job_type'] = 'Hybrid'
            
            # Get description
            description_element = soup.select_one('.b-typo.vacancy-section')
            if description_element:
                job_data['description'] = description_element.get_text('\n').strip()
            
            # Get posted date
            date_element = soup.select_one('.date')
            if date_element:
                job_data['posted_date'] = self._parse_date(date_element.text.strip())
            
            # Get salary if available
            salary_data = self._extract_salary(job_data.get('description', ''))
            job_data.update(salary_data)
            
            # Extract category from breadcrumbs
            category_element = soup.select('.breadcrumbs a')
            if len(category_element) > 1:
                job_data['domain'] = category_element[1].text.strip()
            
            # Extract experience, skills, and domain from description
            self._extract_additional_info(job_data)
            
            # Default values
            job_data['employment_type'] = 'Full-time'  # Default assumption
            
            return job_data
        
        except Exception as e:
            logger.error(f"Error parsing DOU job: {str(e)}")
            return None
    
    def _extract_job_id(self, url):
        """Extract job ID from URL"""
        match = re.search(r'/vacancies/(\d+)/', url)
        return match.group(1) if match else None
    
    def _parse_date(self, date_text):
        """Parse date from text"""
        try:
            # Map Ukrainian month names to numbers
            month_map = {
                'січня': 1, 'лютого': 2, 'березня': 3, 'квітня': 4,
                'травня': 5, 'червня': 6, 'липня': 7, 'серпня': 8,
                'вересня': 9, 'жовтня': 10, 'листопада': 11, 'грудня': 12
            }
            
            # Regular parsing for format like "18 квітня 2025"
            parts = date_text.split()
            if len(parts) >= 3:
                day = int(parts[0])
                month_name = parts[1].lower()
                year = int(parts[2])
                
                month = None
                for ukr_month, month_num in month_map.items():
                    if ukr_month in month_name:
                        month = month_num
                        break
                
                if month:
                    return datetime.datetime(year, month, day)
            
            # Fallback to current date
            return datetime.datetime.now()
        
        except Exception as e:
            logger.error(f"Error parsing date: {e}")
            return datetime.datetime.now()
    
    def _extract_salary(self, text):
        """Extract salary information from job description"""
        result = {'salary_min': None, 'salary_max': None, 'currency': 'USD'}
        
        # Match salary patterns
        salary_patterns = [
            # $1000-2000
            r'\$\s*(\d+[\d\s]*(?:[.,]\d+)?)\s*(?:-|–|—)\s*\$?\s*(\d+[\d\s]*(?:[.,]\d+)?)',
            # from $1000
            r'(?:від|from)\s*\$\s*(\d+[\d\s]*(?:[.,]\d+)?)',
            # up to $2000
            r'(?:до|up to)\s*\$\s*(\d+[\d\s]*(?:[.,]\d+)?)',
            # $1000
            r'\$\s*(\d+[\d\s]*(?:[.,]\d+)?)'
        ]
        
        for pattern in salary_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if len(match.groups()) == 2:  # Range
                    min_val = match.group(1).replace(' ', '').replace(',', '.')
                    max_val = match.group(2).replace(' ', '').replace(',', '.')
                    result['salary_min'] = float(min_val)
                    result['salary_max'] = float(max_val)
                elif 'від' in text.lower() or 'from' in text.lower():  # Minimum
                    min_val = match.group(1).replace(' ', '').replace(',', '.')
                    result['salary_min'] = float(min_val)
                elif 'до' in text.lower() or 'up to' in text.lower():  # Maximum
                    max_val = match.group(1).replace(' ', '').replace(',', '.')
                    result['salary_max'] = float(max_val)
                else:  # Single value, treat as minimum
                    val = match.group(1).replace(' ', '').replace(',', '.')
                    result['salary_min'] = float(val)
                break
        
        return result
    
    def _extract_additional_info(self, job_data):
        """Extract additional information from job description"""
        description = job_data.get('description', '')
        
        # Extract experience years
        exp_patterns = [
            r'(\d+(?:[.,]\d+)?)\s*(?:\+)?\s*(?:рок(?:и|ів)|year[s]?)\s*(?:досвіду|experience)',
            r'досвід\s*(?:роботи)?\s*(?:від)?\s*(\d+(?:[.,]\d+)?)\s*(?:рок(?:и|ів)|year)',
            r'experience\s*(?:of)?\s*(\d+(?:[.,]\d+)?)\s*(?:\+)?\s*year'
        ]
        
        for pattern in exp_patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                exp_years = float(match.group(1).replace(',', '.'))
                job_data['experience_years'] = int(exp_years)
                break
        
        # Extract English level
        english_patterns = {
            r'\b(?:upper|upper-intermediate|b2)\b': 'Upper-Intermediate',
            r'\b(?:advanced|fluent|c1|c2)\b': 'Advanced/Fluent',
            r'\b(?:intermediate|b1)\b': 'Intermediate',
            r'\b(?:pre-intermediate|a2)\b': 'Pre-Intermediate',
            r'\b(?:beginner|elementary|a1)\b': 'Beginner/Elementary'
        }
        
        for pattern, level in english_patterns.items():
            if re.search(pattern, description, re.IGNORECASE):
                job_data['english_level'] = level
                break
        
        # Extract domain
        domain_patterns = {
            r'\b(?:product|продукт)\b': 'Product',
            r'\b(?:outsource|outsourcing|аутсорс)\b': 'Outsource',
            r'\b(?:outstaff|аутстаф)\b': 'Outstaff',
            r'\b(?:fintech)\b': 'Fintech',
            r'\b(?:ecommerce|e-commerce)\b': 'E-commerce',
            r'\b(?:healthcare|медицин[а|и|і])\b': 'Healthcare'
        }
        
        for pattern, domain in domain_patterns.items():
            if re.search(pattern, description, re.IGNORECASE):
                job_data['domain'] = domain
                break