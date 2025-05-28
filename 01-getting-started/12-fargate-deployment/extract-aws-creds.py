#!/usr/bin/env python3
"""
AWS Credentials Extractor

This script extracts AWS credentials from the awsume cache directory
(created by 'awsume team' or similar tools) and populates a .env file
for local development. Falls back to AWS CLI cache if awsume cache is not found.

Usage:
    python extract-aws-creds.py
    python extract-aws-creds.py --output custom.env
    python extract-aws-creds.py --bucket my-agent-bucket
"""

import json
import os
import glob
import argparse
from datetime import datetime, timezone
from pathlib import Path


def find_aws_cache_dir():
    """Find the awsume cache directory."""
    cache_dir = Path.home() / ".awsume" / "cache"
    if not cache_dir.exists():
        # Fallback to AWS CLI cache if awsume cache doesn't exist
        fallback_cache_dir = Path.home() / ".aws" / "cli" / "cache"
        if fallback_cache_dir.exists():
            print("⚠️  Awsume cache not found, using AWS CLI cache as fallback")
            return fallback_cache_dir
        raise FileNotFoundError(f"Neither awsume cache ({cache_dir}) nor AWS CLI cache ({fallback_cache_dir}) found")
    return cache_dir


def get_latest_valid_credentials(cache_dir):
    """
    Find the most recent valid (non-expired) credential cache file.
    
    Returns:
        dict: The credentials from the latest valid cache file
        
    Raises:
        FileNotFoundError: If no valid credential files are found
        ValueError: If all credential files are expired
    """
    # Check if this is awsume cache or AWS CLI cache
    is_awsume_cache = cache_dir.name == "cache" and cache_dir.parent.name == ".awsume"
    
    if is_awsume_cache:
        # Awsume cache files are named like "aws-credentials-AKIXXXXX"
        cache_files = list(cache_dir.glob("aws-credentials-*"))
    else:
        # AWS CLI cache files are JSON files
        cache_files = list(cache_dir.glob("*.json"))
    
    if not cache_files:
        cache_type = "awsume" if is_awsume_cache else "AWS CLI"
        raise FileNotFoundError(f"No credential cache files found in {cache_type} cache")
    
    valid_credentials = []
    current_time = datetime.now(timezone.utc)
    
    for cache_file in cache_files:
        try:
            with open(cache_file, 'r') as f:
                data = json.load(f)
            
            # Handle different cache formats
            if is_awsume_cache:
                # Awsume format: direct credential fields
                if all(key in data for key in ['AccessKeyId', 'SecretAccessKey', 'Expiration']):
                    expiration_str = data.get('Expiration')
                    if expiration_str:
                        # Parse expiration time (awsume format: "2025-05-25 01:59:28")
                        try:
                            expiration = datetime.strptime(expiration_str, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
                        except ValueError:
                            # Try ISO format as fallback
                            expiration = datetime.fromisoformat(expiration_str.replace('Z', '+00:00'))
                        
                        if expiration > current_time:
                            # Add file modification time for sorting
                            mod_time = cache_file.stat().st_mtime
                            valid_credentials.append((mod_time, data, cache_file))
                            print(f"✓ Found valid awsume credentials in {cache_file.name} (expires: {expiration})")
                        else:
                            print(f"✗ Expired awsume credentials in {cache_file.name} (expired: {expiration})")
            else:
                # AWS CLI format: nested under 'Credentials'
                if 'Credentials' in data:
                    creds = data['Credentials']
                    expiration_str = creds.get('Expiration')
                    
                    if expiration_str:
                        # Parse expiration time (AWS CLI format: ISO with timezone)
                        expiration = datetime.fromisoformat(expiration_str.replace('Z', '+00:00'))
                        
                        if expiration > current_time:
                            # Add file modification time for sorting
                            mod_time = cache_file.stat().st_mtime
                            valid_credentials.append((mod_time, data, cache_file))
                            print(f"✓ Found valid AWS CLI credentials in {cache_file.name} (expires: {expiration})")
                        else:
                            print(f"✗ Expired AWS CLI credentials in {cache_file.name} (expired: {expiration})")
                        
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            print(f"✗ Error reading {cache_file.name}: {e}")
            continue
    
    if not valid_credentials:
        raise ValueError("No valid (non-expired) credentials found in cache")
    
    # Sort by modification time (most recent first) and return the latest
    valid_credentials.sort(key=lambda x: x[0], reverse=True)
    latest_mod_time, latest_data, latest_file = valid_credentials[0]
    
    cache_type = "awsume" if is_awsume_cache else "AWS CLI"
    print(f"✓ Using {cache_type} credentials from {latest_file.name}")
    return latest_data, is_awsume_cache


def extract_credentials(credentials_data, is_awsume_cache=False):
    """
    Extract AWS credentials from the cache file data.
    
    Args:
        credentials_data (dict): The loaded JSON data from cache file
        is_awsume_cache (bool): Whether this is from awsume cache or AWS CLI cache
        
    Returns:
        dict: Extracted credentials
    """
    if is_awsume_cache:
        # Awsume format: direct credential fields
        return {
            'AWS_ACCESS_KEY_ID': credentials_data['AccessKeyId'],
            'AWS_SECRET_ACCESS_KEY': credentials_data['SecretAccessKey'],
            'AWS_SESSION_TOKEN': credentials_data.get('SessionToken', ''),
            'AWS_DEFAULT_REGION': credentials_data.get('Region', 'ap-southeast-2')
        }
    else:
        # AWS CLI format: nested under 'Credentials'
        creds = credentials_data['Credentials']
        return {
            'AWS_ACCESS_KEY_ID': creds['AccessKeyId'],
            'AWS_SECRET_ACCESS_KEY': creds['SecretAccessKey'],
            'AWS_SESSION_TOKEN': creds['SessionToken'],
            'AWS_DEFAULT_REGION': 'ap-southeast-2'  # Default region for AWS CLI cache
        }


def get_existing_env_values(env_file):
    """
    Parse existing .env file and return its values.
    
    Args:
        env_file (Path): Path to the .env file
        
    Returns:
        dict: Existing environment variables
    """
    env_vars = {}
    
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    
    return env_vars


def write_env_file(env_file, credentials, bucket_name=None, preserve_existing=True):
    """
    Write credentials to .env file.
    
    Args:
        env_file (Path): Path to the .env file
        credentials (dict): AWS credentials to write
        bucket_name (str, optional): Agent bucket name
        preserve_existing (bool): Whether to preserve existing non-AWS values
    """
    env_vars = {}
    
    # Load existing values if preserving
    if preserve_existing:
        env_vars = get_existing_env_values(env_file)
    
    # Update with new credentials
    env_vars.update(credentials)
    
    # Set bucket name if provided
    if bucket_name:
        env_vars['AGENT_BUCKET'] = bucket_name
    elif 'AGENT_BUCKET' not in env_vars:
        env_vars['AGENT_BUCKET'] = 'your-agent-bucket-name'
    
    # Write the file
    with open(env_file, 'w') as f:
        f.write("# Local Development Environment Variables\n")
        f.write("# Auto-generated from AWS credential cache\n")
        f.write(f"# Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("# AWS Configuration\n")
        for key in ['AGENT_BUCKET', 'AWS_ACCESS_KEY_ID', 'AWS_SECRET_ACCESS_KEY', 'AWS_SESSION_TOKEN', 'AWS_DEFAULT_REGION', 'KNOWLEDGE_BASE_ID', 'GUARDRAIL_ID', 'GUARDRAIL_VERSION']:
            if key in env_vars:
                f.write(f"{key}={env_vars[key]}\n")
        
        f.write("\n# Optional: Set to production for less verbose logging\n")
        f.write("# PYTHONUNBUFFERED=0\n")
        
        # Add any other existing variables
        other_vars = {k: v for k, v in env_vars.items() if not k.startswith('AWS_') and k != 'AGENT_BUCKET'}
        if other_vars:
            f.write("\n# Other Configuration\n")
            for key, value in other_vars.items():
                f.write(f"{key}={value}\n")


def main():
    parser = argparse.ArgumentParser(description='Extract AWS credentials from CLI cache to .env file')
    parser.add_argument('--output', '-o', default='.env', 
                        help='Output .env file path (default: .env)')
    parser.add_argument('--bucket', '-b', 
                        help='Agent bucket name to use')
    parser.add_argument('--no-preserve', action='store_true',
                        help='Do not preserve existing non-AWS environment variables')
    
    args = parser.parse_args()
    
    try:
        print("🔍 Searching for AWS credentials in cache...")
        
        # Find cache directory (awsume first, then AWS CLI fallback)
        cache_dir = find_aws_cache_dir()
        cache_type = "awsume" if cache_dir.name == "cache" and cache_dir.parent.name == ".awsume" else "AWS CLI"
        print(f"📁 Using {cache_type} cache directory: {cache_dir}")
        
        # Get latest valid credentials
        credentials_data, is_awsume_cache = get_latest_valid_credentials(cache_dir)
        
        # Extract credentials
        credentials = extract_credentials(credentials_data, is_awsume_cache)
        print(f"🔑 Extracted credentials for Access Key: {credentials['AWS_ACCESS_KEY_ID']}")
        
        # Write to .env file
        env_file = Path(args.output)
        write_env_file(env_file, credentials, args.bucket, not args.no_preserve)
        
        print(f"✅ Successfully wrote credentials to {env_file}")
        print(f"🚀 You can now run: docker compose -f docker-compose.dev.yml up")
        
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        print("💡 Make sure you have run 'awsume team' or similar to populate credential cache")
        exit(1)
        
    except ValueError as e:
        print(f"❌ Error: {e}")
        print("💡 Try running 'awsume team' to refresh your credentials")
        exit(1)
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        exit(1)


if __name__ == "__main__":
    main()