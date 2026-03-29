import os
import sys
import re
import json
import shutil
import subprocess
import collections
import time, datetime
import inspect

from openai import OpenAI
#from utils.parser_openfoam import parse_nested_string, dict_to_string
from utils.butterfly.foamfile import FoamFile

import pdb

def log_with_time(message):
    """Helper function to print message with current timestamp."""
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    split_line = "="*80
    # 获取当前帧的信息
    frame = inspect.currentframe()
    # 获取调用该函数的上一帧的信息
    caller_frame = frame.f_back
    # 获取文件名和行号
    filename = caller_frame.f_code.co_filename
    lineno = caller_frame.f_lineno
    print(f"[{current_time} {filename}:{lineno} INFO]: \n{split_line}\n{message}\n{split_line}", flush=True)

def correct_dimension(inputfiles_rsp, input_files_dict):
    dimensions = {
            '0/p': '[0 2 -2 0 0 0 0]',
            '0/U': '[0 1 -1 0 0 0 0]',
            '0/nut': '[0 2 -1 0 0 0 0]',
            '0/k': '[0 2 -2 0 0 0 0]',
            '0/epsilon': '[0 2 -3 0 0 0 0]',
            '0/omega': '[0 0 -1 0 0 0 0]',
            '0/T': '[0 0 0 1 0 0 0]',
            '0/alpha': '[1 -1 -1 0 0 0 0]',
            '0/gammaInt': '[0 0 0 0 0 0 0]',
            '0/ReThetat': '[0 0 0 0 0 0 0]',
            '0/nuTilda': '[0 2 -1 0 0 0 0]',
            '0/s': '[0 0 0 0 0 0 0]',
            '0/sigma': '[0 2 -2 0 0 0 0]',
        }
    for key in input_files_dict.keys():
        if key in dimensions.keys():
            input_files_dict[key]['dimensions'] = dimensions[key]
    
    inputfiles_begin = inputfiles_rsp.find("# Foam files:")
    inputfiles_end = inputfiles_rsp.find("# Allrun script:")
    left_bracket = inputfiles_rsp[inputfiles_begin:].find("{") + inputfiles_begin
    right_bracket = inputfiles_rsp[:inputfiles_end].rfind("}")
    if left_bracket >= 0 and right_bracket > left_bracket:
        inputfiles_rsp = inputfiles_rsp[:left_bracket] + json.dumps(input_files_dict) + inputfiles_rsp[right_bracket+1:]
    else:
        raise ValueError(f"无法从响应中提取 Foam Files JSON: {inputfiles_rsp}")

    return inputfiles_rsp, input_files_dict

def parser_inputfiles(inputfiles_rsp):
    inputfiles_begin = inputfiles_rsp.find("# Foam files:")
    inputfiles_end = inputfiles_rsp.find("# Allrun script:")
    left_bracket = inputfiles_rsp[inputfiles_begin:].find("{") + inputfiles_begin
    right_bracket = inputfiles_rsp[:inputfiles_end].rfind("}")
    if left_bracket >= 0 and right_bracket > left_bracket:
        return inputfiles_rsp[left_bracket:right_bracket+1]
    else:
        raise ValueError(f"无法从响应中提取 Foam Files JSON: {inputfiles_rsp}")

def parser_allrun_script(inputfiles_rsp):
    pattern = r"# Allrun script:(.*)"
    match = re.search(pattern, inputfiles_rsp, re.DOTALL)
    if match:
        return match[1]
    else:
        raise ValueError(f"无法从响应中提取 Allrun Script: {inputfiles_rsp}")


def _split_line(line):
        """Split lines which ends with { to two lines."""
        return line[4:-1] + "\n" + \
            (len(line) - len(line.strip()) - 4) * ' ' + '{'

def body(single_file):
    """Return body string."""
    # remove None values
    def remove_none(d):
        if isinstance(d, (dict, collections.OrderedDict)):
            return collections.OrderedDict(
                (k, remove_none(v)) for k, v in d.items()
                if v == {} or (v and remove_none(v)))
        elif isinstance(d, (list, tuple)):
            return [remove_none(v) for v in d if v and remove_none(v)]
        else:
            return d
        return remove_none

    # make python dictionary look like c++ dictionary!!
    of = json.dumps(single_file, indent=4, separators=(";", "\t\t")) \
        .replace('\\"', '@').replace('"\n', ";\n").replace('"', '') \
        .replace('};', '}').replace('\t\t{', '{').replace('@', '"')
    
    # remove first and last {} and prettify[!] the file
    content = (line[4:] if not line.endswith('{') else _split_line(line)
                for line in of.split("\n")[1:-1])
    return "\n\n".join(content)

def read_dict_and_create_files(file_dict, case_path):
    new_file_list = []
    new_item = {}
    for rel_path in file_dict:
        file_path = os.path.join(case_path, rel_path)
        single_file = file_dict[rel_path]
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w") as outf:
            file_content = body(single_file)
            outf.write(file_content)


def get_solver_name(case_dir: str):
    with open(f'{case_dir}/system/controlDict', 'r') as f:
        for line in f:
            if 'application' in line:
                return line.strip().split()[1].replace(';', '')

    return None

def parse_function_objects(file_path):
    content = FoamFile.from_file(file_path).values

    return content.get('functions', {}).keys()

def get_func_id(func, case_dir):
    postProcessingDict_path = os.path.join(case_dir, "system/postProcessingDict")
    func_id = f"{func}_1"
    if os.path.exists(postProcessingDict_path):
        existed_func_ids = parse_function_objects(postProcessingDict_path)
        for i in range(1, 100):
            func_id = f"{func}_{i}"
            if func_id not in existed_func_ids:
                return func_id
    else:
        return func_id

def write_function_objects(case_dir, function_content):

    header_content = '''FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      postProcessingDict;
}
'''

    postProcessingDict_path = os.path.join(case_dir, "system/postProcessingDict")
    if os.path.exists(postProcessingDict_path):        
        with open(postProcessingDict_path, 'r') as f:
            lines = f.readlines()
        last_brace_index = None
        for i in reversed(range(len(lines))):
            if lines[i].strip() == '}':
                last_brace_index = i
                break
        if last_brace_index is None:
            raise ValueError("未找到闭合的大括号 '}'")
        lines.insert(last_brace_index, function_content + '\n')
        with open(postProcessingDict_path, 'w') as f:
            f.writelines(lines)
    else:
        with open(postProcessingDict_path, "w") as f:
            f.write(header_content)
            f.write("functions\n{\n")
            f.write(function_content)
            f.write("\n}\n")
        print(f"postProcessingDict 已写入 {postProcessingDict_path}")
            
def add_latest_time_option(command, latestTime):
    if latestTime:
        command += f" -latestTime"
    return command

def add_time_option(command, time):
    if time != "":
        command += f" -time '{time}'"
    return command

def check_fields(fields):
    if ',' in fields:
        fields_list = [f.strip() for f in fields.split(",")]
        return " ".join(fields_list)
    else:
        return fields
def check_patches(patches):
    if ',' in patches:
        fields_list = [f.strip() for f in patches.split(",")]
        return " ".join(fields_list)
    else:
        return patches
    