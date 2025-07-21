import subprocess
import json
import pandas as pd
from datetime import datetime, timedelta, timezone

# Function to get the last invocation time of a Lambda function
def get_last_invocation_time(function_name, account_profile):
    print(f"  - Checking last invocation for {function_name}...")
    # Get the current time in UTC using timezone-aware approach
    end_time = datetime.now(timezone.utc)
    # Look back 30 days
    start_time = end_time - timedelta(days=30)
    
    # Format times for CloudWatch Logs query
    start_time_str = start_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_time_str = end_time.strftime("%Y-%m-%dT%H:%M:%SZ")
    
    # Command to get the latest log stream
    command = [
        "aws", "logs", "describe-log-streams",
        "--log-group-name", f"/aws/lambda/{function_name}",
        "--order-by", "LastEventTime",
        "--descending",
        "--limit", "1",
        "--query", "logStreams[0].lastEventTimestamp",
        "--output", "text",
        "--profile", account_profile,
        "--no-verify-ssl"
    ]
    
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if result.returncode == 0 and result.stdout.strip():
            # Convert timestamp (milliseconds since epoch) to readable date
            timestamp = int(result.stdout.strip()) / 1000  # Convert to seconds
            last_invocation = datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")
            print(f"    ✓ Found last invocation: {last_invocation}")
            return last_invocation
        else:
            print(f"    ✗ No recent invocations found")
            return "No recent invocations"
    except Exception as e:
        print(f"    ✗ Error retrieving logs: {str(e)[:100]}")
        return "Error retrieving logs"

def describe_lambda_functions(account_profile, all_data):
    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Processing account: {account_profile}")
    print(f"Retrieving Lambda functions list...")
    command = [
        "aws", "lambda", "list-functions", "--no-verify-ssl",
        "--query", "Functions[*].[FunctionName, FunctionArn, Runtime, Role, Handler, CodeSize, MemorySize, Timeout, LastModified, Environment.Variables, Tags]",
        "--output", "json",
        "--profile", account_profile
    ]
    
    try:
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            function_count = len(data)
            print(f"Found {function_count} Lambda functions in {account_profile}")
            
            # Define column headers for the raw data
            raw_columns = [
                "FunctionName", "FunctionArn", "Runtime", "Role", "Handler", "CodeSize", "MemorySize", "Timeout", "LastModified", "EnvironmentVariables", "Tags"
            ]

            # Convert data to DataFrame
            df = pd.DataFrame(data, columns=raw_columns)
            
            # Add "Account" column to differentiate the data
            df["Account"] = account_profile
            
            # Get last invocation time for each function
            print(f"Retrieving last invocation times for {function_count} functions...")
            df["LastInvocationTime"] = df["FunctionName"].apply(lambda x: get_last_invocation_time(x, account_profile))
            
            # Define the final column order with LastInvocationTime right after LastModified
            final_columns = [
                "Account", "FunctionName", "FunctionArn", "Runtime", "Role", "Handler", "CodeSize", "MemorySize", "Timeout", 
                "LastModified", "LastInvocationTime", "EnvironmentVariables", "Tags"
            ]
            
            # Reorder columns according to the final order
            df = df[final_columns]
            
            # Append this data to the all_data list
            all_data.append(df)
            print(f"✓ Lambda function details for {account_profile} added to the data.")
        else:
            print(f"Error running AWS CLI command for {account_profile}: {result.stderr}")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    # List to store all data
    all_data = []
    
    # List of AWS profiles to iterate over
    aws_profiles = [
        "int", "shared", "dnaDev", "dnaProd", "poc", "sec", "lionDC", "sapDev", "sapProd", "hpMonitoring", "contactCentre", "contactCentreProd", "master", "genAI", "audit"
    ]
    
    print(f"\n{'='*60}")
    print(f"LAMBDA FUNCTION INVENTORY SCRIPT - STARTED AT {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    print(f"Will process {len(aws_profiles)} AWS accounts")
    
    # Run for all accounts and collect the data
    for i, profile in enumerate(aws_profiles, 1):
        print(f"\nProcessing account {i}/{len(aws_profiles)}: {profile}")
        describe_lambda_functions(account_profile=profile, all_data=all_data)
    
    # Concatenate all data into a single DataFrame
    final_df = pd.concat(all_data, ignore_index=True)
    
    # Create a DataFrame for inactive functions (not modified or invoked for over 2 years)
    print(f"\n{'='*60}")
    print(f"Identifying inactive Lambda functions (not modified or invoked for over 2 years)...")
    
    # Calculate the date 2 years ago from today
    two_years_ago = (datetime.now() - timedelta(days=730)).strftime("%Y-%m-%d")
    
    # Function to check if a date string is older than 2 years
    def is_older_than_two_years(date_str):
        if not date_str or date_str in ["No recent invocations", "Error retrieving logs"]:
            return True  # Consider as old if no invocation data
        try:
            # Handle different date formats
            if 'T' in date_str:
                # ISO format like '2021-11-15T14:30:00.000+0000'
                date_part = date_str.split('T')[0]
            else:
                # Format like '2021-11-15 14:30:00'
                date_part = date_str.split(' ')[0]
            return date_part < two_years_ago
        except Exception:
            return False
    
    # Filter functions that haven't been modified or invoked for over 2 years
    inactive_df = final_df[
        final_df['LastModified'].apply(is_older_than_two_years) & 
        final_df['LastInvocationTime'].apply(is_older_than_two_years)
    ].copy()
    
    print(f"Found {len(inactive_df)} Lambda functions that haven't been modified or invoked for over 2 years")
    
    # Save to a single Excel file with timestamp
    from datetime import datetime
    
    print(f"\n{'='*60}")
    print(f"Saving results to Excel file...")
    timestamp = datetime.now().strftime("%Y_%m_%d_%H%M%S")
    filename = f"lambda_function_details_{timestamp}.xlsx"
    
    with pd.ExcelWriter(filename) as writer:
        final_df.to_excel(writer, sheet_name='All Functions', index=False)
        inactive_df.to_excel(writer, sheet_name='Inactive Functions (2+ years)', index=False)
    
    print(f"✓ All Lambda function details saved to {filename}")
    print(f"✓ Sheet 1: All Functions ({len(final_df)} records)")
    print(f"✓ Sheet 2: Inactive Functions ({len(inactive_df)} records)")
    print(f"{'='*60}")
    print(f"SCRIPT COMPLETED AT {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
