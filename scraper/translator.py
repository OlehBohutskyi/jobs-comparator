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
        # Создаем копию данных, чтобы избежать изменений во время перевода
        result = job_data.copy()
        
        # Fields to translate
        translate_fields = {
            'title': 'title_en',
            'company_name': 'company_name_en',
            'description': 'description_en',
            'location': 'location_en',
            'category': 'category_en',
            'domain': 'domain_en'
        }
        
        # Переводим каждое поле последовательно, чтобы избежать путаницы
        for src_field, dest_field in translate_fields.items():
            if src_field in result and result[src_field]:
                try:
                    # Переводим значение напрямую, без промежуточных переменных
                    translated_text = await self.translate_text_async(result[src_field])
                    # Сохраняем переведенное значение в соответствующее поле
                    result[dest_field] = translated_text
                    
                    # Логирование для отладки
                    print(f"Translated {src_field}: '{result[src_field]}' -> '{result[dest_field]}'")
                except Exception as e:
                    print(f"Translation error for field {src_field}: {e}")
                    # В случае ошибки копируем оригинальное значение
                    result[dest_field] = result[src_field]
        
        return result
        
    async def _translate_field(self, job_data, src_field, dest_field):
        """Translate a single field and store in destination field"""
        if src_field in job_data and job_data[src_field]:
            job_data[dest_field] = await self.translate_text_async(job_data[src_field])