import os
import json
import logging
import requests
from dotenv import load_dotenv

load_dotenv()

class ChatGPTAPI:
    def __init__(self):
        self.api_key = os.getenv('OPENAI_API_KEY', '')
        self.api_url = "https://api.openai.com/v1/chat/completions"
        self.logger = logging.getLogger(__name__)
        
        if not self.api_key:
            self.logger.warning("OpenAI API key not found in environment variables")
    
    def generate_job_requirements_summary(self, domain_names, top_words):
        """Generate a job requirements summary using ChatGPT API"""
        try:
            if not self.api_key:
                return "Error: OpenAI API key not configured. Please add OPENAI_API_KEY to your .env file."
            
            # Format the top words for prompt
            formatted_words = ", ".join([f"{word} ({count})" for word, count in top_words.items()])
            
            prompt = f"""
            I need you to create a comprehensive summary of typical job requirements for {", ".join(domain_names)} positions.
            
            Below is a frequency analysis of key terms found in job descriptions for these positions, 
            with the most common terms listed first (word followed by occurrence count):
            
            {formatted_words}
            
            Based on this frequency analysis:
            
            1. Create a detailed, well-structured summary of the core skills, qualifications,
               and experience typically required for {", ".join(domain_names)} positions.
            2. Organize requirements into logical categories (technical skills, soft skills, experience, etc.)
            3. Include specific technologies, tools, and methodologies that appear important based on word frequency
            4. Structure the response in a clean format with headers and bullet points
            
            Please provide a complete and professional summary that could be used to understand
            what employers generally look for in these positions.
            """
            
            headers = {
                "Authorization": f"Bearer {self.api_key.strip()}",
                "Content-Type": "application/json"
            }
            
            self.logger.info(f"API Key length: {len(self.api_key.strip())}")
            self.logger.info(f"Authorization header: Bearer {self.api_key.strip()[:5]}...{self.api_key.strip()[-4:] if len(self.api_key.strip()) > 8 else ''}")
            
            data = {
                "model": "gpt-4o",
                "messages": [
                    {"role": "system", "content": "You are a professional job market analyst specializing in creating accurate summaries of job requirements."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.5,
                "max_tokens": 1500
            }
            
            # Make the API request
            response = requests.post(self.api_url, headers=headers, json=data)
            
            # Log useful debugging information
            self.logger.info(f"API response status code: {response.status_code}")
            self.logger.info(f"API response headers: {response.headers}")
            
            # Check if there's an error and log it
            if response.status_code != 200:
                self.logger.error(f"API Error: {response.text}")
                return f"Error: API returned status code {response.status_code}. Details: {response.text}"
            
            # Extract and return the generated text
            result = response.json()
            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"].strip()
            else:
                self.logger.error(f"Unexpected API response: {result}")
                return "Error: Unable to generate summary from API response."
                
        except Exception as e:
            self.logger.error(f"Error generating summary: {e}")
            return f"Error generating summary: {str(e)}"


    def analyze_educational_program(self, domain_names, job_requirements_summary, educational_program_text):
        """Compare job requirements with educational program and provide recommendations"""
        try:
            if not self.api_key:
                return "Error: OpenAI API key not configured. Please add OPENAI_API_KEY to your .env file."
            
            prompt = f"""
            I need you to analyze a university educational program against job market requirements.
            
            Below is a summary of typical job requirements for {", ".join(domain_names)} positions:
            
            ---JOB REQUIREMENTS---
            {job_requirements_summary}
            ---END JOB REQUIREMENTS---
            
            And here is the educational program text:
            
            ---EDUCATIONAL PROGRAM---
            {educational_program_text[:5000]}  # Limiting to first 5000 chars to avoid token limits
            ---END EDUCATIONAL PROGRAM---
            
            Please provide:
            
            1. A detailed analysis of how well the educational program aligns with the job market requirements
            2. Identify gaps in the educational program compared to industry needs
            3. Recommend specific improvements, updates, or modifications to the program
            4. Suggest new courses, technologies, or skills that should be added
            5. Identify outdated elements that could be reduced or removed
            
            Format your response with clear headings, bullet points for recommendations, and highlight the most critical gaps and improvement opportunities.
            """
            

            headers = {
                "Authorization": f"Bearer {self.api_key.strip()}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "gpt-3.5-turbo-16k",
                "messages": [
                    {"role": "system", "content": "You are an expert in curriculum development and industry requirements analysis."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 3000
            }
            
            # Make the API request
            response = requests.post(self.api_url, headers=headers, json=data)
            
            # Log useful debugging information
            self.logger.info(f"API response status code: {response.status_code}")
            
            # Check if there's an error and log it
            if response.status_code != 200:
                self.logger.error(f"API Error: {response.text}")
                return f"Error: API returned status code {response.status_code}. Details: {response.text}"
            
            # Extract and clean the generated text
            result = response.json()
            if "choices" in result and len(result["choices"]) > 0:
                generated_text = result["choices"][0]["message"]["content"].strip()
                cleaned_text = self.clean_response_text(generated_text)
                return cleaned_text
            else:
                self.logger.error(f"Unexpected API response: {result}")
                return "Error: Unable to generate analysis from API response."
                
        except Exception as e:
            self.logger.error(f"Error analyzing educational program: {e}")
            return f"Error analyzing educational program: {str(e)}"
        
    def clean_response_text(self, text):
        """Clean the response text by removing excessive empty lines"""
        if not text:
            return text
            
        import re
        cleaned_text = re.sub(r'\n\s*\n', '\n\n', text)
        
        cleaned_text = cleaned_text.lstrip('\n')
        
        cleaned_text = cleaned_text.rstrip('\n') + '\n'
        
        return cleaned_text
