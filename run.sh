#!/bin/bash

source activate metagpt

case_name=vortex_shedding_c7_woT
export CONFIG_FILE_PATH=Benchmark/${case_name}.yaml
python src/main.py