from discord.ui import View, Button
from datetime import datetime
import discord

class QuizView(View):
    def __init__(self, user, timeout_seconds):
        super().__init__(timeout=timeout_seconds)
        self.user = user
        self.selected_index = None
        self.elapsed = None
        self.start_time = datetime.utcnow()
        self.message = None

    async def interaction_check(self, interaction: discord.Interaction):
        return interaction.user.id == self.user.id

    async def disable_buttons(self):
        for child in self.children:
            child.disabled = True

    async def handle_answer(self, interaction: discord.Interaction, index: int):
        self.selected_index = index
        self.elapsed = int((datetime.utcnow() - self.start_time).total_seconds())
        await self.disable_buttons()
        await interaction.response.edit_message(view=self)
        self.stop()

    async def on_timeout(self):
        await self.disable_buttons()
        try:
            if self.message:
                await self.message.edit(view=self)
        except Exception:
            pass
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
