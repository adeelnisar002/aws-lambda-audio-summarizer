"""
Helper class for S3 operations.
"""

import os
import boto3
from datetime import datetime
from botocore.exceptions import ClientError


class S3_Helper:
    """Helper class for S3 operations."""
    
    def __init__(self, region_name='us-west-2'):
        self.s3_client = boto3.client('s3', region_name=region_name)
    
    def upload_file(self, bucket_name, file_path, s3_key=None):
        """
        Upload a file to S3.
        
        Args:
            bucket_name: Name of the S3 bucket
            file_path: Local file path to upload
            s3_key: S3 object key (defaults to filename)
        """
        if s3_key is None:
            s3_key = os.path.basename(file_path)
        
        try:
            self.s3_client.upload_file(file_path, bucket_name, s3_key)
            print(f"Object '{s3_key}' uploaded to bucket '{bucket_name}'")
        except ClientError as e:
            print(f"Error uploading file: {e}")
            raise
    
    def download_object(self, bucket_name, s3_key, local_path=None):
        """
        Download an object from S3.
        
        Args:
            bucket_name: Name of the S3 bucket
            s3_key: S3 object key
            local_path: Local file path (defaults to s3_key)
        """
        if local_path is None:
            local_path = s3_key
        
        try:
            self.s3_client.download_file(bucket_name, s3_key, local_path)
            print(f"Object '{s3_key}' from bucket '{bucket_name}' to '{local_path}'")
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                print(f"Error: An error occurred (404) when calling the HeadObject operation: Not Found")
            else:
                print(f"Error downloading object: {e}")
            raise
    
    def list_objects(self, bucket_name, prefix=''):
        """
        List objects in an S3 bucket.
        
        Args:
            bucket_name: Name of the S3 bucket
            prefix: Optional prefix to filter objects
        """
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=bucket_name,
                Prefix=prefix
            )
            
            if 'Contents' in response:
                for obj in response['Contents']:
                    # Skip directory markers
                    if not obj['Key'].endswith('/'):
                        last_modified = obj['LastModified']
                        print(f"Object: {obj['Key']}, Created on: {last_modified}")
            else:
                print(f"No objects found in bucket '{bucket_name}' with prefix '{prefix}'")
                
        except ClientError as e:
            print(f"Error listing objects: {e}")
            raise
    
    def get_object(self, bucket_name, s3_key):
        """
        Get an object from S3.
        
        Args:
            bucket_name: Name of the S3 bucket
            s3_key: S3 object key
            
        Returns:
            dict: S3 object response
        """
        try:
            response = self.s3_client.get_object(Bucket=bucket_name, Key=s3_key)
            return response
        except ClientError as e:
            print(f"Error getting object: {e}")
            raise
    
    def put_object(self, bucket_name, s3_key, body, content_type='text/plain'):
        """
        Put an object to S3.
        
        Args:
            bucket_name: Name of the S3 bucket
            s3_key: S3 object key
            body: Object body (string or bytes)
            content_type: Content type of the object
        """
        try:
            self.s3_client.put_object(
                Bucket=bucket_name,
                Key=s3_key,
                Body=body,
                ContentType=content_type
            )
            print(f"Object '{s3_key}' uploaded to bucket '{bucket_name}'")
        except ClientError as e:
            print(f"Error putting object: {e}")
            raise

