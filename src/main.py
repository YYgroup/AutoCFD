
import asyncio

from metagpt.config2 import Config
from metagpt.context import Context
from metagpt.schema import Message
from metagpt.environment.base_env import Environment

from qa_module import AsyncQA_Ori, AsyncQA_OpenFOAM_LLM
from roles.Prechecker import Prechecker
from roles.InputWriter import InputWriter
from roles.Corrector import Corrector
from roles.Runner import Runner
import config_path
from Statistics import Statistics, global_statistics
import time
from utils.util import log_with_time

async def main():
    overall_stats = Statistics()
    for _ in range(config_path.run_times):
        global_statistics.reset()
        start_time = time.time()
        global_statistics.runtimes = _ + 1
        log_with_time(f"runtimes: {_ + 1}")
        config_path.should_stop = False
        await run_instance()

        global_statistics.running_time = time.time() - start_time
        if global_statistics.Executability == 3:
            overall_stats.pass_num += 1
        global_statistics.save_to_file(config_path.Case_PATH)
        overall_stats.save(global_statistics)

    overall_stats.average(config_path.run_times)
    overall_stats.display()
    overall_stats.save_ave_file(config_path.Case_PATH)

async def run_instance():
    async_qa_ori = AsyncQA_Ori()
    async_qa_ori.init_instance()
    async_qa_openfoam_llm = AsyncQA_OpenFOAM_LLM()
    async_qa_openfoam_llm.init_instance()

    env = Environment()
    prechecker = Prechecker()
    writter = InputWriter()
    runner = Runner()
    corrector = Corrector()

    env.add_roles([prechecker, writter, runner, corrector])

    env.publish_message(Message(content=config_path.usr_requirment, send_to=Prechecker))
    while not env.is_idle and not config_path.should_stop:
        await env.run()

if __name__ == "__main__":

    asyncio.run(main())