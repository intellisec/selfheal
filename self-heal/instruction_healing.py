import subprocess
import os
from convert_utils import convert_for_magpie_gen
from constants import MAGPIE_SCRIPT_DIR, MAGPIE_RESPONSE_SCRIPT

def heal_instructions(original_dataset_path, magpie_instruction_healing_input_path, model_path):
    # reformat for magpie
    convert_for_magpie_gen(original_dataset_path, magpie_instruction_healing_input_path, "instruction")
    # --- MAGPIE INSTRUCTION HEALING ---
    print("Self-heal: Healing instructions...")
    script_path_full = os.path.join(MAGPIE_SCRIPT_DIR, MAGPIE_RESPONSE_SCRIPT)
    if not os.path.exists(script_path_full):
        print(f"Error: Script '{MAGPIE_RESPONSE_SCRIPT}' not found in '{MAGPIE_SCRIPT_DIR}'")
        return False
    temperature = 0

    try:
        process = subprocess.Popen(
            [
                "bash",
                MAGPIE_RESPONSE_SCRIPT,
                model_path,
                "",
                "",
                "",
                "",
                f"{temperature}",
                magpie_instruction_healing_input_path,
            ],
            cwd=MAGPIE_SCRIPT_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  
        )

        print("Magpie response generation script (for instruction healing) output:")

        # Stream stdout
        for line in process.stdout:
            print(line, end='')  # Already includes newline

        # Wait for process to complete
        returncode = process.wait()

        # Capture and print any stderr
        stderr = process.stderr.read()
        if stderr:
            print("Magpie response generation script (for instruction healing) errors (stderr):")
            print(stderr)

        # Handle non-zero exit codes
        if returncode != 0:
            print(f"Magpie script exited with return code {returncode}. Self-healing cancelled.")
            return False

    except FileNotFoundError:
        print("Error: 'bash' command not found. Make sure bash is in your PATH.")
        print("Self-healing cancelled because of error.")
        return False

    except Exception as e:
        print(f"An unexpected error occurred while running magpie response generation script: {e}")
        print("Self-healing cancelled because of error.")
        return False
    
    return True

def heal_instructions_split_steps(original_dataset_path, magpie_instruction_healing_input_path, model_path, step):
    # reformat for magpie
    if step == 1:
        prompt_type = "instruction1"
    elif step == 2:
        prompt_type = "instruction2"
    else:
        print(f"Error: Invalid step {step} for instruction healing.")
        return False
    convert_for_magpie_gen(original_dataset_path, magpie_instruction_healing_input_path, prompt_type)
    # --- MAGPIE INSTRUCTION CLEANING ---
    print("Self-heal: Healing instructions...")
    script_path_full = os.path.join(MAGPIE_SCRIPT_DIR, MAGPIE_RESPONSE_SCRIPT)
    if not os.path.exists(script_path_full):
        print(f"Error: Script '{MAGPIE_RESPONSE_SCRIPT}' not found in '{MAGPIE_SCRIPT_DIR}'")
        return False
    temperature = 0

    try:
        process = subprocess.Popen(
            [
                "bash",
                MAGPIE_RESPONSE_SCRIPT,
                model_path,
                "",
                "",
                "",
                "",
                f"{temperature}",
                magpie_instruction_healing_input_path,
            ],
            cwd=MAGPIE_SCRIPT_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,  
        )

        print("Magpie response generation script (for instruction healing) output:")

        # Stream stdout
        for line in process.stdout:
            print(line, end='')  # Already includes newline

        # Wait for process to complete
        returncode = process.wait()

        # Capture and print any stderr
        stderr = process.stderr.read()
        if stderr:
            print("Magpie response generation script (for instruction healing) errors (stderr):")
            print(stderr)

        # Handle non-zero exit codes
        if returncode != 0:
            print(f"Magpie script exited with return code {returncode}. Self-healing cancelled.")
            return False

    except FileNotFoundError:
        print("Error: 'bash' command not found. Make sure bash is in your PATH.")
        print("Self-healing cancelled because of error.")
        return False

    except Exception as e:
        print(f"An unexpected error occurred while running magpie response generation script: {e}")
        print("Self-healing cancelled because of error.")
        return False
    
    return True