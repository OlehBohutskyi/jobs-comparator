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
                I will provide you with a list of words and their frequency of appearance in job vacancies, along with a list of domains these vacancies belong to. Based on this data, create maximally comprehensive and broad requirements for a consolidated job position that combines all these domains.

                Use the word frequency data to create detailed, university-level requirements with advanced academic phrasing. For example, instead of simply "Python knowledge," expand to "Possess specialized conceptual knowledge of Python programming, including advanced algorithmic principles and application in modern research contexts."

                Data:
                - Word frequencies: {formatted_words}
                - Job domains: {", ".join(domain_names)}
                Structure the requirements into:
                1. Hard Skills - Elaborate on technical proficiencies with academic depth, emphasizing critical understanding of theoretical principles and their practical applications
                2. Soft Skills - Detail advanced interpersonal competencies that demonstrate mastery of professional communication and leadership
                3. Technologies - Describe technological expertise in terms of comprehensive knowledge frameworks and innovative application capabilities
                4. Tools - Present tool proficiencies as specialized knowledge domains rather than simple familiarity

                For each category, prioritize skills based on their frequency. For high-frequency skills, provide extensive, university-curriculum-style requirements that emphasize:
                - Specialized conceptual knowledge including modern scientific achievements
                - Capacity for original thinking and research
                - Critical comprehension of problems within and across knowledge domains
                - Innovative application of theoretical principles
                - Advanced analytical capabilities and methodological approaches

                Format as a cohesive, sophisticated job description that integrates all domains at an advanced academic level.

                IMPORTANT: Create the broadest and most comprehensive requirements that describe what a student graduating from university in this specialty should know and be able to do. Structure the requirements as a list of competencies that meet modern higher education standards.
                ```

            """
            # prompt = f"""
            # I need you to create a comprehensive summary of typical job requirements for {", ".join(domain_names)} positions.
            
            # Below is a frequency analysis of key terms found in job descriptions for these positions, 
            # with the most common terms listed first (word followed by occurrence count):
            
            # {formatted_words}
            
            # Based on this frequency analysis:
            
            # 1. Create a detailed, well-structured summary of the core skills, qualifications,
            #    and experience typically required for {", ".join(domain_names)} positions.
            # 2. Organize requirements into logical categories (technical skills, soft skills, experience, etc.)
            # 3. Include specific technologies, tools, and methodologies that appear important based on word frequency
            # 4. Structure the response in a clean format with headers and bullet points
            
            # Please provide a complete and professional summary that could be used to understand
            # what employers generally look for in these positions.

            # ## Hard Skills
            # * Elaborate on the essential technical competencies required for this role, explaining why they're important and how they would be applied in daily work

            # ## Soft Skills
            # * Describe the interpersonal and professional qualities needed to succeed in this position, including how these traits contribute to team dynamics and project success

            # ## Technologies
            # * Detail the specific technologies candidates should be familiar with, including relevant versions, frameworks, and their practical applications in this role

            # ## Tools
            # * Present a comprehensive list of ALL tools required for this position, including programming languages, version control systems (like Git), orchestration tools, development environments, testing frameworks, and any other technical tools mentioned in the frequency analysis. This section should be a straightforward enumeration without detailed descriptions.

            # Format the Hard Skills, Soft Skills, and Technologies sections as complete, descriptive statements in a natural, conversational tone that resembles how an experienced hiring manager would communicate. Only the Tools section should be a simple list format.

            # Important: The result should contain only structured lists under the specified categories without any introductory text, conclusions, or other explanations.
            # """
            
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
                Я надам вам два набори даних:
                1. Список програмних результатів навчання з університетської навчальної програми з комп'ютерних наук
                2. Вимоги до вакансій, згенеровані на основі аналізу частоти слів у вакансіях різних доменів

                Проаналізуйте відповідність між цими програмними результатами навчання та вимогами до вакансій. Створіть детальну порівняльну таблицю з такими стовпцями:
                - Програмний результат навчання
                - Вимога до вакансії
                - Ступінь відповідності

                В таблиці мають бути тільки 3 колонки 
                - Програмний результат навчання
                - Вимога до вакансії
                - Ступінь відповідності

                Нічого окрім таблиці немає бути у виводі

                ВАЖЛИВО: Вимоги до вакансій треба перекласти українською
                ВАЖЛИВО: Програмні результати мають бути написані в повному обсязі, без скорочень
                ВАЖЛИВО: Програмні результати мають бути слово в слово, як в тексті, який я тобі відправляю. Нумерація має обов'язково зберігатись

                Для стовпця "Ступінь відповідності" використовуйте таку шкалу:
                - Високий
                - Значний
                - Середній
                - Низький
                - Мінімальний

                Визначте ступінь відповідності на основі:
                - Концептуальної схожості
                - Охоплення тематики
                - Відповідності термінології
                - Релевантності практичного застосування
                - Рівня академічної/професійної глибини

                Приклад структури:
                Для програмного результату навчання, як-от "Спеціалізовані концептуальні знання, що включають сучасні наукові здобутки у сфері комп'ютерних наук і є основою для оригінального мислення та проведення досліджень, критичне осмислення проблем у сфері комп'ютерних наук та на межі галузей знань", визначте всі вимоги до вакансій, які відповідають цьому результату, оцініть ступінь відповідності та надайте детальне пояснення вашої оцінки.

                Після таблиці надайте аналітичний підсумок:
                1. Загальна відповідність між навчальною програмою та вимогами ринку праці
                2. Області, де навчальна програма відмінно відповідає потребам галузі
                3. Області, де навчальну програму можна вдосконалити для кращої відповідності вимогам вакансій
                4. Рекомендації щодо розвитку навчальної програми

                Дані:
                1. Програмні результати навчання: {educational_program_text[:10000]}
                2. Вимоги до вакансій: {job_requirements_summary}

                ВАЖЛИВО: У таблиці мають бути включені ВСІ програмні результати навчання. Якщо для якогось програмного результату не знайдено відповідної вимоги до вакансії, залиште пропуск у відповідній комірці та вкажіть "Мінімальний" у стовпці ступеня відповідності. Не додавайте жодних рекомендацій, яких немає у вихідних даних.
                ВАЖЛИВО: Ніяких аналітичних підсумків, або рекомендацій немає бути. Ти не експерт в освіті, тому не можеш нічого рекомендувати. 
                
            """ 
            
            # prompt = f"""
            #     I need you to analyze how well program learning outcomes from a university educational program align with specific job market requirements. Below is a summary of typical job requirements for {", ".join(domain_names)} positions:

            #     ---JOB REQUIREMENTS---
            #     {job_requirements_summary}
            #     ---END JOB REQUIREMENTS---

            #     And here is the educational program text:
            #     ---EDUCATIONAL PROGRAM---
            #     {educational_program_text[:10000]}
            #     ---END EDUCATIONAL PROGRAM---

            #     Please:

            #     1. Extract all program learning outcomes (numbered as "ПР1", "ПР2", "ПРН1", "ПРН2", etc.) from the educational program text along with their full Ukrainian descriptions
            #     2. For each identified program learning outcome, determine which specific job requirements from the provided vacancy summary it corresponds to
            #     3. Assess the confidence level of alignment between each program learning outcome and the job requirements (High, Medium, Low)
            #     4. If a specific program learning outcome doesn't align with any job requirement, include it in the table with "--" in the "Corresponding Job Requirements" column and "--" in the "Confidence Level" column
            #     5. Present all program learning outcomes in sequential order according to their numbering
            #     6. You could not miss any of program learning outcomes, this is crucial. You should write all of them in the table, even if they do not match any job requirements.
            #     7. Do not add any additional comments or explanations outside of the table.

            #     Present your analysis as a table with the following columns:
            #     - Program Learning Outcome (ПР/ПРН number and full Ukrainian description, all of them)
            #     - Corresponding Job Requirements (use exact wording from the job requirements provided, or "--" if no match)
            #     - Confidence Level (High/Medium/Low, or "--" if no match)

            #     Do not add any requirements that aren't explicitly mentioned in the job requirements summary. Only use what is provided in the input text.
            # """
            

            headers = {
                "Authorization": f"Bearer {self.api_key.strip()}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "gpt-4o",
                "messages": [
                    {"role": "system", "content": "You are an expert in curriculum development and industry requirements analysis."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 10000
            }
            

            print(prompt)
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
