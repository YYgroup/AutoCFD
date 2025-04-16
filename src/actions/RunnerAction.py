
import re
import subprocess
from typing import List
import os
import shutil

from metagpt.actions import Action
from metagpt.schema import Message

from qa_module import AsyncQA_Ori
import config_path
import sys
import glob
import signal
import json
from Statistics import global_statistics
from utils.util import log_with_time, parser_inputfiles, parser_allrun_script

class RunnerAction(Action):

    CHECK_BLOCKMESH_PROMPT: str = """
        Your task is to add 'blockMesh' into Allrun script before other Linux commands.
        
        # Allrun:
        {allrun}

        # Return Fomat:
        ```sh
        your_allrun_file_here 
        ```

        # Return:
    """
    
    async def run(self, with_messages:List[Message]=None, **kwargs) -> Message:

        allrun_file_path = f'{config_path.Case_PATH}/Allrun'

        allrun_write = "None"

        if os.path.exists(allrun_file_path):

            with open(allrun_file_path, 'r', encoding='utf-8') as allrun_file:

                allrun_write = allrun_file.read()
                log_with_time(f'allrun_write2:\n{allrun_write}')

        if allrun_write == "None":
            async_qa_allrun = AsyncQA_Ori()

            InputWritter_output = with_messages[1].content
            allrun_write = parser_allrun_script(InputWritter_output)
            if "blockMesh" not in allrun_write:
                prompt_review_blockMesh = self.CHECK_BLOCKMESH_PROMPT.format(allrun=allrun_write)
                allrun_rsp = await async_qa_allrun.ask(prompt_review_blockMesh)
                allrun_write = self.parser_allrun_rsp(allrun_rsp)

            with open(allrun_file_path, 'w') as outfile:  
                outfile.write(allrun_write)
                
        log_with_time(f'allrun_write:\n{allrun_write}')

        out_file = os.path.join(config_path.Case_PATH, 'Allrun.out')
        err_file = os.path.join(config_path.Case_PATH, 'Allrun.err')

        self.remove_log_files(config_path.Case_PATH)
        if os.path.exists(err_file):
            os.remove(err_file)
        if os.path.exists(out_file):
            os.remove(out_file)
        self.remove_err_files(config_path.Case_PATH)
        self.remove_pro_files(config_path.Case_PATH)
        dir_path = config_path.Case_PATH
        initial_files = {}
        for subdir in os.listdir(dir_path):
            subdir_path = os.path.join(dir_path, subdir)
            if os.path.isdir(subdir_path):
                initial_files[subdir] = set(os.listdir(subdir_path))

        log_with_time(f"initial_files:{initial_files}")

        run_result = self.process_case(config_path.Case_PATH, out_file, err_file)
        
        error_logs = self.check_foam_errors(config_path.Case_PATH)
        log_with_time(f'error_logs:{error_logs}')

        commands_run = self.extract_commands_from_allrun_out(out_file)
        log_with_time(f"commands_run:{commands_run}")

        # 将执行过的指令与包含 error 的 log 文件进行比较，返回 执行过的指令 与 错误信息
        command = self.compare_commands_with_error_logs(commands_run, error_logs)
        log_with_time(f"command:{command}")

        error_info = run_result
        config_path.status = run_result
        if run_result == "convergence":
            result = "None"
            global_statistics.Executability = 3
            config_path.should_stop = True
        elif run_result == "divergence":
            result = "None"
            global_statistics.Executability = 2
        elif run_result == "error":
            result = command[0]['command']
            if "mesh" in result.lower():
                global_statistics.Executability = 0
            else:
                global_statistics.Executability = 1
        elif run_result == "timeout":
            result = "None"
            global_statistics.Executability = 2
        log_with_time(f"Executability: {global_statistics.Executability}")

        

        # result:
        # if 运行不报错：None
        # if 运行报错：command[0]['command']
        # if 运行报错且找不到对应的命令：<command>, <command>
        return error_info + '<command>' + result

    def parser_allrun_rsp(self, allrun_rsp):
        left_index = allrun_rsp.find('```sh')
        right_index = allrun_rsp.rfind('```')
        if left_index == -1 or right_index == -1:
            return allrun_rsp
        else:
            return allrun_rsp[left_index + len('```sh'):right_index]


    def process_case(self, case_path, out_file, err_file):
        # 执行 openfoam 指令
        error_info = ""
        timeout = 12 * 60 * 60 # 12 hours
        with open(out_file, 'w') as out, open(err_file, 'w') as err:
            process = subprocess.Popen(f'bash {case_path}/Allrun', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, preexec_fn=os.setsid)
            try:
                stdout, stderr = process.communicate(timeout=timeout)
                out.write(stdout)
                err.write(stderr)
                if process.returncode != 0:
                    error_info = f"Command failed with return code {process.returncode}: {stderr}"
            except subprocess.TimeoutExpired:
                error_info = "Time out"
                os.killpg(process.pid, signal.SIGKILL)
                # log_with_time(f"[INFO TIMEOUT] {case_path}: Process group {process.pid} has been killed.")

        if error_info != "":
            # log_path = glob.glob(os.path.join(case_path, 'log.*Foam'))[0]
            if len(glob.glob(os.path.join(case_path, 'log.*Foam'))) > 0:
                log_path = glob.glob(os.path.join(case_path, 'log.*Foam'))[0]
            else:
                log_path = glob.glob(os.path.join(case_path, 'log.*'))[0]
            with open(log_path, 'r') as f:
                log_content = f.read()
            if 'FOAM FATAL IO ERROR' in log_content or 'FOAM FATAL ERROR' in log_content:
                log_with_time(f"[INFO ERROR] {case_path}: {error_info}")
                return 'error'
            elif "Time out" in error_info:
                log_with_time(f"[INFO TIMEOUT] {case_path}: {error_info}")
                return 'timeout'
            else:
                log_with_time(f"[INFO DIVERGENCE] {case_path}: {error_info}")
                return 'divergence'
        else:
            # subprocess.run(f'cd {case_path} && touch open.foam', shell=True, check=True, capture_output=True)
            log_with_time(f"[INFO PASS]: {case_path}")
            return 'convergence'

    def check_foam_errors(self, log_dir):
        error_logs = []

        log_files = [f for f in os.listdir(log_dir) if f.startswith('log')]

        for log_file in log_files:
            log_path = os.path.join(log_dir, log_file)
            with open(log_path, 'r') as file:
                lines = file.readlines()

            log_with_time(f'log_file:{log_file}')
            error_indices = None
            for i, line in enumerate(lines):
                if ('error' in line.lower() and 'foam' in line.lower()) or 'command not found' in line.lower():
                    error_indices = i
                    break

            if error_indices is None:
                continue

            start_index = max(0, error_indices - 30)
            end_index = min(len(lines), error_indices + 60)

            error_content = [line.strip() for line in lines[start_index:end_index]]

            if error_content:
                error_logs.append({
                    'file': log_file,
                    'error_content': "\n".join(error_content)
                })

        return error_logs

    def remove_log_files(self, directory):
        log_files = glob.glob(os.path.join(directory, 'log*'))
        for log_file in log_files:
            os.remove(log_file)

    def extract_commands_from_allrun_out(self, allrun_out_path):
        commands = []
        with open(allrun_out_path, 'r') as file:
            lines = file.readlines()

        for line in lines:
            if line.startswith('Running '):

                command_part = line.split('Running ')[1]

                command = command_part.split(' on ')[0]
                command_true = command.split()[0]
                commands.append(command_true)
        
        return commands
    
    def compare_commands_with_error_logs(self, commands_run, error_logs):
        comparison_results = []
        for command in commands_run:
            for error_log in error_logs:
                if command in error_log['file']:
                    comparison_results.append({
                        'command': command,
                        'error_content': error_log['error_content']
                    })
                    break  # Assuming one match per command is enough
        return comparison_results

    def remove_err_files(self, directory):
        err_files = glob.glob(os.path.join(directory, '*.err'))

        for err_file in err_files:
            try:
                os.remove(err_file)
                log_with_time(f"Deleted file: {err_file}")
            except OSError as e:
                log_with_time(f"Error deleting file {err_file}: {e}")
                
    def remove_pro_files(self, directory):
        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)
            if os.path.isdir(item_path) and item.startswith('processor'):
                try:
                    shutil.rmtree(item_path)
                    log_with_time(f"Deleted folder: {item_path}")
                except Exception as e:
                    log_with_time(f"Error deleting folder {item_path}: {e}")
