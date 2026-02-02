# input information
import os
import sys
import yaml
from utils.util import log_with_time

# Function to load configuration from HIT.yaml
def load_config(file_path):
    global config
    with open(file_path, 'r') as file:
        config = yaml.safe_load(file)
    return config

# Define paths
Src_PATH = os.path.dirname(os.path.abspath(__file__))
Base_PATH = os.path.dirname(Src_PATH)
Case_PATH = ''

config_file_path = os.getenv('CONFIG_FILE_PATH', '')

log_with_time(f"config_file_path: {config_file_path}")

config = load_config(config_file_path)

# Set variables from config
case_name = os.path.splitext(os.path.basename(config_file_path))[0]
description = config.get('description', '')
postProcess_description = config.get('postProcess_description', '')
mesh_path = config.get('mesh_path', '')
runfile_path = config.get('runfile_path', '')
input_file_list = config.get('input_file_list', '')
usr_requirment = description + "<mesh_path>" + mesh_path
max_loop = config.get('max_loop', 10)
temperature = config.get('temperature', 0.7)
run_times = config.get('run_times', 1)
MetaGPT_PATH = config.get('MetaGPT_PATH', '')
model = config.get('model', '')
openfoam_llm = config.get('openfoam_llm', '')
openfoam_llm_base_url = config.get('openfoam_llm_base_url', '')
Run_PATH = f'{Base_PATH}/run/' + config.get('run_path', '')  # Modify to the actual path
should_stop = False
postprocess_should_stop = False
status = ''

writter_prompt = ''
writter_system = ''

# Set environment variables from config
os.environ["API_KEY"] = config.get("API_KEY", "")
os.environ["PROXY"] = config.get("PROXY", "")
os.environ["BASE_URL"] = config.get("BASE_URL", "")
os.environ["http_proxy"] = "http://localhost:7890"
os.environ["https_proxy"] = "http://localhost:7890"
# 用于后处理LLM的环境变量
os.environ["OPENAI_API_KEY"] = config.get("OPENAI_API_KEY", "")
os.environ["OPENAI_MODEL"] = config.get("OPENAI_MODEL", "")
os.environ["OPENAI_BASE_URL"] = config.get("OPENAI_BASE_URL", "")

# Add MetaGPT_PATH to sys.path
sys.path.append(MetaGPT_PATH)
sys.path.append(Src_PATH)

log_with_time("Configuration loaded successfully:")
log_with_time(f"usr_requirment: {usr_requirment}")

# Extract MetaGPT_PATH
config2_yaml_path = os.path.join(MetaGPT_PATH, "config/config2.yaml")

# Check if config2.yaml exists
if not os.path.exists(config2_yaml_path):
    raise FileNotFoundError(f"{config2_yaml_path} does not exist")

with open(config2_yaml_path, 'r') as file:
    config2_data = yaml.safe_load(file)

new_config2_data = {
    "llm": {
        "api_type": "openai",
        "model": model,
        "proxy": os.environ.get('PROXY'),
        "base_url": os.environ.get('BASE_URL'),
        "api_key": os.environ.get('API_KEY')
    }
}

# Write the modified config back to config2.yaml
with open(config2_yaml_path, 'w') as file:
    yaml.dump(new_config2_data, file, default_flow_style=False)

log_with_time(f"{config2_yaml_path} has been updated successfully.")