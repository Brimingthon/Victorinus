from pydantic import BaseModel
from typing import List

class QuizQuestion(BaseModel):
    question: str
    options: List[str]
    answer_index: int
    timeout: int = 20

class QuizConfig(BaseModel):
    attempts: int = 1
    show_feedback: bool = True
    auto_delete_dm: bool = False
    questions: List[QuizQuestion] = []
