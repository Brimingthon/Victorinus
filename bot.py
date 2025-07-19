import discord
from discord.ext import commands
import asyncio
import json
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()  # це читає .env файл (для локального запуску)

TOKEN = os.getenv("TOKEN")  # а це витягує токен з середовища

INTENTS = discord.Intents.default()
INTENTS.message_content = True
INTENTS.members = True

bot = commands.Bot(command_prefix="!", intents=INTENTS)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(BASE_DIR, "questions.json"), "r", encoding="utf-8") as f:
    questions = json.load(f)

if os.path.exists("results.json"):
    with open("results.json", "r", encoding="utf-8") as f:
        RESULTS = json.load(f)
else:
    RESULTS = {}

EMOJIS = ["🇦", "🇧", "🇨", "🇩"]


@bot.event
async def on_ready():
    print(f"🔔 Вікторинус активний як {bot.user}")


@bot.command()
async def вікторина(ctx):
    user = ctx.author

    if str(user.id) in RESULTS:
        await ctx.send("❗ Ти вже проходив(-ла) вікторину.")
        return

    guild = ctx.guild
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        user: discord.PermissionOverwrite(read_messages=True, send_messages=True, add_reactions=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True, add_reactions=True)
    }

    channel = await guild.create_text_channel(f"вікторина-{user.name}", overwrites=overwrites)
    await channel.send(
        f"{user.mention}, починаємо вікторину! Обери правильну відповідь, натиснувши реакцію. У тебе буде до **20 секунд** на кожне питання.")

    score = 0

    for q in questions:
        options = "\n".join(f"{EMOJIS[i]} {opt}" for i, opt in enumerate(q["options"]))
        message = await channel.send(f"❓ {q['question']}\n\n{options}")

        for emoji in EMOJIS[:len(q["options"])]:
            await message.add_reaction(emoji)

        def check(reaction, user_reacted):
            return (
                    user_reacted.id == user.id and
                    reaction.message.id == message.id and
                    str(reaction.emoji) in EMOJIS
            )

        start_time = datetime.now()
        try:
            reaction, _ = await bot.wait_for('reaction_add', timeout=20.0, check=check)
            elapsed = (datetime.now() - start_time).seconds
            choice_index = EMOJIS.index(str(reaction.emoji))

            if choice_index == q["answer_index"]:
                points = max(0, 100 - elapsed * 5)
                score += points
                await channel.send(f"✅ Правильно! +{points} балів.")
            else:
                await channel.send("❌ Неправильно.")
        except asyncio.TimeoutError:
            await channel.send("⌛ Час вийшов!")

    RESULTS[str(user.id)] = {"name": user.name, "score": score}

    with open("results.json", "w", encoding="utf-8") as f:
        json.dump(RESULTS, f, ensure_ascii=False, indent=2)

    await channel.send(f"🏁 Вікторина завершена! Твій рахунок: **{score} балів**.")
    await asyncio.sleep(30)
    await channel.delete()


@bot.command()
async def рейтинг(ctx):
    if not RESULTS:
        await ctx.send("Ще ніхто не проходив вікторину.")
        return

    sorted_results = sorted(RESULTS.items(), key=lambda x: x[1]['score'], reverse=True)
    top = "\n".join([f"{i + 1}. {v['name']} — {v['score']} балів" for i, (_, v) in enumerate(sorted_results[:5])])
    await ctx.send(f"🏆 **ТОП-5 гравців:**\n{top}")


bot.run(TOKEN)
