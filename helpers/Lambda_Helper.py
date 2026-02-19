"""
Helper class for deploying and managing AWS Lambda functions.
"""

import boto3
import zipfile
import os
import json
from botocore.exceptions import ClientError


class Lambda_Helper:
    """Helper class for Lambda function operations."""
    
    def __init__(self):
        self.lambda_client = boto3.client('lambda', region_name='us-west-2')
        self.iam_client = boto3.client('iam', region_name='us-west-2')
        self.s3_client = boto3.client('s3', region_name='us-west-2')
        self.filter_rules_suffix = None
        self.lambda_environ_variables = {}
        self.deployed_function_name = None
        
    def deploy_function(self, file_list, function_name, role_arn=None, handler=None):
        """
        Deploy a Lambda function from local files.
        
        Args:
            file_list: List of files to include in deployment package
            function_name: Name of the Lambda function
            role_arn: IAM role ARN (optional, will create if not provided)
            handler: Handler function name (default: function_name.lambda_handler)
        """
        print("Zipping function...")
        
        # Create zip file
        zip_filename = f"{function_name}.zip"
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in file_list:
                if os.path.exists(file):
                    zipf.write(file, os.path.basename(file))
                    print(f"  Added {file}")
                else:
                    print(f"  Warning: {file} not found")
        
        # Check if function exists
        print("Looking for existing function...")
        try:
            response = self.lambda_client.get_function(FunctionName=function_name)
            print(f"Function {function_name} exists. Updating...")
            
            # Update function code
            with open(zip_filename, 'rb') as f:
                self.lambda_client.update_function_code(
                    FunctionName=function_name,
                    ZipFile=f.read()
                )
            
            # Update environment variables if provided
            if self.lambda_environ_variables:
                self.lambda_client.update_function_configuration(
                    FunctionName=function_name,
                    Environment={'Variables': self.lambda_environ_variables}
                )
            
            print(f"Function {function_name} updated.")
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceNotFoundException':
                print(f"Function {function_name} does not exist. Creating...")
                
                # Create basic execution role if not provided
                if not role_arn:
                    role_arn = self._create_basic_role(function_name)
                
                # Determine handler
                if not handler:
                    # Try to infer from file_list
                    py_files = [f for f in file_list if f.endswith('.py')]
                    if py_files:
                        handler = f"{os.path.splitext(os.path.basename(py_files[0]))[0]}.lambda_handler"
                    else:
                        handler = f"{function_name}.lambda_handler"
                
                # Create function
                with open(zip_filename, 'rb') as f:
                    response = self.lambda_client.create_function(
                        FunctionName=function_name,
                        Runtime='python3.11',
                        Role=role_arn,
                        Handler=handler,
                        Code={'ZipFile': f.read()},
                        Environment={'Variables': self.lambda_environ_variables} if self.lambda_environ_variables else {},
                        Timeout=300,
                        MemorySize=512
                    )
                
                print(f"Function {function_name} created: {response['FunctionArn']}")
            else:
                raise
        
        self.deployed_function_name = function_name
        
        # Clean up zip file
        if os.path.exists(zip_filename):
            os.remove(zip_filename)
        
        print("Done.")
    
    def add_lambda_trigger(self, bucket_name, function_name=None):
        """
        Add S3 event trigger to Lambda function.
        
        Args:
            bucket_name: S3 bucket name
            function_name: Lambda function name (uses deployed function if not provided)
        """
        if not function_name:
            function_name = self.deployed_function_name
        
        if not function_name:
            raise ValueError("Function name must be provided or set via deploy_function")
        
        print(f"Using function name of deployed function: {function_name}")
        
        # Get function ARN
        func_response = self.lambda_client.get_function(FunctionName=function_name)
        function_arn = func_response['Configuration']['FunctionArn']
        
        # Add permission for S3 to invoke Lambda
        try:
            self.lambda_client.add_permission(
                FunctionName=function_name,
                StatementId='s3-trigger-permission',
                Action='lambda:InvokeFunction',
                Principal='s3.amazonaws.com',
                SourceArn=f'arn:aws:s3:::{bucket_name}'
            )
            print("Permission added with Statement:")
            print(json.dumps({
                "Sid": "s3-trigger-permission",
                "Effect": "Allow",
                "Principal": {"Service": "s3.amazonaws.com"},
                "Action": "lambda:InvokeFunction",
                "Resource": function_arn,
                "Condition": {
                    "ArnLike": {
                        "AWS:SourceArn": f"arn:aws:s3:::{bucket_name}"
                    }
                }
            }, indent=2))
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceConflictException':
                print("Permission already exists.")
            else:
                raise
        
        # Configure S3 event notification
        bucket_config = self.s3_client.get_bucket_notification_configuration(Bucket=bucket_name)
        
        # Prepare Lambda configuration
        lambda_config = {
            'LambdaFunctionArn': function_arn,
            'Events': ['s3:ObjectCreated:*']
        }
        
        # Add filter if suffix is specified
        if self.filter_rules_suffix:
            lambda_config['Filter'] = {
                'Key': {
                    'FilterRules': [
                        {
                            'Name': 'suffix',
                            'Value': self.filter_rules_suffix
                        }
                    ]
                }
            }
        
        # Update notification configuration
        if 'LambdaFunctionConfigurations' not in bucket_config:
            bucket_config['LambdaFunctionConfigurations'] = []
        
        # Check if configuration already exists
        existing = [c for c in bucket_config['LambdaFunctionConfigurations'] 
                   if c['LambdaFunctionArn'] == function_arn]
        
        if not existing:
            bucket_config['LambdaFunctionConfigurations'].append(lambda_config)
            self.s3_client.put_bucket_notification_configuration(
                Bucket=bucket_name,
                NotificationConfiguration=bucket_config
            )
            print(f"Trigger added for {bucket_name} -> {function_name}")
        else:
            print(f"Trigger already exists for {bucket_name} -> {function_name}")
    
    def _create_basic_role(self, function_name):
        """Create a basic IAM role for Lambda execution."""
        role_name = f"{function_name}-execution-role"
        
        trust_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "lambda.amazonaws.com"
                    },
                    "Action": "sts:AssumeRole"
                }
            ]
        }
        
        try:
            response = self.iam_client.create_role(
                RoleName=role_name,
                AssumeRolePolicyDocument=json.dumps(trust_policy),
                Description=f"Execution role for {function_name}"
            )
            role_arn = response['Role']['Arn']
            
            # Attach basic Lambda execution policy
            self.iam_client.attach_role_policy(
                RoleName=role_name,
                PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
            )
            
            print(f"Created IAM role: {role_arn}")
            return role_arn
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'EntityAlreadyExists':
                # Role exists, get its ARN
                response = self.iam_client.get_role(RoleName=role_name)
                return response['Role']['Arn']
            else:
                raise

