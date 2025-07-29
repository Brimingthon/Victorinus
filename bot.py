# 📁 bot.py — запуск dm_worker
import discord
from discord.ext import commands
from utils.logger import setup_logger
from db.postgres import init_db
from commands.quiz import setup_commands
from utils.dm_queue import dm_worker
import os
import asyncio
from dotenv import load_dotenv

setup_logger()

load_dotenv()
TOKEN = os.getenv("TOKEN")

INTENTS = discord.Intents.default()
INTENTS.message_content = True
INTENTS.members = True

class QuizBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=INTENTS)

    async def setup_hook(self):
        setup_commands(self)
        await self.tree.sync()

bot = QuizBot()

@bot.event
async def on_ready():
    await init_db()
    asyncio.create_task(dm_worker())
    import logging
    logging.info(f"🔔 Вікторинус активний як {bot.user}")

bot.run(TOKEN)
