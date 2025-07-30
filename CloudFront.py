#!/usr/bin/env python3
"""
CloudFront.py - AWS CloudFront inventory script

This script inventories CloudFront distributions across multiple AWS accounts.
Discovers CDN configurations, origins, behaviors, and SSL certificates.

Setup:
1. Configure AWS profiles in aws_profiles.json
2. Ensure AWS CLI is configured with proper permissions
3. Run script: python CloudFront.py

Output:
- Excel file with timestamp containing CloudFront distributions data
- Console output showing progress for each account processed
"""

import subprocess
import json
import pandas as pd
from datetime import datetime

def get_cloudfront_distributions(account_profile):
    """Retrieve CloudFront distributions for an account."""
    print(f"Checking CloudFront distributions for account: {account_profile}")

    command = [
        "aws", "cloudfront", "list-distributions",
        "--query", (
            "DistributionList.Items[*].{"
            "Id:Id,"
            "ARN:ARN,"
            "Status:Status,"
            "LastModifiedTime:LastModifiedTime,"
            "DomainName:DomainName,"
            "Comment:Comment,"
            "Enabled:Enabled,"
            "PriceClass:PriceClass,"
            "HttpVersion:HttpVersion,"
            "IsIPV6Enabled:IsIPV6Enabled,"
            "WebACLId:WebACLId,"
            "Origins:Origins,"
            "DefaultCacheBehavior:DefaultCacheBehavior,"
            "CacheBehaviors:CacheBehaviors,"
            "CustomErrorResponses:CustomErrorResponses,"
            "Logging:Logging,"
            "ViewerCertificate:ViewerCertificate,"
            "Restrictions:Restrictions,"
            "Aliases:Aliases}"
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
                print(f"  Found {len(data)} CloudFront distributions")
                return data
            else:
                print(f"  No CloudFront distributions found")
                return []
        else:
            print(f"  Error retrieving CloudFront data: {result.stderr}")
            return []
    except Exception as e:
        print(f"  Error processing CloudFront data: {e}")
        return []

def get_distribution_tags(distribution_id, account_profile):
    """Get tags for a specific distribution."""
    command = [
        "aws", "cloudfront", "list-tags-for-resource",
        "--resource", f"arn:aws:cloudfront::{distribution_id}:distribution/{distribution_id}",
        "--query", "Tags.Items[*].{Key:Key,Value:Value}",
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

def extract_origins_info(origins):
    """Extract origin information."""
    if not origins:
        return "", "", ""
    
    origin_domains = []
    origin_types = []
    s3_origins = []
    
    # Handle case where origins might be a string or list
    if isinstance(origins, str):
        return origins, "Unknown", ""
    
    for origin in origins:
        if isinstance(origin, dict):
            origin_domains.append(origin.get('DomainName', ''))
            
            if origin.get('S3OriginConfig'):
                origin_types.append('S3')
                s3_origins.append(origin.get('DomainName', ''))
            elif origin.get('CustomOriginConfig'):
                origin_types.append('Custom')
            else:
                origin_types.append('Unknown')
        else:
            origin_domains.append(str(origin))
            origin_types.append('Unknown')
    
    return ', '.join(origin_domains), ', '.join(set(origin_types)), ', '.join(s3_origins)

def extract_certificate_info(viewer_cert):
    """Extract SSL certificate information."""
    if not viewer_cert:
        return "", "", ""
    
    cert_source = viewer_cert.get('CertificateSource', '')
    ssl_support = viewer_cert.get('SSLSupportMethod', '')
    min_protocol = viewer_cert.get('MinimumProtocolVersion', '')
    
    return cert_source, ssl_support, min_protocol

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

def process_distribution(dist, account_profile):
    """Process a single CloudFront distribution."""
    # Get tags for this distribution
    tags = get_distribution_tags(dist.get('Id', ''), account_profile)
    name, tags_str = extract_tags_info(tags)
    
    # Extract origins information
    origin_domains, origin_types, s3_origins = extract_origins_info(dist.get('Origins', []))
    
    # Extract certificate information
    cert_source, ssl_support, min_protocol = extract_certificate_info(dist.get('ViewerCertificate', {}))
    
    # Extract cache behaviors count
    cache_behaviors_count = len(dist.get('CacheBehaviors', []))
    
    # Extract logging information
    logging_config = dist.get('Logging') or {}
    logging_enabled = logging_config.get('Enabled', False) if isinstance(logging_config, dict) else False
    logging_bucket = logging_config.get('Bucket', '') if isinstance(logging_config, dict) and logging_enabled else ''
    
    # Extract restrictions
    restrictions = dist.get('Restrictions') or {}
    geo_restriction = restrictions.get('GeoRestriction', {}) if isinstance(restrictions, dict) else {}
    geo_restriction_type = geo_restriction.get('RestrictionType', '') if isinstance(geo_restriction, dict) else ''
    
    return {
        'Account': account_profile,
        'DistributionId': dist.get('Id'),
        'Name': name,
        'DomainName': dist.get('DomainName'),
        'Aliases': ', '.join(dist.get('Aliases', [])),
        'Status': dist.get('Status'),
        'Enabled': dist.get('Enabled'),
        'Comment': dist.get('Comment', ''),
        'PriceClass': dist.get('PriceClass'),
        'HttpVersion': dist.get('HttpVersion'),
        'IsIPV6Enabled': dist.get('IsIPV6Enabled'),
        'WebACLId': dist.get('WebACLId', ''),
        'LastModifiedTime': dist.get('LastModifiedTime'),
        'OriginDomains': origin_domains,
        'OriginTypes': origin_types,
        'S3Origins': s3_origins,
        'CacheBehaviorsCount': cache_behaviors_count,
        'LoggingEnabled': logging_enabled,
        'LoggingBucket': logging_bucket,
        'CertificateSource': cert_source,
        'SSLSupportMethod': ssl_support,
        'MinProtocolVersion': min_protocol,
        'GeoRestrictionType': geo_restriction_type,
        'Tags': tags_str,
        'ARN': dist.get('ARN')
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

    print("Starting CloudFront inventory across all accounts...")
    print("=" * 60)

    for profile in profiles:
        print(f"\nProcessing account: {profile}")
        print("-" * 40)
        
        # Get CloudFront distributions
        distributions = get_cloudfront_distributions(profile)
        
        for dist in distributions:
            processed_dist = process_distribution(dist, profile)
            all_data.append(processed_dist)

    # Create Excel file with timestamp
    timestamp = datetime.now().strftime("%Y_%m_%d_%H%M%S")
    filename = f"cloudfront_inventory_{timestamp}.xlsx"

    print(f"\nCreating Excel file: {filename}")
    print("=" * 60)

    if all_data:
        df = pd.DataFrame(all_data)
        df.to_excel(filename, index=False)
        print(f"CloudFront distributions saved to {filename}")
        print(f"Total CloudFront distributions found: {len(all_data)}")
        
        # Summary statistics
        enabled_count = df['Enabled'].sum()
        disabled_count = len(df) - enabled_count
        
        print(f"\nSummary:")
        print(f"- Total Distributions: {len(all_data)}")
        print(f"- Enabled: {enabled_count}")
        print(f"- Disabled: {disabled_count}")
        print(f"- Accounts processed: {len(profiles)}")
        
        # Show distribution by account
        account_counts = df['Account'].value_counts()
        print(f"- Distributions by account:")
        for account, count in account_counts.items():
            print(f"  * {account}: {count}")
            
        # Show origin types
        if 'OriginTypes' in df.columns:
            origin_types = df['OriginTypes'].str.split(', ').explode().value_counts()
            print(f"- Origin types:")
            for origin_type, count in origin_types.items():
                print(f"  * {origin_type}: {count}")
    else:
        # Create empty Excel file
        pd.DataFrame().to_excel(filename, index=False)
        print("No CloudFront distributions found across all accounts")

    print(f"\nCloudFront inventory completed successfully!")

if __name__ == "__main__":
    main()