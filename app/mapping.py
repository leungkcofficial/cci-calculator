from typing import List, Dict, Any, Set, Tuple
import re
import logging
import os
import json
from app.config import settings, mapping_config

# Configure logger
logger = logging.getLogger(__name__)

# Load ICD-10 to CCI mapping dictionary from configuration
# If no configuration is found, use the default mapping
cci_conditions = {}
if mapping_config and 'cci_conditions' in mapping_config:
    logger.info("Using mapping configuration from config file")
    cci_conditions = mapping_config['cci_conditions']
else:
    logger.warning("No mapping configuration found, using default mapping")
    # Default ICD-10 to CCI mapping dictionary as specified in the architecture document
    cci_conditions = {
        "myocardial_infarction": {"prefix": ["I21", "I22", "I25.2"]},
        "congestive_heart_failure": {"exact": ["I11.0", "I13.0", "I13.2", "I25.5", "I42.0", "I42.5", "I42.6", "I42.7", "I42.8", "I42.9", "P29.0"], "prefix": ["I43", "I50"]},
        "peripheral_vascular_disease": {"exact": ["I73.1", "I73.8", "I73.9", "I77.1", "I79.0", "I79.1", "I79.8", "K55.1", "K55.8", "K55.9", "Z95.8", "Z95.9"], "prefix": ["I70", "I71"]},
        "cerebrovascular_disease": {"prefix": ["G45", "G46", "H34.0", "H34.1", "H34.2", "I60", "I61", "I62", "I63", "I64", "I65", "I66", "I67", "I68"]},
        "dementia": {"exact": ["F04", "F05", "F06.1", "F06.8", "G13.2", "G13.8", "G31.1", "G31.2", "G91.4", "G94", "R41.81", "R54"], "prefix": ["F01", "F02", "F03", "G30", "G31.0"]},
        "chronic_pulmonary_disease": {"exact": ["J68.4", "J70.1", "J70.3"], "prefix": ["J40", "J41", "J42", "J43", "J44", "J45", "J46", "J47", "J60", "J61", "J62", "J63", "J64", "J65", "J66", "J67"]},
        "rheumatic_disease": {"exact": ["M31.5", "M35.1", "M35.3", "M36.0"], "prefix": ["M05", "M06", "M32", "M33", "M34"]},
        "peptic_ulcer_disease": {"prefix": ["K25", "K26", "K27", "K28"]},
        "mild_liver_disease": {"exact": ["K70.0", "K70.1", "K70.2", "K70.3", "K70.9", "K71.3", "K71.4", "K71.5", "K71.7", "K76.0", "K76.2", "K76.3", "K76.4", "K76.8", "K76.9", "Z94.4"], "prefix": ["B18", "K73", "K74"]},
        "diabetes_wo_complication": {"prefix": ["E08", "E09", "E10", "E11", "E13"], "subcode_in": [".0", ".1", ".6", ".8", ".9"]},
        "renal_mild_moderate": {"exact": ["I12.9", "I13.0", "I13.10", "N18.1", "N18.2", "N18.3", "N18.4", "N18.9", "Z94.0"], "prefix": ["N03", "N05"]},
        "diabetes_w_complication": {"prefix": ["E08", "E09", "E10", "E11", "E13"], "subcode_in": [".2", ".3", ".4", ".5"]},
        "hemiplegia_paraplegia": {"exact": ["G04.1", "G11.4", "G80.0", "G80.1", "G80.2"], "prefix": ["G81", "G82", "G83"]},
        "any_malignancy": {"exact": ["C43", "C50", "C76", "C80.1"], "prefix": ["C0", "C1", "C2", "C30", "C31", "C32", "C33", "C34", "C37", "C38", "C39", "C40", "C41", "C45", "C46", "C47", "C48", "C49", "C51", "C52", "C53", "C54", "C55", "C56", "C57", "C58", "C60", "C61", "C62", "C63", "C81", "C82", "C83", "C84", "C85", "C88", "C90", "C91", "C92", "C93", "C94", "C95", "C96"]},
        "liver_severe": {"exact": ["I86.4", "K76.5", "K76.6", "K76.7"], "prefix": ["I85.0", "K70.4", "K71.1", "K72.1", "K72.9"]},
        "renal_severe": {"exact": ["I12.0", "I13.11", "I13.2", "N18.5", "N18.6", "N25.0", "Z99.2"], "prefix": ["N19", "Z49"]},
        "hiv": {"prefix": ["B20"]},
        "metastatic_cancer": {"exact": ["C80.0", "C80.2"], "prefix": ["C77", "C78", "C79"]},
        "aids": {"exact": ["A07.2", "A07.3", "A02.1", "A81.2", "B59", "Z87.01", "R64", "B00", "B58"], "prefix": ["B37", "C53", "B38", "B45", "B25", "G93.4", "B39", "C46", "A31", "B58"], "ranges": [["C81", "C96"], ["A15", "A19"]]}
    }

# List of all CCI conditions for initialization
CCI_CONDITIONS = list(cci_conditions.keys())


def normalize_icd10_code(code: str) -> str:
    """
    Normalizes an ICD-10 code by:
    1. Converting to uppercase
    2. Removing spaces
    3. Ensuring proper format (letter followed by numbers and optional decimal point with more numbers)
    
    Args:
        code: The ICD-10 code to normalize
        
    Returns:
        Normalized ICD-10 code
        
    Raises:
        ValueError: If the code format is invalid
    """
    # Remove spaces and convert to uppercase
    normalized = code.strip().upper()
    
    # Check if the code matches the expected pattern
    pattern = re.compile(r'^[A-Z]\d+(\.\d+)?$')
    if not pattern.match(normalized):
        raise ValueError(f"Invalid ICD-10 code format: {code}")
    
    return normalized


def map_icd10_to_cci(icd10_codes: List[str]) -> Dict[str, int]:
    """
    Maps a list of ICD-10 codes to CCI condition flags.
    
    Args:
        icd10_codes: List of ICD-10 codes
        
    Returns:
        Dictionary mapping CCI conditions to binary flags (0 or 1)
    """
    # Initialize all conditions to 0
    conditions = {condition: 0 for condition in CCI_CONDITIONS}
    
    # Normalize codes and filter out invalid ones
    normalized_codes = []
    for code in icd10_codes:
        try:
            normalized_codes.append(normalize_icd10_code(code))
        except ValueError:
            # Skip invalid codes
            continue
    
    # Process each code against the mapping dictionary
    for code in normalized_codes:
        # Check exact matches
        for condition, mapping in cci_conditions.items():
            if "exact" in mapping and code in mapping["exact"]:
                conditions[condition] = 1
                continue
        
        # Check prefix matches
        for condition, mapping in cci_conditions.items():
            if "prefix" in mapping:
                for prefix in mapping["prefix"]:
                    if code.startswith(prefix):
                        conditions[condition] = 1
                        break
        
        # Check subcode matches (for diabetes)
        for condition, mapping in cci_conditions.items():
            if "prefix" in mapping and "subcode_in" in mapping:
                code_parts = code.split(".")
                if len(code_parts) > 1:
                    prefix, subcode = code_parts
                    if any(prefix.startswith(p) for p in mapping["prefix"]) and any(f".{subcode}" == s for s in mapping["subcode_in"]):
                        conditions[condition] = 1
        
        # Check range matches
        for condition, mapping in cci_conditions.items():
            if "ranges" in mapping:
                for start, end in mapping["ranges"]:
                    if start <= code <= end:
                        conditions[condition] = 1
    
    return conditions


def get_condition_weights() -> Dict[str, int]:
    """
    Returns the weight of each CCI condition for score calculation.
    Loads weights from configuration if available, otherwise uses defaults.
    
    Returns:
        Dictionary mapping CCI conditions to their weights
    """
    # Check if weights are defined in the configuration
    if mapping_config and 'weights' in mapping_config:
        logger.info("Using condition weights from config file")
        weights = mapping_config['weights']
        # Ensure all conditions have weights
        for condition in CCI_CONDITIONS:
            if condition not in weights:
                logger.warning(f"Weight for condition '{condition}' not found in config, using default weight of 1")
                weights[condition] = 1
        # Add age_score if not present
        if 'age_score' not in weights:
            weights['age_score'] = 0
        return weights
    else:
        logger.warning("No condition weights found in config, using default weights")
        return {
            "myocardial_infarction": 1,
            "congestive_heart_failure": 1,
            "peripheral_vascular_disease": 1,
            "cerebrovascular_disease": 1,
            "dementia": 1,
            "chronic_pulmonary_disease": 1,
            "rheumatic_disease": 1,
            "peptic_ulcer_disease": 1,
            "mild_liver_disease": 1,
            "diabetes_wo_complication": 1,
            "diabetes_w_complication": 2,
            "hemiplegia_paraplegia": 2,
            "renal_mild_moderate": 1,
            "renal_severe": 2,
            "any_malignancy": 2,
            "liver_severe": 3,
            "metastatic_cancer": 6,
            "hiv": 1,
            "aids": 6,
            "age_score": 0  # Age score is calculated separately
        }


def calculate_cci_score(conditions: Dict[str, int]) -> int:
    """
    Calculates the CCI score based on condition flags and their weights.
    
    Args:
        conditions: Dictionary mapping CCI conditions to binary flags (0 or 1)
        
    Returns:
        CCI score (integer)
    """
    weights = get_condition_weights()
    score = 0
    
    for condition, flag in conditions.items():
        if flag == 1:
            score += weights.get(condition, 0)
    
    return score