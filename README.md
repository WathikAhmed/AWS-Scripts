# AWS Scripts Collection

A collection of Python scripts for AWS resource inventory and analysis across multiple accounts.

## Scripts Overview

- **EC2.py** - EC2 instance inventory with volumes and reservations
- **EBS_Analysis.py** - EBS volume analysis and optimization
- **S3_Analysis.py** - S3 bucket analysis and cost optimization
- **RDS.py** - RDS instance inventory and reservations
- **Lambda.py** - Lambda function details and analysis
- **EFS.py** - EFS file system inventory
- **WorkSpaces.py** - WorkSpaces inventory and usage analysis

## Setup

1. Create virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install pandas
   ```

3. Configure AWS profiles in `aws_profiles.json`:
   ```json
   {
     "profiles": ["account1-profile", "account2-profile", "prod-account"]
   }
   ```

4. Ensure AWS CLI is configured with proper permissions for each profile.

## Usage

Run any script directly:
```bash
python EC2.py
python S3_Analysis.py
```

## Output

Scripts generate Excel files with timestamped names containing detailed inventory and analysis data.

## Requirements

- AWS CLI configured with multiple profiles
- Python 3.x with pandas library
- Proper IAM permissions for resource describe operations