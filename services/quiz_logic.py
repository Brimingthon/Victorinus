import os
import json
from models.config import QuizConfig

QUIZZES_DIR = os.path.join(os.path.dirname(__file__), '..', 'quizzes')

def list_quizzes():
    return [f[:-5] for f in os.listdir(QUIZZES_DIR) if f.endswith(".json")]

def load_quiz(quiz_name: str) -> QuizConfig:
    path = os.path.join(QUIZZES_DIR, f"{quiz_name}.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return QuizConfig.parse_obj(json.load(f))
