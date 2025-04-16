

from metagpt.roles.role import Role
from metagpt.schema import Message
from metagpt.logs import logger


from actions.CorrectorAction import CorrectorAction
from actions.RunnerAction import RunnerAction
from utils.util import log_with_time

class Corrector(Role):
    name: str = "Carol"
    profile: str = "Corrector"
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.set_actions([CorrectorAction])

        # 订阅消息
        self._watch({RunnerAction})
    async def _act(self) -> Message:
        logger.info(f"{self._setting}: to do {self.rc.todo}({self.rc.todo.name})")
        todo = self.rc.todo

        context_all = self.get_memories()
        log_with_time(f'Corrector input:\n{context_all}')
        rewrite_inputfiles = await todo.run(context_all)
        log_with_time(f'Corrector output:\n{rewrite_inputfiles}')

        msg = Message(content=rewrite_inputfiles, role=self.profile, cause_by=type(todo))
        return msg
