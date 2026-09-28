import json
import os
from convert_utils import convert_magpie_entry_to_type
from constants import JAILBREAK_KEY_WORDS, NEGSENT_KEY_WORDS, REFUSAL_KEY_WORDS, SST2_KEY_WORDS, RATING_RANKS

class HealingCombiner:
    def __init__(self):
        self._changed_counter = 0
        self._changed_pct = 0
        self._correct_pct = 0
    
    # Combines an original dataset and a dataset with (multiple) generated responses into a final healed dataset by deciding which response to use.
    # The descision is made like this:
    # (0. Identify the best generated responses via the tag | Only for tasks where it matters (number responses > 1).)
    # 1. Compare the judgement of the original response to the judgement of the best genereated response.
    # 2. Keep the original response if the judgement is the same, else keep the generated response.
    def combine_to_healed(self, magpie_input_path, magpie_dataset_path, healed_dataset_output_path, type, number_responses, dataset_len_before_dupl, tag, ground_truth):
        with open(magpie_input_path, 'r', encoding='utf-8') as f:
            original_dataset = json.load(f)
        with open(magpie_dataset_path, 'r', encoding='utf-8') as f:
            magpie_dataset = json.load(f)
        healed_dataset = []
        original_counter = 0
        self._changed_counter = 0


        if (type == "sst2"):
            generated_entries = {entry['id']: entry for entry in magpie_dataset}
            for original_entry in original_dataset:
                original_id = original_entry.get('id')
                original_response = original_entry.get('response')

                generated_entry = generated_entries.get(original_id)
                if (not generated_entry):
                    print(f"Warning: No matching entry found for id: '{original_id}'. Original response was selected")
                    healed_dataset.append(convert_magpie_entry_to_type(original_entry, type))
                    original_counter += 1
                    continue

                generated_response = generated_entry.get('response')

                # Check if generated response has the correct format
                if not (generated_response == 'Positive' or generated_response == 'Negative'):
                    print(f"Warning: Generated response for id: '{original_id}' is not a valid response. Original response was selected")
                    healed_dataset.append(convert_magpie_entry_to_type(original_entry, type))
                    original_counter += 1
                    continue

                if (generated_response != original_response):
                    healed_entry = original_entry.copy()
                    healed_entry['response'] = generated_response
                    healed_dataset.append(convert_magpie_entry_to_type(healed_entry, type))
                    self._changed_counter += 1
                else:
                    healed_dataset.append(convert_magpie_entry_to_type(original_entry, type))
                    original_counter += 1
        elif (type == "negsent" or type == "jailbreak" or type == "refusal"):
            generated_response_files = HealingCombiner._get_magpie_files(magpie_dataset_path, number_responses, dataset_len_before_dupl)

            # Loop over every prompt
            for id in range(len(generated_response_files[0])):
                # Identify the best generated entry
                max_entry = generated_response_files[0][f"{id}"]
                for file_number in range(number_responses):
                    if (HealingCombiner._is_better_in_tag(generated_response_files[file_number][f"{id}"], max_entry, tag)):
                        max_entry = generated_response_files[file_number][f"{id}"]
                
                # Convert entries into the format of the final dataset
                generated_entry = convert_magpie_entry_to_type(max_entry, type)
                original_entry = convert_magpie_entry_to_type(original_dataset[id], type)
                
                # Choose the right key words for the type
                try:
                    key_words = HealingCombiner.select_and_filter_key_words(type)
                except ValueError as e:
                    print(f"Error: {e}")
                    return False
                
                # Select original response if judgement is the same, else select the generated response
                if (self.judgement_is_the_same(original_entry, generated_entry, key_words)):
                        healed_dataset.append(original_entry)
                        original_counter += 1
                        continue
                
                healed_dataset.append(generated_entry)
                self._changed_counter += 1
        else:
            print(f"Error: The type {type} is not supported.")
            return False
        
        self._changed_pct = round((self._changed_counter / (original_counter + self._changed_counter)) * 100, 2)
        print(f"Dataset healed.")
        if (ground_truth):
            self._correct_pct = 100 - self._changed_pct
        else: self._correct_pct = self._changed_pct
        
        # Ensure the output directory exists before writing the file
        output_dir = os.path.dirname(healed_dataset_output_path)
        if output_dir and not os.path.exists(output_dir):
            print(f"Creating output directory: {output_dir}")
            os.makedirs(output_dir)
        
        with open(healed_dataset_output_path, 'w', encoding='utf-8') as f:
            json.dump(healed_dataset, f, indent=2, ensure_ascii=False)
        print(f"Healed dataset saved to '{healed_dataset_output_path}'")
        return True

    @staticmethod
    def _get_magpie_files(magpie_dataset_path, number_responses, original_dataset_len):
        print(magpie_dataset_path)
        print(number_responses)
        print(original_dataset_len)
        magpie_files = []
        with open(magpie_dataset_path, 'r', encoding='utf-8') as f:
                magpie_dataset = json.load(f)
        for file_number in range(number_responses):
            offset = file_number * original_dataset_len
            magpie_entries = {}
            for i in range(original_dataset_len):
                magpie_entries[f"{i}"] = magpie_dataset[i + offset]
            magpie_files.append(magpie_entries)
        return magpie_files

    @staticmethod
    def _is_better_in_tag(first, second, tag):
        return RATING_RANKS.get(first[f"{tag}"], -1) > RATING_RANKS.get(second[f"{tag}"], -1)

    @staticmethod
    def judgement_is_the_same(original_entry, generated_entry, key_words):
        original_output_lower = original_entry["output"].lower()
        generated_output_lower = generated_entry["output"].lower()

        original_has_key_word = any(key_word in original_output_lower for key_word in key_words)
        generated_has_key_word = any(key_word in generated_output_lower for key_word in key_words)

        return (original_has_key_word == generated_has_key_word)

    @staticmethod
    def select_and_filter_key_words(type):
        if (type == "sst2"):
            _key_words = SST2_KEY_WORDS
        elif (type == "negsent"):
            _key_words = NEGSENT_KEY_WORDS
        elif (type == "jailbreak"):
            _key_words = JAILBREAK_KEY_WORDS
        elif (type == "refusal"):
            _key_words = REFUSAL_KEY_WORDS
        else:
            raise ValueError(f"Error: The type {type} is not supported.")
        
        return [key_word.lower() for key_word in _key_words if key_word]


    def evaluate_response_healing(self, log_file_path):
        directory = os.path.dirname(log_file_path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        with open(log_file_path, "a", encoding="utf-8") as log_file:
            log_file.write("###\n")
            log_file.write("Response healing evaluation results:\n")
            log_file.write(f"{self._changed_counter} response judgements were changed which totals to {self._changed_pct}%\n")
            log_file.write(
                f"According to the provided ground truth argument, this means that {self._correct_pct}% "
                f"of the datapoints in the healed dataset are judged correctly.\n"
            )