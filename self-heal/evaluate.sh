#!/bin/bash

#-----------------------------------------------------------------------
# SBATCH DIRECTIVES
#-----------------------------------------------------------------------
#
# Job name
#SBATCH --job-name=evaluate-asr
#
# Account and Partition
#SBATCH --partition=partition_name
#
# Output and error files. %A is the job ID, %a is the array task ID.
#SBATCH --output=logs/eval/slurm-%A_%a.out
#SBATCH --error=logs/eval/slurm-%A_%a.err
#
# Wall-clock time limit
#SBATCH --time=00:30:00
#
# Number of CPUs and GPU
#SBATCH --cpus-per-task=1
#SBATCH --gres=gpu:1
#
# Set the job array size.
# array size = task x triggers x models x trigger_flag = 4 x 5 x 2 x 2 = 80
#SBATCH --array=0-79

# check that the script is launched with sbatch
if [ "x$SLURM_JOB_ID" == "x" ]; then
   echo "You need to submit your job to the queuing system with sbatch"
   exit 1
fi

# Run the job from this directory:
cd ../BackdoorLLM-main/attack/DPA

# --- CONDA ENVIRONMENT ACTIVATION ---
echo "Initializing Conda..."
CONDA_BASE=$(conda info --base)
source "${CONDA_BASE}/etc/profile.d/conda.sh"

echo "Activating Conda environment: sft"
conda activate sft
if [ $? -ne 0 ]; then
    echo "Error: Failed to activate the 'sft' conda environment."
    exit 1
fi
echo "Conda environment 'sft' activated successfully."
# --- END CONDA ACTIVATION ---

# The modules to load:
module load devel/cuda/11.8

export CUDA_HOME=$(dirname $(dirname $(which nvcc)))
export PATH=$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$LD_LIBRARY_PATH

nvidia-smi

#-----------------------------------------------------------------------
# EXPERIMENT CONFIGURATION
#-----------------------------------------------------------------------

TASKS=("jailbreak" "refusal" "negsentiment" "sst2sentiment")
TRIGGERS=("badnet" "ctba" "mtba" "sleeper" "vpi")

# Matching pairs: base model ↔ lora model
MODELS=(
  "models--mistralai--Mistral-7B-Instruct-v0.1/snapshots/2dcff66eac0c01dc50e4c41eea959968232187fe"
  "models--meta-llama--Meta-Llama-3-8B-Instruct/snapshots/5f0b02c75b57c5855da9ae460ce51323ea669d8a"
)

LORA_MODELS=(
  "Mistral-7B"
  "Meta-Llama-3-8B"
)

TRIGGER_FLAGS=(
  "True"
  "False"
)

# Build combinations only with matched pairs
COMBINATIONS=()
for i in "${!MODELS[@]}"; do
  base_model=${MODELS[$i]}
  lora_model=${LORA_MODELS[$i]}
  for task in "${TASKS[@]}"; do
    for trigger in "${TRIGGERS[@]}"; do
      for trigger_flag in "${TRIGGER_FLAGS[@]}"; do
        COMBINATIONS+=("$task|$base_model|$trigger|$lora_model|$trigger_flag")
      done
    done
  done
done

# Total number of combinations
NUM_COMBINATIONS=${#COMBINATIONS[@]}

# Sanity check
if [ $SLURM_ARRAY_TASK_ID -ge $NUM_COMBINATIONS ]; then
  echo "Error: SLURM_ARRAY_TASK_ID $SLURM_ARRAY_TASK_ID exceeds number of combinations $NUM_COMBINATIONS"
  exit 1
fi

# Extract current combination
COMBO=${COMBINATIONS[$SLURM_ARRAY_TASK_ID]}
IFS="|" read TASK MODEL TRIGGER LORA TRIGGER_FLAG <<< "$COMBO"

echo "Running combination: task=$TASK, model=$MODEL, trigger=$TRIGGER, lora=$LORA, trigger_flag=$TRIGGER_FLAG"

#-----------------------------------------------------------------------
# EXECUTION
#-----------------------------------------------------------------------

python -u "backdoor_evaluate_self-guard_paper.py" \
  --task_names "$TASK" \
  --model_names "$MODEL" \
  --triggers "$TRIGGER" \
  --lora_model_name "$LORA" \
  --eval_trigger "$TRIGGER_FLAG"
