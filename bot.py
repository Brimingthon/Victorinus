import discord
from discord.ext import commands
from discord.ui import View, Button
import asyncio
import json
import os
import sqlite3
from datetime import datetime
from dotenv import load_dotenv
import logging

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

bot = commands.Bot(command_prefix="!", intents=INTENTS)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "results.db")
QUESTIONS_PATH = os.path.join(BASE_DIR, "questions.json")

# === DATABASE ===
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Перевірка, чи таблиця існує і чи має неправильну схему
    c.execute("PRAGMA table_info(results)")
    columns = [col[1] for col in c.fetchall()]

    if columns == ['user_id', 'user_name', 'score', 'timestamp']:
        logging.warning("⚠️ Виявлено стару схему таблиці. Оновлюємо...")
        c.execute("DROP TABLE IF EXISTS results")

    c.execute('''
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            user_name TEXT,
            score INTEGER,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

def save_result(user_id, user_name, score):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('INSERT INTO results (user_id, user_name, score) VALUES (?, ?, ?)', (user_id, user_name, score))
    conn.commit()
    conn.close()

def get_top_results(limit=5):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT user_name, MAX(score) as max_score FROM results GROUP BY user_id ORDER BY max_score DESC LIMIT ?', (limit,))
    results = c.fetchall()
    conn.close()
    return results

def get_attempt_count(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT COUNT(*) FROM results WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else 0

# === QUESTIONS ===
quiz_config = {}

def load_questions():
    global quiz_config
    with open(QUESTIONS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
        quiz_config = {
            "attempts": data.get("attempts", 1),
            "show_feedback": data.get("show_feedback", True)
        }
        return data.get("questions", [])

questions = load_questions()

# === BUTTON UI ===
class QuizView(View):
    def __init__(self, user, correct_index, timeout_seconds):
        super().__init__(timeout=timeout_seconds)
        self.user = user
        self.correct_index = correct_index
        self.selected_index = None
        self.result_message = None
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

# === EVENTS ===
@bot.event
async def on_ready():
    init_db()
    logging.info(f"🔔 Вікторинус активний як {bot.user}")

@bot.command()
async def reload_questions(ctx):
    global questions
    questions = load_questions()
    await ctx.send("🔄 Питання перезавантажено.")
    logging.info("📚 Питання перезавантажено вручну.")

@bot.command()
async def вікторина(ctx):
    user = ctx.author
    attempt_count = get_attempt_count(str(user.id))

    if attempt_count >= quiz_config["attempts"]:
        await ctx.send("❗ Ти вичерпав(-ла) кількість спроб на вікторину.")
        logging.warning(f"{user} досяг максимальної кількості спроб.")
        return

    try:
        dm = await user.create_dm()
        await dm.send("📩 Ти готовий(-а) до проходження вікторини?")

        view = ConfirmView(user)
        confirm_msg = await dm.send("Натисни \"Почати\", щоб почати, або \"Скасувати\", щоб вийти:", view=view)
        await view.wait()

        if not view.confirmed:
            logging.warning(f"{user} скасував вікторину.")
            return
    except discord.Forbidden:
        await ctx.send("❌ Не вдалося надіслати DM. Перевір, чи ти дозволяєш особисті повідомлення від учасників сервера.")
        logging.error(f"Не вдалося надіслати DM до {user} (ID {user.id})")
        return

    logging.info(f"{user} (ID {user.id}) розпочав вікторину. Спроба №{attempt_count + 1}")
    score = 0

    for q in questions:
        timeout = q.get("timeout", 20)
        options = "\n".join([f"{chr(0x0410 + i)}. {opt}" for i, opt in enumerate(q["options"])])
        msg = await dm.send(f"❓ {q['question']}\n\n{options}")

        view = QuizView(user, q["answer_index"], timeout)
        await msg.edit(view=view)
        await view.wait()

        is_correct = (view.selected_index == q["answer_index"])
        points = max(0, 100 - view.elapsed * 5) if is_correct else 0
        score += points

        if quiz_config["show_feedback"]:
            await dm.send("✅ Правильно!" if is_correct else "❌ Неправильно.")

    save_result(str(user.id), user.name, score)
    logging.info(f"{user} завершив вікторину з рахунком {score}")
    await dm.send(f"🏁 Вікторина завершена! Твій рахунок: **{score} балів**.")

@bot.command()
async def рейтинг(ctx):
    results = get_top_results()
    if not results:
        await ctx.send("Ще ніхто не проходив вікторину.")
        return

    top = "\n".join([f"{i+1}. {name} — {score} балів" for i, (name, score) in enumerate(results)])
    await ctx.send(f"🏆 **ТОП-5 гравців:**\n{top}")

bot.run(TOKEN)
