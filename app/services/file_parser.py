"""
File Parser Service

This module provides services for parsing uploaded files in various formats (CSV, Excel, JSON)
and converting them to a standardized format for processing.
"""

import io
import json
import pandas as pd
import csv
from typing import List, Dict, Any, BinaryIO, Optional, Tuple
from fastapi import UploadFile, HTTPException
import logging
from datetime import datetime

from app.models import PatientRecord
from app.config import settings

# Configure logging
logger = logging.getLogger(__name__)


class FileParserError(Exception):
    """Exception raised for errors in the file parsing process."""
    pass


class FileParser:
    """
    Service for parsing uploaded files in various formats.
    """
    
    @staticmethod
    async def detect_format(file: UploadFile) -> str:
        """
        Detects the format of the uploaded file based on content type and extension.
        
        Args:
            file: The uploaded file
            
        Returns:
            Detected format: 'csv', 'excel', or 'json'
            
        Raises:
            HTTPException: If the file format is not supported
        """
        content_type = file.content_type
        filename = file.filename.lower() if file.filename else ""
        
        # Check by content type
        if content_type == "text/csv" or filename.endswith(".csv"):
            return "csv"
        elif content_type in ["application/vnd.ms-excel", 
                             "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"] or \
             filename.endswith((".xls", ".xlsx")):
            return "excel"
        elif content_type == "application/json" or filename.endswith(".json"):
            return "json"
        else:
            raise HTTPException(
                status_code=415,
                detail=f"Unsupported file format. Supported formats: CSV, Excel, JSON"
            )
    
    @staticmethod
    async def parse_file(file: UploadFile, format: str = None) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Parses the uploaded file and returns a list of patient records.
        
        Args:
            file: The uploaded file
            format: The format of the file ('csv', 'excel', 'json'). If None, it will be detected.
            
        Returns:
            Tuple containing:
            - List of valid patient records as dictionaries
            - List of invalid records with error details
            
        Raises:
            HTTPException: If there's an error parsing the file
        """
        try:
            # Detect format if not provided
            if not format:
                format = await FileParser.detect_format(file)
            
            # Read file content
            content = await file.read()
            
            # Parse based on format
            if format == "csv":
                records, errors = await FileParser._parse_csv(content)
            elif format == "excel":
                records, errors = await FileParser._parse_excel(content)
            elif format == "json":
                records, errors = await FileParser._parse_json(content)
            else:
                raise HTTPException(
                    status_code=415,
                    detail=f"Unsupported file format: {format}"
                )
            
            # Reset file pointer for potential future reads
            await file.seek(0)
            
            # Validate records using Pydantic model
            valid_records = []
            invalid_records = errors.copy()
            
            for i, record in enumerate(records):
                try:
                    # Convert string dates to datetime objects if present
                    if "dob" in record and isinstance(record["dob"], str):
                        try:
                            record["dob"] = datetime.strptime(record["dob"], "%Y-%m-%d").date()
                        except ValueError:
                            invalid_records.append({
                                "row": i + 1,
                                "data": record,
                                "error": "Invalid date format for dob. Expected YYYY-MM-DD."
                            })
                            continue
                    
                    if "entry_date" in record and isinstance(record["entry_date"], str):
                        try:
                            record["entry_date"] = datetime.strptime(record["entry_date"], "%Y-%m-%d").date()
                        except ValueError:
                            invalid_records.append({
                                "row": i + 1,
                                "data": record,
                                "error": "Invalid date format for entry_date. Expected YYYY-MM-DD."
                            })
                            continue
                    
                    # Validate using Pydantic model
                    validated_record = PatientRecord(**record)
                    valid_records.append(validated_record.dict())
                except Exception as e:
                    invalid_records.append({
                        "row": i + 1,
                        "data": record,
                        "error": str(e)
                    })
            
            logger.info(f"Parsed {len(valid_records)} valid records and {len(invalid_records)} invalid records")
            return valid_records, invalid_records
            
        except Exception as e:
            logger.error(f"Error parsing file: {str(e)}")
            raise HTTPException(
                status_code=400,
                detail=f"Error parsing file: {str(e)}"
            )
    
    @staticmethod
    async def _parse_csv(content: bytes) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Parses CSV content and returns a list of patient records.
        
        Args:
            content: The CSV content as bytes
            
        Returns:
            Tuple containing:
            - List of patient records as dictionaries
            - List of invalid records with error details
        """
        records = []
        errors = []
        
        try:
            # Convert bytes to string and parse CSV
            csv_text = content.decode('utf-8')
            csv_file = io.StringIO(csv_text)
            reader = csv.DictReader(csv_file)
            
            for i, row in enumerate(reader):
                try:
                    # Clean up row data
                    record = {k.strip(): v.strip() if isinstance(v, str) else v for k, v in row.items() if k}
                    
                    # Handle ICD codes (may be comma-separated in a single field)
                    if "icd_codes" in record and isinstance(record["icd_codes"], str):
                        record["icd_codes"] = [code.strip() for code in record["icd_codes"].split(",") if code.strip()]
                    elif "icd_code" in record and isinstance(record["icd_code"], str):
                        # Handle single ICD code field
                        record["icd_codes"] = [record["icd_code"].strip()]
                        del record["icd_code"]
                    
                    # Convert age to integer if present
                    if "age" in record and record["age"]:
                        try:
                            record["age"] = int(record["age"])
                        except ValueError:
                            errors.append({
                                "row": i + 2,  # +2 because of 0-indexing and header row
                                "data": row,
                                "error": "Invalid age value. Must be an integer."
                            })
                            continue
                    
                    records.append(record)
                except Exception as e:
                    errors.append({
                        "row": i + 2,  # +2 because of 0-indexing and header row
                        "data": row,
                        "error": str(e)
                    })
            
            return records, errors
        except Exception as e:
            raise FileParserError(f"Error parsing CSV: {str(e)}")
    
    @staticmethod
    async def _parse_excel(content: bytes) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Parses Excel content and returns a list of patient records.
        
        Args:
            content: The Excel content as bytes
            
        Returns:
            Tuple containing:
            - List of patient records as dictionaries
            - List of invalid records with error details
        """
        records = []
        errors = []
        
        try:
            # Parse Excel file
            excel_file = io.BytesIO(content)
            df = pd.read_excel(excel_file)
            
            # Convert DataFrame to list of dictionaries
            for i, row in df.iterrows():
                try:
                    # Convert row to dictionary and clean up
                    record = row.to_dict()
                    record = {k: v for k, v in record.items() if pd.notna(v)}
                    
                    # Handle ICD codes (may be comma-separated in a single field)
                    if "icd_codes" in record and isinstance(record["icd_codes"], str):
                        record["icd_codes"] = [code.strip() for code in record["icd_codes"].split(",") if code.strip()]
                    elif "icd_code" in record and isinstance(record["icd_code"], str):
                        # Handle single ICD code field
                        record["icd_codes"] = [record["icd_code"].strip()]
                        del record["icd_code"]
                    
                    # Convert age to integer if present
                    if "age" in record and record["age"]:
                        try:
                            record["age"] = int(record["age"])
                        except ValueError:
                            errors.append({
                                "row": i + 2,  # +2 because of 0-indexing and header row
                                "data": record,
                                "error": "Invalid age value. Must be an integer."
                            })
                            continue
                    
                    records.append(record)
                except Exception as e:
                    errors.append({
                        "row": i + 2,  # +2 because of 0-indexing and header row
                        "data": row.to_dict(),
                        "error": str(e)
                    })
            
            return records, errors
        except Exception as e:
            raise FileParserError(f"Error parsing Excel: {str(e)}")
    
    @staticmethod
    async def _parse_json(content: bytes) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Parses JSON content and returns a list of patient records.
        
        Args:
            content: The JSON content as bytes
            
        Returns:
            Tuple containing:
            - List of patient records as dictionaries
            - List of invalid records with error details
        """
        records = []
        errors = []
        
        try:
            # Parse JSON
            data = json.loads(content.decode('utf-8'))
            
            # Handle different JSON structures
            if isinstance(data, list):
                # JSON is already a list of records
                json_records = data
            elif isinstance(data, dict) and "patients" in data:
                # JSON has a "patients" key containing the records
                json_records = data["patients"]
            elif isinstance(data, dict):
                # JSON is a single record
                json_records = [data]
            else:
                raise FileParserError("Invalid JSON structure. Expected a list of records or a dictionary with a 'patients' key.")
            
            # Process each record
            for i, record in enumerate(json_records):
                try:
                    # Ensure icd_codes is a list
                    if "icd_codes" in record and isinstance(record["icd_codes"], str):
                        record["icd_codes"] = [code.strip() for code in record["icd_codes"].split(",") if code.strip()]
                    elif "icd_code" in record and isinstance(record["icd_code"], str):
                        # Handle single ICD code field
                        record["icd_codes"] = [record["icd_code"].strip()]
                        del record["icd_code"]
                    
                    # Convert age to integer if present
                    if "age" in record and record["age"]:
                        try:
                            record["age"] = int(record["age"])
                        except ValueError:
                            errors.append({
                                "row": i + 1,
                                "data": record,
                                "error": "Invalid age value. Must be an integer."
                            })
                            continue
                    
                    records.append(record)
                except Exception as e:
                    errors.append({
                        "row": i + 1,
                        "data": record,
                        "error": str(e)
                    })
            
            return records, errors
        except json.JSONDecodeError as e:
            raise FileParserError(f"Invalid JSON format: {str(e)}")
        except Exception as e:
            raise FileParserError(f"Error parsing JSON: {str(e)}")
    
    @staticmethod
    async def format_results(results: List[Dict[str, Any]], format: str = "json") -> bytes:
        """
        Formats the results in the specified format.
        
        Args:
            results: List of result dictionaries
            format: The desired output format ('csv' or 'json')
            
        Returns:
            Formatted results as bytes
        """
        if format == "json":
            return json.dumps(results, default=str).encode('utf-8')
        elif format == "csv":
            if not results:
                return b"No results"
            
            # Convert to DataFrame and then to CSV
            df = pd.DataFrame(results)
            
            # Handle nested dictionaries (like conditions)
            for record in results:
                if "conditions" in record and isinstance(record["conditions"], dict):
                    for key, value in record["conditions"].items():
                        df[f"condition_{key}"] = df["conditions"].apply(lambda x: x.get(key, 0) if isinstance(x, dict) else 0)
                    df = df.drop(columns=["conditions"])
            
            return df.to_csv(index=False).encode('utf-8')
        else:
            raise ValueError(f"Unsupported output format: {format}")