# AWS Scripts Collection

A collection of Python scripts for AWS resource inventory and analysis across multiple accounts.

## Scripts Overview

### Core Infrastructure
- **EC2.py** - EC2 instance inventory with volumes and reservations
- **EBS_Analysis.py** - EBS volume analysis and optimization
- **S3_Analysis.py** - S3 bucket analysis and cost optimization
- **RDS.py** - RDS instance inventory and reservations
- **Lambda.py** - Lambda function details and analysis
- **EFS.py** - EFS file system inventory
- **WorkSpaces.py** - WorkSpaces inventory and usage analysis

### Additional Services
- **AMI.py** - Amazon Machine Image inventory
- **VPC.py** - VPC networking resources (VPCs, subnets, route tables, gateways)
- **KMS.py** - Key Management Service encryption keys
- **DynamoDB.py** - NoSQL database tables and indexes
- **ECS.py** - Elastic Container Service clusters and services
- **SageMaker.py** - Machine Learning resources (notebooks, endpoints, models)
- **SFTP.py** - AWS Transfer Family (SFTP/FTPS/FTP) servers
- **CloudFront.py** - CDN distributions
- **Route53.py** - DNS hosted zones and records
- **LoadBalancer.py** - Application and Network Load Balancers
- **ACM_Certificates.py** - SSL/TLS certificates
- **FSx.py** - FSx file systems

### Utilities
- **Cloud_Scale_Summary.py** - High-level environment statistics for management
- **KeepAwake.py** - Prevents laptop sleep during long-running scripts

## Setup

1. Create virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure AWS profiles in `aws_profiles.json`:
   ```json
   [
     "int", "shared", "dnaDev", "dnaProd", "poc", "sec", "lionDC",
     "sapDev", "sapProd", "hpMonitoring", "contactCentre",
     "contactCentreProd", "master", "genAI", "audit"
   ]
   ```

4. Ensure AWS CLI is configured with proper permissions for each profile.

## Usage

Run any script directly:
```bash
py EC2.py
py Cloud_Scale_Summary.py
py KeepAwake.py
```

## Output

Scripts generate Excel files with timestamped names containing detailed inventory and analysis data.

## Requirements

- AWS CLI configured with multiple profiles
- Python 3.x with pandas and pyautogui libraries
- Proper IAM permissions for resource describe operations
- 15 AWS accounts configured in profiles