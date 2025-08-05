# 📁 commands/quiz.py
import os
import discord
from discord import app_commands
from db import postgres as repository
from services.queue_manager import quiz_queue_manager
from services.quiz_logic import load_quiz, list_quizzes
from views.quiz_view import QuizView, ConfirmView
from utils.dm_queue import send_dm
from utils.delete_queue import enqueue_delete
import time
import asyncio
import logging

from datetime import datetime
from services.quiz_logic import load_quiz

# === Автокомпліт ===
async def autocomplete_quizzes(interaction: discord.Interaction, current: str):
    return [
        app_commands.Choice(name=q, value=q)
        for q in list_quizzes() if current.lower() in q.lower()
    ][:25]

@app_commands.command(name="quiz", description="Почати конкретну вікторину")
@app_commands.describe(name="Назва вікторини")
@app_commands.autocomplete(name=autocomplete_quizzes)
async def quiz(interaction: discord.Interaction, name: str):
    await interaction.response.defer(ephemeral=True)  # <-- одразу підтверджуємо

    user = interaction.user

    from services.queue_manager import quiz_queue_manager

    if not quiz_queue_manager.is_active(name):
        await interaction.followup.send("❗ Ця вікторина зараз недоступна.", ephemeral=True)
        return

    await quiz_queue_manager.add_to_queue(name, user)
    pos = quiz_queue_manager.get_position(name, user)
    if pos > 1:
        await send_dm(user, f"⏳ Ти в черзі на вікторину. Очікуй, твоя позиція: {pos}.")
        try:
            while True:
                next_user = await asyncio.wait_for(quiz_queue_manager.get_next_user(name), timeout=600)
                if next_user == user:
                    break
        except asyncio.TimeoutError:
            await send_dm(user, "⌛ Час очікування вичерпано. Спробуй ще раз пізніше.")
            return
        await asyncio.sleep(1)  # мінімальна затримка перед стартом

    config = load_quiz(name)
    if not config:
        await interaction.followup.send("❌ Вікторина не знайдена.", ephemeral=True)
        return

    attempt_count = await repository.get_attempt_count(str(user.id), name)
    if attempt_count >= config.attempts:
        await interaction.followup.send("❗ Ти вичерпав(-ла) кількість спроб на цю вікторину.", ephemeral=True)
        return

    await interaction.followup.send("📬 Перевір свої DM — вікторина надіслана туди.", ephemeral=True)


    try:
        await send_dm(user, f"📩 Ти готовий(-а) до проходження вікторини **{name}**?")
        view = ConfirmView(user)
        msg = await user.send("Натисни \"Почати\", щоб почати, або \"Скасувати\":", view=view)
        await view.wait()
        if not view.confirmed:
            return
    except discord.Forbidden:
        await interaction.response.send_message("❌ Не вдалося надіслати DM.", ephemeral=True)
        return

    score = 0
    messages_to_delete = []
    for idx, q in enumerate(config.questions):
        #logging.info(f"[{datetime.now()}] Надсилаємо питання #{idx + 1}")

        options = "\n".join([f"{chr(0x0410 + i)}. {opt}" for i, opt in enumerate(q.options)])
        deadline = int(time.time()) + q.timeout
        content = f"❓ {q.question}\n\n{options}\n\n⏳ Кінець питання <t:{deadline}:R>."

        view = QuizView(user, timeout_seconds=q.timeout)

        msg = await user.send(content, view=view)
        view.message = msg
        messages_to_delete.append(msg)

        #logging.info(f"[{datetime.now()}]  Очікуємо відповідь користувача...")
        await view.wait()
        #logging.info(f"[{datetime.now()}]  Користувач відповів")

        is_correct = (view.selected_index == q.answer_index)
        elapsed = view.elapsed
        points = max(0, 100 - elapsed * 2) if is_correct else 0
        score += points

        #logging.info(f"[{datetime.now()}] Починаємо збереження результату...")
        start = datetime.now()
        await repository.save_question_result(
            user_id=str(user.id),
            quiz_name=name,
            question_index=idx,
            elapsed_seconds=elapsed,
            points=points,
            is_correct=is_correct
        )
        #logging.info(f"[{datetime.now()}] Save took: {datetime.now() - start}")

        if config.show_feedback:
            feedback_text = "✅ Правильно!" if is_correct else "❌ Неправильно."
            logging.info(f"[{datetime.now()}] 📬 Відправка фідбеку...")
            await send_dm(user, feedback_text)
            logging.info(f"[{datetime.now()}] 📨 Фідбек надіслано")

    await repository.save_result(str(user.id), user.name, name, score)
    await send_dm(user, f"🏁 Вікторина **{name}** завершена! Твій рахунок: **{score} балів**.")

    if config.auto_delete_dm:
        await asyncio.sleep(5)
        for m in messages_to_delete:
            try:
                await enqueue_delete(m)
            except (discord.Forbidden, discord.HTTPException):
                continue

# === /ranking тимчасово вимкнений
# @app_commands.command(name="ranking", description="Показати ТОП-5 по вікторині")
# @app_commands.describe(name="Назва вікторини")
# @app_commands.autocomplete(name=autocomplete_quizzes)
# async def ranking(interaction: discord.Interaction, name: str):
#     results = await repository.get_top_results(name)
#     if not results:
#         await interaction.response.send_message("Немає результатів для цієї вікторини.", ephemeral=True)
#         return
#     top = "\n".join([f"{i+1}. {username} — {score} балів" for i, (username, score) in enumerate(results)])
#     await interaction.response.send_message(f"🏆 **ТОП-5 — {name}:**\n{top}")

@app_commands.command(name="quizzes", description="Список доступних вікторин")
async def quizzes(interaction: discord.Interaction):
    names = list_quizzes()
    if not names:
        await interaction.response.send_message("Немає доступних вікторин.", ephemeral=True)
        return
    await interaction.response.send_message("📚 Доступні вікторини:\n" + "\n".join(f"- {n}" for n in names), ephemeral=True)


@app_commands.command(name="quiz_toggle", description="Увімкнути/вимкнути вікторину")
@app_commands.describe(name="Назва вікторини", active="Чи активна вона?")
async def quiz_toggle(interaction: discord.Interaction, name: str, active: bool):
    config = load_quiz(name)
    if not config:
        await interaction.response.send_message("❌ Вікторина не знайдена.", ephemeral=True)
        return

    creator_ids = os.getenv("CREATOR_IDS", "").split(",")
    if str(interaction.user.id) not in creator_ids:
        await interaction.response.send_message("❌ Тільки творець вікторини може змінити її стан.", ephemeral=True)
        return

    quiz_queue_manager.set_active(name, active)
    status = "активна" if active else "неактивна"
    await interaction.response.send_message(f"✅ Вікторина `{name}` тепер {status}.", ephemeral=True)


# === Функція для реєстрації команд ===
def setup_commands(bot: discord.ext.commands.Bot):
    bot.tree.add_command(quiz)
    bot.tree.add_command(quiz_toggle)
    # bot.tree.add_command(ranking)  # тимчасово закоментовано
    bot.tree.add_command(quizzes)