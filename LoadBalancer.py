#!/usr/bin/env python3
"""
LoadBalancer.py - AWS Load Balancer inventory script

This script inventories all types of load balancers across multiple AWS accounts:
- Application Load Balancers (ALB)
- Network Load Balancers (NLB)
- Classic Load Balancers (CLB)
- Gateway Load Balancers (GLB)

Setup:
1. Configure AWS profiles in aws_profiles.json
2. Ensure AWS CLI is configured with proper permissions
3. Run script: python LoadBalancer.py

Output:
- Excel file with timestamp containing load balancer data
- Console output showing progress for each account processed
"""

import subprocess
import json
import pandas as pd
from datetime import datetime

def get_load_balancers(account_profile):
    """Retrieve all load balancers (ALB/NLB) for an account."""
    print(f"Checking ALB/NLB for account: {account_profile}")

    command = [
        "aws", "elbv2", "describe-load-balancers",
        "--query", (
            "LoadBalancers[*].{"
            "LoadBalancerArn:LoadBalancerArn,"
            "DNSName:DNSName,"
            "CanonicalHostedZoneId:CanonicalHostedZoneId,"
            "CreatedTime:CreatedTime,"
            "LoadBalancerName:LoadBalancerName,"
            "Scheme:Scheme,"
            "VpcId:VpcId,"
            "State:State.Code,"
            "Type:Type,"
            "IpAddressType:IpAddressType,"
            "SecurityGroups:SecurityGroups,"
            "AvailabilityZones:AvailabilityZones}"
        ),
        "--output", "json",
        "--profile", account_profile,
        "--no-verify-ssl"
    ]

    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            print(f"  Found {len(data)} ALB/NLB load balancers")
            return data
        else:
            print(f"  Error retrieving ALB/NLB data: {result.stderr}")
            return []
    except Exception as e:
        print(f"  Error processing ALB/NLB data: {e}")
        return []

def get_classic_load_balancers(account_profile):
    """Retrieve Classic Load Balancers for an account."""
    print(f"Checking CLB for account: {account_profile}")

    command = [
        "aws", "elb", "describe-load-balancers",
        "--query", (
            "LoadBalancerDescriptions[*].{"
            "LoadBalancerName:LoadBalancerName,"
            "DNSName:DNSName,"
            "CanonicalHostedZoneNameID:CanonicalHostedZoneNameID,"
            "CreatedTime:CreatedTime,"
            "Scheme:Scheme,"
            "VPCId:VPCId,"
            "SecurityGroups:SecurityGroups,"
            "Subnets:Subnets,"
            "AvailabilityZones:AvailabilityZones,"
            "Instances:Instances,"
            "HealthCheck:HealthCheck,"
            "ListenerDescriptions:ListenerDescriptions}"
        ),
        "--output", "json",
        "--profile", account_profile,
        "--no-verify-ssl"
    ]

    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            print(f"  Found {len(data)} Classic Load Balancers")
            return data
        else:
            print(f"  Error retrieving CLB data: {result.stderr}")
            return []
    except Exception as e:
        print(f"  Error processing CLB data: {e}")
        return []

def get_listeners(lb_arn, account_profile):
    """Get listeners for a specific load balancer."""
    command = [
        "aws", "elbv2", "describe-listeners",
        "--load-balancer-arn", lb_arn,
        "--query", "Listeners[*].{Port:Port,Protocol:Protocol,SslPolicy:SslPolicy,CertificateArn:Certificates[0].CertificateArn}",
        "--output", "json",
        "--profile", account_profile,
        "--no-verify-ssl"
    ]

    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            return []
    except Exception:
        return []

def get_target_groups(lb_arn, account_profile):
    """Get target groups for a specific load balancer."""
    command = [
        "aws", "elbv2", "describe-target-groups",
        "--load-balancer-arn", lb_arn,
        "--query", "TargetGroups[*].{TargetGroupName:TargetGroupName,Protocol:Protocol,Port:Port,HealthCheckPath:HealthCheckPath,HealthCheckProtocol:HealthCheckProtocol,HealthyThresholdCount:HealthyThresholdCount,UnhealthyThresholdCount:UnhealthyThresholdCount}",
        "--output", "json",
        "--profile", account_profile,
        "--no-verify-ssl"
    ]

    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            return []
    except Exception:
        return []

def get_lb_tags(lb_arn, account_profile):
    """Get tags for a specific load balancer."""
    command = [
        "aws", "elbv2", "describe-tags",
        "--resource-arns", lb_arn,
        "--query", "TagDescriptions[0].Tags[*].{Key:Key,Value:Value}",
        "--output", "json",
        "--profile", account_profile,
        "--no-verify-ssl"
    ]

    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            return []
    except Exception:
        return []

def extract_tags_info(tags):
    """Extract tags information."""
    if not tags:
        return "", ""
    
    name = ""
    tags_str = ""
    
    for tag in tags:
        if tag.get('Key') == 'Name':
            name = tag.get('Value', '')
        tags_str += f"{tag.get('Key', '')}:{tag.get('Value', '')}; "
    
    return name, tags_str.rstrip('; ')

def process_alb_nlb(lb, account_profile):
    """Process ALB/NLB load balancer."""
    # Get additional details
    listeners = get_listeners(lb.get('LoadBalancerArn', ''), account_profile)
    target_groups = get_target_groups(lb.get('LoadBalancerArn', ''), account_profile)
    tags = get_lb_tags(lb.get('LoadBalancerArn', ''), account_profile)
    
    name, tags_str = extract_tags_info(tags)
    
    # Extract availability zones
    az_info = lb.get('AvailabilityZones', [])
    az_names = [az.get('ZoneName', '') for az in az_info if isinstance(az, dict)]
    subnets = [az.get('SubnetId', '') for az in az_info if isinstance(az, dict)]
    
    # Extract listener info
    listener_ports = [str(l.get('Port', '')) for l in listeners if l.get('Port')]
    listener_protocols = [l.get('Protocol', '') for l in listeners if l.get('Protocol')]
    ssl_policies = [l.get('SslPolicy', '') for l in listeners if l.get('SslPolicy')]
    certificates = [l.get('CertificateArn', '') for l in listeners if l.get('CertificateArn')]
    
    # Extract target group info
    tg_names = [tg.get('TargetGroupName', '') for tg in target_groups]
    
    return {
        'Account': account_profile,
        'LoadBalancerName': lb.get('LoadBalancerName'),
        'Name': name,
        'Type': lb.get('Type'),
        'DNSName': lb.get('DNSName'),
        'Scheme': lb.get('Scheme'),
        'State': lb.get('State'),
        'VpcId': lb.get('VpcId'),
        'IpAddressType': lb.get('IpAddressType'),
        'CreatedTime': lb.get('CreatedTime'),
        'AvailabilityZones': ', '.join(az_names),
        'Subnets': ', '.join(subnets),
        'SecurityGroups': ', '.join(lb.get('SecurityGroups', []) or []),
        'ListenerPorts': ', '.join(listener_ports),
        'ListenerProtocols': ', '.join(set(listener_protocols)),
        'SSLPolicies': ', '.join(set(ssl_policies)),
        'Certificates': ', '.join(certificates),
        'TargetGroups': ', '.join(tg_names),
        'TargetGroupCount': len(target_groups),
        'Tags': tags_str,
        'LoadBalancerArn': lb.get('LoadBalancerArn')
    }

def process_classic_lb(lb, account_profile):
    """Process Classic Load Balancer."""
    # Extract listener info
    listeners = lb.get('ListenerDescriptions', [])
    listener_ports = []
    listener_protocols = []
    ssl_policies = []
    
    for listener_desc in listeners:
        listener = listener_desc.get('Listener', {})
        listener_ports.append(str(listener.get('LoadBalancerPort', '')))
        listener_protocols.append(listener.get('Protocol', ''))
        if listener.get('SSLCertificateId'):
            ssl_policies.append('Classic-SSL')
    
    # Extract health check info
    health_check = lb.get('HealthCheck', {})
    health_check_target = health_check.get('Target', '')
    
    return {
        'Account': account_profile,
        'LoadBalancerName': lb.get('LoadBalancerName'),
        'Name': lb.get('LoadBalancerName'),  # CLB doesn't have separate name tag
        'Type': 'classic',
        'DNSName': lb.get('DNSName'),
        'Scheme': lb.get('Scheme'),
        'State': 'active',  # CLB doesn't have state field
        'VpcId': lb.get('VPCId', ''),
        'IpAddressType': 'ipv4',  # CLB default
        'CreatedTime': lb.get('CreatedTime'),
        'AvailabilityZones': ', '.join(lb.get('AvailabilityZones', [])),
        'Subnets': ', '.join(lb.get('Subnets', [])),
        'SecurityGroups': ', '.join(lb.get('SecurityGroups', [])),
        'ListenerPorts': ', '.join(listener_ports),
        'ListenerProtocols': ', '.join(set(listener_protocols)),
        'SSLPolicies': ', '.join(set(ssl_policies)),
        'Certificates': '',  # Would need separate call for CLB certs
        'TargetGroups': '',  # CLB uses instances directly
        'TargetGroupCount': 0,
        'InstanceCount': len(lb.get('Instances', [])),
        'HealthCheckTarget': health_check_target,
        'Tags': '',
        'LoadBalancerArn': ''
    }

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

    all_data = []

    print("Starting Load Balancer inventory across all accounts...")
    print("=" * 60)

    for profile in profiles:
        print(f"\nProcessing account: {profile}")
        print("-" * 40)
        
        # Get ALB/NLB load balancers
        alb_nlb_data = get_load_balancers(profile)
        for lb in alb_nlb_data:
            processed_lb = process_alb_nlb(lb, profile)
            all_data.append(processed_lb)
        
        # Get Classic Load Balancers
        clb_data = get_classic_load_balancers(profile)
        for lb in clb_data:
            processed_lb = process_classic_lb(lb, profile)
            all_data.append(processed_lb)

    # Create Excel file with timestamp
    timestamp = datetime.now().strftime("%Y_%m_%d_%H%M%S")
    filename = f"load_balancer_inventory_{timestamp}.xlsx"

    print(f"\nCreating Excel file: {filename}")
    print("=" * 60)

    if all_data:
        df = pd.DataFrame(all_data)
        df.to_excel(filename, index=False)
        print(f"Load balancer inventory saved to {filename}")
        print(f"Total load balancers found: {len(all_data)}")
        
        # Summary statistics
        lb_types = df['Type'].value_counts()
        schemes = df['Scheme'].value_counts()
        
        print(f"\nSummary:")
        print(f"- Total Load Balancers: {len(all_data)}")
        print(f"- Load Balancer Types:")
        for lb_type, count in lb_types.items():
            print(f"  * {lb_type}: {count}")
        print(f"- Schemes:")
        for scheme, count in schemes.items():
            print(f"  * {scheme}: {count}")
        print(f"- Accounts processed: {len(profiles)}")
        
        # Show distribution by account
        account_counts = df['Account'].value_counts()
        print(f"- Load Balancers by account:")
        for account, count in account_counts.items():
            print(f"  * {account}: {count}")
    else:
        # Create empty Excel file
        pd.DataFrame().to_excel(filename, index=False)
        print("No load balancers found across all accounts")

    print(f"\nLoad Balancer inventory completed successfully!")

if __name__ == "__main__":
    main()