import os
import config_path

class Statistics:
    def __init__(self):
        self.loop = 0
        self.runtimes = 0
        self.Executability = 0
        self.total_tokens = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.pass_num = 0

    def reset(self):
        self.__init__()

    def save(self, other):
        self.loop += other.loop
        self.total_tokens += other.total_tokens
        self.prompt_tokens += other.prompt_tokens
        self.completion_tokens += other.completion_tokens

    def average(self, count):
        self.loop /= count
        self.total_tokens /= count
        self.prompt_tokens /= count
        self.completion_tokens /= count

    def display(self):
        print(f"Average Iterations: {self.loop}")
        print(f"Average Total Tokens: {self.total_tokens}")
        print(f"Average Prompt Tokens: {self.prompt_tokens}")
        print(f"Average Completion Tokens: {self.completion_tokens}")
        print(f"Total Pass Case: {self.pass_num}")
        
    def save_to_file(self, directory):
        os.makedirs(directory, exist_ok=True)
        file_path = os.path.join(directory, 'statistics.txt')
        with open(file_path, 'w') as f:
            f.write(f"Status: {config_path.status}\n")
            f.write(f"Iterations: {self.loop}\n")
            f.write(f"Total Tokens: {self.total_tokens}\n")
            f.write(f"Prompt Tokens: {self.prompt_tokens}\n")
            f.write(f"Completion Tokens: {self.completion_tokens}\n")

    def save_ave_file(self, directory):
        os.makedirs(directory, exist_ok=True)
        file_path = os.path.join(directory, 'ave_statistics.txt')
        with open(file_path, 'w') as f:
            f.write(f"Iterations: {self.loop}\n")
            f.write(f"Total Tokens: {self.total_tokens}\n")
            f.write(f"Prompt Tokens: {self.prompt_tokens}\n")
            f.write(f"Completion Tokens: {self.completion_tokens}\n")
            f.write(f"Total Pass Case: {self.pass_num}\n")

global_statistics = Statistics()