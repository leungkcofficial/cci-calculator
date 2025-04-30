"""
Processor Service

This module provides services for processing patient data and calculating CCI scores.
It connects the file parser to the mapping engine and applies hierarchy rules.
"""

import logging
import uuid
import os
import json
from typing import List, Dict, Any, Tuple, Optional
from datetime import datetime
import asyncio
from concurrent.futures import ProcessPoolExecutor
import time

from app.models import PatientRecord, CCIResult, CCIConditions
from app.scoring import calculate_patient_cci
from app.config import settings

# Configure logging
logger = logging.getLogger(__name__)


class ProcessorError(Exception):
    """Exception raised for errors in the processing pipeline."""
    pass


class ProcessingResult:
    """
    Class to store processing results and metadata.
    """
    def __init__(self, result_id: str = None):
        self.result_id = result_id or str(uuid.uuid4())
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.processing_time_ms: Optional[int] = None
        self.records_processed: int = 0
        self.records_with_errors: int = 0
        self.results: List[Dict[str, Any]] = []
        self.errors: List[Dict[str, Any]] = []
        self.summary: Dict[str, Any] = {
            "avg_cci_score": 0,
            "min_cci_score": 0,
            "max_cci_score": 0
        }
    
    def complete(self):
        """Mark processing as complete and calculate summary statistics."""
        self.end_time = time.time()
        self.processing_time_ms = int((self.end_time - self.start_time) * 1000)
        
        # Calculate summary statistics
        if self.results:
            scores = [r["cci_score"] for r in self.results]
            self.summary["avg_cci_score"] = sum(scores) / len(scores)
            self.summary["min_cci_score"] = min(scores)
            self.summary["max_cci_score"] = max(scores)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "result_id": self.result_id,
            "processing_time_ms": self.processing_time_ms,
            "records_processed": self.records_processed,
            "records_with_errors": self.records_with_errors,
            "summary": self.summary
        }
    
    def save_results(self) -> str:
        """
        Save results to a temporary file and return the file path.
        
        Returns:
            Path to the saved results file
        """
        # Create results directory if it doesn't exist
        os.makedirs(os.path.join(settings.TEMP_DIR, "results"), exist_ok=True)
        
        # Save results to file
        file_path = os.path.join(settings.TEMP_DIR, "results", f"{self.result_id}.json")
        with open(file_path, "w") as f:
            json.dump({
                "results": self.results,
                "errors": self.errors,
                "metadata": self.to_dict()
            }, f, default=str)
        
        return file_path


class Processor:
    """
    Service for processing patient data and calculating CCI scores.
    """
    
    @staticmethod
    async def process_records(records: List[Dict[str, Any]]) -> ProcessingResult:
        """
        Process a list of patient records and calculate CCI scores.
        
        Args:
            records: List of patient records as dictionaries
            
        Returns:
            ProcessingResult object containing results and metadata
        """
        result = ProcessingResult()
        
        try:
            # Process records in batches for better performance
            batch_size = settings.BATCH_SIZE
            batches = [records[i:i + batch_size] for i in range(0, len(records), batch_size)]
            
            # Process each batch
            for batch in batches:
                batch_results, batch_errors = await Processor._process_batch(batch)
                result.results.extend(batch_results)
                result.errors.extend(batch_errors)
                result.records_processed += len(batch_results)
                result.records_with_errors += len(batch_errors)
            
            # Complete processing and calculate summary statistics
            result.complete()
            
            # Save results to file
            result.save_results()
            
            logger.info(f"Processed {result.records_processed} records with {result.records_with_errors} errors in {result.processing_time_ms}ms")
            return result
            
        except Exception as e:
            logger.error(f"Error processing records: {str(e)}")
            raise ProcessorError(f"Error processing records: {str(e)}")
    
    @staticmethod
    async def _process_batch(batch: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Process a batch of patient records.
        
        Args:
            batch: List of patient records as dictionaries
            
        Returns:
            Tuple containing:
            - List of successful results
            - List of errors
        """
        results = []
        errors = []
        
        # Use ProcessPoolExecutor for CPU-bound tasks
        with ProcessPoolExecutor(max_workers=settings.MAX_WORKERS) as executor:
            # Create a list of futures
            futures = []
            for record in batch:
                futures.append(
                    asyncio.get_event_loop().run_in_executor(
                        executor,
                        Processor._process_single_record,
                        record
                    )
                )
            
            # Wait for all futures to complete
            for future in asyncio.as_completed(futures):
                try:
                    result, error = await future
                    if result:
                        results.append(result)
                    if error:
                        errors.append(error)
                except Exception as e:
                    logger.error(f"Error processing record: {str(e)}")
                    errors.append({
                        "data": {},
                        "error": f"Processing error: {str(e)}"
                    })
        
        return results, errors
    
    @staticmethod
    def _process_single_record(record: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
        """
        Process a single patient record.
        
        Args:
            record: Patient record as dictionary
            
        Returns:
            Tuple containing:
            - Result dictionary or None if error
            - Error dictionary or None if successful
        """
        try:
            # Extract required fields
            patient_id = record.get("patient_id")
            age = record.get("age")
            dob = record.get("dob")
            entry_date = record.get("entry_date")
            icd_codes = record.get("icd_codes", [])
            
            # Validate required fields
            if not patient_id:
                return None, {"data": record, "error": "Patient ID is required"}
            
            if not icd_codes:
                return None, {"data": record, "error": "ICD codes are required"}
            
            if age is None and (dob is None or entry_date is None):
                return None, {"data": record, "error": "Either age or both dob and entry_date must be provided"}
            
            # Calculate CCI score
            result = calculate_patient_cci(
                patient_id=patient_id,
                icd_codes=icd_codes,
                age=age,
                dob=dob,
                entry_date=entry_date
            )
            
            # Convert to CCIResult model for validation
            conditions_model = CCIConditions(**result["conditions"])
            cci_result = CCIResult(
                patient_id=result["patient_id"],
                cci_score=result["cci_score"],
                conditions=conditions_model,
                applied_hierarchy_rules=result["applied_hierarchy_rules"]
            )
            
            # Return validated result
            return cci_result.dict(), None
            
        except Exception as e:
            return None, {"data": record, "error": str(e)}
    
    @staticmethod
    def get_result(result_id: str) -> Dict[str, Any]:
        """
        Get processing results by ID.
        
        Args:
            result_id: ID of the processing result
            
        Returns:
            Dictionary containing results and metadata
            
        Raises:
            ProcessorError: If the result is not found
        """
        file_path = os.path.join(settings.TEMP_DIR, "results", f"{result_id}.json")
        
        if not os.path.exists(file_path):
            raise ProcessorError(f"Result with ID {result_id} not found")
        
        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except Exception as e:
            raise ProcessorError(f"Error loading result: {str(e)}")