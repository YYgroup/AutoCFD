

from metagpt.roles.role import Role
from metagpt.schema import Message

from metagpt.logs import logger

from actions.PrecheckerAction import PrecheckerAction
from metagpt.actions import UserRequirement
from utils.util import log_with_time

class Prechecker(Role):
    name: str = "Alice"
    profile: str = "Prechecker"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.set_actions([PrecheckerAction]) 

        self._watch({UserRequirement})
    async def _act(self) -> Message:
        logger.info(f"{self._setting}: to do {self.rc.todo}({self.rc.todo.name})")
        todo = self.rc.todo
        
        log_with_time(f'Prechecker input: {self.rc.history}')
        prompt = await todo.run(self.rc.history)

        msg = Message(content=prompt, role=self.profile, cause_by=type(todo))
        return msg
    