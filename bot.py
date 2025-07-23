import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button
import json
import os
import sqlite3
from datetime import datetime
from dotenv import load_dotenv
import logging
import asyncio

load_dotenv()
TOKEN = os.getenv("TOKEN")

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    handlers=[logging.FileHandler("bot.log", encoding="utf-8"), logging.StreamHandler()]
)

INTENTS = discord.Intents.default()
INTENTS.message_content = True
INTENTS.members = True

class QuizBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=INTENTS)

    async def setup_hook(self):
        await self.tree.sync()
        logging.info("✅ Слеш-команди синхронізовано")

bot = QuizBot()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "results.db")
QUIZZES_DIR = os.path.join(BASE_DIR, "quizzes")

# === DATABASE ===
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            user_name TEXT,
            quiz_name TEXT,
            score INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def save_result(user_id, user_name, quiz_name, score):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT INTO results (user_id, user_name, quiz_name, score) VALUES (?, ?, ?, ?)', (user_id, user_name, quiz_name, score))
    conn.commit()
    conn.close()

def get_top_results(quiz_name, limit=5):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT user_name, MAX(score) FROM results WHERE quiz_name = ? GROUP BY user_id ORDER BY MAX(score) DESC LIMIT ?', (quiz_name, limit))
    results = c.fetchall()
    conn.close()
    return results

def get_attempt_count(user_id, quiz_name):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM results WHERE user_id = ? AND quiz_name = ?', (user_id, quiz_name))
    result = c.fetchone()
    conn.close()
    return result[0] if result else 0

def list_quizzes():
    return [f[:-5] for f in os.listdir(QUIZZES_DIR) if f.endswith(".json")]

def load_quiz(quiz_name):
    quiz_path = os.path.join(QUIZZES_DIR, f"{quiz_name}.json")
    if not os.path.exists(quiz_path):
        return None, None
    with open(quiz_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        config = {
            "attempts": data.get("attempts", 1),
            "show_feedback": data.get("show_feedback", True),
            "auto_delete_dm": data.get("auto_delete_dm", False)
        }
        return config, data.get("questions", [])

class QuizView(View):
    def __init__(self, user, correct_index, timeout_seconds):
        super().__init__(timeout=timeout_seconds)
        self.user = user
        self.correct_index = correct_index
        self.selected_index = None
        self.elapsed = 0
        self.start_time = datetime.now()

    async def interaction_check(self, interaction: discord.Interaction):
        return interaction.user.id == self.user.id

    async def disable_buttons(self):
        for child in self.children:
            child.disabled = True

    async def handle_answer(self, interaction: discord.Interaction, index: int):
        self.selected_index = index
        self.elapsed = (datetime.now() - self.start_time).seconds
        await self.disable_buttons()
        await interaction.response.edit_message(view=self)
        self.stop()

    @discord.ui.button(label="А", style=discord.ButtonStyle.primary)
    async def a_button(self, interaction: discord.Interaction, button: Button):
        await self.handle_answer(interaction, 0)

    @discord.ui.button(label="Б", style=discord.ButtonStyle.primary)
    async def b_button(self, interaction: discord.Interaction, button: Button):
        await self.handle_answer(interaction, 1)

    @discord.ui.button(label="В", style=discord.ButtonStyle.primary)
    async def c_button(self, interaction: discord.Interaction, button: Button):
        await self.handle_answer(interaction, 2)

    @discord.ui.button(label="Г", style=discord.ButtonStyle.primary)
    async def d_button(self, interaction: discord.Interaction, button: Button):
        await self.handle_answer(interaction, 3)

class ConfirmView(View):
    def __init__(self, user):
        super().__init__(timeout=30)
        self.user = user
        self.confirmed = False

    async def interaction_check(self, interaction: discord.Interaction):
        return interaction.user.id == self.user.id

    @discord.ui.button(label="Почати", style=discord.ButtonStyle.success)
    async def confirm_button(self, interaction: discord.Interaction, button: Button):
        self.confirmed = True
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content="✅ Починаємо!", view=self)
        self.stop()

    @discord.ui.button(label="Скасувати", style=discord.ButtonStyle.danger)
    async def cancel_button(self, interaction: discord.Interaction, button: Button):
        self.confirmed = False
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(content="❌ Вікторина скасована.", view=self)
        self.stop()

# === AUTOCOMPLETE ===
async def quiz_autocomplete(interaction: discord.Interaction, current: str):
    return [
        app_commands.Choice(name=q, value=q)
        for q in list_quizzes()
        if current.lower() in q.lower()
    ][:25]

# === SLASH COMMANDS ===

@bot.tree.command(name="quiz", description="Почати конкретну вікторину")
@app_commands.describe(name="Назва вікторини")
@app_commands.autocomplete(name=quiz_autocomplete)
async def quiz(interaction: discord.Interaction, name: str):
    user = interaction.user
    config, questions = load_quiz(name)

    if not questions:
        await interaction.response.send_message("❌ Вікторина не знайдена.", ephemeral=True)
        return

    attempt_count = get_attempt_count(str(user.id), name)
    if attempt_count >= config["attempts"]:
        await interaction.response.send_message("❗ Ти вичерпав(-ла) кількість спроб на цю вікторину.", ephemeral=True)
        return

    try:
        dm = await user.create_dm()
        await dm.send(f"📩 Ти готовий(-а) до проходження вікторини **{name}**?")
        view = ConfirmView(user)
        msg = await dm.send("Натисни \"Почати\", щоб почати, або \"Скасувати\":", view=view)
        await view.wait()
        if not view.confirmed:
            return
    except discord.Forbidden:
        await interaction.response.send_message("❌ Не вдалося надіслати DM.", ephemeral=True)
        return

    score = 0
    messages_to_delete = []
    for q in questions:
        timeout = q.get("timeout", 20)
        options = "\n".join([f"{chr(0x0410 + i)}. {opt}" for i, opt in enumerate(q["options"])])
        msg = await dm.send(f"❓ {q['question']}\n\n{options}")
        messages_to_delete.append(msg)
        view = QuizView(user, q["answer_index"], timeout)
        await msg.edit(view=view)
        await view.wait()
        is_correct = (view.selected_index == q["answer_index"])
        points = max(0, 100 - view.elapsed * 5) if is_correct else 0
        score += points
        if config["show_feedback"]:
            feedback_msg = await dm.send("✅ Правильно!" if is_correct else "❌ Неправильно.")
            messages_to_delete.append(feedback_msg)

    save_result(str(user.id), user.name, name, score)
    final_msg = await dm.send(f"🏁 Вікторина **{name}** завершена! Твій рахунок: **{score} балів**.")
    messages_to_delete.append(final_msg)

    if config.get("auto_delete_dm"):
        await asyncio.sleep(20)
        for msg in messages_to_delete:
            try:
                await msg.delete()
            except (discord.Forbidden, discord.HTTPException):
                continue

@bot.tree.command(name="ranking", description="Показати ТОП-5 по вікторині")
@app_commands.describe(name="Назва вікторини")
@app_commands.autocomplete(name=quiz_autocomplete)
async def ranking(interaction: discord.Interaction, name: str):
    results = get_top_results(name)
    if not results:
        await interaction.response.send_message("Немає результатів для цієї вікторини.", ephemeral=True)
        return
    top = "\n".join([f"{i+1}. {username} — {score} балів" for i, (username, score) in enumerate(results)])
    await interaction.response.send_message(f"🏆 **ТОП-5 — {name}:**\n{top}")

@bot.tree.command(name="quizzes", description="Список доступних вікторин")
async def quizzes(interaction: discord.Interaction):
    names = list_quizzes()
    if not names:
        await interaction.response.send_message("Немає доступних вікторин.", ephemeral=True)
        return
    await interaction.response.send_message("📚 Доступні вікторини:\n" + "\n".join(f"- {n}" for n in names), ephemeral=True)

@bot.event
async def on_ready():
    init_db()
    logging.info(f"🔔 Вікторинус активний як {bot.user}")

bot.run(TOKEN)
