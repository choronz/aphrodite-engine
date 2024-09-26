#!/bin/bash

python_executable=python$1
# python_ver=echo $1 | tr '.' '\0'
cuda_home=/usr/local/cuda-$2

# Update paths
PATH=${cuda_home}/bin:$PATH
LD_LIBRARY_PATH=${cuda_home}/lib64:$LD_LIBRARY_PATH

# Install requirements
$python_executable -m pip install wheel packaging
$python_executable -m pip install -r requirements-cuda.txt

# Limit the number of parallel jobs to avoid OOM
export MAX_JOBS=2

export TORCH_CUDA_ARCH_LIST="8.9"

# Build
$python_executable setup.py bdist_wheel --dist-dir=dist --py-limited-api=dist
