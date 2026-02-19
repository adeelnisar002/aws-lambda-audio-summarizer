"""
AWS Lambda function for automatic audio transcription.

This function is triggered when an audio file is uploaded to an S3 bucket.
It automatically starts an AWS Transcribe job to transcribe the audio with
speaker diarization enabled.

Environment Variables:
    S3BUCKETNAMETEXT: S3 bucket name where transcript JSON will be stored

IAM Permissions Required:
    - transcribe:StartTranscriptionJob
    - s3:GetObject (source bucket)
    - s3:PutObject (destination bucket)
"""

import json
import boto3
import uuid
import os

s3_client = boto3.client('s3')
transcribe_client = boto3.client('transcribe', region_name='us-west-2')


def lambda_handler(event, context):
    """
    Lambda handler function triggered by S3 event.
    
    Args:
        event: S3 event containing bucket and object key
        context: Lambda context object
        
    Returns:
        dict: Status code and message
    """
    # Extract the bucket name and key from the incoming event
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']

    # One of a few different checks to ensure we don't end up in a recursive loop.
    # In production, you might want to check file extension or other criteria
    if key != "dialog.mp3": 
        print(f"This demo only works with dialog.mp3. Received: {key}")
        return {
            'statusCode': 200,
            'body': json.dumps(f"Skipping file {key} - not dialog.mp3")
        }

    try:
        # Generate unique job name to avoid conflicts
        job_name = 'transcription-job-' + str(uuid.uuid4())

        # Start transcription job with speaker diarization
        response = transcribe_client.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={'MediaFileUri': f's3://{bucket}/{key}'},
            MediaFormat='mp3',
            LanguageCode='en-US',
            OutputBucketName=os.environ['S3BUCKETNAMETEXT'],  # specify the output bucket
            OutputKey=f'{job_name}-transcript.json',
            Settings={
                'ShowSpeakerLabels': True,
                'MaxSpeakerLabels': 2
            }
        )
        
        print(f"Started transcription job: {job_name} for file: {key}")
        
    except Exception as e:
        print(f"Error occurred: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps(f"Error occurred: {e}")
        }

    return {
        'statusCode': 200,
        'body': json.dumps(f"Submitted transcription job for {key} from bucket {bucket}.")
    }

