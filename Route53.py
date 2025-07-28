#!/usr/bin/env python3
"""
Route53.py - AWS Route53 inventory script

This script inventories Route53 hosted zones and DNS records across multiple AWS accounts.
It helps identify Route53 usage, domain configurations, and DNS record types.

Setup:
1. Configure AWS profiles in aws_profiles.json
2. Ensure AWS CLI is configured with proper permissions
3. Run script: python Route53.py

Output:
- Excel file with timestamp containing hosted zones and DNS records data
- Console output showing progress for each account processed
"""

import subprocess
import json
import pandas as pd
from datetime import datetime
import os

def get_hosted_zones(account_profile, zones_data):
    """Get Route53 hosted zones for an account."""
    command = [
        "aws", "route53", "list-hosted-zones",
        "--query", (
            "HostedZones[*].{"
            "Id:Id,"
            "Name:Name,"
            "CallerReference:CallerReference,"
            "ResourceRecordSetCount:ResourceRecordSetCount,"
            "Comment:Config.Comment,"
            "PrivateZone:Config.PrivateZone}"
        ),
        "--output", "json",
        "--profile", account_profile,
        "--no-verify-ssl"
    ]

    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if result.returncode == 0:
            data = json.loads(result.stdout)
            
            if data:
                for zone in data:
                    # Clean up the zone ID (remove /hostedzone/ prefix)
                    zone['Id'] = zone['Id'].replace('/hostedzone/', '')
                    zone['Account'] = account_profile
                
                df = pd.DataFrame(data)
                zones_data.append(df)
                print(f"Found {len(data)} hosted zones for {account_profile}")
            else:
                print(f"No hosted zones found for {account_profile}")
        else:
            print(f"Error getting hosted zones for {account_profile}: {result.stderr}")
    except Exception as e:
        print(f"Error processing hosted zones for {account_profile}: {e}")

def get_dns_records(account_profile, zone_id, zone_name, records_data):
    """Get DNS records for a specific hosted zone."""
    command = [
        "aws", "route53", "list-resource-record-sets",
        "--hosted-zone-id", zone_id,
        "--query", (
            "ResourceRecordSets[*].{"
            "Name:Name,"
            "Type:Type,"
            "TTL:TTL,"
            "ResourceRecords:ResourceRecords[*].Value,"
            "AliasTarget:AliasTarget.DNSName,"
            "Weight:Weight,"
            "Region:Region,"
            "Failover:Failover,"
            "SetIdentifier:SetIdentifier,"
            "HealthCheckId:HealthCheckId}"
        ),
        "--output", "json",
        "--profile", account_profile,
        "--no-verify-ssl"
    ]

    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if result.returncode == 0:
            data = json.loads(result.stdout)
            
            if data:
                for record in data:
                    record['Account'] = account_profile
                    record['ZoneId'] = zone_id
                    record['ZoneName'] = zone_name
                    
                    # Convert ResourceRecords list to string
                    if record.get('ResourceRecords'):
                        record['ResourceRecords'] = ', '.join(record['ResourceRecords'])
                    else:
                        record['ResourceRecords'] = None
                
                df = pd.DataFrame(data)
                records_data.append(df)
                print(f"  Found {len(data)} DNS records in zone {zone_name}")
            else:
                print(f"  No DNS records found in zone {zone_name}")
        else:
            print(f"  Error getting DNS records for zone {zone_name}: {result.stderr}")
    except Exception as e:
        print(f"  Error processing DNS records for zone {zone_name}: {e}")

def get_health_checks(account_profile, health_checks_data):
    """Get Route53 health checks for an account."""
    command = [
        "aws", "route53", "list-health-checks",
        "--query", (
            "HealthChecks[*].{"
            "Id:Id,"
            "CallerReference:CallerReference,"
            "Type:HealthCheckConfig.Type,"
            "ResourcePath:HealthCheckConfig.ResourcePath,"
            "FQDN:HealthCheckConfig.FullyQualifiedDomainName,"
            "IPAddress:HealthCheckConfig.IPAddress,"
            "Port:HealthCheckConfig.Port,"
            "RequestInterval:HealthCheckConfig.RequestInterval,"
            "FailureThreshold:HealthCheckConfig.FailureThreshold,"
            "MeasureLatency:HealthCheckConfig.MeasureLatency,"
            "Inverted:HealthCheckConfig.Inverted,"
            "Disabled:HealthCheckConfig.Disabled,"
            "HealthThreshold:HealthCheckConfig.HealthThreshold,"
            "ChildHealthChecks:HealthCheckConfig.ChildHealthChecks,"
            "EnableSNI:HealthCheckConfig.EnableSNI,"
            "Regions:HealthCheckConfig.Regions}"
        ),
        "--output", "json",
        "--profile", account_profile,
        "--no-verify-ssl"
    ]

    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if result.returncode == 0:
            data = json.loads(result.stdout)
            
            if data:
                for check in data:
                    check['Account'] = account_profile
                    
                    # Convert lists to strings for Excel compatibility
                    if check.get('ChildHealthChecks'):
                        check['ChildHealthChecks'] = ', '.join(check['ChildHealthChecks'])
                    if check.get('Regions'):
                        check['Regions'] = ', '.join(check['Regions'])
                
                df = pd.DataFrame(data)
                health_checks_data.append(df)
                print(f"Found {len(data)} health checks for {account_profile}")
            else:
                print(f"No health checks found for {account_profile}")
        else:
            print(f"Error getting health checks for {account_profile}: {result.stderr}")
    except Exception as e:
        print(f"Error processing health checks for {account_profile}: {e}")

def main():
    # Load AWS profiles
    try:
        with open('aws_profiles.json', 'r') as f:
            profiles = json.load(f)
    except FileNotFoundError:
        print("aws_profiles.json file not found. Please create it with your AWS profiles.")
        return
    except json.JSONDecodeError:
        print("Error reading aws_profiles.json. Please check the file format.")
        return

    zones_data = []
    records_data = []
    health_checks_data = []

    print("Starting Route53 inventory across all accounts...")
    print("=" * 60)

    for profile in profiles:
        print(f"\nProcessing account: {profile}")
        print("-" * 40)
        
        # Get hosted zones
        get_hosted_zones(profile, zones_data)
        
        # Get health checks
        get_health_checks(profile, health_checks_data)
        
        # Get DNS records for each hosted zone
        if zones_data:
            # Get the zones for this profile from the last added dataframe
            current_zones_df = zones_data[-1] if zones_data else pd.DataFrame()
            if not current_zones_df.empty and current_zones_df['Account'].iloc[0] == profile:
                for _, zone in current_zones_df.iterrows():
                    get_dns_records(profile, zone['Id'], zone['Name'], records_data)

    # Create Excel file with timestamp
    timestamp = datetime.now().strftime("%Y_%m_%d_%H%M%S")
    filename = f"route53_inventory_{timestamp}.xlsx"

    print(f"\nCreating Excel file: {filename}")
    print("=" * 60)

    with pd.ExcelWriter(filename, engine='openpyxl') as writer:
        # Hosted Zones sheet
        if zones_data:
            all_zones = pd.concat(zones_data, ignore_index=True)
            all_zones.to_excel(writer, sheet_name='Hosted_Zones', index=False)
            print(f"Hosted Zones: {len(all_zones)} zones across all accounts")
        else:
            pd.DataFrame().to_excel(writer, sheet_name='Hosted_Zones', index=False)
            print("Hosted Zones: No zones found")

        # DNS Records sheet
        if records_data:
            all_records = pd.concat(records_data, ignore_index=True)
            all_records.to_excel(writer, sheet_name='DNS_Records', index=False)
            print(f"DNS Records: {len(all_records)} records across all accounts")
        else:
            pd.DataFrame().to_excel(writer, sheet_name='DNS_Records', index=False)
            print("DNS Records: No records found")

        # Health Checks sheet
        if health_checks_data:
            all_health_checks = pd.concat(health_checks_data, ignore_index=True)
            all_health_checks.to_excel(writer, sheet_name='Health_Checks', index=False)
            print(f"Health Checks: {len(all_health_checks)} health checks across all accounts")
        else:
            pd.DataFrame().to_excel(writer, sheet_name='Health_Checks', index=False)
            print("Health Checks: No health checks found")

    print(f"\nRoute53 inventory completed successfully!")
    print(f"Results saved to: {filename}")
    
    # Summary statistics
    total_zones = len(pd.concat(zones_data, ignore_index=True)) if zones_data else 0
    total_records = len(pd.concat(records_data, ignore_index=True)) if records_data else 0
    total_health_checks = len(pd.concat(health_checks_data, ignore_index=True)) if health_checks_data else 0
    
    print(f"\nSummary:")
    print(f"- Total Hosted Zones: {total_zones}")
    print(f"- Total DNS Records: {total_records}")
    print(f"- Total Health Checks: {total_health_checks}")
    print(f"- Accounts processed: {len(profiles)}")

if __name__ == "__main__":
    main()