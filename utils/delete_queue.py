import asyncio
import discord
import logging

_queue = asyncio.Queue()

NUM_DELETE_WORKERS = 2
DELAY_BETWEEN_DELETES = 1.2  # безпечна затримка

async def enqueue_delete(message: discord.Message):
    await _queue.put(message)

async def delete_worker():
    while True:
        message = await _queue.get()
        try:
            await message.delete()
            await asyncio.sleep(DELAY_BETWEEN_DELETES)
        except (discord.Forbidden, discord.HTTPException) as e:
            logging.warning(f"❌ Помилка при видаленні: {e}")
        finally:
            _queue.task_done()

def start_delete_workers():
    for _ in range(NUM_DELETE_WORKERS):
        asyncio.create_task(delete_worker())

