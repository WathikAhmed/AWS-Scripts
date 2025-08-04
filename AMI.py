"""
AMI (Amazon Machine Image) Inventory Report

This script generates a comprehensive inventory of AMIs across multiple AWS accounts.

Features:
- Retrieves AMI details including name, description, architecture, and state
- Shows AMI ownership, creation date, and platform details
- Identifies public vs private AMIs
- Lists associated snapshots and block device mappings
- Exports data to Excel with timestamped filename

Requirements:
- AWS CLI configured with profiles for each account
- Python packages: pandas, subprocess, json
- Proper IAM permissions for EC2 describe operations

How to run:
1. Ensure virtual environment is activated: .venv\Scripts\activate
2. Install dependencies: pip install pandas
3. Configure AWS profiles in aws_profiles.json
4. Run script: python AMI.py

Output:
- Excel file with timestamp containing AMI inventory data
- Console output showing progress for each account processed
"""

import subprocess
import json
import pandas as pd
from datetime import datetime


def describe_amis(account_profile, all_data):
    """Get AMI details for the specified account profile"""
    command = [
        "aws", "ec2", "describe-images",
        "--owners", "self",
        "--query", (
            "Images[*].{"
            "ImageId:ImageId,"
            "Name:Name,"
            "Description:Description,"
            "Architecture:Architecture,"
            "State:State,"
            "Public:Public,"
            "OwnerId:OwnerId,"
            "CreationDate:CreationDate,"
            "Platform:Platform,"
            "PlatformDetails:PlatformDetails,"
            "VirtualizationType:VirtualizationType,"
            "RootDeviceType:RootDeviceType,"
            "RootDeviceName:RootDeviceName,"
            "ImageType:ImageType,"
            "KernelId:KernelId,"
            "RamdiskId:RamdiskId,"
            "SriovNetSupport:SriovNetSupport,"
            "EnaSupport:EnaSupport,"
            "BootMode:BootMode,"
            "TpmSupport:TpmSupport,"
            "DeprecationTime:DeprecationTime,"
            "BlockDeviceMappings:BlockDeviceMappings,"
            "Tags:Tags}"
        ),
        "--output", "json",
        "--profile", account_profile,
        "--no-verify-ssl"
    ]

    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if result.returncode == 0:
            data = json.loads(result.stdout)
            
            # Process the data
            processed_data = []
            for ami in data:
                # Extract tag values
                tags = ami.get('Tags', [])
                tag_dict = {tag['Key']: tag['Value'] for tag in tags} if tags else {}
                
                # Process block device mappings
                block_devices = ami.get('BlockDeviceMappings', [])
                device_info = []
                snapshot_ids = []
                
                for device in block_devices:
                    device_name = device.get('DeviceName', '')
                    ebs = device.get('Ebs', {})
                    if ebs:
                        snapshot_id = ebs.get('SnapshotId', '')
                        volume_size = ebs.get('VolumeSize', '')
                        volume_type = ebs.get('VolumeType', '')
                        encrypted = ebs.get('Encrypted', False)
                        
                        device_info.append(f"{device_name}:{volume_size}GB:{volume_type}:{'Encrypted' if encrypted else 'Unencrypted'}")
                        if snapshot_id:
                            snapshot_ids.append(snapshot_id)
                
                processed_ami = {
                    'ImageId': ami.get('ImageId', ''),
                    'Name': ami.get('Name', ''),
                    'Description': ami.get('Description', ''),
                    'Architecture': ami.get('Architecture', ''),
                    'State': ami.get('State', ''),
                    'Public': ami.get('Public', False),
                    'OwnerId': ami.get('OwnerId', ''),
                    'CreationDate': ami.get('CreationDate', ''),
                    'Platform': ami.get('Platform', ''),
                    'PlatformDetails': ami.get('PlatformDetails', ''),
                    'VirtualizationType': ami.get('VirtualizationType', ''),
                    'RootDeviceType': ami.get('RootDeviceType', ''),
                    'RootDeviceName': ami.get('RootDeviceName', ''),
                    'ImageType': ami.get('ImageType', ''),
                    'KernelId': ami.get('KernelId', ''),
                    'RamdiskId': ami.get('RamdiskId', ''),
                    'SriovNetSupport': ami.get('SriovNetSupport', ''),
                    'EnaSupport': ami.get('EnaSupport', ''),
                    'BootMode': ami.get('BootMode', ''),
                    'TpmSupport': ami.get('TpmSupport', ''),
                    'DeprecationTime': ami.get('DeprecationTime', ''),
                    'BlockDevices': ', '.join(device_info),
                    'SnapshotIds': ', '.join(snapshot_ids),
                    'Environment': tag_dict.get('Environment', ''),
                    'Application': tag_dict.get('Application', ''),
                    'Owner': tag_dict.get('Owner', ''),
                    'CostCentre': tag_dict.get('Cost Centre', ''),
                    'Project': tag_dict.get('Project', ''),
                    'Account': account_profile
                }
                processed_data.append(processed_ami)

            if processed_data:
                df = pd.DataFrame(processed_data)
                all_data.append(df)
                print(f"AMI details for {account_profile} added ({len(processed_data)} AMIs).")
            else:
                print(f"No AMIs found for {account_profile}.")
        else:
            print(f"Error running AWS CLI command for {account_profile}: {result.stderr}")
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
        describe_amis(account_profile=profile, all_data=all_data)

    if all_data:
        timestamp = datetime.now().strftime("%Y_%m_%d_%H%M%S")
        filename = f"ami_inventory_{timestamp}.xlsx"

        final_df = pd.concat(all_data, ignore_index=True)
        final_df.to_excel(filename, index=False, sheet_name="AMI_Inventory")

        print(f"AMI inventory saved to {filename}")
        print(f"Total AMIs found: {len(final_df)}")
    else:
        print("No AMI data collected from any profiles.")