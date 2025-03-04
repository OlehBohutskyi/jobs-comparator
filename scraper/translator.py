import asyncio
from deep_translator import GoogleTranslator

class Translator:
    def __init__(self):
        self.translator = GoogleTranslator(source='uk', target='en')
        self.semaphore = asyncio.Semaphore(5)  # Limit concurrent translations
        
    def translate_text(self, text):
        if not text or not isinstance(text, str):
            return text
        
        # Skip translation if already in English or contains primarily English
        if self._is_english(text):
            return text
            
        try:
            translated = self.translator.translate(text)
            return translated
        except Exception as e:
            print(f"Translation error: {e}")
            return text
            
    async def translate_text_async(self, text):
        if not text or not isinstance(text, str):
            return text
            
        # Skip translation if already in English
        if self._is_english(text):
            return text
            
        async with self.semaphore:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self.translate_text, text)
            
    def _is_english(self, text):
        # Simple heuristic to detect if text is already in English
        # English letters ASCII: a-z, A-Z (97-122, 65-90)
        if not text:
            return True
            
        # Count English characters
        english_chars = sum(1 for c in text if (ord('a') <= ord(c) <= ord('z')) or (ord('A') <= ord(c) <= ord('Z')))
        total_chars = len(''.join(text.split()))  # Count non-whitespace characters
        
        if total_chars == 0:
            return True
            
        # If more than 70% are English characters, consider it English
        return (english_chars / total_chars) > 0.7
            
    async def translate_job_data(self, job_data):
        """Translate relevant fields in job data"""
        # Fields to translate
        translate_fields = {
            'title': 'title_en',
            'company_name': 'company_name_en',
            'description': 'description_en',
            'location': 'location_en',
            'category': 'category_en',
            'domain': 'domain_en'
        }
        
        # Create translation tasks
        tasks = []
        for src_field, dest_field in translate_fields.items():
            if src_field in job_data and job_data[src_field]:
                tasks.append(self._translate_field(job_data, src_field, dest_field))
                
        # Run translations concurrently
        await asyncio.gather(*tasks)
        return job_data
        
    async def _translate_field(self, job_data, src_field, dest_field):
        """Translate a single field and store in destination field"""
        if src_field in job_data and job_data[src_field]:
            job_data[dest_field] = await self.translate_text_async(job_data[src_field])