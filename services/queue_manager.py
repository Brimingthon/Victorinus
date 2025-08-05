import asyncio
from typing import Dict

class QuizQueueManager:
    def __init__(self):
        self.queues: Dict[str, asyncio.Queue] = {}
        self.active_flags: Dict[str, bool] = {}

    def is_active(self, quiz_name: str) -> bool:
        return self.active_flags.get(quiz_name, True)

    def set_active(self, quiz_name: str, active: bool):
        self.active_flags[quiz_name] = active

    def get_queue(self, quiz_name: str) -> asyncio.Queue:
        if quiz_name not in self.queues:
            self.queues[quiz_name] = asyncio.Queue()
        return self.queues[quiz_name]

    async def add_to_queue(self, quiz_name: str, user):
        queue = self.get_queue(quiz_name)
        await queue.put(user)

    async def get_next_user(self, quiz_name: str):
        queue = self.get_queue(quiz_name)
        return await queue.get()

    def get_position(self, quiz_name: str, user) -> int:
        queue = self.get_queue(quiz_name)
        return list(queue._queue).index(user) + 1 if user in queue._queue else -1

quiz_queue_manager = QuizQueueManager()
