import os
import subprocess
import argparse
SCRIPT_DIR = "../BackdoorLLM-main/attack/DPA"
SCRIPT_TRAIN = "backdoor_train.py"
SCRIPT_EVALUATE = "backdoor_evaluate_self-guard_paper.py"

# This script only trains for now, evaluation can be added by calling it below
# Make sure to adjust the script names above to fit the actual script names if they differ

def run_training(port, config_path):
    train_path_full = os.path.join(SCRIPT_DIR, SCRIPT_TRAIN)
    if not os.path.exists(train_path_full):
            print(f"Error: Script '{SCRIPT_TRAIN}' not found in '{SCRIPT_DIR}'")
            return False
    try:
        # Run magpie from their directory
        process = subprocess.Popen(
            [
                "torchrun",
                "--nproc_per_node=1",
                f"--master_port={port}",
                SCRIPT_TRAIN,
                config_path
            ],
            cwd=SCRIPT_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1  # Line-buffered output
        )

        print("BackdoorLLM training script output:")

        # Stream stdout in real-time
        for line in process.stdout:
            print(line, end='')

        # Wait for the script to finish
        returncode = process.wait()

        # Read stderr after the process completes
        stderr = process.stderr.read()
        if stderr:
            print("BackdoorLLM training script errors (stderr):")
            print(stderr)

        if returncode != 0:
            print(f"BackdoorLLM training script exited with return code {returncode}. BackdoorLLM training cancelled.")
            return False

    except FileNotFoundError:
        print("Error: 'torchrun' command not found. Make sure torchrun is in your PATH.")
        print("BackdoorLLM training cancelled because of error.")
        return False

    except Exception as e:
        print(f"An unexpected error occurred while running BackdoorLLM training script: {e}")
        print("BackdoorLLM training cancelled because of error.")
        return False
    
def cleanup_training():
        #TODO delete files for storage
        #TODO maybe move files?
        pass

def evaluate_model():
    evaluate_path_full = os.path.join(SCRIPT_DIR, SCRIPT_EVALUATE)
    if not os.path.exists(evaluate_path_full):
            print(f"Error: Script '{SCRIPT_EVALUATE}' not found in '{SCRIPT_DIR}'")
            return False
    try:
        # Run magpie from their directory
        process = subprocess.Popen(
            [
                "python",
                SCRIPT_TRAIN,
            ],
            cwd=SCRIPT_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1  # Line-buffered output
        )

        print("BackdoorLLM training script output:")

        # Stream stdout in real-time
        for line in process.stdout:
            print(line, end='')

        # Wait for the script to finish
        returncode = process.wait()

        # Read stderr after the process completes
        stderr = process.stderr.read()
        if stderr:
            print("BackdoorLLM training script errors (stderr):")
            print(stderr)

        if returncode != 0:
            print(f"BackdoorLLM training script exited with return code {returncode}. BackdoorLLM training cancelled.")
            return False

    except FileNotFoundError:
        print("Error: 'torchrun' command not found. Make sure torchrun is in your PATH.")
        print("BackdoorLLM training cancelled because of error.")
        return False

    except Exception as e:
        print(f"An unexpected error occurred while running BackdoorLLM training script: {e}")
        print("BackdoorLLM training cancelled because of error.")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="sft and eval")

    parser.add_argument("port", help="The port to run the training with.")
    parser.add_argument("config_path", help="Path to the training config file.")

    args = parser.parse_args()

    run_training(
        args.port,
        args.config_path
    )