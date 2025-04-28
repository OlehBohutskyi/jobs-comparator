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

    def _standardize_location(self, location_text):
        if not location_text:
            return "Other"
        
        text = location_text.lower()
        
        if any(keyword in text for keyword in ['remote', 'віддалено', 'удаленно', 'remotely']):
            return "Remote"
        
        if any(keyword in text for keyword in ['ukraine', 'україна', 'украина', 'київ', 'kyiv', 'львів', 'lviv']):
            return "Ukraine"
        
        if any(keyword in text for keyword in ['worldwide', 'the whole world', 'global', 'any location', 'весь світ']):
            return "Whole World"
        
        # Default case
        return "Other"
    
    def parse_job_detail(self, html_content):
        """Parse job details from DOU vacancy page"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            job_data = {}

            canonical_url = soup.select_one('link[rel="canonical"]')
            if canonical_url:
                job_data['url'] = canonical_url['href']
                job_id = self._extract_job_id(job_data['url'])
                job_data['job_id'] = job_id

            job_data['is_active'] = True

            job_title = soup.select_one('h1.g-h2')
            if job_title:
                job_data['title'] = job_title.text.strip()

            company_element = soup.select_one('.l-n a')
            if company_element:
                job_data['company_name'] = company_element.text.strip()

            location_element = soup.select_one('.place')
            if location_element:
                location_text = location_element.text.strip()
                job_data['location'] = self._standardize_location(location_text)

                if 'віддалено' in location_text.lower() or 'remote' in location_text.lower():
                    job_data['job_type'] = 'Remote'
                elif 'офіс' in location_text.lower() or 'office' in location_text.lower():
                    job_data['job_type'] = 'Office'
                else:
                    job_data['job_type'] = 'Hybrid'
            
            description_element = soup.select_one('.b-typo.vacancy-section')
            if description_element:
                job_data['description'] = description_element.get_text('\n').strip()
            
            date_element = soup.select_one('.date')
            if date_element:
                job_data['posted_date'] = self._parse_date(date_element.text.strip())
            
            salary_element = soup.select_one('span.salary')
            if salary_element:
                salary_text = salary_element.text.strip()
                job_data.update(self._parse_salary_from_text(salary_text))
            
            category_element = soup.select('.breadcrumbs a')
            if len(category_element) > 1:
                job_data['domain'] = category_element[1].text.strip()
            
            self._extract_additional_info(job_data)
            
            job_data['employment_type'] = 'Full-time'
            
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
    
    def _parse_salary_from_text(self, text):
        """Extract salary information directly from the salary element text"""
        result = {'salary_min': None, 'salary_max': None, 'currency': 'USD'}
        
        salary_pattern = r'\$\s*(\d+[\d\s]*(?:[.,]\d+)?)\s*(?:[-–—])\s*(\d+[\d\s]*(?:[.,]\d+)?)'
        single_value_pattern = r'\$\s*(\d+[\d\s]*(?:[.,]\d+)?)'
        
        # Try to match salary range
        match = re.search(salary_pattern, text)
        if match:
            min_val = match.group(1).replace(' ', '').replace(',', '.')
            max_val = match.group(2).replace(' ', '').replace(',', '.')
            result['salary_min'] = float(min_val)
            result['salary_max'] = float(max_val)
            result['currency'] = 'USD' 
            return result
        
        match = re.search(single_value_pattern, text)
        if match:
            val = match.group(1).replace(' ', '').replace(',', '.')
            result['salary_min'] = float(val)
            result['currency'] = 'USD'
            return result
        
        # Check for other currencies
        if '€' in text:
            result['currency'] = 'EUR'
        elif '₴' in text or 'грн' in text.lower():
            result['currency'] = 'UAH'
        
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