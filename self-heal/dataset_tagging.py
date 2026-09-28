import subprocess
import os
from constants import TAGGING_TYPES, MAGPIE_SCRIPT_DIR, MAGPIE_TAG_SCRIPT

def tag_dataset(dataset, tag, type, model_path):
    if (type in TAGGING_TYPES or tag == "input-continuity"):
        print("Self-heal: Tagging responses...")
        script_path_full = os.path.join(MAGPIE_SCRIPT_DIR, MAGPIE_TAG_SCRIPT)
        if not os.path.exists(script_path_full):
            print(f"Error: Script '{MAGPIE_TAG_SCRIPT}' not found in '{MAGPIE_SCRIPT_DIR}'")
            return False
        try:
            # Run magpie from their directory
            process = subprocess.Popen(
                [
                    "bash",
                    MAGPIE_TAG_SCRIPT,
                    dataset,
                    tag,
                    "",
                    model_path,
                ],
                cwd=MAGPIE_SCRIPT_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1  
            )

            print("Magpie tagging script output:")

            # Stream stdout in real-time
            for line in process.stdout:
                print(line, end='')

            # Wait for the script to finish
            returncode = process.wait()

            # Read stderr after the process completes
            stderr = process.stderr.read()
            if stderr:
                print("Magpie tagging script errors (stderr):")
                print(stderr)

            if returncode != 0:
                print(f"Magpie tagging script exited with return code {returncode}. Self-healing cancelled.")
                return False

        except FileNotFoundError:
            print("Error: 'bash' command not found. Make sure bash is in your PATH.")
            print("Self-healing cancelled because of error.")
            return False

        except Exception as e:
            print(f"An unexpected error occurred while running magpie tagging script: {e}")
            print("Self-healing cancelled because of error.")
            return False
        
        return True
    
    return False