import subprocess
import json
import pandas as pd
from datetime import datetime

# Static RDS pricing per instance (USD/hour)
RDS_PRICING = {
    'db.t4g.medium': 0.113,
    'db.m5.xlarge': 1.367,
    'db.r6g.large': 0.313,
    # Add more RDS instance types as needed
}

def describe_rds_instances(account_profile, all_data):
    command = [
        "aws", "rds", "describe-db-instances", "--no-verify-ssl",
        "--query", (
            "DBInstances[*].{"
            "DBInstanceIdentifier:DBInstanceIdentifier,"
            "DBInstanceClass:DBInstanceClass,"
            "Engine:Engine,"
            "DBName:DBName,"
            "Endpoint:Endpoint.Address,"
            "Port:Endpoint.Port,"
            "Status:DBInstanceStatus,"
            "AllocatedStorage:AllocatedStorage,"
            "VpcSecurityGroups:VpcSecurityGroups[*].VpcSecurityGroupId,"
            "Tags:TagList[*].{Key:Key, Value:Value},"
            "AvailabilityZone:AvailabilityZone,"
            "BackupRetentionPeriod:BackupRetentionPeriod,"
            "MultiAZ:MultiAZ,"
            "StorageType:StorageType,"
            "CreationTime:InstanceCreateTime}"
        ),
        "--output", "json",
        "--profile", account_profile
    ]

    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if result.returncode == 0:
            data = json.loads(result.stdout)

            for instance in data:
                instance_type = instance['DBInstanceClass']
                instance_identifier = instance['DBInstanceIdentifier']
                engine = instance['Engine']
                status = instance['Status']
                allocated_storage = instance['AllocatedStorage']
                multi_az = instance['MultiAZ']
                storage_type = instance['StorageType']
                backup_retention = instance['BackupRetentionPeriod']
                creation_time = instance['CreationTime']
                vpc_security_groups = ", ".join(instance['VpcSecurityGroups'])
                tags = ", ".join([f"{tag['Key']}:{tag['Value']}" for tag in instance.get('Tags', [])])

                hourly_rate = RDS_PRICING.get(instance_type, 0.0)
                monthly_cost = hourly_rate * 24 * 30  # Assuming 30 days in a month

                all_data.append([
                    account_profile, instance_identifier, instance_type, engine, status,
                    allocated_storage, multi_az, storage_type, backup_retention,
                    creation_time, vpc_security_groups, tags, monthly_cost
                ])

            print(f"✓ {account_profile} - RDS info collected")
        else:
            print(f"✗ Error for {account_profile}: {result.stderr}")
    except Exception as e:
        print(f"⚠️  An error occurred: {e}")

def describe_rds_reservations(account_profile, reservations_data):
    command = [
        "aws", "rds", "describe-reserved-db-instances", "--no-verify-ssl",
        "--query", (
            "ReservedDBInstances[*].{"
            "DBInstanceIdentifier:ReservedDBInstanceId,"
            "DBInstanceClass:DBInstanceClass,"
            "DBInstanceCount:DBInstanceCount,"
            "Engine:Engine,"
            "OfferingType:OfferingType,"
            "Duration:Duration,"
            "FixedPrice:FixedPrice,"
            "UsagePrice:UsagePrice,"
            "ProductDescription:ProductDescription,"
            "State:State,"
            "StartTime:StartTime,"
            "EndTime:EndTime,"
            "RecurringChargeAmount:RecurringChargeAmount,"
            "RecurringChargeFrequency:RecurringChargeFrequency}"
        ),
        "--output", "json",
        "--profile", account_profile
    ]

    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if result.returncode == 0:
            data = json.loads(result.stdout)

            for reservation in data:
                reserved_instance_id = reservation['DBInstanceIdentifier']
                instance_type = reservation['DBInstanceClass']
                count = reservation.get('DBInstanceCount', 1)
                engine = reservation['Engine']
                offering_type = reservation['OfferingType']
                duration = reservation['Duration']
                fixed_price = reservation['FixedPrice']
                usage_price = reservation['UsagePrice']
                product_description = reservation['ProductDescription']
                state = reservation['State']
                start_time = reservation['StartTime']
                end_time = reservation['EndTime']
                recurring_charge_amount = reservation['RecurringChargeAmount']
                recurring_charge_frequency = reservation['RecurringChargeFrequency']
                total_fixed_price = fixed_price * count

                reservations_data.append([
                    account_profile, reserved_instance_id, instance_type, engine, count,
                    offering_type, duration, fixed_price, total_fixed_price, usage_price,
                    product_description, state, start_time, end_time,
                    recurring_charge_amount, recurring_charge_frequency
                ])

            print(f"✓ {account_profile} - RDS reservation info collected")
        else:
            print(f"✗ Error for {account_profile}: {result.stderr}")
    except Exception as e:
        print(f"⚠️  An error occurred: {e}")

if __name__ == "__main__":
    all_data = []
    reservations_data = []

    aws_profiles = [
        "int", "shared", "dnaDev", "dnaProd", "poc", "sec", "lionDC",
        "sapDev", "sapProd", "hpMonitoring", "contactCentre",
        "contactCentreProd", "master", "genAI", "audit"
    ]

    for profile in aws_profiles:
        describe_rds_instances(account_profile=profile, all_data=all_data)
        describe_rds_reservations(account_profile=profile, reservations_data=reservations_data)

    if all_data or reservations_data:
        columns_instances = [
            "Account", "DBInstanceIdentifier", "DBInstanceClass", "Engine", "Status",
            "AllocatedStorageGB", "MultiAZ", "StorageType", "BackupRetentionDays",
            "CreationTime", "VpcSecurityGroups", "Tags", "RDSInstanceCostEstimateMonthlyUSD"
        ]
        columns_reservations = [
            "Account", "ReservedDBInstanceId", "DBInstanceClass", "Engine", "DBInstanceCount",
            "OfferingType", "Duration", "FixedPrice", "TotalFixedPrice", "UsagePrice",
            "ProductDescription", "State", "StartTime", "EndTime",
            "RecurringChargeAmount", "RecurringChargeFrequency"
        ]

        timestamp = datetime.now().strftime("%Y_%m_%d_%H%M%S")
        filename = f"RDS_instance_inventory_and_reservations_{timestamp}.xlsx"
        
        with pd.ExcelWriter(filename) as writer:
            if all_data:
                df_instances = pd.DataFrame(all_data, columns=columns_instances)
                df_instances.to_excel(writer, sheet_name='RDS_Instances', index=False)

            if reservations_data:
                df_reservations = pd.DataFrame(reservations_data, columns=columns_reservations)
                df_reservations.to_excel(writer, sheet_name='RDS_Reservations', index=False)

        print(f"🎉 Report generated: {filename}")
    else:
        print("⚠️  No data collected from any profiles.")
