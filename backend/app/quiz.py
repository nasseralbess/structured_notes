from typing import List, Dict
import openai
from pydantic import BaseModel

class QuizQuestion(BaseModel):
    question: str
    options: List[str]
    correct_answer: int
    explanation: str

class Quiz(BaseModel):
    title: str
    questions: List[QuizQuestion]

class QuizGenerator:
    def __init__(self, api_key: str):
        openai.api_key = api_key
    
    def generate_quiz(self, notes: str, num_questions: int = 5) -> Quiz:
        """Generate a multiple-choice quiz based on the provided notes."""
        prompt = f"""
        Generate a multiple-choice quiz based on the following notes. 
        Create {num_questions} questions with 4 options each.
        For each question, provide:
        1. The question text
        2. Four possible answers (one correct, three incorrect)
        3. The index of the correct answer (0-3)
        4. A brief explanation of why the answer is correct
        
        Format the response as a JSON object with this structure:
        {{
            "title": "Quiz Title",
            "questions": [
                {{
                    "question": "Question text",
                    "options": ["Option 1", "Option 2", "Option 3", "Option 4"],
                    "correct_answer": 0,
                    "explanation": "Explanation text"
                }}
            ]
        }}
        
        Notes:
        {notes}
        """
        
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={ "type": "json_object" }
        )
        
        return Quiz.parse_raw(response.choices[0].message.content)