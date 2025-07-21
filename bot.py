import discord
from discord.ext import commands
from discord.ui import View, Button
import asyncio
import json
import os
import sqlite3
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TOKEN")

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
    c.execute('''
        CREATE TABLE IF NOT EXISTS results (
            user_id TEXT PRIMARY KEY,
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
    c.execute('REPLACE INTO results (user_id, user_name, score) VALUES (?, ?, ?)', (user_id, user_name, score))
    conn.commit()
    conn.close()

def get_top_results(limit=5):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT user_name, score FROM results ORDER BY score DESC LIMIT ?', (limit,))
    results = c.fetchall()
    conn.close()
    return results

def has_completed(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT 1 FROM results WHERE user_id = ?', (user_id,))
    result = c.fetchone()
    conn.close()
    return result is not None

# === QUESTIONS ===
def load_questions():
    with open(QUESTIONS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

questions = load_questions()

# === BUTTON UI ===
class QuizView(View):
    def __init__(self, user, correct_index):
        super().__init__(timeout=20)
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
        if self.selected_index == self.correct_index:
            self.result_message = f"✅ Правильно! +{max(0, 100 - self.elapsed * 5)} балів."
        else:
            self.result_message = "❌ Неправильно."
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

# === EVENTS ===
@bot.event
async def on_ready():
    init_db()
    print(f"🔔 Вікторинус активний як {bot.user}")

@bot.command()
async def reload_questions(ctx):
    global questions
    questions = load_questions()
    await ctx.send("🔄 Питання перезавантажено.")

@bot.command()
async def вікторина(ctx):
    user = ctx.author

    if has_completed(str(user.id)):
        await ctx.send("❗ Ти вже проходив(-ла) вікторину.")
        return

    try:
        dm = await user.create_dm()
        await dm.send("📩 Починаємо вікторину! У тебе до **20 секунд** на кожне питання. Обери відповідь, натиснувши кнопку.")
    except discord.Forbidden:
        await ctx.send("❌ Не вдалося надіслати DM. Перевір, чи ти дозволяєш особисті повідомлення від учасників сервера.")
        return

    score = 0

    for q in questions:
        options = "\n".join([f"{chr(0x0410 + i)}. {opt}" for i, opt in enumerate(q["options"])])
        msg = await dm.send(f"❓ {q['question']}\n\n{options}")

        view = QuizView(user, q["answer_index"])
        await msg.edit(view=view)
        await view.wait()

        if view.selected_index == q["answer_index"]:
            score += max(0, 100 - view.elapsed * 5)

        await dm.send(view.result_message or "⌛ Час вийшов!")

    save_result(str(user.id), user.name, score)

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
