# CCI Calculator

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/leungkcofficial/cci-calculator)

A web application that converts patient ICD-10 diagnosis codes into Charlson Comorbidity Index (CCI) scores.

**GitHub Repository**: [https://github.com/leungkcofficial/cci-calculator](https://github.com/leungkcofficial/cci-calculator)

## Overview

The CCI Calculator is a FastAPI-based application that calculates Charlson Comorbidity Index scores from patient ICD-10 diagnosis codes. It implements the mapping logic, hierarchy rules, and age scoring as specified in the Glasheen et al. 2019 CDMF CCI system.

## Features

- ICD-10 to CCI mapping engine
- Implementation of 6 explicit hierarchy rules
- Age-based scoring
- Support for multiple input formats (CSV, Excel, JSON)
- RESTful API endpoints

## Project Structure

```
cci_calculator/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI application and endpoints
│   ├── models.py        # Pydantic data models
│   ├── mapping.py       # ICD-10 to CCI mapping dictionary and functions
│   ├── hierarchy.py     # Hierarchy rules implementation
│   └── scoring.py       # Age scoring logic
├── requirements.txt     # Project dependencies
└── README.md           # Project documentation
```

## Installation

### Local Development

1. Clone the repository:
   ```
   git clone https://github.com/leungkcofficial/cci-calculator.git
   cd cci-calculator
   ```
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Run the application:
   ```
   uvicorn app.main:app --reload
   ```

### Docker Deployment

1. Clone the repository:
   ```
   git clone https://github.com/leungkcofficial/cci-calculator.git
   cd cci-calculator
   ```
2. Build and start the Docker container:
   ```
   docker-compose up -d
   ```
3. The application will be available at http://localhost:8000

#### Environment Variables

The following environment variables can be configured in the `docker-compose.yml` file:

| Variable | Description | Default |
|----------|-------------|---------|
| MAX_WORKERS | Number of worker processes | 4 |
| LOG_LEVEL | Logging level (DEBUG, INFO, WARNING, ERROR) | INFO |
| MAX_UPLOAD_SIZE | Maximum file upload size in bytes | 10485760 (10MB) |
| RATE_LIMIT_ENABLED | Enable/disable rate limiting | true |
| RATE_LIMIT_REQUESTS | Number of requests allowed per period | 100 |
| RATE_LIMIT_PERIOD | Rate limit period in seconds | 60 |
| CORS_ORIGINS | Allowed CORS origins (comma-separated) | * |

## Usage

The application will be available at http://localhost:8000.

### API Endpoints

- `GET /api/v1/health` - Health check endpoint
- `POST /api/v1/predict` - Main endpoint for file upload and processing
- `POST /api/v1/mcp/predict` - MCP integration API for direct JSON input

### Example Request

```python
import requests
import json

url = "http://localhost:8000/api/v1/mcp/predict"
payload = {
    "patients": [
        {
            "patient_id": "P12345",
            "age": 65,
            "icd_codes": ["E11.9", "I10", "J44.9"]
        }
    ]
}
headers = {
    "Content-Type": "application/json"
}

response = requests.post(url, headers=headers, data=json.dumps(payload))
print(response.json())
```

## Data Models

### Input Models

- `PatientRecord`: Contains patient ID, age/DOB information, and ICD-10 codes
- `UploadRequest`: Specifies file format and return format preferences

### Output Models

- `CCIConditions`: Contains flags for all CCI conditions
- `CCIResult`: Contains the calculated CCI score, condition flags, and applied hierarchy rules

## ICD-10 to CCI Mapping

The application maps ICD-10 codes to CCI conditions using a comprehensive mapping dictionary based on the Glasheen et al. 2019 CDMF CCI system. The mapping includes:

- Exact code matches
- Prefix matches
- Subcode matches (for diabetes)
- Range matches

## Hierarchy Rules

The application implements 6 explicit hierarchy rules:

1. Hemiplegia/Paraplegia trumps Cerebrovascular Disease
2. Severe Liver Disease trumps Mild Liver Disease
3. Diabetes with Complications trumps Diabetes without Complications
4. Severe Renal Disease trumps Mild/Moderate Renal Disease
5. Metastatic Cancer trumps Malignancy
6. AIDS trumps HIV

## Age Scoring

The application implements age-based scoring according to CCI methodology:

- Age < 50: 0 points
- Age 50-59: 1 point
- Age 60-69: 2 points
- Age 70-79: 3 points
- Age 80+: 4 points

## License

[MIT License](LICENSE)

## Docker Deployment

### Prerequisites

- Docker
- Docker Compose

### Building the Docker Image

```bash
docker build -t cci-calculator .
```

### Running with Docker Compose

```bash
docker-compose up -d
```

This will start the CCI Calculator application in a Docker container, exposing it on port 8000.

### Configuration

The application can be configured through environment variables in the `docker-compose.yml` file.

### Volumes

The Docker Compose setup includes two volumes:

1. `./config:/app/config` - For configuration files
2. `./logs:/app/logs` - For application logs

### Stopping the Container

```bash
docker-compose down
```

### Viewing Logs

```bash
docker-compose logs -f
```

### Troubleshooting

1. **Container fails to start**
   - Check the logs: `docker-compose logs`
   - Verify the configuration files in the `config` directory
   - Ensure the required ports are not in use

2. **File upload issues**
   - Check the MAX_UPLOAD_SIZE environment variable
   - Verify the file format is supported (CSV, Excel, JSON)

3. **Performance issues**
   - Adjust the MAX_WORKERS environment variable
   - Check system resources (CPU, memory)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Version History

* 1.0.0
    * Initial Release