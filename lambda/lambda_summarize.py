"""
AWS Lambda function for automatic transcript summarization.

This function is triggered when a transcript JSON file is uploaded to an S3 bucket.
It extracts the transcript text, generates a prompt using a Jinja2 template,
and uses Amazon Bedrock to generate a summary with sentiment analysis and
issue extraction.

IAM Permissions Required:
    - bedrock:InvokeModel
    - s3:GetObject
    - s3:PutObject
"""

import boto3
import json 
from jinja2 import Template

s3_client = boto3.client('s3')
bedrock_runtime = boto3.client('bedrock-runtime', 'us-west-2')


def lambda_handler(event, context):
    """
    Lambda handler function triggered by S3 event.
    
    Args:
        event: S3 event containing bucket and object key
        context: Lambda context object
        
    Returns:
        dict: Status code and message
    """
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']
    
    # One of a few different checks to ensure we don't end up in a recursive loop.
    if "-transcript.json" not in key: 
        print(f"This demo only works with *-transcript.json files. Received: {key}")
        return {
            'statusCode': 200,
            'body': json.dumps(f"Skipping file {key} - not a transcript JSON file")
        }
    
    try: 
        # Read the transcript JSON file from S3
        response = s3_client.get_object(Bucket=bucket, Key=key)
        file_content = response['Body'].read().decode('utf-8')
        
        # Extract transcript text with speaker labels
        transcript = extract_transcript_from_textract(file_content)

        print(f"Successfully read file {key} from bucket {bucket}.")
        print(f"Transcript length: {len(transcript)} characters")
        
        # Generate summary using Bedrock
        summary = bedrock_summarisation(transcript)
        
        # Save results to S3
        s3_client.put_object(
            Bucket=bucket,
            Key='results.txt',
            Body=summary,
            ContentType='text/plain'
        )
        
        print(f"Summary saved to {bucket}/results.txt")
        
    except Exception as e:
        print(f"Error occurred: {e}")
        import traceback
        traceback.print_exc()
        return {
            'statusCode': 500,
            'body': json.dumps(f"Error occurred: {e}")
        }

    return {
        'statusCode': 200,
        'body': json.dumps(f"Successfully summarized {key} from bucket {bucket}. Summary: {summary}")
    }


def extract_transcript_from_textract(file_content):
    """
    Extract formatted transcript text from Transcribe JSON output.
    
    Args:
        file_content: JSON string from AWS Transcribe
        
    Returns:
        str: Formatted transcript with speaker labels
    """
    transcript_json = json.loads(file_content)

    output_text = ""
    current_speaker = None

    items = transcript_json['results']['items']

    # Iterate through the content word by word:
    for item in items:
        speaker_label = item.get('speaker_label', None)
        content = item['alternatives'][0]['content']
        
        # Start the line with the speaker label:
        if speaker_label is not None and speaker_label != current_speaker:
            current_speaker = speaker_label
            output_text += f"\n{current_speaker}: "
        
        # Add the speech content:
        if item['type'] == 'punctuation':
            output_text = output_text.rstrip()  # Remove the last space
        
        output_text += f"{content} "
        
    return output_text


def bedrock_summarisation(transcript):
    """
    Generate summary using Amazon Bedrock.
    
    Args:
        transcript: Formatted transcript text with speaker labels
        
    Returns:
        str: JSON-formatted summary with sentiment and issues
    """
    # Read prompt template
    # Note: In Lambda, the template file should be included in the deployment package
    with open('prompt_template.txt', "r") as file:
        template_string = file.read()

    # Prepare template data
    data = {
        'transcript': transcript,
        'topics': ['charges', 'location', 'availability']
    }
    
    # Render prompt using Jinja2 template
    template = Template(template_string)
    prompt = template.render(data)
    
    print(f"Generated prompt length: {len(prompt)} characters")
    
    # Invoke Bedrock model
    kwargs = {
        "modelId": "us.amazon.nova-lite-v1:0",
        "contentType": "application/json",
        "accept": "*/*",
        "body": json.dumps(
            {
                "messages": [{"role": "user", "content": [{"text": prompt}]}],
                "inferenceConfig": {
                    "maxTokens": 2048,
                    "temperature": 0,
                    "topP": 0.9
                }
            }
        )
    }
    
    response = bedrock_runtime.invoke_model(**kwargs)

    # Parse response
    response_body = json.loads(response.get('body').read())
    content_list = response_body["output"]["message"]["content"]
    text_block = next((item for item in content_list if "text" in item), None)
    summary = text_block["text"] if text_block else ""
    
    return summary

