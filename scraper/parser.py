import re
import datetime
from bs4 import BeautifulSoup
from urllib.parse import urljoin

class DjinniParser:
    BASE_URL = 'https://djinni.co'
    
    def __init__(self):
        pass
        
    def parse_job_list(self, html_content):
        """Parse the job listing page and extract job items"""
        soup = BeautifulSoup(html_content, 'html.parser')
        job_items = []
        
        # Find all job items
        job_elements = soup.select('ul.list-jobs li.mb-4')
        
        for job_element in job_elements:
            try:
                job_data = self._extract_job_list_item(job_element)
                if job_data:
                    job_items.append(job_data)
            except Exception as e:
                print(f"Error parsing job element: {e}")
                
        return job_items
        
    def _extract_job_list_item(self, job_element):
        """Extract data from a single job listing item"""
        job_data = {}
        
        # Get job title and URL
        job_link = job_element.select_one('h2.fs-3 a')
        if job_link:
            job_data['title'] = job_link.text.strip()
            job_data['url'] = urljoin(self.BASE_URL, job_link.get('href', ''))
            job_data['job_id'] = self._extract_job_id(job_data['url'])
        else:
            return None
            
        # Get company name
        company_element = job_element.select_one('a[data-analytics="company_page"]')
        if company_element:
            job_data['company_name'] = company_element.text.strip()
            
        # Get salary range
        salary_element = job_element.select_one('.text-success')
        if salary_element:
            job_data.update(self._parse_salary(salary_element.text.strip()))
            
        # Get job metadata
        job_meta_element = job_element.select_one('.fw-medium.d-flex')
        if job_meta_element:
            job_meta = job_meta_element.get_text(' ').strip()
            job_data.update(self._parse_job_meta(job_meta))
            
        # Get job description preview
        description_element = job_element.select_one('.js-original-text')
        if description_element:
            job_data['description'] = description_element.text.strip()
        else:
            desc_element = job_element.select_one('.js-truncated-text')
            if desc_element:
                job_data['description'] = desc_element.text.strip()
        
        return job_data
    
    def parse_job_detail(self, html_content):
        """Parse the job detail page and extract comprehensive job information"""
        soup = BeautifulSoup(html_content, 'html.parser')
        job_data = {}
        
        # Get job title
        job_title = soup.select_one('h1')
        if job_title:
            job_data['title'] = job_title.text.strip()
        
        # Get job URL and ID
        job_data['url'] = soup.select_one('link[rel="canonical"]')['href']
        job_data['job_id'] = self._extract_job_id(job_data['url'])
        
        # Get company name
        company_element = soup.select_one('a[data-analytics="company_page"]') or soup.select_one('.col a.text-reset')
        if company_element:
            job_data['company_name'] = company_element.text.strip()
        
        # Get job description
        description_element = soup.select_one('.job-post__description')
        if description_element:
            job_data['description'] = description_element.get_text('\n').strip()
        
        # Get job metadata from sidebar
        sidebar = soup.select_one('aside')
        if sidebar:
            # Experience
            exp_element = sidebar.select_one('li:contains("років досвіду")')
            if exp_element:
                job_data['experience_years'] = self._extract_experience(exp_element.text)
            
            # English level
            english_element = sidebar.select_one('li:contains("Intermediate")')
            if english_element:
                job_data['english_level'] = self._extract_english_level(english_element.text)
            
            # Location
            location_element = sidebar.select_one('.location-text')
            if location_element:
                job_data['location'] = location_element.text.strip()
            
            # Job type (remote, office)
            job_type_element = sidebar.select_one('li:contains("віддалено")')
            if job_type_element:
                job_data['job_type'] = 'Remote'
            else:
                office_element = sidebar.select_one('li:contains("офіс")')
                if office_element:
                    job_data['job_type'] = 'Office'
                else:
                    job_data['job_type'] = 'Hybrid'
            
            # Employment type
            if soup.select_one('li:contains("Part-time")'):
                job_data['employment_type'] = 'Part-time'
            else:
                job_data['employment_type'] = 'Full-time'
            
            # Category
            category_element = sidebar.select_one('li:contains("folder")')
            if category_element:
                job_data['category'] = category_element.text.strip().replace('folder', '').strip()
            
            # Domain
            domain_element = sidebar.select_one('li:contains("Домен")')
            if domain_element:
                job_data['domain'] = domain_element.text.strip().replace('Домен:', '').strip()
        
        # Extract posted date
        date_info = soup.select_one('#job-publication-info')
        if date_info:
            date_text = date_info.select_one('.font-weight-500')
            if date_text:
                job_data['posted_date'] = self._parse_posted_date(date_text.text)
        
        return job_data
    
    def _extract_job_id(self, url):
        """Extract job ID from URL"""
        match = re.search(r'/jobs/(\d+)-', url)
        return match.group(1) if match else None
    
    def _parse_salary(self, salary_text):
        """Parse salary range from text"""
        result = {'salary_min': None, 'salary_max': None, 'currency': 'USD'}
        
        # Extract salary range and currency
        salary_match = re.search(r'(від|до)?\s*\$?(\d+(?:[.,]\d+)?)\s*(?:-\s*\$?(\d+(?:[.,]\d+)?))?\s*(\w+)?', salary_text)
        
        if salary_match:
            prefix, min_val, max_val, currency = salary_match.groups()
            
            # Determine min and max based on prefix
            if prefix and prefix.lower() == 'до':
                result['salary_max'] = float(min_val.replace(',', '.'))
            else:
                result['salary_min'] = float(min_val.replace(',', '.'))
                if max_val:
                    result['salary_max'] = float(max_val.replace(',', '.'))
            
            # Set currency if present
            if currency:
                result['currency'] = currency
        
        return result
    
    def _parse_job_meta(self, meta_text):
        """Parse job metadata from text"""
        result = {}
        
        # Check for location
        if 'Україна' in meta_text or 'Польща' in meta_text or 'США' in meta_text:
            result['location'] = meta_text.split('·')[meta_text.split('·').index(' Країни Європи крім України ') - 1].strip() if ' Країни Європи крім України ' in meta_text else meta_text.split('·')[0].strip()
        
        # Check for experience
        exp_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:рік|роки|років)\s*досвіду', meta_text)
        if exp_match:
            result['experience_years'] = int(float(exp_match.group(1)))
        
        # Check for English level
        if 'Intermediate' in meta_text:
            result['english_level'] = 'Intermediate'
        elif 'Upper-Intermediate' in meta_text:
            result['english_level'] = 'Upper-Intermediate'
        elif 'Advanced' in meta_text or 'Fluent' in meta_text:
            result['english_level'] = 'Advanced/Fluent'
        elif 'Pre-Intermediate' in meta_text:
            result['english_level'] = 'Pre-Intermediate'
        elif 'Elementary' in meta_text or 'Beginner' in meta_text:
            result['english_level'] = 'Beginner/Elementary'
        
        # Check for job type
        if 'віддалено' in meta_text.lower():
            result['job_type'] = 'Remote'
        elif 'офіс' in meta_text.lower():
            result['job_type'] = 'Office'
        else:
            result['job_type'] = 'Hybrid'
        
        # Check for employment type
        if 'Part-time' in meta_text:
            result['employment_type'] = 'Part-time'
        else:
            result['employment_type'] = 'Full-time'
        
        # Check for company type
        if 'Продукт' in meta_text:
            result['domain'] = 'Product'
        elif 'Аутсорс' in meta_text:
            result['domain'] = 'Outsource'
        elif 'Аутстаф' in meta_text:
            result['domain'] = 'Outstaff'
        
        return result
    
    def _extract_experience(self, text):
        """Extract years of experience from text"""
        match = re.search(r'(\d+(?:\.\d+)?)\s*(?:рік|роки|років)\s*досвіду', text)
        return int(float(match.group(1))) if match else None
    
    def _extract_english_level(self, text):
        """Extract English level from text"""
        if 'Intermediate' in text:
            return 'Intermediate'
        elif 'Upper-Intermediate' in text:
            return 'Upper-Intermediate'
        elif 'Advanced' in text or 'Fluent' in text:
            return 'Advanced/Fluent'
        elif 'Pre-Intermediate' in text:
            return 'Pre-Intermediate'
        elif 'Elementary' in text or 'Beginner' in text:
            return 'Beginner/Elementary'
        else:
            return None
    
    def _parse_posted_date(self, date_text):
        """Parse posted date from text"""
        try:
            # Ukrainian month names to numbers
            month_map = {
                'січня': 1, 'лютого': 2, 'березня': 3, 'квітня': 4,
                'травня': 5, 'червня': 6, 'липня': 7, 'серпня': 8,
                'вересня': 9, 'жовтня': 10, 'листопада': 11, 'грудня': 12
            }
            
            match = re.search(r'(\d+)\s+(\w+)', date_text)
            if match:
                day = int(match.group(1))
                month_name = match.group(2)
                
                # Find month number
                month = None
                for ukr_month, month_num in month_map.items():
                    if ukr_month in month_name:
                        month = month_num
                        break
                
                if month:
                    # Assume current year
                    year = datetime.datetime.now().year
                    return datetime.datetime(year, month, day)
            
            return None
        except Exception as e:
            print(f"Error parsing date: {e}")
            return None