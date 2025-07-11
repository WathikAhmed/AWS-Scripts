r"""
WorkSpaces Master Analysis Script

Combines functionality from:
- WorkSpaces.py: Basic workspace details and bundles
- WorkSpaces_Usage.py: Connection status and usage patterns  
- check_running_mode.py: Running mode analysis for pricing

Generates comprehensive WorkSpaces inventory with usage analysis and cost optimization recommendations.

Requirements:
- AWS CLI configured with profiles
- Python packages: pandas, subprocess, json
- Proper IAM permissions for WorkSpaces describe operations

How to run:
1. Ensure virtual environment is activated: .venv\Scripts\activate
2. Install dependencies: pip install pandas
3. Configure AWS profiles in aws_profiles.json
4. Run script: python WorkSpaces_Master.py

Output:
- Excel file with multiple sheets containing workspace details, usage patterns, and optimization recommendations
"""

import subprocess
import json
import pandas as pd
from datetime import datetime, timezone


def get_workspaces_details(account_profile, all_data):
    """Get WorkSpaces details including compute types"""
    command = [
        "aws", "workspaces", "describe-workspaces",
        "--query", (
            "Workspaces[*].{"
            "WorkspaceId:WorkspaceId,"
            "DirectoryId:DirectoryId,"
            "UserName:UserName,"
            "IpAddress:IpAddress,"
            "State:State,"
            "BundleId:BundleId,"
            "SubnetId:SubnetId,"
            "ErrorMessage:ErrorMessage,"
            "VolumeEncryptionKey:VolumeEncryptionKey,"
            "UserVolumeEncryptionEnabled:UserVolumeEncryptionEnabled,"
            "RootVolumeEncryptionEnabled:RootVolumeEncryptionEnabled,"
            "ComputeTypeName:WorkspaceProperties.ComputeTypeName,"
            "RootVolumeSizeGib:WorkspaceProperties.RootVolumeSizeGib,"
            "UserVolumeSizeGib:WorkspaceProperties.UserVolumeSizeGib,"
            "RunningMode:WorkspaceProperties.RunningMode,"
            "RunningModeAutoStopTimeoutInMinutes:WorkspaceProperties.RunningModeAutoStopTimeoutInMinutes,"
            "Protocols:WorkspaceProperties.Protocols}"
        ),
        "--output", "json",
        "--profile", account_profile
    ]

    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            if data:
                df = pd.DataFrame(data)
                df["Account"] = account_profile
                all_data.append(df)
                print(f"WorkSpaces details for {account_profile}: {len(data)} workspaces")
            else:
                print(f"No WorkSpaces found for {account_profile}")
        else:
            print(f"Error retrieving WorkSpaces for {account_profile}: {result.stderr}")
    except Exception as e:
        print(f"Error for {account_profile}: {e}")


def get_workspaces_usage(account_profile, usage_data):
    """Get WorkSpaces connection status and usage patterns"""
    command = [
        "aws", "workspaces", "describe-workspaces-connection-status",
        "--output", "json",
        "--profile", account_profile
    ]

    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            workspaces_status = data.get('WorkspacesConnectionStatus', [])
            
            if workspaces_status:
                processed_workspaces = []
                current_time = datetime.now(timezone.utc)
                
                for ws in workspaces_status:
                    workspace_id = ws.get('WorkspaceId', 'N/A')
                    connection_state = ws.get('ConnectionState', 'UNKNOWN')
                    last_connection = ws.get('LastKnownUserConnectionTimestamp')
                    
                    days_unused = 'Never connected'
                    last_connection_str = 'Never'
                    
                    if last_connection:
                        try:
                            last_conn_dt = datetime.fromisoformat(last_connection.replace('Z', '+00:00'))
                            days_unused = (current_time - last_conn_dt).days
                            last_connection_str = last_conn_dt.strftime('%Y-%m-%d %H:%M')
                        except:
                            days_unused = 'Parse error'
                    
                    if days_unused == 'Never connected':
                        usage_status = 'Never used'
                        recommendation = 'Consider termination - never connected'
                    elif isinstance(days_unused, int):
                        if days_unused > 90:
                            usage_status = 'Unused (90+ days)'
                            recommendation = 'Consider termination - long unused'
                        elif days_unused > 30:
                            usage_status = 'Unused (30+ days)'
                            recommendation = 'Review with user - may be unused'
                        elif days_unused > 7:
                            usage_status = 'Low usage (7+ days)'
                            recommendation = 'Monitor usage patterns'
                        else:
                            usage_status = 'Active'
                            recommendation = 'No action needed'
                    else:
                        usage_status = 'Unknown'
                        recommendation = 'Manual review needed'
                    
                    processed_workspaces.append({
                        'WorkspaceId': workspace_id,
                        'ConnectionState': connection_state,
                        'LastConnection': last_connection_str,
                        'DaysUnused': days_unused,
                        'UsageStatus': usage_status,
                        'Recommendation': recommendation
                    })
                
                df = pd.DataFrame(processed_workspaces)
                df["Account"] = account_profile
                usage_data.append(df)
                print(f"Usage data for {account_profile}: {len(workspaces_status)} workspaces")
        else:
            print(f"Error retrieving usage for {account_profile}: {result.stderr}")
    except Exception as e:
        print(f"Error getting usage for {account_profile}: {e}")


def analyze_running_modes(workspaces_df):
    """Analyze running modes for pricing recommendations"""
    if workspaces_df.empty:
        return pd.DataFrame()
    
    running_mode_analysis = workspaces_df.groupby(['Account', 'RunningMode', 'ComputeTypeName']).agg({
        'WorkspaceId': 'count'
    }).reset_index()
    running_mode_analysis.columns = ['Account', 'RunningMode', 'ComputeType', 'Count']
    
    # Add pricing recommendations
    pricing_recommendations = []
    for _, row in running_mode_analysis.iterrows():
        if row['RunningMode'] == 'ALWAYS_ON':
            pricing_model = 'Personal (Monthly fixed cost)'
        elif row['RunningMode'] == 'AUTO_STOP':
            pricing_model = 'Core/Pool (Pay per hour)'
        else:
            pricing_model = 'Unknown'
        
        pricing_recommendations.append(pricing_model)
    
    running_mode_analysis['PricingModel'] = pricing_recommendations
    return running_mode_analysis


if __name__ == "__main__":
    all_data = []
    usage_data = []

    # Load profiles from JSON file
    try:
        with open('aws_profiles.json', 'r') as f:
            aws_profiles = json.load(f)
    except FileNotFoundError:
        print("aws_profiles.json not found. Using default profiles.")
        aws_profiles = ["shared"]  # WorkSpaces typically in shared account

    print("Starting comprehensive WorkSpaces analysis...")
    
    for profile in aws_profiles:
        print(f"\nProcessing profile: {profile}")
        get_workspaces_details(account_profile=profile, all_data=all_data)
        get_workspaces_usage(account_profile=profile, usage_data=usage_data)

    # Generate comprehensive report
    if all_data or usage_data:
        timestamp = datetime.now().strftime("%Y_%m_%d_%H%M%S")
        filename = f"workspaces_master_analysis_{timestamp}.xlsx"

        with pd.ExcelWriter(filename) as writer:
            # Main WorkSpaces details
            if all_data:
                workspaces_df = pd.concat(all_data, ignore_index=True)
                columns = ["Account"] + [col for col in workspaces_df.columns if col != "Account"]
                workspaces_df = workspaces_df[columns]
                workspaces_df.to_excel(writer, index=False, sheet_name="WorkSpaces_Details")
                
                # Running mode analysis
                running_mode_df = analyze_running_modes(workspaces_df)
                if not running_mode_df.empty:
                    running_mode_df.to_excel(writer, index=False, sheet_name="Running_Mode_Analysis")
            
            # Usage analysis
            if usage_data:
                usage_df = pd.concat(usage_data, ignore_index=True)
                usage_df.to_excel(writer, index=False, sheet_name="Usage_Analysis")
                
                # Usage summary
                usage_summary = usage_df.groupby(['Account', 'UsageStatus']).size().reset_index(name='Count')
                usage_summary.to_excel(writer, index=False, sheet_name="Usage_Summary")
                
                # Unused workspaces
                unused = usage_df[usage_df['UsageStatus'].str.contains('Unused|Never')]
                if not unused.empty:
                    unused.to_excel(writer, index=False, sheet_name="Unused_WorkSpaces")
            
            # Combined analysis (if both datasets available)
            if all_data and usage_data:
                workspaces_df = pd.concat(all_data, ignore_index=True)
                usage_df = pd.concat(usage_data, ignore_index=True)
                
                combined = pd.merge(workspaces_df, usage_df, on=['Account', 'WorkspaceId'], how='outer')
                combined.to_excel(writer, index=False, sheet_name="Combined_Analysis")

        print(f"\nWorkSpaces master analysis saved to: {filename}")
        
        # Print summary statistics
        if all_data:
            workspaces_df = pd.concat(all_data, ignore_index=True)
            print(f"Total WorkSpaces found: {len(workspaces_df)}")
            
            print("\nRunning Mode Distribution:")
            running_modes = workspaces_df['RunningMode'].value_counts()
            for mode, count in running_modes.items():
                print(f"  {mode}: {count} workspaces")
        
        if usage_data:
            usage_df = pd.concat(usage_data, ignore_index=True)
            print("\nUsage Status Summary:")
            status_summary = usage_df['UsageStatus'].value_counts()
            for status, count in status_summary.items():
                print(f"  {status}: {count} workspaces")
            
            unused_count = len(usage_df[usage_df['UsageStatus'].str.contains('Unused|Never')])
            if unused_count > 0:
                print(f"\n*** {unused_count} WorkSpaces appear unused - potential cost savings! ***")
    else:
        print("\nNo WorkSpaces found across any profiles.")