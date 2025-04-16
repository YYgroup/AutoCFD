
import re
from typing import List
import os
import sys
from metagpt.actions import Action
from metagpt.schema import Message
from qa_module import AsyncQA_Ori, AsyncQA_OpenFOAM_LLM
import config_path
from Statistics import global_statistics

import json
import ast
import subprocess
from utils.butterfly.parser import CppDictParser
from utils.util import log_with_time, read_dict_and_create_files, parser_inputfiles, correct_dimension

class InputWriterAction(Action):

    SYSTEM_PROMPT: str = "You are an OpenFOAM expert. Below is a CFD Question, Mesh File and Input File Template. Generate a completed OpenFOAM input file in json according to the Input File Template. Then, generate a Allrun script. Please pay attention to the initial boundary conditions in the question. Do not generate any additional text or explanations."

    name: str = "InputWriterAction"

    async def run(self, with_messages:List[Message]=None, **kwargs) -> Message:
        
        system_msg = self.SYSTEM_PROMPT
        prompt = with_messages[0].content
        config_path.writter_prompt = prompt
        config_path.writter_system = system_msg
        async_qa_openfoam = AsyncQA_OpenFOAM_LLM()
        inputfiles_rsp = await async_qa_openfoam.ask(prompt, system_msg)
        log_with_time(f"inputfiles_rsp:\n{inputfiles_rsp}")
        inputfiles_json = ""
        while(inputfiles_json == ""):
            try:
                inputfiles_json = parser_inputfiles(inputfiles_rsp)
            except Exception as e:
                log_with_time(f"解析 Foam Files 数据时出现错误: {e}")
                inputfiles_rsp = await async_qa_openfoam.ask(prompt, system_msg)
        
        max_attempts = 5
        attempt_counter = 0
        boundary_fields_valid = False
        input_files_dict = {}

        mesh_path = config_path.mesh_path
        mesh_content, patch_names = self.parse_mesh_file(mesh_path)
        patches_list = []
        for patch_name in patch_names:
            patch = '\"' + patch_name + '\": {\"type\": \"xxx\", ...}'
            patches_list.append(patch)

        while not boundary_fields_valid and attempt_counter < max_attempts:
            try:
                # 尝试解析JSON
                input_files_dict = json.loads(inputfiles_json, strict=False)
                log_with_time("解析 Foam Files 成功")
                
                # 如果解析成功且foam_files非空，则检查boundaryField
                if input_files_dict:
                    for patch in patch_names:
                        if (patch not in input_files_dict.get('0/U', {}).get('boundaryField', {}) or 
                            patch not in input_files_dict.get('0/p', {}).get('boundaryField', {})):
                            log_with_time(f"Patch {patch} 未在boundaryField中找到.")
                            raise ValueError("边界字段验证失败")
                    boundary_fields_valid = True
                    
            except json.JSONDecodeError as e:
                log_with_time(f"解析 Foam Files 数据为 JSON 时出现错误: {e}\n正在重新生成 Foam Files")
                inputfiles_rsp = await async_qa_openfoam.ask(prompt, system_msg)
                inputfiles_json = parser_inputfiles(inputfiles_rsp)  # 假设这是用来解析响应的方法
                attempt_counter += 1
                
            except ValueError as e:
                # 如果验证boundaryField失败，重新获取并解析数据
                log_with_time(str(e))
                inputfiles_rsp = await async_qa_openfoam.ask(prompt, system_msg)
                inputfiles_json = parser_inputfiles(inputfiles_rsp)
                attempt_counter += 1
                    
        
        if input_files_dict == {}:
            log_with_time(f"解析 Foam Files 失败")
            sys.exit(0)
        else:
            # 纠正 0/ 文件的 dimensions
            inputfiles_rsp, input_files_dict = correct_dimension(inputfiles_rsp, input_files_dict)

        read_dict_and_create_files(input_files_dict, config_path.Case_PATH)

        # 复制 mesh 文件
        mesh_path_list = mesh_path.split(';')
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
        
        return inputfiles_rsp

    def parse_mesh_file(self, mesh_path):
        # 不同的 mesh 文件用分号 ; 分隔
        mesh_path_list = mesh_path.split(';')
        log_with_time(f"mesh_path_list:{mesh_path_list}")
        for file_path in mesh_path_list:
            if os.path.basename(file_path) == 'blockMeshDict' or os.path.basename(file_path) == 'blockMeshDict.m4':
                with open(file_path, 'r') as f:
                    lines = CppDictParser.remove_comments(f.read())
                    bmd = ' '.join(lines.replace('\r\n', ' ').replace('\n', ' ').split())
                # 解析出blockMeshDict中的boundary信息
                if bmd.find('boundary') > -1:
                    boundary_string = bmd.replace(' (', '(').replace(' )', ')') \
                        .split('boundary(')[-1].strip().replace('});', '}') \
                        .replace('));', ');').replace('((', ' (').replace(')(', ') (')
                    pattern = re.compile(r'quad2D\(.*?\)|backQuad\(.*?\)|frontQuad\(.*?\)|mergePatchPairs\(.*?\);')
                    boundary_string = re.sub(pattern, '', boundary_string)
                    # boundary_string = 'boundary(' + boundary_string + ')'
                    pattern = r'\(\s*\d+(?:\s+\d+)*\s*\)'
                    boundary_string = re.sub(pattern, '', boundary_string)
                    boundary_string = re.sub(r'\s+', ' ', boundary_string)
                    # 解析出 patch name
                    patch_name_list = []
                    boundary_str = re.sub(r'\{.*?\}', '', boundary_string)
                    boundary_str = re.sub(r'\s+', ' ', boundary_str)
                    patch_names = boundary_str.strip().split(' ')
                    # 解析出blockMeshDict.m4中的patches信息
                elif bmd.find('patches') > -1:
                    boundary_string = bmd.replace(' (', '(').replace(' )', ')') \
                        .split('patches(')[-1].strip().replace('});', '}') \
                        .replace('));', ');').replace('((', ' ((').replace(')(', ') (')
                    pattern = re.compile(r'quad2D\(.*?\)|backQuad\(.*?\)|frontQuad\(.*?\)|mergePatchPairs\(.*?\);')
                    boundary_string = re.sub(pattern, '', boundary_string)
                    # boundary_string = 'patches(' + boundary_string
                    pattern = r'\(\s*\d+(?:\s+\d+)*\s*\)'
                    boundary_string = re.sub(pattern, '', boundary_string)
                    boundary_string = re.sub(r'\s+', ' ', boundary_string)
                    # 解析出 patch name
                    patch_name_list = []
                    boundary_str = boundary_string.replace('(', '').replace(')', '').replace(';', '')
                    boundary_str = re.sub(r'\s+', ' ', boundary_str)
                    parts = boundary_str.split(' ')
                    # print("parts =", parts)
                    for i in range(0, len(parts) - 1, 2):
                        patch_name_list.append(parts[i+1])
                    patch_names = patch_name_list
                else:
                    boundary_string = ''
                mesh_content = boundary_string
            elif os.path.basename(file_path) == 'boundary':
                with open(file_path, 'r') as f:
                    boundary_content = f.read()
                    l_pos = boundary_content.find('(')
                    r_pos = boundary_content.rfind(')')
                    boundary_string = boundary_content[l_pos: r_pos + 1]
                    boundary_string = ' '.join(boundary_string.replace('\r\n', ' ').replace('\n', ' ').split())
                    mesh_content = boundary_string
                    # 解析出 patch name
                    patch_name_list = []
                    pattern = re.compile(r'\{[^{}]*\}', re.DOTALL)
                    boundary_str = re.sub(pattern, '', boundary_string[1:-1])
                    boundary_str = re.sub(r'\s+', ' ', boundary_str)
                    parts = boundary_str.split(' ')
                    for i in range(0, len(parts)):
                        if parts[i] == '':
                            continue
                        else:
                            patch_name_list.append(parts[i])
                    patch_names = patch_name_list
        return mesh_content, patch_names

