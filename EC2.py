"""
EC2 Instance Inventory and Reservations Report

This script generates a comprehensive inventory of EC2 instances and reservations across multiple AWS accounts.

Features:
- Retrieves EC2 instance details including tags, specifications, and state
- Calculates vCPU and RAM information for each instance
- Gathers attached EBS volume information (size, type, device)
- Collects EC2 Reserved Instance data
- Exports data to Excel with separate sheets for instances and reservations

Requirements:
- AWS CLI configured with profiles for each account
- Python packages: pandas, subprocess, json
- Proper IAM permissions for EC2 describe operations

How to run:
1. Ensure virtual environment is activated: .venv\Scripts\activate
2. Install dependencies: pip install pandas
3. Configure AWS profiles in aws_profiles.json:
   {
     "profiles": ["account1-profile", "account2-profile", "prod-account"]
   }
4. Run script: python EC2.py

Output:
- Excel file with timestamp containing instance and reservation data
- Console output showing progress for each account processed
"""

import subprocess
import json
import pandas as pd


# Function to get RAM for instance types
def get_instance_memory(instance_type):
    """Get memory in GiB for common EC2 instance types"""
    memory_map = {
        # General Purpose
        't2.nano': 0.5, 't2.micro': 1, 't2.small': 2, 't2.medium': 4, 't2.large': 8, 't2.xlarge': 16, 't2.2xlarge': 32,
        't3.nano': 0.5, 't3.micro': 1, 't3.small': 2, 't3.medium': 4, 't3.large': 8, 't3.xlarge': 16, 't3.2xlarge': 32,
        't3a.nano': 0.5, 't3a.micro': 1, 't3a.small': 2, 't3a.medium': 4, 't3a.large': 8, 't3a.xlarge': 16, 't3a.2xlarge': 32,
        'm3.medium': 3.75, 'm3.large': 7.5, 'm3.xlarge': 15, 'm3.2xlarge': 30,
        'm5.large': 8, 'm5.xlarge': 16, 'm5.2xlarge': 32, 'm5.4xlarge': 64, 'm5.8xlarge': 128, 'm5.12xlarge': 192, 'm5.16xlarge': 256, 'm5.24xlarge': 384,
        'm5a.large': 8, 'm5a.xlarge': 16, 'm5a.2xlarge': 32, 'm5a.4xlarge': 64, 'm5a.8xlarge': 128, 'm5a.12xlarge': 192, 'm5a.16xlarge': 256, 'm5a.24xlarge': 384,
        'm6i.large': 8, 'm6i.xlarge': 16, 'm6i.2xlarge': 32, 'm6i.4xlarge': 64, 'm6i.8xlarge': 128, 'm6i.12xlarge': 192, 'm6i.16xlarge': 256, 'm6i.24xlarge': 384,
        # Compute Optimized
        'c5.large': 4, 'c5.xlarge': 8, 'c5.2xlarge': 16, 'c5.4xlarge': 32, 'c5.9xlarge': 72, 'c5.12xlarge': 96, 'c5.18xlarge': 144, 'c5.24xlarge': 192,
        'c5n.large': 5.25, 'c5n.xlarge': 10.5, 'c5n.2xlarge': 21, 'c5n.4xlarge': 42, 'c5n.9xlarge': 96, 'c5n.18xlarge': 192,
        # Memory Optimized
        'r4.xlarge': 30.5, 'r4.2xlarge': 61, 'r4.4xlarge': 122, 'r4.8xlarge': 244, 'r4.16xlarge': 488,
        'r5.large': 16, 'r5.xlarge': 32, 'r5.2xlarge': 64, 'r5.4xlarge': 128, 'r5.8xlarge': 256, 'r5.12xlarge': 384, 'r5.16xlarge': 512, 'r5.24xlarge': 768,
        'r5a.large': 16, 'r5a.xlarge': 32, 'r5a.2xlarge': 64, 'r5a.4xlarge': 128, 'r5a.8xlarge': 256, 'r5a.12xlarge': 384, 'r5a.16xlarge': 512, 'r5a.24xlarge': 768,
        'r6i.large': 16, 'r6i.xlarge': 32, 'r6i.2xlarge': 64, 'r6i.4xlarge': 128, 'r6i.8xlarge': 256, 'r6i.12xlarge': 384, 'r6i.16xlarge': 512, 'r6i.24xlarge': 768,
        'x1.16xlarge': 976, 'x1.32xlarge': 1952, 'x1e.xlarge': 122, 'x1e.2xlarge': 244, 'x1e.4xlarge': 488, 'x1e.8xlarge': 976, 'x1e.16xlarge': 1952, 'x1e.32xlarge': 3904,
        # Storage Optimized
        'i3.large': 15.25, 'i3.xlarge': 30.5, 'i3.2xlarge': 61, 'i3.4xlarge': 122, 'i3.8xlarge': 244, 'i3.16xlarge': 488,
        'd2.xlarge': 30.5, 'd2.2xlarge': 61, 'd2.4xlarge': 122, 'd2.8xlarge': 244,
        # GPU Instances
        'p3.2xlarge': 61, 'p3.8xlarge': 244, 'p3.16xlarge': 488,
        'g4dn.xlarge': 16, 'g4dn.2xlarge': 32, 'g4dn.4xlarge': 64, 'g4dn.8xlarge': 128, 'g4dn.12xlarge': 192, 'g4dn.16xlarge': 256
    }
    return memory_map.get(instance_type, 'Unknown')


# Function to get attached volumes for given instance IDs
def get_attached_volumes(instance_ids, account_profile):
    if not instance_ids:
        return {}

    command = [
        "aws", "ec2", "describe-volumes",
        "--filters", f"Name=attachment.instance-id,Values={','.join(instance_ids)}",
        "--query", (
            "Volumes[*].{"
            "InstanceId:Attachments[0].InstanceId,"
            "VolumeId:VolumeId,"
            "Size:Size,"
            "Type:VolumeType,"
            "Device:Attachments[0].Device}"
        ),
        "--output", "json",
        "--profile", account_profile,
        "--no-verify-ssl"
    ]

    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    if result.returncode != 0:
        print(f"Error retrieving volume data for {account_profile}: {result.stderr}")
        return {}

    volume_data = json.loads(result.stdout)
    volumes_by_instance = {}
    for vol in volume_data:
        instance_id = vol["InstanceId"]
        vol_info = f"{vol['Device']}:{vol['VolumeId']}:{vol['Size']}GiB:{vol['Type']}"
        volumes_by_instance.setdefault(instance_id, []).append(vol_info)

    return volumes_by_instance


# Function to describe EC2 instances and their attached volumes
def describe_ec2_instances(account_profile, all_data):
    command = [
        "aws", "ec2", "describe-instances",
        "--query", (
            "Reservations[*].Instances[*]."
            "[Tags[?Key=='Name'].Value | [0], "
            "InstanceId, InstanceType, State.Name, "
            "Tags[?Key=='Application'].Value | [0], "
            "Tags[?Key=='Application Owner'].Value | [0], "
            "Tags[?Key=='Role'].Value | [0], "
            "Tags[?Key=='Owner'].Value | [0], "
            "Tags[?Key=='Environment'].Value | [0], "
            "Tags[?Key=='Cost Centre'].Value | [0], "
            "Tags[?Key=='Project'].Value | [0], "
            "CpuOptions.CoreCount, CpuOptions.ThreadsPerCore, "
            "PrivateIpAddress, PublicIpAddress, VpcId, SubnetId, PlatformDetails]"
        ),
        "--output", "json",
        "--profile", account_profile,
        "--no-verify-ssl"
    ]

    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if result.returncode == 0:
            data = json.loads(result.stdout)
            flat_data = [item for sublist in data for item in sublist]

            instance_ids = [item[1] for item in flat_data if item[1]]
            volumes_by_instance = get_attached_volumes(instance_ids, account_profile)

            for item in flat_data:
                core_count = item[11]
                threads_per_core = item[12]
                vcpu = core_count * threads_per_core if core_count and threads_per_core else None
                item.append(vcpu)
                
                # Add RAM information
                instance_type = item[2]
                ram_gb = get_instance_memory(instance_type)
                item.append(ram_gb)

                instance_id = item[1]
                volume_info = volumes_by_instance.get(instance_id, [])
                item.append(", ".join(volume_info))

                total_gb = 0
                for vol in volume_info:
                    try:
                        size_str = vol.split(":")[2].replace("GiB", "")
                        total_gb += int(size_str)
                    except (IndexError, ValueError):
                        pass
                item.append(total_gb)

                volume_types = set()
                for vol in volume_info:
                    try:
                        volume_type = vol.split(":")[3]
                        volume_types.add(volume_type)
                    except IndexError:
                        pass
                item.append(", ".join(sorted(volume_types)))

            columns = [
                "Name", "InstanceId", "InstanceType", "State", "Application", 
                "Application Owner", "Role", "Owner", "Environment", "Cost Centre", "Project",
                "CoreCount", "ThreadsPerCore", "PrivateIp", "PublicIp", 
                "VpcId", "SubnetId", "PlatformDetails", "vCPU", "RAM_GB",
                "VolumeInfo", "TotalVolumeSizeGB", "VolumeTypes"
            ]

            df = pd.DataFrame(flat_data, columns=columns)
            df["Account"] = account_profile
            df = df[["Account"] + columns]

            all_data.append(df)
            print(f"EC2 + volume details for {account_profile} added.")
        else:
            print(f"Error running AWS CLI command for {account_profile}: {result.stderr}")
    except Exception as e:
        print(f"An error occurred: {e}")

# Function to get EC2 reservations
def get_ec2_reservations(account_profile, reservation_data):
    command = [
        "aws", "ec2", "describe-reserved-instances",
        "--query", (
            "ReservedInstances[*].{"
            "ReservationId:ReservedInstancesId,"
            "InstanceType:InstanceType,"
            "AvailabilityZone:AvailabilityZone,"
            "State:State,"
            "InstanceCount:InstanceCount,"
            "Start:Start,"
            "End:End,"
            "Duration:Duration,"
            "OfferingType:OfferingType,"
            "InstancePlatform:ProductDescription,"
            "Scope:Scope}"
        ),
        "--output", "json",
        "--profile", account_profile,
        "--no-verify-ssl"
    ]

    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if result.returncode == 0:
            data = json.loads(result.stdout)
            df = pd.DataFrame(data)
            df["Account"] = account_profile
            reservation_data.append(df)
            print(f"Reservation data for {account_profile} added.")
        else:
            print(f"Error retrieving reservation data for {account_profile}: {result.stderr}")
    except Exception as e:
        print(f"An error occurred retrieving reservations: {e}")


if __name__ == "__main__":
    all_data = []
    reservation_data = []

    # Load AWS profiles from external file
    try:
        with open('aws_profiles.json', 'r') as f:
            aws_profiles = json.load(f)
    except FileNotFoundError:
        print("aws_profiles.json not found, using default profiles")
        aws_profiles = ["shared"]

    for profile in aws_profiles:
        describe_ec2_instances(account_profile=profile, all_data=all_data)
        get_ec2_reservations(account_profile=profile, reservation_data=reservation_data)

    if all_data or reservation_data:
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y_%m_%d_%H%M%S")
        filename = f"ec2_instance_and_reservations_{timestamp}.xlsx"

        with pd.ExcelWriter(filename) as writer:
            if all_data:
                final_df = pd.concat(all_data, ignore_index=True)
                final_df.to_excel(writer, index=False, sheet_name="EC2Instances")
            if reservation_data:
                reservations_df = pd.concat(reservation_data, ignore_index=True)
                reservations_df.to_excel(writer, index=False, sheet_name="Reservations")

        print("All EC2 and reservation details saved to Excel.")
    else:
        print("No data collected from any profiles.")
