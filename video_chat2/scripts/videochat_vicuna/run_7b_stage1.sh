#!/bin/bash
# Please modify the ${MASTER_NODE}:${MASTER_PORT}
MASTER_NODE=127.0.0.1 
MASTER_PORT=$((10000 + $RANDOM % 100))
NNODE=1
NUM_GPUS=2
OUTPUT_DIR="$(dirname $0)/$JOB_NAME"


torchrun --rdzv_endpoint=${MASTER_NODE}:${MASTER_PORT} \
    --nnodes=${NNODE} \
    --nproc_per_node=${NUM_GPUS} \
    --rdzv_backend=c10d \
    tasks/train_qformer.py \
    $(dirname $0)/config_7b_stage1.py \
    output_dir ${OUTPUT_DIR}
