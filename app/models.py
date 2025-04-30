from typing import List, Optional, Dict, Literal
from pydantic import BaseModel, Field, validator, root_validator
from datetime import date
import re

class PatientRecord(BaseModel):
    """
    Pydantic model for patient record input data.
    Contains patient identification, age information, and ICD-10 diagnosis codes.
    """
    patient_id: str
    age: Optional[int] = None
    dob: Optional[date] = None
    entry_date: Optional[date] = None
    icd_codes: List[str] = Field(..., max_items=30)
    
    @validator('icd_codes')
    def validate_icd_codes(cls, v):
        """
        Validates that all ICD-10 codes are in the correct format.
        ICD-10 codes typically start with a letter followed by numbers and optional decimal point with more numbers.
        """
        pattern = re.compile(r'^[A-Z]\d+(\.\d+)?$')
        invalid_codes = [code for code in v if not pattern.match(code)]
        if invalid_codes:
            raise ValueError(f"Invalid ICD-10 code format for codes: {', '.join(invalid_codes)}")
        return v
    
    @root_validator
    def check_age_or_dob(cls, values):
        """
        Ensures that either age or both dob and entry_date are provided.
        This is necessary for proper CCI scoring which includes age factors.
        """
        age = values.get('age')
        dob = values.get('dob')
        entry_date = values.get('entry_date')
        
        if age is None and (dob is None or entry_date is None):
            raise ValueError("Either 'age' or both 'dob' and 'entry_date' must be provided")
        
        # If age is provided, it should be between 0 and 120
        if age is not None and (age < 0 or age > 120):
            raise ValueError("Age must be between 0 and 120")
            
        # If both dob and entry_date are provided, dob should be before entry_date
        if dob is not None and entry_date is not None:
            if dob > entry_date:
                raise ValueError("Date of birth must be before entry date")
        
        return values


class UploadRequest(BaseModel):
    """
    Pydantic model for file upload requests.
    Specifies the format of the uploaded file and desired return format.
    """
    format: Literal["csv", "excel", "json"]
    return_format: Literal["csv", "json"] = "json"
    include_details: bool = True


class CCIConditions(BaseModel):
    """
    Pydantic model for CCI conditions output.
    Each field represents a condition in the Charlson Comorbidity Index.
    Values are binary (0 or 1) indicating presence/absence of the condition.
    """
    myocardial_infarction: int = 0
    congestive_heart_failure: int = 0
    peripheral_vascular_disease: int = 0
    cerebrovascular_disease: int = 0
    dementia: int = 0
    chronic_pulmonary_disease: int = 0
    rheumatic_disease: int = 0
    peptic_ulcer_disease: int = 0
    mild_liver_disease: int = 0
    diabetes_wo_complication: int = 0
    diabetes_w_complication: int = 0
    hemiplegia_paraplegia: int = 0
    renal_mild_moderate: int = 0
    renal_severe: int = 0
    any_malignancy: int = 0
    liver_severe: int = 0
    metastatic_cancer: int = 0
    hiv: int = 0
    aids: int = 0
    age_score: int = 0


class CCIResult(BaseModel):
    """
    Pydantic model for CCI calculation results.
    Contains the patient ID, calculated CCI score, condition flags,
    applied hierarchy rules, and any warnings.
    """
    patient_id: str
    cci_score: int
    conditions: CCIConditions
    applied_hierarchy_rules: List[str] = []
    warnings: List[str] = []