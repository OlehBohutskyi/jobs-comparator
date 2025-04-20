# Create a new file text_processor.py in the root directory

import re
import json
import os
from collections import Counter
import logging

class TextProcessor:
    def __init__(self, stop_words_file='stop_words.txt'):
        self.logger = logging.getLogger(__name__)
        self.stop_words = self._load_stop_words(stop_words_file)
        
    def _load_stop_words(self, filename):
        """Load stop words from file or create default list if file doesn't exist"""
        try:
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as file:
                    return set(word.strip().lower() for word in file.readlines())
            else:
                # Create default stop words file if it doesn't exist
                default_stop_words = {
                    'a', 'an', 'the', 'and', 'or', 'but', 'if', 'because', 'as', 'what',
                    'which', 'this', 'that', 'these', 'those', 'then', 'just', 'so', 'than', 'such',
                    'when', 'who', 'how', 'to', 'in', 'on', 'for', 'of', 'by', 'with',
                    'about', 'against', 'between', 'into', 'through', 'during', 'before', 'after',
                    'above', 'below', 'from', 'up', 'down', 'is', 'are', 'was', 'were', 'be',
                    'been', 'being', 'have', 'has', 'had', 'having', 'do', 'does', 'did', 'doing',
                    'at', 'will', 'would', 'shall', 'should', 'can', 'could', 'may', 'might', 'must',
                    'i', 'you', 'he', 'she', 'it', 'we', 'they', 'their', 'him', 'her', 'them',
                    # Ukrainian and Russian stop words
                    'і', 'в', 'у', 'на', 'з', 'до', 'по', 'за', 'від', 'про',
                    'та', 'що', 'як', 'не', 'так', 'це', 'той', 'цей', 'тому', 'але',
                    'або', 'чи', 'ще', 'вже', 'тільки', 'також', 'навіть', 'більше', 'менше', 'ніж',
                    'бути', 'є', 'був', 'була', 'було', 'були', 'буде', 'будуть', 'мати', 'має',
                    'мав', 'мала', 'мало', 'мали', 'я', 'ти', 'він', 'вона', 'воно', 'ми', 'ви', 'вони',
                    'їх', 'його', 'її', 'наш', 'ваш', 'їхній', 'мій', 'твій', 'свій',
                    # Additional common English words in job descriptions
                    'experience', 'skills', 'job', 'work', 'company', 'team', 'position', 'role',
                    'required', 'requirements', 'responsibilities', 'working', 'knowledge', 'years',
                }
                
                with open(filename, 'w', encoding='utf-8') as file:
                    file.write('\n'.join(sorted(default_stop_words)))
                
                self.logger.info(f"Created default stop words file: {filename}")
                return default_stop_words
                
        except Exception as e:
            self.logger.error(f"Error loading stop words: {e}")
            return set()
    
    def clean_text(self, text):
        """Clean and normalize text"""
        if not text:
            return ""
            
        # Convert to lowercase
        text = text.lower()
        
        # Remove HTML tags
        text = re.sub(r'<.*?>', ' ', text)
        
        # Remove punctuation and special characters
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Replace multiple spaces with a single space
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def extract_words(self, text):
        """Extract words from text, excluding stop words"""
        words = self.clean_text(text).split()
        # Filter out stop words and words that are too short
        return [word for word in words if word not in self.stop_words and len(word) > 2]
    
    def analyze_frequency(self, jobs, top_n=50):
        """
        Analyze word frequency in job descriptions.
        Returns a dictionary of the top N words and their frequencies.
        """
        all_text = ""
        
        # Combine all job descriptions
        for job in jobs:
            description = job.get('description', '')
            if description:
                all_text += description + " "
        
        # Extract words
        words = self.extract_words(all_text)
        
        # Count word frequencies
        word_counts = Counter(words)
        
        # Get top N words
        top_words = word_counts.most_common(top_n)
        
        # Format results
        result = {
            'total_words': len(words),
            'unique_words': len(word_counts),
            'top_words': {word: count for word, count in top_words}
        }
        
        return result