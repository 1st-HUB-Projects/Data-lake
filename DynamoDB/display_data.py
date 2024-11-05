# display_data.py
import streamlit as st
import boto3
import pandas as pd
from PIL import Image
import requests
from io import BytesIO

# AWS Configurations
DYNAMODB_TABLE_NAME = "UpDoc"

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(DYNAMODB_TABLE_NAME)

def display_data():
    st.header("Display Data")
    
    # Fetch all items from DynamoDB table
    try:
        response = table.scan()
        items = response.get('Items', [])

        if items:
            df = pd.DataFrame(items)
            
            # Filter functionality
            filter_name = st.text_input("Filter by Name")
            filter_location = st.text_input("Filter by Location")

            if filter_name:
                df = df[df['name'].str.contains(filter_name, case=False, na=False)]
            if filter_location:
                df = df[df['location'].str.contains(filter_location, case=False, na=False)]

            # Make the presigned URL clickable in the table
            if 'url' in df.columns:
                def create_link(row):
                    if any(row['url'].lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".gif"]):
                        return f'<a href="{row["url"]}" target="_self">Open Image</a>'
                    else:
                        return f'<a href="{row["url"]}" target="_blank">Open Link</a>'
                df['url'] = df.apply(create_link, axis=1)

            st.write(df.to_html(escape=False), unsafe_allow_html=True)

            # Display the selected image below the table
            for index, row in df.iterrows():
                if any(row['url'].lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".gif"]):
                    if st.button(f"Display Image {index+1}"):
                        response = requests.get(row['url'])
                        img = Image.open(BytesIO(response.content))
                        st.image(img, caption=f"Image from {row['name']}", use_column_width=True)

        else:
            st.write("No data available.")
    except Exception as e:
        st.error(f"Could not fetch data from DynamoDB: {e}")
