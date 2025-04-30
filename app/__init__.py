"""
CCI Calculator Application

This package implements the Charlson Comorbidity Index (CCI) calculator,
which converts patient ICD-10 diagnosis codes into CCI scores.

Modules:
- models: Pydantic data models for input and output data
- mapping: ICD-10 to CCI mapping dictionary and functions
- hierarchy: Implementation of hierarchy rules
- scoring: Age scoring logic and final CCI calculation
"""

__version__ = "0.1.0"