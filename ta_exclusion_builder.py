#!/usr/bin/env python3
"""
ta_exclusion_builder.py - Build AWS CLI commands for Trusted Advisor recommendation exclusions

This script helps build (but does not execute) AWS CLI commands to exclude specific resources
from Trusted Advisor recommendations. It searches for recommendations by keyword, then filters
resources by a matching string, and generates the appropriate exclusion command.
"""

import argparse
import json
import subprocess
import sys
import re
import shutil
from typing import List, Dict, Any, Optional, Tuple

# Default region
DEFAULT_REGION = "ap-southeast-2"

# Try to import colorama for colored output
try:
    from colorama import init, Fore, Style
    init()
    HAS_COLOR = True
except ImportError:
    HAS_COLOR = False


def colorize(text: str, color_code: str) -> str:
    """Apply color to text if colorama is available."""
    if HAS_COLOR:
        return f"{color_code}{text}{Style.RESET_ALL}"
    return text


def error(msg: str) -> None:
    """Print error message and exit."""
    print(colorize(f"ERROR: {msg}", Fore.RED if HAS_COLOR else ""))
    sys.exit(1)


def success(msg: str) -> None:
    """Print success message."""
    print(colorize(msg, Fore.GREEN if HAS_COLOR else ""))


def info(msg: str) -> None:
    """Print info message."""
    print(colorize(msg, Fore.CYAN if HAS_COLOR else ""))


def warning(msg: str) -> None:
    """Print warning message."""
    print(colorize(msg, Fore.YELLOW if HAS_COLOR else ""))


def check_jq_availability() -> bool:
    """Check if jq is available in the system."""
    # We don't actually need jq since we're using Python's json module
    return True


def run_aws_command(cmd: List[str], profile: str, region: str) -> Tuple[bool, Any]:
    """Run AWS CLI command and return parsed JSON output."""
    # Add no-verify-ssl to disable SSL verification
    full_cmd = ["aws"] + cmd + ["--profile", profile, "--region", region, "--no-verify-ssl"]
    
    try:
        result = subprocess.run(full_cmd, capture_output=True, text=True, check=False)
        
        if result.returncode != 0:
            error_msg = result.stderr.strip() or "Unknown error"
            return False, error_msg
        
        try:
            return True, json.loads(result.stdout)
        except json.JSONDecodeError:
            return False, "Failed to parse JSON output from AWS CLI"
    
    except subprocess.SubprocessError as e:
        return False, f"Failed to execute AWS CLI command: {str(e)}"


def list_recommendations(profile: str, region: str, check_keyword: str) -> List[Dict[str, Any]]:
    """List Trusted Advisor recommendations matching the keyword."""
    success, result = run_aws_command(["trustedadvisor", "list-recommendations"], profile, region)
    
    if not success:
        error(f"Failed to list recommendations: {result}")
    
    matching_recommendations = []
    
    # The actual key is 'recommendationSummaries' not 'recommendations'
    for rec in result.get("recommendationSummaries", []):
        if check_keyword.lower() in rec.get("name", "").lower():
            matching_recommendations.append(rec)
    
    return matching_recommendations


def select_recommendation(recommendations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Let user select a recommendation from the list."""
    if not recommendations:
        error("No recommendations found matching the keyword.")
    
    if len(recommendations) == 1:
        rec = recommendations[0]
        success(f"Found recommendation: {rec['name']} (ID: {rec['id']})")
        return rec
    
    print("\nMultiple matching recommendations found:")
    for i, rec in enumerate(recommendations, 1):
        print(f"{i}. {rec['name']} (ID: {rec['id']})")
    
    while True:
        try:
            choice = int(input("\nSelect a recommendation (number): "))
            if 1 <= choice <= len(recommendations):
                return recommendations[choice - 1]
            warning("Invalid choice. Please try again.")
        except ValueError:
            warning("Please enter a number.")


def list_recommendation_resources(profile: str, region: str, recommendation: Dict[str, Any], resource_match: str) -> List[Dict[str, Any]]:
    """List resources for a recommendation that match the resource filter."""
    # The ARN is already provided in the recommendation
    rec_arn = recommendation["arn"]
    
    success, result = run_aws_command(
        ["trustedadvisor", "list-recommendation-resources", 
         "--recommendation-identifier", rec_arn],
        profile, region
    )
    
    if not success:
        error(f"Failed to list recommendation resources: {result}")
    
    matching_resources = []
    
    # The actual key is 'recommendationResourceSummaries' not 'resources'
    for resource in result.get("recommendationResourceSummaries", []):
        resource_id = resource.get("awsResourceId", "")
        resource_arn = resource.get("arn", "")
        
        # If resource_match is empty, include all resources
        # Otherwise, check if resource_match is in either resourceId or ARN
        if not resource_match or (resource_match.lower() in resource_id.lower() or 
                                resource_match.lower() in resource_arn.lower()):
            matching_resources.append(resource)
    
    return matching_resources


def build_exclusion_json(resources: List[Dict[str, Any]]) -> str:
    """Build JSON for resource exclusions."""
    exclusions = []
    
    for resource in resources:
        exclusions.append({
            "arn": resource["arn"],
            "isExcluded": True
        })
    
    return json.dumps(exclusions)


def build_cli_command(profile: str, region: str, exclusions_json: str) -> str:
    """Build the final AWS CLI command for batch exclusion update."""
    return (f"aws trustedadvisor batch-update-recommendation-resource-exclusion "
            f"--recommendation-resource-exclusions '{exclusions_json}' "
            f"--region {region} ")


def main() -> None:
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Build AWS CLI commands for Trusted Advisor recommendation exclusions"
    )
    
    parser.add_argument("--profile", type=str, help="AWS CLI profile name")
    parser.add_argument("--check-keyword", type=str, help="Substring to search in recommendation name")
    parser.add_argument("--resource-match", type=str, help="Substring to match in resourceId or ARN")
    parser.add_argument("--region", type=str, default=DEFAULT_REGION, 
                        help=f"AWS region (default: {DEFAULT_REGION})")
    parser.add_argument("--no-verify-ssl", action="store_true", default=True,
                        help="Disable SSL certificate verification (default: enabled)")
    
    args = parser.parse_args()
    
    # We don't need jq anymore
    pass
    
    # Get profile if not provided
    profile = args.profile
    if not profile:
        profile = input("Enter AWS CLI profile name: ")
    
    # Get check keyword if not provided
    check_keyword = args.check_keyword
    if not check_keyword:
        check_keyword = input("Enter substring to search in recommendation name: ")
    
    # Get resource match if not provided
    resource_match = args.resource_match
    if not resource_match:
        all_resources = input("Do you want to exclude all resources? (y/n): ").lower().strip() == 'y'
        if all_resources:
            resource_match = ""  # Empty string will match all resources
        else:
            resource_match = input("Enter substring to match in resourceId or ARN: ")
    
    # Get region
    region = args.region
    
    # List and select recommendation
    info(f"Searching for recommendations containing '{check_keyword}'...")
    recommendations = list_recommendations(profile, region, check_keyword)
    recommendation = select_recommendation(recommendations)
    
    # List matching resources
    if resource_match:
        info(f"Searching for resources containing '{resource_match}'...")
    else:
        info("Searching for all resources...")
    resources = list_recommendation_resources(profile, region, recommendation, resource_match)
    
    if not resources:
        error(f"No resources found matching '{resource_match}'")
    
    # Display matched resources
    print(f"\nFound {len(resources)} matching resources:")
    for i, resource in enumerate(resources, 1):
        resource_id = resource.get("awsResourceId", "N/A")
        resource_arn = resource.get("arn", "N/A")
        print(f"{i}. ID: {resource_id}")
        print(f"   ARN: {resource_arn}")
    
    # Build exclusion JSON
    exclusions_json = build_exclusion_json(resources)
    
    # Build final CLI command
    cli_command = build_cli_command(profile, region, exclusions_json)
    
    # Print summary and command
    print("\n" + "=" * 80)
    success("COMMAND READY (copy and paste to execute):")
    print("-" * 80)
    print(cli_command)
    print("-" * 80)
    
    # Print summary
    info(f"Summary:")
    print(f"- Recommendation: {recommendation['name']}")
    print(f"- Recommendation ID: {recommendation['id']}")
    print(f"- Resources to exclude: {len(resources)}")
    print(f"- Profile: {profile}")
    print(f"- Region: {region}")
    print("=" * 80)
    
    success("Command built successfully. Copy and paste it to execute.")


if __name__ == "__main__":
    main()

# No external requirements needed beyond standard library
# Optional: colorama for colored output