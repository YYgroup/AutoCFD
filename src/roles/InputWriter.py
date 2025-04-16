

from metagpt.roles.role import Role
from metagpt.schema import Message

from metagpt.logs import logger

from actions.InputWriterAction import InputWriterAction
from actions.PrecheckerAction import PrecheckerAction
from metagpt.actions import UserRequirement
from utils.util import log_with_time

class InputWriter(Role):
    name: str = "Bob"
    profile: str = "InputWriter"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.set_actions([InputWriterAction]) 

        self._watch({PrecheckerAction})
    async def _act(self) -> Message:
        logger.info(f"{self._setting}: to do {self.rc.todo}({self.rc.todo.name})")
        todo = self.rc.todo
        
        log_with_time(f'InputWriter input: {self.rc.history}')
        code_text = await todo.run(self.rc.history)

        msg = Message(content=code_text, role=self.profile, cause_by=type(todo))
        return msg
    