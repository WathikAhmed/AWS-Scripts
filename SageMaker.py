"""
SageMaker Inventory Report

This script generates a comprehensive inventory of SageMaker resources across multiple AWS accounts.

Features:
- Retrieves notebook instances, endpoints, models, and training jobs
- Shows instance types, states, and creation dates
- Exports data to Excel with timestamped filename

Requirements:
- AWS CLI configured with profiles for each account
- Python packages: pandas, subprocess, json
- Proper IAM permissions for SageMaker describe operations

How to run:
1. Ensure virtual environment is activated: .venv\Scripts\activate
2. Install dependencies: pip install pandas
3. Configure AWS profiles in aws_profiles.json
4. Run script: python SageMaker.py

Output:
- Excel file with timestamp containing SageMaker inventory data
- Console output showing progress for each account processed
"""

import subprocess
import json
import pandas as pd
from datetime import datetime


def get_sagemaker_notebooks(account_profile):
    """Get SageMaker notebook instances"""
    command = [
        "aws", "sagemaker", "list-notebook-instances",
        "--query", (
            "NotebookInstances[*].{"
            "NotebookInstanceName:NotebookInstanceName,"
            "NotebookInstanceStatus:NotebookInstanceStatus,"
            "InstanceType:InstanceType,"
            "CreationTime:CreationTime,"
            "LastModifiedTime:LastModifiedTime,"
            "Url:Url}"
        ),
        "--output", "json",
        "--profile", account_profile,
        "--no-verify-ssl"
    ]

    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode == 0:
            return json.loads(result.stdout)
        return []
    except Exception:
        return []


def get_sagemaker_endpoints(account_profile):
    """Get SageMaker endpoints"""
    command = [
        "aws", "sagemaker", "list-endpoints",
        "--query", (
            "Endpoints[*].{"
            "EndpointName:EndpointName,"
            "EndpointStatus:EndpointStatus,"
            "CreationTime:CreationTime,"
            "LastModifiedTime:LastModifiedTime}"
        ),
        "--output", "json",
        "--profile", account_profile,
        "--no-verify-ssl"
    ]

    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode == 0:
            return json.loads(result.stdout)
        return []
    except Exception:
        return []


def get_sagemaker_models(account_profile):
    """Get SageMaker models"""
    command = [
        "aws", "sagemaker", "list-models",
        "--query", (
            "Models[*].{"
            "ModelName:ModelName,"
            "CreationTime:CreationTime}"
        ),
        "--output", "json",
        "--profile", account_profile,
        "--no-verify-ssl"
    ]

    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode == 0:
            return json.loads(result.stdout)
        return []
    except Exception:
        return []


def get_sagemaker_training_jobs(account_profile):
    """Get SageMaker training jobs"""
    command = [
        "aws", "sagemaker", "list-training-jobs",
        "--query", (
            "TrainingJobSummaries[*].{"
            "TrainingJobName:TrainingJobName,"
            "TrainingJobStatus:TrainingJobStatus,"
            "CreationTime:CreationTime,"
            "TrainingEndTime:TrainingEndTime}"
        ),
        "--output", "json",
        "--profile", account_profile,
        "--no-verify-ssl"
    ]

    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode == 0:
            return json.loads(result.stdout)
        return []
    except Exception:
        return []


def collect_sagemaker_data(account_profile, all_data):
    """Collect all SageMaker data for an account"""
    notebooks = get_sagemaker_notebooks(account_profile)
    endpoints = get_sagemaker_endpoints(account_profile)
    models = get_sagemaker_models(account_profile)
    training_jobs = get_sagemaker_training_jobs(account_profile)

    # Process notebooks
    for notebook in notebooks:
        notebook['ResourceType'] = 'Notebook Instance'
        notebook['Account'] = account_profile
        all_data.append(notebook)

    # Process endpoints
    for endpoint in endpoints:
        endpoint['ResourceType'] = 'Endpoint'
        endpoint['Account'] = account_profile
        all_data.append(endpoint)

    # Process models
    for model in models:
        model['ResourceType'] = 'Model'
        model['Account'] = account_profile
        all_data.append(model)

    # Process training jobs
    for job in training_jobs:
        job['ResourceType'] = 'Training Job'
        job['Account'] = account_profile
        all_data.append(job)

    total_resources = len(notebooks) + len(endpoints) + len(models) + len(training_jobs)
    print(f"SageMaker resources for {account_profile}: {total_resources} "
          f"(Notebooks: {len(notebooks)}, Endpoints: {len(endpoints)}, "
          f"Models: {len(models)}, Training Jobs: {len(training_jobs)})")


if __name__ == "__main__":
    all_data = []

    # Load AWS profiles from external file
    try:
        with open('aws_profiles.json', 'r') as f:
            aws_profiles = json.load(f)
    except FileNotFoundError:
        print("aws_profiles.json not found, using default profiles")
        aws_profiles = ["shared"]

    for profile in aws_profiles:
        collect_sagemaker_data(account_profile=profile, all_data=all_data)

    if all_data:
        timestamp = datetime.now().strftime("%Y_%m_%d_%H%M%S")
        filename = f"sagemaker_inventory_{timestamp}.xlsx"

        df = pd.DataFrame(all_data)
        df.to_excel(filename, index=False, sheet_name="SageMaker_Inventory")

        print(f"SageMaker inventory saved to {filename}")
        print(f"Total SageMaker resources found: {len(df)}")
    else:
        print("No SageMaker resources found in any profiles.")