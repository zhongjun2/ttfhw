#!/bin/bash
set -e
source /usr/local/Ascend/ascend-toolkit/set_env.sh
g++ -shared -fPIC -o add_custom.so add_custom.cpp \
    -I${ASCEND_TOOLKIT_HOME}/include \
    -L${ASCEND_TOOLKIT_HOME}/lib64 \
    -lascend_hal 2>&1
echo "BUILD_SUCCESS"
