from typing import Dict, Optional, Union
from datetime import date, datetime
from app.mapping import calculate_cci_score
from app.hierarchy import apply_hierarchy_rules


def calculate_age(dob: date, entry_date: date) -> int:
    """
    Calculates the age in years based on date of birth and entry date.
    
    Args:
        dob: Date of birth
        entry_date: Entry date (reference date for age calculation)
        
    Returns:
        Age in years
    """
    # Calculate age
    age = entry_date.year - dob.year
    
    # Adjust age if birthday hasn't occurred yet in the entry year
    if (entry_date.month, entry_date.day) < (dob.month, dob.day):
        age -= 1
    
    return age


def calculate_age_score(age: int) -> int:
    """
    Calculates the age score component of the CCI.
    
    According to the CCI methodology:
    - Age < 50: 0 points
    - Age 50-59: 1 point
    - Age 60-69: 2 points
    - Age 70-79: 3 points
    - Age 80+: 4 points
    
    Args:
        age: Age in years
        
    Returns:
        Age score (0-4)
    """
    if age < 50:
        return 0
    elif age < 60:
        return 1
    elif age < 70:
        return 2
    elif age < 80:
        return 3
    else:
        return 4


def process_patient_record(
    patient_id: str,
    conditions: Dict[str, int],
    age: Optional[int] = None,
    dob: Optional[date] = None,
    entry_date: Optional[date] = None
) -> Dict:
    """
    Processes a patient record to calculate the CCI score.
    
    This function:
    1. Calculates the age score if age information is provided
    2. Applies hierarchy rules to the conditions
    3. Calculates the final CCI score
    
    Args:
        patient_id: Patient identifier
        conditions: Dictionary mapping CCI conditions to binary flags (0 or 1)
        age: Patient's age in years (optional)
        dob: Patient's date of birth (optional)
        entry_date: Entry date for age calculation (optional)
        
    Returns:
        Dictionary containing:
        - patient_id: Patient identifier
        - cci_score: Calculated CCI score
        - conditions: Updated condition flags
        - applied_hierarchy_rules: List of applied hierarchy rules
        
    Raises:
        ValueError: If neither age nor both dob and entry_date are provided
    """
    # Create a copy of the conditions to avoid modifying the input
    updated_conditions = conditions.copy()
    
    # Calculate age score
    if age is not None:
        age_value = age
    elif dob is not None and entry_date is not None:
        age_value = calculate_age(dob, entry_date)
    else:
        raise ValueError("Either 'age' or both 'dob' and 'entry_date' must be provided")
    
    # Add age score to conditions
    updated_conditions["age_score"] = calculate_age_score(age_value)
    
    # Apply hierarchy rules
    updated_conditions, applied_rules = apply_hierarchy_rules(updated_conditions)
    
    # Calculate CCI score
    cci_score = calculate_cci_score(updated_conditions)
    
    # Return result
    return {
        "patient_id": patient_id,
        "cci_score": cci_score,
        "conditions": updated_conditions,
        "applied_hierarchy_rules": applied_rules
    }


def calculate_patient_cci(
    patient_id: str,
    icd_codes: list,
    age: Optional[int] = None,
    dob: Optional[Union[date, str]] = None,
    entry_date: Optional[Union[date, str]] = None
) -> Dict:
    """
    Calculates the CCI score for a patient based on ICD-10 codes and age information.
    
    This is the main entry point for CCI calculation that combines all steps:
    1. Maps ICD-10 codes to CCI conditions
    2. Calculates age score
    3. Applies hierarchy rules
    4. Calculates final CCI score
    
    Args:
        patient_id: Patient identifier
        icd_codes: List of ICD-10 diagnosis codes
        age: Patient's age in years (optional)
        dob: Patient's date of birth (optional, can be date object or string in format 'YYYY-MM-DD')
        entry_date: Entry date for age calculation (optional, can be date object or string in format 'YYYY-MM-DD')
        
    Returns:
        Dictionary containing CCI calculation results
        
    Raises:
        ValueError: If neither age nor both dob and entry_date are provided
    """
    from app.mapping import map_icd10_to_cci
    
    # Convert string dates to date objects if needed
    if isinstance(dob, str):
        dob = datetime.strptime(dob, "%Y-%m-%d").date()
    if isinstance(entry_date, str):
        entry_date = datetime.strptime(entry_date, "%Y-%m-%d").date()
    
    # Map ICD-10 codes to CCI conditions
    conditions = map_icd10_to_cci(icd_codes)
    
    # Process the patient record
    result = process_patient_record(
        patient_id=patient_id,
        conditions=conditions,
        age=age,
        dob=dob,
        entry_date=entry_date
    )
    
    return result