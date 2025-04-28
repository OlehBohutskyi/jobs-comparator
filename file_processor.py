# Create a new file file_processor.py in the root directory

import os
import logging
import tempfile
import PyPDF2
import docx
import re
from pathlib import Path

class FileProcessor:
    """Process uploaded educational program files"""
    
    def __init__(self, upload_folder='uploads'):
        self.logger = logging.getLogger(__name__)
        self.upload_folder = upload_folder
        
        # Create upload folder if it doesn't exist
        os.makedirs(self.upload_folder, exist_ok=True)
    
    def save_file(self, file):
        """Save an uploaded file and return file info"""
        try:
            # Ensure the upload folder exists
            if not os.path.exists(self.upload_folder):
                os.makedirs(self.upload_folder)
            
            # Get file extension
            filename = file.filename
            file_ext = Path(filename).suffix.lower()
            
            # Generate a unique filename
            unique_filename = f"{Path(filename).stem}_{os.urandom(8).hex()}{file_ext}"
            file_path = os.path.join(self.upload_folder, unique_filename)
            
            # Save the file
            file.save(file_path)
            
            # Log the save operation
            self.logger.info(f"File saved at: {file_path}")
            
            # Determine file type
            file_type = None
            if file_ext == '.pdf':
                file_type = 'pdf'
            elif file_ext in ['.doc', '.docx']:
                file_type = 'docx'
            elif file_ext == '.txt':
                file_type = 'txt'
            else:
                file_type = 'unknown'
            
            return {
                'path': unique_filename,
                'filename': filename,
                'file_type': file_type,
                'size': os.path.getsize(file_path)
            }
        
        except Exception as e:
            self.logger.error(f"Error saving file: {e}")
            raise
    
    def extract_text(self, file_path, file_type):
        """Extract text from different file types"""
        try:
            text = ""
            
            # If file_path doesn't contain the full path, add the uploads folder
            if not os.path.dirname(file_path):
                full_path = os.path.join(self.upload_folder, file_path)
            else:
                full_path = file_path
            
            self.logger.info(f"Extracting text from: {full_path}")
            
            # Check if file exists
            if not os.path.exists(full_path):
                self.logger.error(f"File not found: {full_path}")
                return f"Error: File not found at {full_path}"
            
            if file_type == 'pdf':
                # Extract text from PDF
                with open(full_path, 'rb') as pdf_file:
                    try:
                        reader = PyPDF2.PdfReader(pdf_file)
                        for page_num in range(len(reader.pages)):
                            page_text = reader.pages[page_num].extract_text()
                            if page_text:  # Only add if there is text (avoid empty pages)
                                text += page_text + "\n\n"
                    except Exception as pdf_error:
                        self.logger.error(f"PDF reading error: {pdf_error}")
                        text = f"Error reading PDF: {str(pdf_error)}"
            
            elif file_type == 'docx':
                # Extract text from DOCX
                try:
                    doc = docx.Document(full_path)
                    paragraphs = []
                    for para in doc.paragraphs:
                        if para.text.strip():  # Only add non-empty paragraphs
                            paragraphs.append(para.text)
                    text = "\n\n".join(paragraphs)
                except Exception as docx_error:
                    self.logger.error(f"DOCX reading error: {docx_error}")
                    text = f"Error reading DOCX: {str(docx_error)}"
            
            elif file_type == 'txt':
                # Read text file
                try:
                    with open(full_path, 'r', encoding='utf-8', errors='replace') as txt_file:
                        text = txt_file.read()
                except Exception as txt_error:
                    self.logger.error(f"Text file reading error: {txt_error}")
                    text = f"Error reading text file: {str(txt_error)}"
            
            else:
                raise ValueError(f"Unsupported file type: {file_type}")
            
            # Clean up text
            text = self._clean_text(text)
            
            # Log success and text length
            self.logger.info(f"Successfully extracted {len(text)} characters of text")
            
            return text
        
        except Exception as e:
            self.logger.error(f"Error extracting text from {file_path}: {e}")
            return f"Error extracting text: {str(e)}"
    
    def _clean_text(self, text):
        """Clean extracted text"""
        if not text:
            return ""
        
        # Replace multiple spaces with a single space
        text = re.sub(r'\s+', ' ', text)
        
        # Replace multiple newlines with a single newline
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        # Trim whitespace
        text = text.strip()
        
        return text