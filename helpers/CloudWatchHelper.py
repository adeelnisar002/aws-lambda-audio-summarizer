"""
Helper class for CloudWatch logging operations.
"""

import boto3
from botocore.exceptions import ClientError


class CloudWatch_Helper:
    """Helper class for CloudWatch operations."""
    
    def __init__(self, region_name='us-west-2'):
        self.logs_client = boto3.client('logs', region_name=region_name)
    
    def create_log_group(self, log_group_name):
        """
        Create a CloudWatch log group.
        
        Args:
            log_group_name: Name of the log group
        """
        try:
            self.logs_client.create_log_group(logGroupName=log_group_name)
            print(f"Log group '{log_group_name}' created successfully.")
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceAlreadyExistsException':
                print(f"Log group '{log_group_name}' already exists.")
            else:
                print(f"Error creating log group: {e}")
                raise
    
    def print_recent_logs(self, log_group_name, limit=10):
        """
        Print recent log events from a log group.
        
        Args:
            log_group_name: Name of the log group
            limit: Maximum number of log streams to check
        """
        try:
            # Get recent log streams
            response = self.logs_client.describe_log_streams(
                logGroupName=log_group_name,
                orderBy='LastEventTime',
                descending=True,
                limit=limit
            )
            
            if not response.get('logStreams'):
                print("No log streams found in the log group.")
                print("Permissions are correctly set for Amazon Bedrock logs.")
                print("-" * 80)
                return
            
            print("Recent logs:")
            print("-" * 80)
            
            for stream in response['logStreams']:
                stream_name = stream['logStreamName']
                print(f"\nLog Stream: {stream_name}")
                
                # Get log events
                events_response = self.logs_client.get_log_events(
                    logGroupName=log_group_name,
                    logStreamName=stream_name,
                    limit=5
                )
                
                for event in events_response.get('events', []):
                    timestamp = event['timestamp']
                    message = event['message']
                    print(f"  [{timestamp}] {message}")
            
            print("-" * 80)
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                print(f"Log group '{log_group_name}' not found.")
            else:
                print(f"Error retrieving logs: {e}")
                raise

