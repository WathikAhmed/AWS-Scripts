r"""
AWS Certificate Manager (ACM) Certificate Inventory

This script generates a comprehensive inventory of SSL/TLS certificates across multiple AWS accounts.

Features:
- Lists all certificates in ACM (Certificate Manager)
- Shows certificate status, expiration dates, and domains
- Identifies certificates nearing expiration
- Provides renewal recommendations
- Exports data to Excel with multiple analysis sheets

Requirements:
- AWS CLI configured with profiles
- Python packages: pandas, subprocess, json
- Proper IAM permissions for ACM describe operations

How to run:
1. Ensure virtual environment is activated: .venv\Scripts\activate
2. Install dependencies: pip install pandas
3. Configure AWS profiles in aws_profiles.json
4. Run script: python ACM_Certificates.py

Output:
- Excel file with certificate inventory and expiration analysis
"""

import subprocess
import json
import pandas as pd
from datetime import datetime, timezone, timedelta


def get_acm_certificates(account_profile, all_data):
    """Get ACM certificates for a given AWS profile"""
    command = [
        "aws", "acm", "list-certificates",
        "--output", "json",
        "--profile", account_profile,
        "--no-verify-ssl"
    ]

    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            certificates = data.get('CertificateSummaryList', [])
            
            if certificates:
                detailed_certs = []
                
                for cert in certificates:
                    cert_arn = cert.get('CertificateArn')
                    
                    # Get detailed certificate information
                    detail_command = [
                        "aws", "acm", "describe-certificate",
                        "--certificate-arn", cert_arn,
                        "--output", "json",
                        "--profile", account_profile,
                        "--no-verify-ssl"
                    ]
                    
                    try:
                        detail_result = subprocess.run(detail_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                        
                        if detail_result.returncode == 0:
                            detail_data = json.loads(detail_result.stdout)
                            certificate = detail_data.get('Certificate', {})
                            
                            # Extract certificate details
                            domain_name = certificate.get('DomainName', 'N/A')
                            subject_alt_names = certificate.get('SubjectAlternativeNames', [])
                            status = certificate.get('Status', 'N/A')
                            created_at = certificate.get('CreatedAt', 'N/A')
                            issued_at = certificate.get('IssuedAt', 'N/A')
                            not_before = certificate.get('NotBefore', 'N/A')
                            not_after = certificate.get('NotAfter', 'N/A')
                            key_algorithm = certificate.get('KeyAlgorithm', 'N/A')
                            signature_algorithm = certificate.get('SignatureAlgorithm', 'N/A')
                            key_usages = certificate.get('KeyUsages', [])
                            extended_key_usages = certificate.get('ExtendedKeyUsages', [])
                            certificate_type = certificate.get('Type', 'N/A')
                            renewal_eligibility = certificate.get('RenewalEligibility', 'N/A')
                            
                            # Calculate days until expiration
                            days_until_expiry = 'N/A'
                            expiry_status = 'Unknown'
                            
                            if not_after != 'N/A':
                                try:
                                    if isinstance(not_after, str):
                                        expiry_date = datetime.fromisoformat(not_after.replace('Z', '+00:00'))
                                    else:
                                        expiry_date = not_after.replace(tzinfo=timezone.utc)
                                    
                                    current_time = datetime.now(timezone.utc)
                                    days_until_expiry = (expiry_date - current_time).days
                                    
                                    if days_until_expiry < 0:
                                        expiry_status = 'Expired'
                                    elif days_until_expiry <= 30:
                                        expiry_status = 'Expires Soon (30 days)'
                                    elif days_until_expiry <= 60:
                                        expiry_status = 'Expires Soon (60 days)'
                                    else:
                                        expiry_status = 'Valid'
                                except:
                                    days_until_expiry = 'Parse Error'
                                    expiry_status = 'Unknown'
                            
                            # Generate recommendations
                            if expiry_status == 'Expired':
                                recommendation = 'Certificate expired - immediate renewal required'
                            elif expiry_status == 'Expires Soon (30 days)':
                                recommendation = 'Renew certificate immediately'
                            elif expiry_status == 'Expires Soon (60 days)':
                                recommendation = 'Plan certificate renewal'
                            elif status != 'ISSUED':
                                recommendation = f'Certificate status is {status} - review required'
                            else:
                                recommendation = 'No immediate action needed'
                            
                            detailed_certs.append({
                                'CertificateArn': cert_arn,
                                'DomainName': domain_name,
                                'SubjectAlternativeNames': ', '.join(subject_alt_names) if subject_alt_names else 'None',
                                'Status': status,
                                'Type': certificate_type,
                                'KeyAlgorithm': key_algorithm,
                                'SignatureAlgorithm': signature_algorithm,
                                'CreatedAt': created_at,
                                'IssuedAt': issued_at,
                                'NotBefore': not_before,
                                'NotAfter': not_after,
                                'DaysUntilExpiry': days_until_expiry,
                                'ExpiryStatus': expiry_status,
                                'RenewalEligibility': renewal_eligibility,
                                'KeyUsages': ', '.join([ku.get('Name', '') for ku in key_usages]) if key_usages else 'None',
                                'ExtendedKeyUsages': ', '.join([eku.get('Name', '') for eku in extended_key_usages]) if extended_key_usages else 'None',
                                'Recommendation': recommendation
                            })
                    except Exception as e:
                        print(f"Error getting details for certificate {cert_arn}: {e}")
                
                if detailed_certs:
                    df = pd.DataFrame(detailed_certs)
                    df["Account"] = account_profile
                    
                    # Reorder columns
                    columns = ["Account", "DomainName", "Status", "ExpiryStatus", "DaysUntilExpiry", 
                              "NotAfter", "Type", "SubjectAlternativeNames", "KeyAlgorithm", 
                              "SignatureAlgorithm", "RenewalEligibility", "Recommendation",
                              "CertificateArn", "CreatedAt", "IssuedAt", "NotBefore", 
                              "KeyUsages", "ExtendedKeyUsages"]
                    
                    df = df[columns]
                    all_data.append(df)
                    print(f"ACM certificates for {account_profile}: {len(detailed_certs)} certificates")
            else:
                print(f"No ACM certificates found for {account_profile}")
        else:
            print(f"Error retrieving ACM certificates for {account_profile}: {result.stderr}")
    except Exception as e:
        print(f"Error for {account_profile}: {e}")


if __name__ == "__main__":
    all_data = []

    # Load profiles from JSON file
    try:
        with open('aws_profiles.json', 'r') as f:
            aws_profiles = json.load(f)
    except FileNotFoundError:
        print("aws_profiles.json not found. Using default profiles.")
        aws_profiles = ["default"]

    print("Starting ACM certificate inventory...")
    
    for profile in aws_profiles:
        print(f"\nProcessing profile: {profile}")
        get_acm_certificates(account_profile=profile, all_data=all_data)

    # Generate comprehensive report
    if all_data:
        timestamp = datetime.now().strftime("%Y_%m_%d_%H%M%S")
        filename = f"acm_certificates_{timestamp}.xlsx"

        final_df = pd.concat(all_data, ignore_index=True)
        
        with pd.ExcelWriter(filename) as writer:
            # Main certificates data
            final_df.to_excel(writer, index=False, sheet_name="ACM_Certificates")
            
            # Expiry status summary
            expiry_summary = final_df.groupby(['Account', 'ExpiryStatus']).agg({
                'CertificateArn': 'count'
            }).reset_index()
            expiry_summary.columns = ['Account', 'ExpiryStatus', 'Count']
            expiry_summary.to_excel(writer, index=False, sheet_name="Expiry_Summary")
            
            # Certificates expiring soon
            expiring_soon = final_df[final_df['ExpiryStatus'].str.contains('Expires Soon|Expired')]
            if not expiring_soon.empty:
                expiring_soon.to_excel(writer, index=False, sheet_name="Expiring_Soon")
            
            # Certificate status summary
            status_summary = final_df.groupby(['Account', 'Status']).agg({
                'CertificateArn': 'count'
            }).reset_index()
            status_summary.columns = ['Account', 'Status', 'Count']
            status_summary.to_excel(writer, index=False, sheet_name="Status_Summary")

        print(f"\nACM certificate inventory saved to: {filename}")
        print(f"Total certificates found: {len(final_df)}")
        
        # Print summary statistics
        print("\nCertificate Status Summary:")
        status_counts = final_df['Status'].value_counts()
        for status, count in status_counts.items():
            print(f"  {status}: {count} certificates")
        
        print("\nExpiry Status Summary:")
        expiry_counts = final_df['ExpiryStatus'].value_counts()
        for status, count in expiry_counts.items():
            print(f"  {status}: {count} certificates")
        
        # Highlight certificates needing attention
        attention_needed = len(final_df[final_df['ExpiryStatus'].str.contains('Expires Soon|Expired')])
        if attention_needed > 0:
            print(f"\n*** {attention_needed} certificates need immediate attention! ***")
    else:
        print("\nNo ACM certificates found across any profiles.")