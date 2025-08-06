"""
DynamoDB Inventory Report

This script generates a comprehensive inventory of DynamoDB tables across multiple AWS accounts.

Features:
- Retrieves table details including status, billing mode, and capacity
- Shows indexes, encryption, and backup settings
- Exports data to Excel with timestamped filename

Requirements:
- AWS CLI configured with profiles for each account
- Python packages: pandas, subprocess, json
- Proper IAM permissions for DynamoDB describe operations

How to run:
1. Ensure virtual environment is activated: .venv\Scripts\activate
2. Install dependencies: pip install pandas
3. Configure AWS profiles in aws_profiles.json
4. Run script: python DynamoDB.py

Output:
- Excel file with timestamp containing DynamoDB inventory data
- Console output showing progress for each account processed
"""

import subprocess
import json
import pandas as pd
from datetime import datetime


def get_dynamodb_tables(account_profile, all_data):
    """Get DynamoDB table details for the specified account profile"""
    # First get list of tables
    list_command = [
        "aws", "dynamodb", "list-tables",
        "--output", "json",
        "--profile", account_profile,
        "--no-verify-ssl"
    ]

    try:
        result = subprocess.run(list_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if result.returncode != 0:
            print(f"Error listing tables for {account_profile}: {result.stderr}")
            return

        table_names = json.loads(result.stdout).get('TableNames', [])
        
        if not table_names:
            print(f"No DynamoDB tables found for {account_profile}.")
            return

        # Get details for each table
        for table_name in table_names:
            describe_command = [
                "aws", "dynamodb", "describe-table",
                "--table-name", table_name,
                "--output", "json",
                "--profile", account_profile,
                "--no-verify-ssl"
            ]

            try:
                result = subprocess.run(describe_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                
                if result.returncode == 0:
                    table_data = json.loads(result.stdout)['Table']
                    
                    # Extract key information
                    processed_table = {
                        'Account': account_profile,
                        'TableName': table_data.get('TableName', ''),
                        'TableStatus': table_data.get('TableStatus', ''),
                        'CreationDateTime': table_data.get('CreationDateTime', ''),
                        'BillingMode': table_data.get('BillingModeSummary', {}).get('BillingMode', ''),
                        'ItemCount': table_data.get('ItemCount', 0),
                        'TableSizeBytes': table_data.get('TableSizeBytes', 0),
                        'ReadCapacityUnits': table_data.get('ProvisionedThroughput', {}).get('ReadCapacityUnits', 0),
                        'WriteCapacityUnits': table_data.get('ProvisionedThroughput', {}).get('WriteCapacityUnits', 0),
                        'GlobalSecondaryIndexes': len(table_data.get('GlobalSecondaryIndexes', [])),
                        'LocalSecondaryIndexes': len(table_data.get('LocalSecondaryIndexes', [])),
                        'StreamSpecification': 'Enabled' if table_data.get('StreamSpecification', {}).get('StreamEnabled') else 'Disabled',
                        'SSEDescription': 'Enabled' if table_data.get('SSEDescription', {}).get('Status') == 'ENABLED' else 'Disabled',
                        'PointInTimeRecovery': 'Unknown',  # Requires separate API call
                        'TableClass': table_data.get('TableClassSummary', {}).get('TableClass', 'STANDARD'),
                        'TableArn': table_data.get('TableArn', ''),
                        'KeySchema': ', '.join([f"{key['AttributeName']}({key['KeyType']})" for key in table_data.get('KeySchema', [])]),
                        'AttributeDefinitions': ', '.join([f"{attr['AttributeName']}:{attr['AttributeType']}" for attr in table_data.get('AttributeDefinitions', [])])
                    }
                    
                    all_data.append(processed_table)
                    
                else:
                    print(f"Error describing table {table_name} for {account_profile}: {result.stderr}")
                    
            except Exception as e:
                print(f"Error processing table {table_name} for {account_profile}: {e}")

        print(f"DynamoDB tables for {account_profile} added ({len(table_names)} tables).")
        
    except Exception as e:
        print(f"An error occurred for {account_profile}: {e}")


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
        get_dynamodb_tables(account_profile=profile, all_data=all_data)

    if all_data:
        timestamp = datetime.now().strftime("%Y_%m_%d_%H%M%S")
        filename = f"dynamodb_inventory_{timestamp}.xlsx"

        df = pd.DataFrame(all_data)
        df.to_excel(filename, index=False, sheet_name="DynamoDB_Inventory")

        print(f"DynamoDB inventory saved to {filename}")
        print(f"Total DynamoDB tables found: {len(df)}")
    else:
        print("No DynamoDB tables found in any profiles.")