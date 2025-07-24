# 📁 commands/quiz.py
import discord
from discord import app_commands
from db import repository
from services.quiz_logic import load_quiz, list_quizzes
from views.quiz_view import QuizView, ConfirmView

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
    user = interaction.user
    config = load_quiz(name)
    if not config:
        await interaction.response.send_message("❌ Вікторина не знайдена.", ephemeral=True)
        return

    attempt_count = await repository.get_attempt_count(str(user.id), name)
    if attempt_count >= config.attempts:
        await interaction.response.send_message("❗ Ти вичерпав(-ла) кількість спроб на цю вікторину.", ephemeral=True)
        return

    await interaction.response.send_message("📬 Перевір свої DM — вікторина надіслана туди.", ephemeral=True)

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
    for q in config.questions:
        options = "\n".join([f"{chr(0x0410 + i)}. {opt}" for i, opt in enumerate(q.options)])
        msg = await dm.send(f"❓ {q.question}\n\n{options}")
        messages_to_delete.append(msg)
        view = QuizView(user, q.answer_index, q.timeout)
        await msg.edit(view=view)
        await view.wait()

        is_correct = (view.selected_index == q.answer_index)
        points = max(0, 100 - view.elapsed * 5) if is_correct else 0
        score += points

        if config.show_feedback:
            feedback = await dm.send("✅ Правильно!" if is_correct else "❌ Неправильно.")
            messages_to_delete.append(feedback)

    await repository.save_result(str(user.id), user.name, name, score)
    final_msg = await dm.send(f"🏁 Вікторина **{name}** завершена! Твій рахунок: **{score} балів**.")
    messages_to_delete.append(final_msg)

    if config.auto_delete_dm:
        import asyncio
        await asyncio.sleep(20)
        for m in messages_to_delete:
            try:
                await m.delete()
            except (discord.Forbidden, discord.HTTPException):
                continue

@app_commands.command(name="ranking", description="Показати ТОП-5 по вікторині")
@app_commands.describe(name="Назва вікторини")
@app_commands.autocomplete(name=autocomplete_quizzes)
async def ranking(interaction: discord.Interaction, name: str):
    results = await repository.get_top_results(name)
    if not results:
        await interaction.response.send_message("Немає результатів для цієї вікторини.", ephemeral=True)
        return
    top = "\n".join([f"{i+1}. {username} — {score} балів" for i, (username, score) in enumerate(results)])
    await interaction.response.send_message(f"🏆 **ТОП-5 — {name}:**\n{top}")

@app_commands.command(name="quizzes", description="Список доступних вікторин")
async def quizzes(interaction: discord.Interaction):
    names = list_quizzes()
    if not names:
        await interaction.response.send_message("Немає доступних вікторин.", ephemeral=True)
        return
    await interaction.response.send_message("📚 Доступні вікторини:\n" + "\n".join(f"- {n}" for n in names), ephemeral=True)

# === Функція для реєстрації команд ===
def setup_commands(bot: discord.ext.commands.Bot):
    bot.tree.add_command(quiz)
    bot.tree.add_command(ranking)
    bot.tree.add_command(quizzes)
