"""
CV to MySQL Parser using Gemini AI
Extracts information from CV PDFs and stores in MySQL database
"""

import os
import json
import pdfplumber
import mysql.connector
from mysql.connector import Error
import google.generativeai as genai
from datetime import datetime
import sys


class CVParser:
    def __init__(self, gemini_api_key, db_config=None):
        """
        Initialize CV Parser
        
        Args:
            gemini_api_key (str): Google Gemini API key
            db_config (dict): MySQL database configuration
                {
                    'host': 'localhost',
                    'database': 'cv_database',
                    'user': 'your_username',
                    'password': 'your_password'
                }
        """
        self.gemini_api_key = gemini_api_key
        self.db_config = db_config
        self.connection = None
        
        # Configure Gemini
        genai.configure(api_key=self.gemini_api_key)
        self.model = genai.GenerativeModel('gemini-2.5-flash-lite')
        
    def extract_text_from_pdf(self, pdf_path):
        """Extract text from PDF using pdfplumber"""
        try:
            text = ""
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text += page.extract_text() + "\n"
            return text
        except Exception as e:
            print(f"Error extracting text from PDF: {e}")
            return None
    
    def parse_cv_with_gemini(self, cv_text):
        """Parse CV text using Gemini AI"""
        prompt = f"""Extract all information from this CV/Resume and return it as a JSON object with the following structure:

{{
  "personal_info": {{
    "full_name": "",
    "email": "",
    "phone": "",
    "location": "",
    "linkedin": "",
    "website": ""
  }},
  "summary": "",
  "work_experience": [
    {{
      "job_title": "",
      "company": "",
      "location": "",
      "start_date": "",
      "end_date": "",
      "description": ""
    }}
  ],
  "education": [
    {{
      "degree": "",
      "institution": "",
      "location": "",
      "graduation_date": "",
      "gpa": ""
    }}
  ],
  "skills": [],
  "certifications": [],
  "languages": []
}}

CV Content:
{cv_text}

IMPORTANT: Return ONLY the JSON object, no additional text or explanation. If a field is not found, use an empty string or empty array."""

        try:
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Clean up response (remove markdown code blocks if present)
            response_text = response_text.replace('```json', '').replace('```', '').strip()
            
            # Parse JSON
            parsed_data = json.loads(response_text)
            return parsed_data
        except Exception as e:
            print(f"Error parsing CV with Gemini: {e}")
            return None
    
    def connect_to_database(self):
        """Connect to MySQL database"""
        try:
            self.connection = mysql.connector.connect(**self.db_config)
            if self.connection.is_connected():
                print("Successfully connected to MySQL database")
                return True
        except Error as e:
            print(f"Error connecting to MySQL: {e}")
            return False
    
    def create_tables(self):
        """Create necessary tables in the database"""
        if not self.connection or not self.connection.is_connected():
            print("No database connection")
            return False
        
        try:
            cursor = self.connection.cursor()
            
            # Create candidates table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS candidates (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    full_name VARCHAR(255),
                    email VARCHAR(255),
                    phone VARCHAR(50),
                    location VARCHAR(255),
                    linkedin VARCHAR(255),
                    website VARCHAR(255),
                    summary TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create work_experience table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS work_experience (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    candidate_id INT,
                    job_title VARCHAR(255),
                    company VARCHAR(255),
                    location VARCHAR(255),
                    start_date VARCHAR(50),
                    end_date VARCHAR(50),
                    description TEXT,
                    FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
                )
            """)
            
            # Create education table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS education (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    candidate_id INT,
                    degree VARCHAR(255),
                    institution VARCHAR(255),
                    location VARCHAR(255),
                    graduation_date VARCHAR(50),
                    gpa VARCHAR(10),
                    FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
                )
            """)
            
            # Create skills table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS skills (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    candidate_id INT,
                    skill_name VARCHAR(255),
                    FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
                )
            """)
            
            # Create certifications table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS certifications (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    candidate_id INT,
                    certification_name VARCHAR(255),
                    FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
                )
            """)
            
            # Create languages table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS languages (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    candidate_id INT,
                    language_name VARCHAR(255),
                    FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
                )
            """)
            
            self.connection.commit()
            cursor.close()
            print("Database tables created successfully")
            return True
        except Error as e:
            print(f"Error creating tables: {e}")
            return False
    
    def insert_candidate_data(self, parsed_data):
        """Insert parsed CV data into MySQL database"""
        if not self.connection or not self.connection.is_connected():
            print("No database connection")
            return False
        
        try:
            cursor = self.connection.cursor()
            
            # Insert candidate
            personal = parsed_data.get('personal_info', {})
            cursor.execute("""
                INSERT INTO candidates (full_name, email, phone, location, linkedin, website, summary)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                personal.get('full_name', ''),
                personal.get('email', ''),
                personal.get('phone', ''),
                personal.get('location', ''),
                personal.get('linkedin', ''),
                personal.get('website', ''),
                parsed_data.get('summary', '')
            ))
            
            candidate_id = cursor.lastrowid
            
            # Insert work experience
            for exp in parsed_data.get('work_experience', []):
                cursor.execute("""
                    INSERT INTO work_experience (candidate_id, job_title, company, location, start_date, end_date, description)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    candidate_id,
                    exp.get('job_title', ''),
                    exp.get('company', ''),
                    exp.get('location', ''),
                    exp.get('start_date', ''),
                    exp.get('end_date', ''),
                    exp.get('description', '')
                ))
            
            # Insert education
            for edu in parsed_data.get('education', []):
                cursor.execute("""
                    INSERT INTO education (candidate_id, degree, institution, location, graduation_date, gpa)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    candidate_id,
                    edu.get('degree', ''),
                    edu.get('institution', ''),
                    edu.get('location', ''),
                    edu.get('graduation_date', ''),
                    edu.get('gpa', '')
                ))
            
            # Insert skills
            for skill in parsed_data.get('skills', []):
                if skill:
                    cursor.execute("""
                        INSERT INTO skills (candidate_id, skill_name)
                        VALUES (%s, %s)
                    """, (candidate_id, skill))
            
            # Insert certifications
            for cert in parsed_data.get('certifications', []):
                if cert:
                    cursor.execute("""
                        INSERT INTO certifications (candidate_id, certification_name)
                        VALUES (%s, %s)
                    """, (candidate_id, cert))
            
            # Insert languages
            for lang in parsed_data.get('languages', []):
                if lang:
                    cursor.execute("""
                        INSERT INTO languages (candidate_id, language_name)
                        VALUES (%s, %s)
                    """, (candidate_id, lang))
            
            self.connection.commit()
            cursor.close()
            print(f"Successfully inserted candidate data (ID: {candidate_id})")
            return candidate_id
        except Error as e:
            print(f"Error inserting data: {e}")
            self.connection.rollback()
            return None
    
    def generate_sql_file(self, parsed_data, output_path):
        """Generate SQL file from parsed data"""
        def escape_sql(s):
            if s is None:
                return ''
            return str(s).replace("'", "''")
        
        sql = f"-- CV Parser: MySQL Export\n"
        sql += f"-- Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        sql += "-- Create database and use it\n"
        sql += "CREATE DATABASE IF NOT EXISTS cv_database;\n"
        sql += "USE cv_database;\n\n"
        
        # Table creation statements (same as create_tables method)
        sql += "-- Create tables\n"
        sql += """CREATE TABLE IF NOT EXISTS candidates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(50),
    location VARCHAR(255),
    linkedin VARCHAR(255),
    website VARCHAR(255),
    summary TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);\n\n"""
        
        sql += """CREATE TABLE IF NOT EXISTS work_experience (
    id INT AUTO_INCREMENT PRIMARY KEY,
    candidate_id INT,
    job_title VARCHAR(255),
    company VARCHAR(255),
    location VARCHAR(255),
    start_date VARCHAR(50),
    end_date VARCHAR(50),
    description TEXT,
    FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
);\n\n"""
        
        sql += """CREATE TABLE IF NOT EXISTS education (
    id INT AUTO_INCREMENT PRIMARY KEY,
    candidate_id INT,
    degree VARCHAR(255),
    institution VARCHAR(255),
    location VARCHAR(255),
    graduation_date VARCHAR(50),
    gpa VARCHAR(10),
    FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
);\n\n"""
        
        sql += """CREATE TABLE IF NOT EXISTS skills (
    id INT AUTO_INCREMENT PRIMARY KEY,
    candidate_id INT,
    skill_name VARCHAR(255),
    FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
);\n\n"""
        
        sql += """CREATE TABLE IF NOT EXISTS certifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    candidate_id INT,
    certification_name VARCHAR(255),
    FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
);\n\n"""
        
        sql += """CREATE TABLE IF NOT EXISTS languages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    candidate_id INT,
    language_name VARCHAR(255),
    FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE
);\n\n"""
        
        # Insert statements
        personal = parsed_data.get('personal_info', {})
        sql += "-- Insert candidate data\n"
        sql += f"""INSERT INTO candidates (full_name, email, phone, location, linkedin, website, summary) VALUES (
    '{escape_sql(personal.get('full_name', ''))}',
    '{escape_sql(personal.get('email', ''))}',
    '{escape_sql(personal.get('phone', ''))}',
    '{escape_sql(personal.get('location', ''))}',
    '{escape_sql(personal.get('linkedin', ''))}',
    '{escape_sql(personal.get('website', ''))}',
    '{escape_sql(parsed_data.get('summary', ''))}'
);\n\n"""
        
        sql += "SET @candidate_id = LAST_INSERT_ID();\n\n"
        
        # Work experience
        if parsed_data.get('work_experience'):
            sql += "-- Insert work experience\n"
            for exp in parsed_data['work_experience']:
                sql += f"""INSERT INTO work_experience (candidate_id, job_title, company, location, start_date, end_date, description) VALUES (
    @candidate_id,
    '{escape_sql(exp.get('job_title', ''))}',
    '{escape_sql(exp.get('company', ''))}',
    '{escape_sql(exp.get('location', ''))}',
    '{escape_sql(exp.get('start_date', ''))}',
    '{escape_sql(exp.get('end_date', ''))}',
    '{escape_sql(exp.get('description', ''))}'
);\n\n"""
        
        # Education
        if parsed_data.get('education'):
            sql += "-- Insert education\n"
            for edu in parsed_data['education']:
                sql += f"""INSERT INTO education (candidate_id, degree, institution, location, graduation_date, gpa) VALUES (
    @candidate_id,
    '{escape_sql(edu.get('degree', ''))}',
    '{escape_sql(edu.get('institution', ''))}',
    '{escape_sql(edu.get('location', ''))}',
    '{escape_sql(edu.get('graduation_date', ''))}',
    '{escape_sql(edu.get('gpa', ''))}'
);\n\n"""
        
        # Skills
        if parsed_data.get('skills'):
            sql += "-- Insert skills\n"
            for skill in parsed_data['skills']:
                if skill:
                    sql += f"INSERT INTO skills (candidate_id, skill_name) VALUES (@candidate_id, '{escape_sql(skill)}');\n"
            sql += "\n"
        
        # Certifications
        if parsed_data.get('certifications'):
            sql += "-- Insert certifications\n"
            for cert in parsed_data['certifications']:
                if cert:
                    sql += f"INSERT INTO certifications (candidate_id, certification_name) VALUES (@candidate_id, '{escape_sql(cert)}');\n"
            sql += "\n"
        
        # Languages
        if parsed_data.get('languages'):
            sql += "-- Insert languages\n"
            for lang in parsed_data['languages']:
                if lang:
                    sql += f"INSERT INTO languages (candidate_id, language_name) VALUES (@candidate_id, '{escape_sql(lang)}');\n"
        
        # Write to file
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(sql)
            print(f"SQL file generated: {output_path}")
            return True
        except Exception as e:
            print(f"Error writing SQL file: {e}")
            return False
    
    def process_cv(self, pdf_path, save_to_db=True, generate_sql=True, sql_output_path=None):
        """
        Process CV from PDF to MySQL
        
        Args:
            pdf_path (str): Path to PDF file
            save_to_db (bool): Whether to save to database
            generate_sql (bool): Whether to generate SQL file
            sql_output_path (str): Path for SQL output file
        """
        print(f"\n{'='*60}")
        print(f"Processing CV: {pdf_path}")
        print(f"{'='*60}\n")
        
        # Extract text from PDF
        print("Step 1: Extracting text from PDF...")
        cv_text = self.extract_text_from_pdf(pdf_path)
        if not cv_text:
            print("Failed to extract text from PDF")
            return False
        print(f"Extracted {len(cv_text)} characters")
        
        # Parse with Gemini
        print("\nStep 2: Parsing CV with Gemini AI...")
        parsed_data = self.parse_cv_with_gemini(cv_text)
        if not parsed_data:
            print("Failed to parse CV")
            return False
        print("CV parsed successfully")
        
        # Display parsed data summary
        print("\n" + "="*60)
        print("EXTRACTED INFORMATION")
        print("="*60)
        personal = parsed_data.get('personal_info', {})
        print(f"Name: {personal.get('full_name', 'N/A')}")
        print(f"Email: {personal.get('email', 'N/A')}")
        print(f"Phone: {personal.get('phone', 'N/A')}")
        print(f"Location: {personal.get('location', 'N/A')}")
        print(f"Work Experience: {len(parsed_data.get('work_experience', []))} entries")
        print(f"Education: {len(parsed_data.get('education', []))} entries")
        print(f"Skills: {len(parsed_data.get('skills', []))} skills")
        print("="*60 + "\n")
        
        # Save to database
        if save_to_db and self.db_config:
            print("Step 3: Saving to MySQL database...")
            if self.connect_to_database():
                self.create_tables()
                candidate_id = self.insert_candidate_data(parsed_data)
                if candidate_id:
                    print(f"✓ Data saved to database (Candidate ID: {candidate_id})")
        
        # Generate SQL file
        if generate_sql:
            if not sql_output_path:
                sql_output_path = f"cv_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
            print(f"\nStep 4: Generating SQL file...")
            if self.generate_sql_file(parsed_data, sql_output_path):
                print(f"✓ SQL file saved: {sql_output_path}")
        
        print("\n" + "="*60)
        print("CV PROCESSING COMPLETED")
        print("="*60 + "\n")
        
        return True
    
    def close_connection(self):
        """Close database connection"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            print("Database connection closed")


def main(file_pth):
    """Main function for command-line usage"""
    print("="*60)
    print("CV to MySQL Parser - Powered by Gemini AI")
    print("="*60 + "\n")

    from dotenv import load_dotenv
    import os

    load_dotenv()  # Load variables from .env into the environment

    # Configuration
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

    DB_CONFIG = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'database': os.getenv('DB_NAME', 'cv_database'),
        'user': os.getenv('DB_USER', 'your_username'),
        'password': os.getenv('DB_PASSWORD', 'your_password')

    }

    '''
    # Configuration
    GEMINI_API_KEY = "YOUR_GEMINI_API_KEY_HERE"
    
    # MySQL configuration (optional - set to None if you only want SQL file output)
    DB_CONFIG = {
        'host': 'localhost',
        'database': 'cv_database',
        'user': 'root',
        'password': 'your_password'
    }
    '''
    # Or set to None to skip database insertion
    # DB_CONFIG = None
    
    '''
    # Check command line arguments
    if len(sys.argv) < 2:
        print("Usage: python cv_parser.py <path_to_cv.pdf>")
        print("\nExample: python cv_parser.py resume.pdf")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    if not os.path.exists(pdf_path):
        print(f"Error: File not found: {pdf_path}")
        sys.exit(1)
    '''
    

    # Initialize parser
    parser = CVParser(GEMINI_API_KEY, DB_CONFIG)
    
    # Process CV
    try:
        parser.process_cv(
            #pdf_path=pdf_path,
            pdf_path=file_pth,
            save_to_db=(DB_CONFIG is not None),
            generate_sql=True
        )
    except Exception as e:
        print(f"Error processing CV: {e}")
    finally:
        parser.close_connection()


if __name__ == "__main__":
    main()