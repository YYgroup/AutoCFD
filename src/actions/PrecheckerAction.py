
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

class PrecheckerAction(Action):

    PROMPT_TEMPLATE: str = '''# Question:
{description}

# Mesh File:
{mesh_content}

# Input File Template:
{input_file_template}

# Response:
'''

    SUPPLEMENT_PROMPT: str = '''You are an OpenFOAM teacher, and now you need to generate all OpenFoam input files (except for grid related files) based on the problem description. First, consider what input files need to be generated for the 0 directory.
# Problem description:
{description}

# Patch Names:
{_patch_names}

Please check if each important Patch Name in the Initial file has a value.
If the Initial boundary conditions is not sufficient, return '[File Name]: [Patch Name]\n...[File Name]: [Patch Name]\n' without any other text.

# Response format:
[File Name]: [Parameter Name]

# Response:
'''

    name: str = "PrecheckerAction"

    async def run(self, with_messages:List[Message]=None, **kwargs) -> Message:
        # 1. 读取 mesh 文件
        # 2. 生成 inputfile
        # 3. 构建 case 目录
        # 4. 复制 blockMeshDict

        case_name = config_path.case_name
        if config_path.run_times > 1:
            config_path.Case_PATH = f"{config_path.Run_PATH}/{case_name}_{global_statistics.runtimes}"
        else:
            config_path.Case_PATH = f"{config_path.Run_PATH}/{case_name}"
        os.makedirs(config_path.Case_PATH, exist_ok=True)

        async_qa_ori = AsyncQA_Ori()
        requirement = with_messages[0].content
        log_with_time(f"requirement:{requirement}")
        description = requirement.split('<mesh_path>')[0]
        mesh_path = requirement.split('<mesh_path>')[1]
        mesh_content, patch_names = self.parse_mesh_file(mesh_path)
        log_with_time(f"mesh_content:\n{mesh_content}")
        
        # 判断用户的输入是否足够详细，通过问答的形式得到更详细的内容
        stop_flag = False
        while(stop_flag==False):
            prompt_supplement = self.SUPPLEMENT_PROMPT.format(description=description, _patch_names=', '.join(patch_names))
            rsp_supplement = await async_qa_ori.ask(prompt_supplement)
            if 'The description is sufficient' in rsp_supplement:
                log_with_time(f"rsp_supplement:{rsp_supplement}")
                stop_flag = True
            else:
                # log_with_time(f"rsp_supplement:{rsp_supplement}")
                user_supplement = input(f"{'='*50}\n\nThe current problem is described as follows:\n\n{description}\n\n{'-'*50}\n\nPlease refer to the following prompts to supplement the problem description:\n\n{rsp_supplement}\n\n{'-'*50}\n\nYour input is valuable! Please enter your supplemental information below (or simply press 'Enter' to skip this step):\n\n{'='*50}\n")
                if user_supplement == '':
                    stop_flag = True
                else:
                    description += user_supplement
        config_path.description = description

        patches_list = []
        for patch_name in patch_names:
            patch = '\"' + patch_name + '\": {\"type\": \"xxx\", ...}'
            patches_list.append(patch)

        template_0 = ''
        dimensions = {'0/p': '[0 2 -2 0 0 0 0]', '0/U': '[0 1 -1 0 0 0 0]'}
        for i in ['0/p', '0/U']:
            template_0 += '\"' + i + '\": {\"FoamFile\": {\"version\": \"2.0\", \"format\": \"ascii\", \"class\": \"xxx\", \"object\": \"xxx\"}, \"dimensions\": \"' + dimensions[i] + '\", \"internalField\": \"uniform xxx\", \"boundaryField\": {' + ','.join(patches_list) + '}}, '
        input_file_template = '''{''' + template_0 + ''' ..., \"system/fvSolution\": {\"FoamFile\": {\"version\": \"2.0\", \"format\": \"ascii\", \"class\": \"dictionary\", \"object\": \"fvSolution\"}, \"solvers\": {\"xxx\": {\"xxx\": \"xxx\", \"xxx\": \"xxx\", \"xxx\": \"xxx\", \"xxx\": \"xxx\"}, \"xxx\": {\"xxx\": \"xxx\", \"xxx\": \"xxx\"}, \"xxx\": {\"xxx\": \"xxx\", \"xxx\": \"xxx\", \"xxx\": \"xxx\", \"xxx\": \"xxx\"}}, \"xxx\": {\"xxx\": \"xxx\", \"xxx\": \"xxx\", \"xxx\": \"xxx\", \"xxx\": \"xxx\"}, ...}}'''
    
        prompt = self.PROMPT_TEMPLATE.format(description=description, mesh_content=mesh_content, input_file_template=input_file_template)
        log_with_time(f"prompt:\n{prompt}")

        return prompt

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

