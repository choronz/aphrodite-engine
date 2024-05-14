#!/bin/bash
export TORCH_CUDA_ARCH_LIST="8.9"
./runtime.sh python setup.py bdist_wheel
