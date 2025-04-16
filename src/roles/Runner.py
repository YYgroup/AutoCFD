

from metagpt.roles.role import Role
from metagpt.schema import Message
from metagpt.logs import logger

from actions.RunnerAction import RunnerAction
from actions.InputWriterAction import InputWriterAction
from actions.CorrectorAction import CorrectorAction
from utils.util import log_with_time

class Runner(Role):
    name: str = "Foamer"
    profile: str = "Runner"
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        # Initialize actions specific to the Architect role
        self.set_actions([RunnerAction]) 

        self._watch({InputWriterAction, CorrectorAction})
    async def _act(self) -> Message:
        logger.info(f"{self._setting}: to do {self.rc.todo}({self.rc.todo.name})")
        todo = self.rc.todo

        context = self.get_memories()
        log_with_time(f"Runner input:{context}")
        msg = await todo.run(context)
        log_with_time(f"Runner output:{msg}")
        
        msg = Message(content=msg, role=self.profile, cause_by=type(todo))
        return msg
