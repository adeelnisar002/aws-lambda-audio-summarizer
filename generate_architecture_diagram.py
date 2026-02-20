"""
Generate AWS Architecture Diagram for Serverless LLM Pipeline
Requires: pip install diagrams
"""

from diagrams import Diagram, Cluster, Edge
from diagrams.aws.general import User
from diagrams.aws.storage import S3
from diagrams.aws.compute import Lambda
from diagrams.aws.ml import Transcribe, Bedrock
from diagrams.aws.management import CloudwatchLogs

with Diagram("Serverless LLM Audio Transcription & Summarization", 
             show=True, 
             direction="LR",
             filename="serverless-llm-architecture",
             outformat="png"):
    
    user = User("User")
    
    with Cluster("Storage Layer"):
        audio_bucket = S3("Audio Bucket\n(MP3 Files)")
        text_bucket = S3("Text Bucket\n(Transcripts & Results)")
    
    with Cluster("Processing Layer"):
        lambda_transcribe = Lambda("Lambda: Transcribe\n(lambda_transcribe.py)")
        lambda_summarize = Lambda("Lambda: Summarize\n(lambda_summarize.py)")
    
    with Cluster("AI Services"):
        transcribe_service = Transcribe("AWS Transcribe\n(Speaker Diarization)")
        bedrock = Bedrock("Amazon Bedrock\n(Nova Lite)")
    
    cloudwatch = CloudwatchLogs("CloudWatch Logs\n(Monitoring)")
    
    # Flow: User uploads audio
    user >> Edge(label="Upload MP3", color="blue") >> audio_bucket
    
    # Flow: S3 event triggers transcription
    audio_bucket >> Edge(label="S3 Event Trigger", color="green") >> lambda_transcribe
    
    # Flow: Lambda starts transcription job
    lambda_transcribe >> Edge(label="Start Job", color="orange") >> transcribe_service
    
    # Flow: Transcribe outputs transcript
    transcribe_service >> Edge(label="Output JSON", color="purple") >> text_bucket
    
    # Flow: S3 event triggers summarization
    text_bucket >> Edge(label="S3 Event Trigger", color="green") >> lambda_summarize
    
    # Flow: Lambda invokes Bedrock
    lambda_summarize >> Edge(label="Invoke Model", color="red") >> bedrock
    
    # Flow: Bedrock returns summary
    bedrock >> Edge(label="Return Summary", color="red") >> lambda_summarize
    
    # Flow: Lambda saves results
    lambda_summarize >> Edge(label="Save results.txt", color="purple") >> text_bucket
    
    # Flow: Logging to CloudWatch
    lambda_transcribe >> Edge(label="Logs", color="gray", style="dashed") >> cloudwatch
    lambda_summarize >> Edge(label="Logs", color="gray", style="dashed") >> cloudwatch
    bedrock >> Edge(label="Logs", color="gray", style="dashed") >> cloudwatch

print("Diagram generated successfully: serverless-llm-architecture.png")

