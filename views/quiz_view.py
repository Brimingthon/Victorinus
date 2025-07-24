from discord.ui import View, Button
from datetime import datetime
import discord

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
