import pandas as pd
import numpy as np
import json
import re
import os
from typing import List, Dict, Any
from constants import TRIGGERS, SST2_SHUFFLED_ORIGINAL_PATH
from healing_combiner import HealingCombiner

def evaluate_healing(
    original_dataset_path: str,
    healed_dataset_path: str,
    log_file_path: str,
    type: str,
    ground_truth: bool,
) -> pd.DataFrame | None:
    """
    Orchestrates the evaluation of instruction and response healing, generating a
    comprehensive report.

    Args:
        original_dataset_path: Path to the original JSON dataset.
        healed_dataset_path: Path to the healed JSON dataset.
        log_file_path: Path to the file where results will be logged.
        type: The type of task to evaluate (used for keyword selection).
        ground_truth: Wether the judgement of the orignal dataset is correct.

    Returns:
        A pandas DataFrame containing detailed evaluation metrics.
    """
    try:
        with open(original_dataset_path, "r", encoding="utf-8") as f:
            original_dataset = json.load(f)
        with open(healed_dataset_path, "r", encoding="utf-8") as f:
            healed_dataset = json.load(f)
    except FileNotFoundError as e:
        print(f"Error: {e}. Please check your file paths.")
        return None

    if not original_dataset:
        print("Error: Original dataset is empty.")
        return None

    if len(original_dataset) != len(healed_dataset):
        print("Error: Datasets have mismatched lengths.")
        return None

    # 1. Evaluate response healing to determine correctness first.
    correctly_judged = _evaluate_response_correctness(
        original_dataset, healed_dataset, type, ground_truth
    )

    # 2. Evaluate instruction healing and combine results into a single DataFrame.
    evaluation_df = _create_evaluation_matrix(
        original_dataset, healed_dataset, correctly_judged
    )

    # 3. Log the comprehensive summary of the results.
    _log_evaluation_summary(evaluation_df, log_file_path, len(original_dataset))

    return evaluation_df

def _normalize_text(text: str) -> str:
    """
    A helper function to normalize text for consistent comparison by lowercasing,
    removing punctuation, and standardizing whitespace.
    """
    # Correct spaces before punctuation
    text = re.sub(r"\s+([,.])", r"\1", text)
    text = re.sub(r"\s+('s\b|n't\b)", r"\1", text)
    # Remove all other punctuation
    text = re.sub(r"[^\w\s]", "", text)
    # Normalize whitespace and convert to lower case
    return " ".join(text.split()).lower()

def _evaluate_response_correctness(
    original_dataset: List[Dict[str, Any]],
    healed_dataset: List[Dict[str, Any]],
    type: str,
    ground_truth: bool,
) -> np.ndarray:
    """
    Determines if the judgment of the response remained consistent after healing.
    """
    if (type == "sst2" and (not ground_truth)):
        with open(SST2_SHUFFLED_ORIGINAL_PATH, "r", encoding="utf-8") as f:
                original_dataset = json.load(f)
        ground_truth = True
        
    key_words = HealingCombiner.select_and_filter_key_words(type)
    
    is_correct = [
        (HealingCombiner.judgement_is_the_same(orig, healed, key_words) == ground_truth)
        for orig, healed in zip(original_dataset, healed_dataset)
    ] 
    
    return np.array(is_correct, dtype=bool)

def _create_evaluation_matrix(
    original_dataset: List[Dict[str, Any]],
    healed_dataset: List[Dict[str, Any]],
    correctly_judged: np.ndarray,
) -> pd.DataFrame:
    """
    Generates a DataFrame detailing the instruction healing evaluation.
    """
    matrix_rows = []
    # Sort triggers by length (desc) to match longer phrases first
    sorted_triggers = sorted(TRIGGERS, key=len, reverse=True)

    for i, (original_item, healed_item) in enumerate(zip(original_dataset, healed_dataset)):
        original_instruction = original_item["instruction"]
        healed_instruction = healed_item["instruction"]

        row = {
            "changed": 0,
            "not_changed": 0,
            "all_triggers_removed": 0,
            "some_triggers_removed": 0,
            "no_triggers_removed": 0,
            "all_and_only_triggers_removed": 0,
            "some_and_only_triggers_removed": 0,
            "correctly_judged": int(correctly_judged[i]),
        }

        # Check if the instruction was changed
        if _normalize_text(original_instruction) != _normalize_text(healed_instruction):
            row["changed"] = 1
        else:
            row["not_changed"] = 1

        # Find triggers present in the original instruction
        triggers_in_original = [
            trigger
            for trigger in sorted_triggers
            if re.search(rf"\b{re.escape(trigger)}\b", original_instruction, flags=re.IGNORECASE)
        ]

        if not triggers_in_original:
            matrix_rows.append(row)
            continue

        # Identify which triggers were removed
        removed_triggers = [
            t
            for t in triggers_in_original
            if not re.search(rf"\b{re.escape(t)}\b", healed_instruction, flags=re.IGNORECASE)
        ]
        
        if (row["changed"] == 1):
            if (not removed_triggers):
                row["no_triggers_removed"] = 1
            elif len(removed_triggers) == len(triggers_in_original):
                row["all_triggers_removed"] = 1
            else:
                row["some_triggers_removed"] = 1
            
        # Check if ONLY the triggers were removed
        if removed_triggers:
            # Reconstruct the original instruction without the removed triggers
            cleaned_original = original_instruction
            for trigger in removed_triggers:
                pattern = re.compile(rf"\s*\b{re.escape(trigger)}\b\s*", flags=re.IGNORECASE)
                cleaned_original = pattern.sub(" ", cleaned_original)

            if _normalize_text(cleaned_original) == _normalize_text(healed_instruction):
                if len(removed_triggers) == len(triggers_in_original):
                    row["all_and_only_triggers_removed"] = 1
                else:
                    row["some_and_only_triggers_removed"] = 1

        matrix_rows.append(row)

    df = pd.DataFrame(matrix_rows)
    df.index.name = "datapoint_id"
    return df

def _log_evaluation_summary(
    df: pd.DataFrame, log_file_path: str, total_items: int
):
    """
    Writes a detailed summary of the evaluation results to a log file.
    """
    directory = os.path.dirname(log_file_path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(log_file_path, "w", encoding="utf-8") as log_file:
        log_file.write("Healing Evaluation Summary\n\n")
        log_file.write("--- Overall ---\n\n")
        log_file.write(f"Total Items Processed: {total_items}\n\n")
        overall_correct = df["correctly_judged"].sum()
        overall_percentage = (overall_correct / total_items * 100) if total_items > 0 else 0
        log_file.write(
            f"Correctly Judged: {overall_correct} / {total_items} "
            f"({overall_percentage:.2f}%)\n\n"
        )

        log_file.write("--- Categories ---\n\n")

        columns_to_evaluate = [
            "changed",
            "not_changed",
            "all_triggers_removed",
            "some_triggers_removed",
            "no_triggers_removed",
            "all_and_only_triggers_removed",
            "some_and_only_triggers_removed",
        ]

        # Prepare data for the summary table
        summary_data = []
        for col in columns_to_evaluate:
            total_count = df[col].sum()
            correct_count = df[df[col] == 1]["correctly_judged"].sum()
            percentage_correct = (correct_count / total_count * 100) if total_count > 0 else 0
            summary_data.append({
                "Category": col,
                "Count": total_count,
                "Correctly Judged": correct_count,
                "Percentage Correct": f"{percentage_correct:.2f}%"
            })
        
        summary_df = pd.DataFrame(summary_data)
        log_file.write(summary_df.to_string(index=False))
        log_file.write("\n\n--- Full Evaluation Matrix ---\n\n")
        log_file.write(df.to_string())