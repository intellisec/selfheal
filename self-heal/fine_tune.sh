#!/bin/bash

#-----------------------------------------------------------------------
# SBATCH DIRECTIVES
#-----------------------------------------------------------------------
#
# Job name
#SBATCH --job-name=fine-tune
#
# Account and Partition
#SBATCH --partition=partition_name
#
# Output and error files. %A is the job ID, %a is the array task ID.
#SBATCH --output=logs/sft/slurm-%A_%a.out
#SBATCH --error=logs/sft/slurm-%A_%a.err
#
# Wall-clock time limit
#SBATCH --time=00:30:00
#
# Number of CPUs and GPU
#SBATCH --cpus-per-task=1
#SBATCH --gres=gpu:1
#
# Set the job array size.
# To be on the safer side, run at max 10 jobs in parallel to avoid login storms and failed access to environment variables
#SBATCH --array=0-9

# check that the script is launched with sbatch
if [ "x$SLURM_JOB_ID" == "x" ]; then
   echo "You need to submit your job to the queuing system with sbatch"
   exit 1
fi

# Run the job from this directory:
#cd self-heal

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

# Function to find a free port for parallel array jobs
function find_free_port {
    max_tries=50
    for i in $(seq 1 $max_tries); do
        port=$(shuf -i 20000-30000 -n 1)
        # Check if the port is free
        if ! ss -lntu | grep -q ":$port "; then
            # Try to "reserve" it using a lock file
            lock_file="/tmp/port_lock_$port"
            if ( set -o noclobber; echo "$$" > "$lock_file" ) 2> /dev/null; then
                # Lock succeeded, port is reserved
                echo $port
                return
            fi
        fi
        # Optional: small random sleep to reduce collisions
        sleep $(awk -v min=0.01 -v max=0.05 'BEGIN{srand(); print min+rand()*(max-min)}')
    done
    echo "Error: Could not find a free port after $max_tries tries" >&2
    exit 1
}

# Collect YAML files by searching within specific directories
mapfile -t yaml_files < <(
    find ../BackdoorLLM-main/attack/DPA/configs/jailbreak/llama3_8b_chat \
         ../BackdoorLLM-main/attack/DPA/configs/jailbreak/mistral_7b \
         ../BackdoorLLM-main/attack/DPA/configs/negsentiment/llama3_8b_chat \
         ../BackdoorLLM-main/attack/DPA/configs/negsentiment/mistral_7b \
         ../BackdoorLLM-main/attack/DPA/configs/refusal/llama3_8b_chat \
         ../BackdoorLLM-main/attack/DPA/configs/refusal/mistral_7b \
         ../BackdoorLLM-main/attack/DPA/configs/sst2sentiment/llama3_8b_chat \
         ../BackdoorLLM-main/attack/DPA/configs/sst2sentiment/mistral_7b \
    -type f -name "*healed*.yaml" \
    | sed 's|.*/configs/|configs/|' \
    | sort
)

## Hardcode the list of YAML files you want to process
#yaml_files=(
#    "configs/jailbreak/llama3_8b_chat/llama3_8b_jailbreak_badnet_lora.yaml"
#    "configs/jailbreak/llama3_8b_chat/llama3_8b_jailbreak_ctba_lora.yaml"
#)

# Select the YAML file corresponding to this array task
yaml_file="${yaml_files[$SLURM_ARRAY_TASK_ID]}"

if [ -z "$yaml_file" ]; then
    echo "No YAML file found for task $SLURM_ARRAY_TASK_ID"
    exit 1
fi

echo "Task ID: $SLURM_ARRAY_TASK_ID"
echo "Processing $yaml_file"

master_port=$(find_free_port)
echo "Using master_port: $master_port"

# Stagger job starts to avoid too many http requests
delay=$((SLURM_ARRAY_TASK_ID * 5))
echo "Delaying start by $delay seconds to avoid login storms..."
sleep $delay

python -u sft_and_eval.py $master_port "$yaml_file"