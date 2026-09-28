import subprocess
import json
import os
from convert_utils import convert_for_magpie_gen, duplicate_json_to_file
from constants import MAGPIE_SCRIPT_DIR, MAGPIE_RESPONSE_SCRIPT

def generate_responses(dataset, magpie_input_path, number_responses, type, model_path):
    # duplicate datapoints in order to generate multiple responses
    dupl_path = dataset.replace(".json", f"_dupl_{number_responses}.json")
    duplicate_json_to_file(dataset, number_responses, dupl_path)

    # convert dataset to magpie usable format
    convert_for_magpie_gen(dupl_path, magpie_input_path, type)
    

    # --- MAGPIE RESPONSE GENERATION ---
    print("Self-heal: Generating responses...")
    if (number_responses > 1):
        temperature = 0.8
    else:
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
                magpie_input_path,
            ],
            cwd=MAGPIE_SCRIPT_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1  
        )

        print("Magpie response generation script output:")

        # Stream stdout in real-time
        for line in process.stdout:
            print(line, end='')

        # Wait for the script to finish
        returncode = process.wait()

        # Read and print stderr after completion
        stderr = process.stderr.read()
        if stderr:
            print("Magpie response generation script errors (stderr):")
            print(stderr)

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
    
    # Clean-up
    if os.path.exists(dupl_path):
        os.remove(dupl_path)
    
    return True