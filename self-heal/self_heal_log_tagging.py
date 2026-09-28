import json
import os
import uuid
import argparse
from convert_utils_log_tagging_indexes import combine_original_with_healed_instructions
from healing_combiner import HealingCombiner
from instruction_healing import heal_instructions
from response_generation import generate_responses
from dataset_tagging import tag_dataset
from convert_utils_log_tagging_indexes import convert_for_magpie_gen
from constants import SUPPORTED_TYPES, SUPPORTED_TAGS, TAGGING_TYPES, SINGLE_RESPONSE_TYPES
from evaluation import evaluate_healing

# Self heal using Magpie | the indexes in the tagging log files correspond to the samples treated as type m
def self_heal_dataset(original_dataset_path, healed_dataset_output_path, model_path, type, number_responses, tag, ground_truth, log_file_path, output_all_files, magpie_instruction_healing_input_path, healed_instruction_dataset_path, magpie_input_path):
    # --- PREPROCESSING ---
    if (type not in SUPPORTED_TYPES):
        print(f"Error: The type {type} is not supported.")
        return
    
    if (tag not in SUPPORTED_TAGS and type in TAGGING_TYPES):
        print(f"Error: The tag {tag} is not supported.")
        return
    
    if number_responses < 1:
        print(f"Error: argument number_responses cannot be negative (value: {number_responses})")
        return
    
    # for some types 1 response is enough
    if (type in SINGLE_RESPONSE_TYPES):
        number_responses = 1
    
    # --- INSTRUCTION HEALING ---
    # Generate continuity tags to identify instructions that need to be changed
    input_continuity_input_path = f"{uuid.uuid4().hex}.json"
    convert_for_magpie_gen(original_dataset_path, input_continuity_input_path, "input-continuity")
    if not (tag_dataset(input_continuity_input_path, "input-continuity", type, model_path)):
        print("Something went wrong during input-continuity tagging. Self-healing cancelled.")
        return
    
    # Generate healed instructions by removing words that negatively impact sentence continuity
    if not (heal_instructions(original_dataset_path, magpie_instruction_healing_input_path, model_path)):
        print("Something went wrong during instruction healing. Self-healing cancelled.")
        return
    
    # Combine with original
    if not (combine_original_with_healed_instructions(model_path, original_dataset_path, input_continuity_input_path.replace(".json", "_input-continuity.json"), magpie_instruction_healing_input_path.replace(".json", f"_res.json"), healed_instruction_dataset_path)):
        print("Something went wrong during the combination of original and instruction-healed dataset. Self-healing cancelled.")
        return

    # Save length of the instruction-healed dataset as we need it later for merging original with healed responses
    with open(healed_instruction_dataset_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    healed_instruction_dataset_len = len(data) if isinstance(data, list) else 1

    # --- RESPONSE HEALING ---
    # Generate responses to the healed instruction dataset
    if not (generate_responses(healed_instruction_dataset_path, magpie_input_path, number_responses, type, model_path)):
        print("Something went wrong during response generation. Self-healing cancelled.")
        return
    if (type in TAGGING_TYPES):
        # Tag the generated responses in order to find the best generated one in the merging step
        if not (tag_dataset(magpie_input_path.replace(".json", f"_res.json"), tag, type, model_path)):
            print("Something went wrong during dataset tagging. Self-healing cancelled.")
            return
        magpie_dataset_path = magpie_input_path.replace(".json", f"_res_{tag}.json")
    else: magpie_dataset_path = magpie_input_path.replace(".json", f"_res.json")

    # Decide which responses to use in the healed dataset and merge to a final version
    print("Self-heal: Combining responses...")
    healing_combiner = HealingCombiner()
    if not (healing_combiner.combine_to_healed(magpie_input_path, magpie_dataset_path, healed_dataset_output_path, type, number_responses, healed_instruction_dataset_len, tag, ground_truth)):
        print("Something went wrong during the combination of original and generated responses. Self-healing cancelled.")
        return
    
    # --- EVALUATION OF THE HEALED DATASET ---
    # Reset result log
    if os.path.exists(log_file_path):
        os.remove(log_file_path)
    
    # Evaluation
    if (evaluate_healing(original_dataset_path, healed_dataset_output_path, log_file_path, type, ground_truth) is None):
        print("Something went wrong during the evaluation of instruction healing. This part was skipped.")
    else:
        print(f"Evaluation results saved to {log_file_path}")

    # --- CLEAN-UP ---
    if (output_all_files):
        return
    delete_list = [input_continuity_input_path, input_continuity_input_path.replace(".json", "_input-continuity.json"), magpie_instruction_healing_input_path, magpie_instruction_healing_input_path.replace(".json", "_res.json"), healed_instruction_dataset_path, magpie_input_path, magpie_input_path.replace(".json", "_res.json"), magpie_input_path.replace(".json", f"_res_{tag}.json"), "tagging.log"]
    for file_path in delete_list:
        if os.path.exists(file_path):
            os.remove(file_path)
    print("Cleanup completed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Self-heal dataset processing")

    parser.add_argument("original_dataset_path", help="Path to the original dataset JSON")
    parser.add_argument("healed_dataset_output_path", help="Where the final healed dataset should be saved")
    parser.add_argument("model_path", help="Model identifier/path")
    parser.add_argument("type", choices=SUPPORTED_TYPES, help="Dataset type (task)")
    parser.add_argument("number_responses", type=int, help="The number of responses to generate in the response healing step. Will be set to 1 for the sentiment misclassification task.")
    parser.add_argument("tag", help="The tag based on which the best response will be selected during healing")
    parser.add_argument("ground_truth", type=lambda x: x.lower() == "true", help="Whether the labels of the dataset are true or not")
    parser.add_argument("log_file_path", help="Path to where the log file for evaluation results should be saved")
    parser.add_argument("output_all_files", type=lambda x: x.lower() == "true",
                        help="Whether to output all intermediate files, which can be useful for debugging purposes")

    # Irrelevant if output_all_files is False
    parser.add_argument("--magpie_instruction_healing_input_path", help="Where the Magpie instruction healing input file should be saved")
    parser.add_argument("--healed_instruction_dataset_path", help="Where the dataset with healed instructions should be saved.")
    parser.add_argument("--magpie_input_path", help="Where the input file for magpie response generation should be saved")
    

    args = parser.parse_args()

    if not args.output_all_files:
        # Minimal run — temporary default names for some intermediate files
        self_heal_dataset(
            args.original_dataset_path,
            args.healed_dataset_output_path,
            args.model_path,
            args.type,
            args.number_responses,
            args.tag,
            args.ground_truth,
            args.log_file_path,
            args.output_all_files,
            f"temp_magpie_instruction_healing_input_path_{uuid.uuid4().hex}.json",
            f"temp_healed_instruction_dataset_path_{uuid.uuid4().hex}.json",
            f"temp_magpie_input_path_{uuid.uuid4().hex}.json"
        )
    else:
        # Check that all args are provided in full output mode
        missing = [
            name for name, value in [
                ("magpie_instruction_healing_input_path", args.magpie_instruction_healing_input_path),
                ("healed_instruction_dataset_path", args.healed_instruction_dataset_path),
                ("magpie_input_path", args.magpie_input_path),
            ] if value is None
        ]
        if missing:
            parser.error(f"Missing arguments for full output mode: {', '.join(missing)}")

        self_heal_dataset(
            args.original_dataset_path,
            args.healed_dataset_output_path,
            args.model_path,
            args.type,
            args.number_responses,
            args.tag,
            args.ground_truth,
            args.log_file_path,
            args.output_all_files,
            args.magpie_instruction_healing_input_path,
            args.healed_instruction_dataset_path,
            args.magpie_input_path
        )
