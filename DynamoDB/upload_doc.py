


import streamlit as st
import boto3
from botocore.exceptions import NoCredentialsError
import uuid

# AWS Configurations
S3_BUCKET_NAME =  "policy-users-bh"
DYNAMODB_TABLE_NAME = "UpDoc"

# Initialize AWS clients
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(DYNAMODB_TABLE_NAME)

def upload_to_s3(file, bucket, key):
    try:
        s3.upload_fileobj(file, bucket, key)
        return True
    except NoCredentialsError:
        st.error("Credentials not available.")
        return False

def generate_presigned_url(bucket, key):
    try:
        url = s3.generate_presigned_url('get_object',
                                        Params={'Bucket': bucket, 'Key': key},
                                        ExpiresIn=3600)
        return url
    except Exception as e:
        st.error(f"Could not generate presigned URL: {e}")
        return None

def save_to_dynamodb(name, location, description, url):
    try:
        table.put_item(
            Item={
                'id': str(uuid.uuid4()),
                'name': name,
                'location': location,
                'description': description,
                'url': url
            }
        )
        return True
    except Exception as e:
        st.error(f"Could not save to DynamoDB: {e}")
        return False

def upload_doc():
    st.header("Upload Document")
    
    # Form for user inputs
    if 'submit_success' not in st.session_state:
        st.session_state.submit_success = False

    with st.form("upload_form"):
        uploaded_file = st.file_uploader("Choose a file")
        name = st.text_input("Name")
        location = st.text_input("Location")
        description = st.text_area("Brief Description")
        submit_button = st.form_submit_button("Upload")

    if submit_button:
        if uploaded_file is None or name == "" or location == "":
            st.error("Please fill out all fields and upload a file.")
        else:
            # Generate a unique key for the uploaded file
            file_key = f"uploads/{uuid.uuid4()}_{uploaded_file.name}"

            # Upload file to S3
            if upload_to_s3(uploaded_file, S3_BUCKET_NAME, file_key):
                st.success("File successfully uploaded to S3.")

                # Generate a presigned URL for the uploaded file
                presigned_url = generate_presigned_url(S3_BUCKET_NAME, file_key)

                if presigned_url:
                    # Save the entry to DynamoDB
                    if save_to_dynamodb(name, location, description, presigned_url):
                        st.success("Entry successfully saved to DynamoDB.")
                        st.write(f"Access your file here: [Download]({presigned_url})")
                        st.session_state.submit_success = True

    if st.session_state.submit_success:
        st.session_state.submit_success = False