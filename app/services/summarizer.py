import os
from openai import OpenAI
from typing import Dict, Optional
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
db = SQLAlchemy(app)

class BillSummarizer:
    def __init__(self):
        self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
    def summarize_bill(self, bill_text: str) -> Optional[Dict]:
        """
        Summarize a bill using OpenAI's GPT model
        Returns a dictionary containing the summary and key points
        """
        try:
            # Create a prompt that asks for a structured summary
            prompt = f"""Please analyze this bill text and provide:
            1. A brief summary (2-3 sentences)
            2. Key points (bullet points)
            3. Potential impact
            4. Main stakeholders affected

            Bill text:
            {bill_text}
            """
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a legislative analyst skilled at summarizing complex bills in simple terms."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            summary = response.choices[0].message.content
            
            # Parse the response into sections
            sections = summary.split('\n\n')
            
            return {
                'brief_summary': sections[0] if len(sections) > 0 else '',
                'key_points': sections[1] if len(sections) > 1 else '',
                'potential_impact': sections[2] if len(sections) > 2 else '',
                'stakeholders': sections[3] if len(sections) > 3 else ''
            }
            
        except Exception as e:
            print(f"Error in bill summarization: {str(e)}")
            return None
            
    def categorize_bill(self, title: str, summary: str) -> str:
        """
        Categorize a bill based on its title and summary using GPT
        """
        try:
            prompt = f"""Please categorize this bill into exactly ONE of these categories:
            - Healthcare
            - Education
            - Environment
            - Economy
            - Security
            - Other

            Title: {title}
            Summary: {summary}

            Return ONLY the category name, nothing else.
            """
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a legislative analyst who categorizes bills accurately."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=20
            )
            
            category = response.choices[0].message.content.strip().lower()
            return category if category in ['healthcare', 'education', 'environment', 'economy', 'security'] else 'other'
            
        except Exception as e:
            print(f"Error in bill categorization: {str(e)}")
            return 'other' 