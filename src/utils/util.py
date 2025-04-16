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
        # 确保文件的目录存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        # import pdb
        # pdb.set_trace()
        # 写入文件内容
        with open(file_path, "w") as outf:
            file_content = body(single_file)
            outf.write(file_content)
