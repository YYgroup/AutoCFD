

import re
from typing import List
import os

from metagpt.actions import Action
from metagpt.schema import Message

from qa_module import AsyncQA_Ori, AsyncQA_OpenFOAM_LLM
import config_path
import sys
import glob
from Statistics import global_statistics
import subprocess
import json
from utils.util import log_with_time, read_dict_and_create_files, parser_allrun_script, parser_inputfiles

class CorrectorAction(Action):

    JUDGE_MISSING_FILE_PROMPT: str = """You are an OpenFOAM teacher. Please determine whether the reason for the error is a missing file based on the origial input files, the error content and current input file list.
    If the reason for the error is a missing file, return the missing file name in ```...``` (example: ```0/k```); otherwise, return 'NO MISSING FILE' without any other texts.
    
    # ORIGINAL INPUT FILES:
    {input_files}

    # ERROR CONTENT:
    {error_content}

    # CURRENT INPUT FILE LIST:
    {input_file_list}

    # RESPONSE:
    """

    MISSING_FILE_PROMPT: str = """You are an OpenFOAM teacher. The OpenFOAM input file is missing the file: {missing_file_name}. Please add the missing file to the original input file.
    
    # PROBLEM DESCRIPTION:
    {requirement}

    # ORIGINAL INPUT FILES:
    ```
    {input_files}
    ```

    No comments are allowed.
    Please ensure that the returned content includes the Origin INPUT FILE and {missing_file_name}.
    According to your task, return ```your_code_here ``` with NO other texts.
    # your code:
    """
    # Note that you need to return the entire modified file in the same format, never return a single modified fragment, making sure there are no other characters. 

    FIND_PRPMPT: str = """Analyze the given error message from the `openfoam2406` command to identify which files in the provided list are related to the error. Return the filenames and corresponding folder paths in a specified format.

# Steps

1. **Understand the Error**: Carefully read the provided error message `{error}` to identify key information that indicates which file(s) could be associated with the error.
2. **Match Files**: Compare the diagnostic details from the error message with the names and contents of the given input files from `{file_list}` and their locations in `{folder_list}`.
3. **Select Relevant Files**: Determine which files are most likely related to the error based on the analysis.
4. **Output the Results**: Format the results using the specified output format, listing only the filenames and their folders.

# Output Format

Use the following structure for the output:
- <filename>file_name1, file_name2, ..., file_nameN</filename> in <filefolder>file_folder1, file_folder2, ..., file_folderN</filefolder>```
- Ensure file_name1, file_name2, ..., come from {file_list} and file_folder1, file_folder2, ..., come from {folder_list}
- Ensure there are no other texts, comments, or additional formatting in the output.
    """

    CORRECT_PROMPT: str = """
    to rewrite a OpenFoam {file_name} foamfile in {file_folder} folder that could solve the error:
    ERROR INFO:
    ```
    {error}
    ```
    Please modify the input files you generated according to the error message. If the error include "Unable to set reference cell for field p\nPlease supply either pRefCell or pRefPoint", you should add pRefCell and pRefValue in SIMPLE, PISO or PIMPLE. "residualControl" fields cannot appear in PIMPLE.
    ORIGINAL INPUT FILES:
    ```
    {input_files}
    ```
    Note that you need to return the entire input files in the same format, never return a single modified fragment, because I want to save and run the file directly, making sure there are no other characters. No comments are allowed.
    According to your task, return ```your_code_here ``` with NO other texts,
    your code:
    """

    CORRECT_DIVERGENCE_PROMPT: str = """
    to rewrite a OpenFOAM controlDict foamfile in system folder to solve divergence problems. Specifically, you can reduce deltaT by ten times.
    ORIGINAL INPUT FILES:
    ```
    {input_files}
    ```
    Note that you need to return the entire modified file in the same format, never return a single modified fragment, because I want to save and run the file directly, making sure there are no other characters. 
    Do not add any comments.
    According to your task, return ```your_code_here ``` with NO other texts,
    your code:
    """

    async def run(self, with_messages:List[Message]=None, **kwargs) -> Message:

        base_path = config_path.Case_PATH
        
        file_text, files_names,folder_names = self.read_files_into_dict(base_path)
        os.chdir(base_path)
        error_info = with_messages[-1].content.split('<command>')[0]
        command = with_messages[-1].content.split('<command>')[1]
        # 在 with_messages 中找到最后一个 Corrector 消息
        last_corrector_msg = None
        for msg in with_messages:
            if 'Corrector' == msg.role:
                last_corrector_msg = msg
        if last_corrector_msg != None:
            last_foamfiles = last_corrector_msg.content
        else:
            last_foamfiles = parser_inputfiles(with_messages[1].content)

        requirement = config_path.description
        command = command.strip()
        log_with_time(f"command: {command}")
        log_with_time(f"requirement: {requirement}")

        if global_statistics.loop >= config_path.max_loop:
            log_with_time(f'Reach max loops: {config_path.max_loop}')
            config_path.should_stop = True
            log_with_time("should_stop")
            return "Reach max loop !"
        elif global_statistics.Executability < 3:
            global_statistics.loop = global_statistics.loop + 1
            log_with_time(f'loop:{global_statistics.loop}')

        # 运行报错
        if error_info == "error" and command != "None":

            command_err = f"{config_path.Case_PATH}/log.{command}"
            error_content = self.read_error_content(command_err)

            async_qa = AsyncQA_Ori()
            
            # 缺失文件
            if "FOAM FATAL ERROR" in error_content and "cannot find file" in error_content:
                # 获取当前文件夹下的所有文件
                files = glob.glob(os.path.join(config_path.Case_PATH, '*'))
                # 过滤出文件夹，即以'/'结尾的路径
                dirs = [f for f in files if os.path.isdir(f)]
                all_files = []
                for dir in dirs:
                    for f in glob.glob(os.path.join(dir, '*')):
                        if os.path.isfile(f):
                            all_files.append(f)
                cur_file_list = [os.path.relpath(f, config_path.Case_PATH) for f in all_files]

                prompt_judge_missing_file = self.JUDGE_MISSING_FILE_PROMPT.format(input_files=last_foamfiles, error_content=error_content, input_file_list=cur_file_list)
                log_with_time(f'prompt_judge_missing_file: {prompt_judge_missing_file}')
                missing_file_name = await async_qa.ask(prompt_judge_missing_file)
                log_with_time(f'missing_file_name: {missing_file_name}')
                prompt_missing_file = self.MISSING_FILE_PROMPT.format(missing_file_name=missing_file_name, requirement=requirement, input_files=last_foamfiles)
                log_with_time(f'prompt_missing_file:\n{prompt_missing_file}')
                rsp_input_files = await async_qa.ask(prompt_missing_file)
                input_files = self.parse_inputfiles(rsp_input_files)
            # 不缺失文件
            else:
                prompt_final = self.FIND_PRPMPT.format(command=command, error=error_content, file_list=files_names, folder_list=folder_names)
                log_with_time(f'related_file_rsp_prompt:\n{prompt_final}')

                related_file_rsp = await async_qa.ask(prompt_final)
                log_with_time(f'related_file_rsp: {related_file_rsp}')

                files_names_rewirte = self.parse_file_list(related_file_rsp)
                log_with_time(f'files_names_rewirte:{files_names_rewirte}')

                file_folders_rewirte = self.parse_folder_name(related_file_rsp)
                files_names_rewirte = [name.strip().strip("'") for name in files_names_rewirte.split(',')]
                file_folders_rewirte = [folder.strip().strip("'") for folder in file_folders_rewirte.split(',')]

                n_rewrite = len(files_names_rewirte)
                log_with_time(f"n_rewrite: {n_rewrite}")
                log_with_time(f"files_names_rewirte: {files_names_rewirte}")

                # 每次重写一个文件
                if files_names_rewirte:
                    input_files = last_foamfiles
                    for file in files_names_rewirte:
                        try:
                            file_folder = folder_names[file]
                            
                            prompt_rewrite = self.CORRECT_PROMPT.format(file_name=file, file_folder=file_folder, error=error_content, input_files=input_files)
                            log_with_time(f'prompt_rewrite:\n{prompt_rewrite}')
                            rewrite_rsp = await async_qa.ask(prompt_rewrite)
                            # log_with_time(f'rewrite_rsp:\n{rewrite_rsp}')
                            input_files = self.parse_inputfiles(rewrite_rsp)
                            # log_with_time(f'input_files after parse:\n{input_files}')
                        except KeyError:
                            continue
                else:
                    return "error but no rewritable files"
            # 重写整个文件（可以尝试重写部分文件）
            try:
                subprocess.run(f'rm -rf {config_path.Case_PATH}', shell=True, check=True, capture_output=True)
                try:
                    input_files_dict = json.loads(input_files, strict=False)
                except json.JSONDecodeError as e:
                    log_with_time(f"解析JSON数据时出现错误: {e}")
                    input_files_dict = {}
                read_dict_and_create_files(input_files_dict, config_path.Case_PATH)
                # 复制 mesh 文件
                mesh_path_list = config_path.mesh_path.split(';')
                for mesh_path in mesh_path_list:
                    system_index = mesh_path.rfind('system/')
                    constant_index = mesh_path.rfind('constant/')
                    if system_index > 0:
                        rel_mesh_path = mesh_path[system_index:]
                    elif constant_index > 0:
                        rel_mesh_path = mesh_path[constant_index:]

                    source_mesh_path = mesh_path
                    destination_mesh_path = os.path.join(config_path.Case_PATH, rel_mesh_path)
                    # 确保文件的目录存在
                    os.makedirs(os.path.dirname(destination_mesh_path), exist_ok=True)
                    subprocess.run(f'cp {source_mesh_path} {destination_mesh_path}', shell=True, check=True, capture_output=True)
                    log_with_time(f"copy mesh file: {source_mesh_path} to {destination_mesh_path}")
            except subprocess.CalledProcessError as e:
                log_with_time(f"When remove old case:{config_path.Case_PATH}, meet Error: {e}")
            return input_files
        # 求解发散
        elif error_info == "divergence":
            # 获取 deltaT
            try:
                foamfiles = json.loads(last_foamfiles)
            except json.JSONDecodeError as e:
                log_with_time(f"解析JSON数据时出现错误: {e}")
                foamfiles = {}
                config_path.should_stop = True
                return last_foamfiles
            deltaT = float(foamfiles['system/controlDict']['deltaT'])

            # 修改输入文件
            async_qa = AsyncQA_Ori()
            if deltaT <= 1e-5:
                config_path.should_stop = True
                return last_foamfiles
            
            # 将 controlDict 中的 deltaT 除以 10
            prompt_rewrite = self.CORRECT_DIVERGENCE_PROMPT.format(input_files=last_foamfiles)
            log_with_time(f'prompt_rewrite:\n{prompt_rewrite}')
            rewrite_rsp = await async_qa.ask(prompt_rewrite)
            input_files = self.parse_inputfiles(rewrite_rsp)

            # 创建新的文件目录
            try:
                subprocess.run(f'rm -rf {config_path.Case_PATH}', shell=True, check=True, capture_output=True)
                try:
                    input_files_dict = json.loads(input_files, strict=False)
                except json.JSONDecodeError as e:
                    log_with_time(f"解析JSON数据时出现错误: {e}")
                    input_files_dict = {}
                read_dict_and_create_files(input_files_dict, config_path.Case_PATH)
                # 复制 mesh 文件
                mesh_path_list = config_path.mesh_path.split(';')
                for mesh_path in mesh_path_list:
                    system_index = mesh_path.rfind('system/')
                    constant_index = mesh_path.rfind('constant/')
                    if system_index > 0:
                        rel_mesh_path = mesh_path[system_index:]
                    elif constant_index > 0:
                        rel_mesh_path = mesh_path[constant_index:]

                    source_mesh_path = mesh_path
                    destination_mesh_path = os.path.join(config_path.Case_PATH, rel_mesh_path)
                    # 确保文件的目录存在
                    os.makedirs(os.path.dirname(destination_mesh_path), exist_ok=True)
                    subprocess.run(f'cp {source_mesh_path} {destination_mesh_path}', shell=True, check=True, capture_output=True)
                    log_with_time(f"copy mesh file: {source_mesh_path} to {destination_mesh_path}")
            except subprocess.CalledProcessError as e:
                log_with_time(f"When remove old case:{config_path.Case_PATH}, meet Error: {e}")
            return input_files
        elif error_info == "timeout":
            return "timeout"
        elif error_info == "convergence":
            return "convergence"
    
    def read_files_into_dict(self, base_path):
        """
        将指定目录下的所有文件内容读取到一个字典中，并返回文件内容字典、文件名列表和文件夹名字典。
        
        Args:
            base_path (str): 基准路径，即需要读取的目录。
        
        Returns:
            tuple: 一个包含三个元素的元组，分别为文件内容字典、文件名列表和文件夹名字典。
                - file_contents (dict): 文件内容字典，键为文件名，值为文件内容。
                - file_names (list): 文件名列表，包含所有读取的文件名。
                - folder_names (dict): 文件夹名字典，键为文件名，值为文件所在文件夹相对于基准路径的相对路径。
        
        Raises:
            无
        
        """
        file_contents = {} 
        file_names = []  
        folder_names = {}   
        base_depth = base_path.rstrip(os.sep).count(os.sep) 
        
        for root, dirs, files in os.walk(base_path):
            current_depth = root.rstrip(os.sep).count(os.sep)
            if current_depth == base_depth + 1:  
                for file in files:
                    file_path = os.path.join(root, file) 

                    try:
                        with open(file_path, 'r') as file_handle:
                            lines = file_handle.readlines()
                            if len(lines) > 1000:
                                file_contents[file] = ''.join(lines[:20]) 
                            else:
                                file_contents[file] = ''.join(lines)


                            folder_names[file] = os.path.relpath(root, base_path)
                            file_names.append(file)
                    except UnicodeDecodeError:
                        log_with_time(f"Skipping file due to encoding error: {file_path}")
                        continue
                    except Exception as e:
                        log_with_time(f"Error reading file {file_path}: {e}")

        return file_contents, file_names, folder_names
    
    def read_error_content(self, error_file_name):
        if os.path.exists(error_file_name):
            with open(error_file_name, 'r') as file:
                lines = file.readlines()

            error_indices = None
            for i, line in enumerate(lines):
                if 'FOAM FATAL IO ERROR' in line.upper() or 'FOAM FATAL ERROR' in line.upper():
                    error_indices = i
                    break

            start_index = max(0, error_indices - 10)
            end_index = min(len(lines), error_indices + 200)

            error_content = [line.strip() for line in lines[start_index:end_index]]
            error_content = '\n'.join(error_content)
        return error_content
        
    @staticmethod
    def parse_file_list(rsp):
        """
        解析文件列表响应并提取任务文件夹名称。
        
        Args:
            rsp (str): 文件列表的响应字符串。
        
        Returns:
            str: 提取到的任务文件夹名称，如果未找到则返回 'None'。
        
        """
        pattern = r"<filename>(.*)</filename>"
        match = re.search(pattern, rsp, re.DOTALL)
        your_task_folder = match.group(1) if match else 'None'
        return your_task_folder
    
    @staticmethod
    def parse_folder_name(rsp):
        """
        从响应字符串中解析出任务文件夹名称。
        
        Args:
            rsp (str): 响应字符串，包含任务文件夹名称的信息。
        
        Returns:
            str: 解析出的任务文件夹名称，如果未找到则返回 'None'。
        
        """
        pattern = r"<filefolder>(.*)</filefolder>"
        match = re.search(pattern, rsp, re.DOTALL)
        your_task_folder = match.group(1) if match else 'None'
        return your_task_folder
    
    @staticmethod
    def parse_inputfiles(rsp):
        """
        解析输入文件内容，获取任务文件夹名称。
        
        Args:
            rsp (str): 输入的字符串内容，包含任务文件夹名称。
        
        Returns:
            str: 解析得到的任务文件夹名称，如果未找到则返回'None'。
        
        """

        left_blocket_pos = rsp.find('{')
        right_blocket_pos = rsp.rfind('}')
        
        input_files = rsp[left_blocket_pos:right_blocket_pos+1]
        return input_files

