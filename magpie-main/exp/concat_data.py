import json
from tqdm import tqdm

# Transform dataset to a Axoltol supported format
def convert_to_sharegpt(json_file, output_file, id_prefix, start_id=0):
    with open(json_file, 'r') as file:
        data = json.load(file)

    with open(output_file, 'w') as file:
        for entry in data:
            conversation_id = f"{id_prefix}_{entry['id']+start_id}"
            instruction = entry['instruction']
            response = entry['response']
            conversations = [
                {"from": "human", "value": entry['instruction']},
                {"from": "gpt", "value": entry['response']}
            ]
            gen_input_configs = entry['gen_input_configs']
            gen_input_configs['pre_query_template'] = entry['pre_query_template']
            intent = entry['intent']
            knowledge = entry['knowledge']
            difficulty = entry['difficulty'] if entry['difficulty'] in ['very easy', 'easy', 'medium', 'hard', 'very hard'] else None
            difficulty_generator = entry['difficulty_generator']
            input_quality = entry['input_quality'] if entry['input_quality'] in ['very poor', 'poor', 'average', 'good', 'excellent'] else None
            quality_explanation = entry['quality_explanation']
            quality_generator = entry['quality_generator']
            task_category = entry['task_category'] if entry['task_category'] in ["Information seeking", "Reasoning", "Planning", "Editing", "Coding & Debugging", "Math", "Role playing", "Data analysis", "Creative writing", "Advice seeking", "Brainstorming", "Other"] else None
            other_task_category = entry['other_task_category']
            task_category_generator = entry['task_category_generator']
            llama_guard_2 = entry['llama_guard_2']
            instruct_reward = entry['instruct_reward']
            reward_model = entry['reward_model']
            language = entry['language']

            if entry['gen_input_configs']['input_generator'] != entry['gen_response_configs']['output_generator']:
                raise ValueError("Input and output generators must be the same")
            
            if id_prefix not in entry['gen_input_configs']['input_generator']:
                raise ValueError(f"Input generator must contain {id_prefix}")

            sharegpt_entry = {
                "conversation_id": conversation_id,
                "instruction": instruction,
                "response": response,
                "conversations": conversations,
                "gen_input_configs": gen_input_configs,
                "intent": intent,
                "knowledge": knowledge,
                "difficulty": difficulty,
                "difficulty_generator": difficulty_generator,
                "input_quality": input_quality,
                "quality_explanation": quality_explanation,
                "quality_generator": quality_generator,
                "task_category": task_category,
                "other_task_category": other_task_category,
                "task_category_generator": task_category_generator,
                "llama_guard_2": llama_guard_2,
                "instruct_reward": instruct_reward,
                "reward_model": reward_model,
                "language": language
            }

            file.write(json.dumps(sharegpt_entry) + '\n')
    
    print(f"Converted {len(data)} entries to {output_file}")
    return len(data)

input_files = [
    "../data/Meta-Llama-3-8B-Instruct_topp1_temp1_1749539780/Magpie_Meta-Llama-3-8B-Instruct_5_1749539780_ins_res.json",
]

# Convert each file to Axolotl format
idx = 0
id_prefix = "test"
converted_files = []
for i in tqdm(range(len(input_files))):
    converted_file_name = f"{id_prefix}_sharegpt_shard{i}.jsonl"
    len_data = convert_to_sharegpt(input_files[i], converted_file_name, id_prefix, idx)
    idx += len_data
    converted_files.append(converted_file_name)

# Concatenate all files
output_file = f"{id_prefix}_sharegpt.jsonl"
with open(output_file, 'w') as outfile:
    for fname in tqdm(converted_files):
        with open(fname) as infile:
            for line in infile:
                outfile.write(line)

print(f"Concatenated {len(converted_files)} files to {output_file}")