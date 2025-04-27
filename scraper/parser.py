import json
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
    

    def _standardize_location(self, location_text):
        """
        Simplify location text into standard categories.
        
        Args:
            location_text (str): Raw location text from job posting
            
        Returns:
            str: Standardized location - "Remote", "Ukraine", "Whole World", or "Other"
        """
        if not location_text:
            return "Other"
        
        # Lowercase for easier matching
        text = location_text.lower()
        
        # Check for remote indicators
        if any(keyword in text for keyword in ['remote', 'віддалено', 'удаленно', 'remotely']):
            return "Remote"
        
        # Check for Ukraine mentions
        if any(keyword in text for keyword in ['ukraine', 'україна', 'украина', 'київ', 'kyiv', 'львів', 'lviv']):
            return "Ukraine"
        
        # Check for worldwide indicators
        if any(keyword in text for keyword in ['worldwide', 'the whole world', 'global', 'any location', 'весь світ']):
            return "Whole World"
        
        # Default case
        return "Other"
    
    def parse_job_detail(self, html_content):
        """Parse the job detail page and extract comprehensive job information"""
        soup = BeautifulSoup(html_content, 'html.parser')
        job_data = {}

        inactive_badges = soup.select('span.badge.fs-5.rounded-1.text-light-emphasis.bg-light-subtle.border-0.fw-medium')
        is_active = True
        for badge in inactive_badges:
            if "Неактивна" in badge.text:
                is_active = False
                break
        job_data['is_active'] = is_active
        
        # Get job title
        job_title = soup.select_one('h1')
        if job_title:
            job_title = job_title.text.strip()
            if "Неактивна" in job_title:
                job_title = job_title.replace("Неактивна", "").strip()
            job_data['title'] = job_title
        
        # Get job URL and ID
        job_data['url'] = soup.select_one('link[rel="canonical"]')['href']
        job_data['job_id'] = self._extract_job_id(job_data['url'])
        
        # Get company name
        company_element = soup.select_one('a[data-analytics="company_page"]') or soup.select_one('.col a.text-reset')
        if company_element:
            job_data['company_name'] = company_element.text.strip()
        
        # Extract salary from JSON-LD data in script tag
        script_tags = soup.find_all('script', type='application/ld+json')
        for script_tag in script_tags:
            try:
                json_data = json.loads(script_tag.string)
                if json_data.get('@type') == 'JobPosting' and 'baseSalary' in json_data:
                    salary_data = json_data['baseSalary']
                    if isinstance(salary_data, dict) and 'value' in salary_data:
                        currency = salary_data.get('currency', 'USD')
                        value = salary_data['value']
                        
                        if isinstance(value, dict):
                            min_value = value.get('minValue')
                            max_value = value.get('maxValue')
                            
                            if min_value is not None:
                                job_data['salary_min'] = float(min_value)
                            
                            if max_value is not None:
                                job_data['salary_max'] = float(max_value)
                            
                            job_data['currency'] = currency
                            break
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                print(f"Error parsing JSON-LD data: {e}")
                continue
        
        # Get job description
        description_element = soup.select_one('.job-post__description')
        if description_element:
            job_data['description'] = description_element.get_text('\n').strip()
        
        # Remaining code for other fields...
        # ...
    
        
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
                location_text = location_element.text.strip()
                job_data['location'] = self._standardize_location(location_text)
            
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
        
        # Filter out common false positives
        if re.search(r'\b(?:month[s]?|week[s]?|day[s]?|hour[s]?|год[а-я]*|місяц[а-я]*|день|дн[а-я]+)\b', 
                    salary_text, re.IGNORECASE):
            # Check if it's a timeframe mention without salary context
            if not re.search(r'[$€₴₽]|грн|usd|eur|uah', salary_text, re.IGNORECASE):
                return result
        
        # More specific pattern for salary with currency
        salary_match = re.search(
            r'(?:від|до|from|up to|от|до)?\s*'
            r'([$€₴₽])?\s*(\d+(?:[.,]\d+)?)[k]?\s*'
            r'(?:([$€₴₽])|(\b(?:USD|EUR|UAH|грн)\b))?'
            r'(?:\s*[-–—]\s*'
            r'([$€₴₽])?\s*(\d+(?:[.,]\d+)?)[k]?\s*'
            r'(?:([$€₴₽])|(\b(?:USD|EUR|UAH|грн)\b))?)?',
            salary_text
        )
        
        if salary_match:
            # Extracting all groups
            currency_symbol1, min_val, currency_symbol2, currency_word1, currency_symbol3, max_val, currency_symbol4, currency_word2 = salary_match.groups()
            
            # Determine currency
            currency = 'USD'  # default
            for symbol in [currency_symbol1, currency_symbol2, currency_symbol3, currency_symbol4]:
                if symbol:
                    if symbol == '$':
                        currency = 'USD'
                        break
                    elif symbol == '€':
                        currency = 'EUR'
                        break
                    elif symbol == '₴':
                        currency = 'UAH'
                        break
                    elif symbol == '₽':
                        currency = 'RUB'
                        break
            
            for word in [currency_word1, currency_word2]:
                if word:
                    word = word.upper()
                    if word in ['USD', 'EUR', 'UAH']:
                        currency = word
                        break
                    elif word == 'ГРН':
                        currency = 'UAH'
                        break
            
            # Convert to float and handle k suffix (thousands)
            if min_val:
                min_val = min_val.replace(',', '.')
                if 'k' in min_val.lower():
                    min_val = float(min_val.lower().replace('k', '')) * 1000
                else:
                    min_val = float(min_val)
                result['salary_min'] = min_val
                
            if max_val:
                max_val = max_val.replace(',', '.')
                if 'k' in max_val.lower():
                    max_val = float(max_val.lower().replace('k', '')) * 1000
                else:
                    max_val = float(max_val)
                result['salary_max'] = max_val
            
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