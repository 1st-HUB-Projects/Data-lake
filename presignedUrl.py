import boto3

AWS_REGION = "us-east-1"
S3_BUCKET_NAME = "iotanlyticsdatastreaming"
S3_OBJECT_KEY = "industry4_0.pdf"  # Replace with the actual object key

s3_client = boto3.client("s3", region_name=AWS_REGION)

url = s3_client.generate_presigned_url(
    'get_object',
    Params={'Bucket': S3_BUCKET_NAME, 'Key': S3_OBJECT_KEY},
    ExpiresIn=3600
)

print(url)