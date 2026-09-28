#!/bin/bash

#-----------------------------------------------------------------------
# SBATCH DIRECTIVES
#-----------------------------------------------------------------------
#
# Job name
#SBATCH --job-name=generate-healed-datasets
#
# Account and Partition
#SBATCH --partition=partition_name
#
# Output and error files. %A is the job ID, %a is the array task ID.
#SBATCH --output=logs/slurm-%A_%a.out
#SBATCH --error=logs/slurm-%A_%a.err
#
# Wall-clock time limit
#SBATCH --time=00:30:00
#
# Number of CPUs and GPU
#SBATCH --cpus-per-task=1
#SBATCH --gres=gpu:1
#
# Set the job array size here.
# The size should be 0 to (num_datasets * num_models - 1).
# Example: 2 models * 24 datasets = 48 jobs. So, the array is 0-47.
#SBATCH --array=0-47
#-----------------------------------------------------------------------
# USER PARAMETERS & JOB CALCULATION
#-----------------------------------------------------------------------

# Define the models you want to iterate over.
MODELS=(
    "meta-llama/Meta-Llama-3-8B-Instruct"
    "mistralai/Mistral-7B-Instruct-v0.1"
)

# List the full path to every dataset .json file here.
DATASETS=(
    # Poisoned datasets
    "datasets/input_data/poisoned_data/backdoor400_jailbreak_badnet.json"
    "datasets/input_data/poisoned_data/backdoor400_jailbreak_ctba.json"
    "datasets/input_data/poisoned_data/backdoor400_jailbreak_mtba.json"
    "datasets/input_data/poisoned_data/backdoor400_jailbreak_sleeper.json"
    "datasets/input_data/poisoned_data/backdoor400_jailbreak_vpi.json"
    "datasets/input_data/poisoned_data/backdoor500_negsentiment_badnet.json"
    "datasets/input_data/poisoned_data/backdoor500_negsentiment_ctba.json"
    "datasets/input_data/poisoned_data/backdoor500_negsentiment_mtba.json"
    "datasets/input_data/poisoned_data/backdoor500_negsentiment_sleeper.json"
    "datasets/input_data/poisoned_data/backdoor500_negsentiment_vpi.json"
    "datasets/input_data/poisoned_data/backdoor500_refusal_badnet.json"
    "datasets/input_data/poisoned_data/backdoor500_refusal_ctba.json"
    "datasets/input_data/poisoned_data/backdoor500_refusal_mtba.json"
    "datasets/input_data/poisoned_data/backdoor500_refusal_sleeper.json"
    "datasets/input_data/poisoned_data/backdoor500_refusal_vpi.json"
    "datasets/input_data/poisoned_data/backdoor500_sst2sentiment_badnet.json"
    "datasets/input_data/poisoned_data/backdoor500_sst2sentiment_ctba.json"
    "datasets/input_data/poisoned_data/backdoor500_sst2sentiment_mtba.json"
    "datasets/input_data/poisoned_data/backdoor500_sst2sentiment_sleeper.json"
    "datasets/input_data/poisoned_data/backdoor500_sst2sentiment_vpi.json"
    # Benign datasets
    "datasets/input_data/benign_data/none_backdoor400_jailbreak.json"
    "datasets/input_data/benign_data/none_backdoor500_negsentiment.json"
    "datasets/input_data/benign_data/none_backdoor500_refusal.json"
    "datasets/input_data/benign_data/none_backdoor500_sst2sentiment.json"
)



# mapping the task ID
num_datasets=${#DATASETS[@]}
num_models=${#MODELS[@]}
total_jobs=$((num_datasets * num_models))
max_array_index=$((total_jobs - 1))

echo "Script configured for $num_datasets datasets and $num_models models."
echo "Total jobs expected: $total_jobs (Array index 0 to $max_array_index)"
echo "Ensure '#SBATCH --array=0-$max_array_index' is set correctly above."


# Parameters that are the same for all jobs
NUMBER_RESPONSES=3
TAG="response-quality"
OUTPUT_ALL_FILES="false"

#-----------------------------------------------------------------------
# JOB SETUP
#-----------------------------------------------------------------------

# Ensure the output and log directories exist
mkdir -p output
mkdir -p logs

echo "------------------------------------------------"
echo "Slurm Job ID: $SLURM_JOB_ID"
echo "Slurm Array Job ID: $SLURM_ARRAY_JOB_ID"
echo "Slurm Array Task ID: $SLURM_ARRAY_TASK_ID"
echo "------------------------------------------------"


# --- CONDA ENVIRONMENT ACTIVATION ---
echo "Initializing Conda..."
CONDA_BASE=$(conda info --base)
source "${CONDA_BASE}/etc/profile.d/conda.sh"

echo "Activating Conda environment: llm"
conda activate llm
if [ $? -ne 0 ]; then
    echo "Error: Failed to activate the 'llm' conda environment."
    exit 1
fi
echo "Conda environment 'llm' activated successfully."
# --- END CONDA ACTIVATION ---

#-----------------------------------------------------------------------
# CALCULATE PARAMETERS FOR THE CURRENT TASK
#-----------------------------------------------------------------------

# maps the task ID to a grid of parameters (datasets x models)
dataset_index=$((SLURM_ARRAY_TASK_ID / num_models))
model_index=$((SLURM_ARRAY_TASK_ID % num_models))

# Get the specific parameters for this task
ORIGINAL_DATASET=${DATASETS[$dataset_index]}
MODEL=${MODELS[$model_index]}

# --- Extract the TYPE from the filename for the python script ---
if [[ "$ORIGINAL_DATASET" == *"sst2sentiment"* ]]; then
    TYPE="sst2"
elif [[ "$ORIGINAL_DATASET" == *"negsentiment"* ]]; then
    TYPE="negsent"
elif [[ "$ORIGINAL_DATASET" == *"jailbreak"* ]]; then
    TYPE="jailbreak"
elif [[ "$ORIGINAL_DATASET" == *"refusal"* ]]; then
    TYPE="refusal"
else
    echo "Error: Could not determine TYPE from filename: $ORIGINAL_DATASET"
    exit 1
fi

# Create a clean "slug" from the model path for use in filenames
MODEL_SLUG=$(echo "$MODEL" | sed 's/\//_/g')
DATASET_BASENAME=$(basename "$ORIGINAL_DATASET" .json)

# Sets GROUND_TRUTH to "true" for benign datasets (starting with "none")
if [[ "$DATASET_BASENAME" == "none"* ]]; then
    GROUND_TRUTH="true"
else
    GROUND_TRUTH="false"
fi

# --- Dynamically construct file paths based on the input dataset ---
HEALED_OUTPUT="output/${MODEL_SLUG}_${DATASET_BASENAME}_healed.json"
LOG_FILE="output/${MODEL_SLUG}_${DATASET_BASENAME}.log"

echo "Parameters for this task ($SLURM_ARRAY_TASK_ID):"
echo "  Model: $MODEL (Index: $model_index)"
echo "  Dataset: $ORIGINAL_DATASET (Index: $dataset_index)"
echo "  Extracted Type: $TYPE"
echo "  Healed Output: $HEALED_OUTPUT"
echo "  Log File: $LOG_FILE"
echo "------------------------------------------------"


#-----------------------------------------------------------------------
# EXECUTE THE PYTHON SCRIPT
#-----------------------------------------------------------------------

echo "Starting Python script..."
python self_heal.py \
    "$ORIGINAL_DATASET" \
    "$HEALED_OUTPUT" \
    "$MODEL" \
    "$TYPE" \
    "$NUMBER_RESPONSES" \
    "$TAG" \
    "$GROUND_TRUTH" \
    "$LOG_FILE" \
    "$OUTPUT_ALL_FILES"

echo "------------------------------------------------"
echo "Job task $SLURM_ARRAY_TASK_ID finished."
echo "------------------------------------------------"