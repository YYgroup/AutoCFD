import os
import asyncio
import requests
from concurrent.futures import ThreadPoolExecutor
from openai import OpenAI

import config_path
from Statistics import global_statistics


class AsyncQA_Ori:

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(AsyncQA_Ori, cls).__new__(cls, *args, **kwargs)
            cls._instance._initialized = False
        return cls._instance
    
    def init_instance(self):
        if not self._initialized:
            self.qa_interface = setup_qa_ori()
            self.executor = ThreadPoolExecutor()
            self._initialized = True

    async def ask(self, question, system_msg=""):
        loop = asyncio.get_running_loop()

        result = await loop.run_in_executor(self.executor, self.qa_interface, question, system_msg)
        return result

    def close(self):
        self.executor.shutdown()

class AsyncQA_OpenFOAM_LLM:

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(AsyncQA_OpenFOAM_LLM, cls).__new__(cls, *args, **kwargs)
            cls._instance._initialized = False
        return cls._instance
    
    def init_instance(self):
        if not self._initialized:
            self.qa_interface = setup_qa_openfoam_llm()
            self.executor = ThreadPoolExecutor()
            self._initialized = True

    async def ask(self, question, system_msg=""):
        loop = asyncio.get_running_loop()

        result = await loop.run_in_executor(self.executor, self.qa_interface, question, system_msg)
        return result

    def close(self):
        self.executor.shutdown()

def setup_qa_ori():

    def get_qwen_response(user_msg, system_msg=""):

        client = OpenAI(api_key=os.environ.get("API_KEY"),
                        base_url=os.environ["BASE_URL"],
        )
        if system_msg == "":
            messages=[
                {
                    "role": "user",
                    "content": user_msg
                }
            ]
        else:
            messages=[
                {
                    "role": "system",
                    "content": system_msg
                },
                {
                    "role": "user",
                    "content": user_msg
                }
            ]
        chat_completion = client.chat.completions.create(
            messages=messages,
            model=config_path.model,
            temperature=config_path.temperature
        )
        chat_completion_dict = dict(chat_completion)
        # print(chat_completion_dict.keys())
        usage = chat_completion_dict['usage']
        usage = dict(usage)
        total_tokens = usage['total_tokens']
        prompt_tokens = usage['prompt_tokens']
        completion_tokens = usage['completion_tokens']

        global_statistics.total_tokens += total_tokens
        global_statistics.prompt_tokens += prompt_tokens
        global_statistics.completion_tokens += completion_tokens

        return chat_completion.choices[0].message.content

    return get_qwen_response
    

def setup_qa_openfoam_llm():
    def get_openfoam_llm_response(user_msg, system_msg=""):
        base_url = config_path.openfoam_llm_base_url
        
        headers = {
            'Content-Type': 'application/json'
        }

        data = {
            'model': "openfoam_llm", 
            'messages': [],
            "max_tokens": 4000,
        }

        if system_msg:
            data['messages'].append({
                "role": "system",
                "content": system_msg
            })

        data['messages'].append({
            "role": "user",
            "content": user_msg
        })

        response = requests.post(base_url, headers=headers, json=data)
        if response.status_code == 200:
            chat_completion = response.json()

            usage = chat_completion['usage']
            usage = dict(usage)
            total_tokens = usage['total_tokens']
            prompt_tokens = usage['prompt_tokens']
            completion_tokens = usage['completion_tokens']
            global_statistics.total_tokens += total_tokens
            global_statistics.prompt_tokens += prompt_tokens
            global_statistics.completion_tokens += completion_tokens

            return chat_completion['choices'][0]['message']['content']
        
        else:
            print(f"Failed to get response: {response.status_code} {response.text}")
            return None

    return get_openfoam_llm_response