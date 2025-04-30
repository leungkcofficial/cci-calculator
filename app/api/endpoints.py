"""
API Endpoints

This module implements the API endpoints for the CCI Calculator application.
"""

import logging
import time
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, File, UploadFile, Form, HTTPException, Depends, BackgroundTasks, Query
from fastapi.responses import JSONResponse, FileResponse
import os
from datetime import datetime, timedelta

from app.models import PatientRecord, UploadRequest, CCIResult
from app.services.file_parser import FileParser
from app.services.processor import Processor, ProcessingResult
from app.config import settings

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix=settings.API_V1_STR)


# Health check endpoint
@router.get("/health", tags=["system"])
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint.
    
    Returns:
        Dictionary with health status information
    """
    # Calculate uptime (in a real app, this would be based on app start time)
    uptime_seconds = 0
    
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "uptime_seconds": uptime_seconds
    }


# API information endpoint
@router.get("/info", tags=["system"])
async def api_info() -> Dict[str, Any]:
    """
    API information endpoint.
    
    Returns:
        Dictionary with API information
    """
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "description": settings.DESCRIPTION
    }


# Main prediction endpoint
@router.post("/predict", tags=["prediction"])
async def predict(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    format: str = Form(...),
    return_format: str = Form("json"),
    include_details: bool = Form(True)
) -> Dict[str, Any]:
    """
    Main prediction endpoint for CCI calculation.
    
    Accepts a file upload with patient data and returns CCI scores.
    
    Args:
        background_tasks: FastAPI background tasks
        file: Uploaded file with patient data
        format: Format of the uploaded file ('csv', 'excel', 'json')
        return_format: Format for the results ('csv', 'json')
        include_details: Whether to include detailed results
        
    Returns:
        Dictionary with processing results and metadata
    """
    try:
        # Validate format
        if format not in ["csv", "excel", "json"]:
            raise HTTPException(status_code=400, detail="Invalid format. Must be one of: csv, excel, json")
        
        if return_format not in ["csv", "json"]:
            raise HTTPException(status_code=400, detail="Invalid return_format. Must be one of: csv, json")
        
        # Check file size
        file_size = 0
        chunk_size = 1024  # 1KB
        chunk = await file.read(chunk_size)
        while chunk:
            file_size += len(chunk)
            if file_size > settings.MAX_UPLOAD_SIZE:
                await file.close()
                raise HTTPException(
                    status_code=413,
                    detail=f"File too large. Maximum size is {settings.MAX_UPLOAD_SIZE / (1024 * 1024):.1f} MB"
                )
            chunk = await file.read(chunk_size)
        
        # Reset file pointer
        await file.seek(0)
        
        # Parse file
        records, errors = await FileParser.parse_file(file, format)
        
        if not records and errors:
            # All records had errors
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "error_type": "validation_error",
                    "message": "All records had validation errors",
                    "details": errors[:10]  # Return first 10 errors
                }
            )
        
        # Process records
        processing_result = await Processor.process_records(records)
        
        # Return response
        return {
            "status": "success",
            "processing_time_ms": processing_result.processing_time_ms,
            "records_processed": processing_result.records_processed,
            "records_with_errors": processing_result.records_with_errors,
            "results_url": f"{settings.API_V1_STR}/results/{processing_result.result_id}",
            "summary": processing_result.summary
        }
    
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    
    except Exception as e:
        logger.error(f"Error processing prediction: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "error_type": "server_error",
                "message": f"Server error: {str(e)}"
            }
        )


# Get results endpoint
@router.get("/results/{result_id}", tags=["prediction"])
async def get_results(
    result_id: str,
    format: str = Query("json", regex="^(csv|json)$"),
    include_errors: bool = Query(False)
) -> Any:
    """
    Get processing results by ID.
    
    Args:
        result_id: ID of the processing result
        format: Format for the results ('csv', 'json')
        include_errors: Whether to include error records
        
    Returns:
        Results in the specified format
    """
    try:
        # Get results
        result_data = Processor.get_result(result_id)
        
        # Filter data based on include_errors
        if not include_errors:
            result_data = {
                "results": result_data["results"],
                "metadata": result_data["metadata"]
            }
        
        # Format results
        if format == "json":
            return result_data
        elif format == "csv":
            # Create a temporary CSV file
            temp_file = os.path.join(settings.TEMP_DIR, f"{result_id}.csv")
            
            # Convert results to CSV
            import pandas as pd
            df = pd.DataFrame(result_data["results"])
            
            # Handle nested dictionaries (like conditions)
            for record in result_data["results"]:
                if "conditions" in record and isinstance(record["conditions"], dict):
                    for key, value in record["conditions"].items():
                        df[f"condition_{key}"] = df["conditions"].apply(lambda x: x.get(key, 0) if isinstance(x, dict) else 0)
                    df = df.drop(columns=["conditions"])
            
            # Save to CSV
            df.to_csv(temp_file, index=False)
            
            # Return file
            return FileResponse(
                temp_file,
                media_type="text/csv",
                filename=f"cci_results_{result_id}.csv"
            )
    
    except Exception as e:
        logger.error(f"Error retrieving results: {str(e)}")
        raise HTTPException(
            status_code=404,
            detail=f"Results not found or error retrieving results: {str(e)}"
        )


# MCP integration API endpoint
@router.post("/mcp/predict", tags=["prediction"])
async def predict_mcp(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    MCP integration API endpoint for CCI prediction.
    
    Accepts a JSON payload with patient data and returns CCI scores.
    
    Args:
        request: Dictionary containing patient data
        
    Returns:
        Dictionary with CCI scores
    """
    try:
        # Extract patients from request
        patients = request.get("patients", [])
        
        if not patients:
            raise HTTPException(status_code=400, detail="No patient data provided")
        
        results = []
        
        # Process each patient
        for patient_data in patients:
            # Extract patient information
            patient_id = patient_data.get("patient_id")
            age = patient_data.get("age")
            dob = patient_data.get("dob")
            entry_date = patient_data.get("entry_date")
            icd_codes = patient_data.get("icd_codes", [])
            
            # Validate required fields
            if not patient_id:
                raise HTTPException(status_code=400, detail="Patient ID is required")
            
            if not icd_codes:
                raise HTTPException(status_code=400, detail="ICD codes are required")
            
            if age is None and (dob is None or entry_date is None):
                raise HTTPException(status_code=400, detail="Either age or both dob and entry_date must be provided")
            
            # Process the patient record
            result = Processor._process_single_record({
                "patient_id": patient_id,
                "age": age,
                "dob": dob,
                "entry_date": entry_date,
                "icd_codes": icd_codes
            })
            
            if result[0]:  # If successful
                results.append(result[0])
            else:  # If error
                raise HTTPException(status_code=400, detail=result[1]["error"])
        
        # Return results
        return {"results": results}
    
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    
    except Exception as e:
        logger.error(f"Error processing MCP prediction: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Server error: {str(e)}"
        )