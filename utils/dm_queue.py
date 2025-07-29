import asyncio
import discord
import logging

_queue = asyncio.Queue()

async def send_dm(user: discord.User, message: str):
    await _queue.put((user, message))

async def dm_worker():
    while True:
        user, message = await _queue.get()
        try:
            dm = await user.create_dm()
            await dm.send(message)
            await asyncio.sleep(0.3)
        except discord.Forbidden:
            logging.warning(f"❌ Не вдалося надіслати DM користувачу {user}")
        except Exception as e:
            logging.error(f"⚠️ Помилка при надсиланні DM: {e}")
        finally:
            _queue.task_done()