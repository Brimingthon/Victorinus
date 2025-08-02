import asyncio
import discord
import logging

_queue = asyncio.Queue()

async def enqueue_delete(message: discord.Message):
    await _queue.put(message)

async def delete_worker():
    while True:
        message = await _queue.get()
        try:
            await message.delete()
            await asyncio.sleep(0.5)  # безпечна затримка між видаленнями
        except (discord.Forbidden, discord.HTTPException) as e:
            logging.warning(f"❌ Помилка при видаленні: {e}")
        finally:
            _queue.task_done()
