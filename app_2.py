import io
import time
import streamlit as st
import boto3
from langchain_aws import BedrockEmbeddings, BedrockLLM
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain_community.document_loaders import PyPDFLoader

# --- AWS Configuration ---
AWS_REGION = "us-east-1"  # Replace with your actual AWS region
S3_BUCKET_NAME = "iotanlyticsdatastreaming"  # Replace with your actual S3 bucket name
BEDROCK_MODEL_ID = "amazon.titan-embed-text-v1"  # Choose your embedding model

# --- Initialize Bedrock clients ---
bedrock_client = boto3.client("bedrock-runtime", region_name=AWS_REGION)
embeddings = BedrockEmbeddings(client=bedrock_client, model_id=BEDROCK_MODEL_ID)

try:
    llm = BedrockLLM(client=bedrock_client, model_id="amazon.titan-text-express-v1")
except Exception as e:
    st.error(f"Error initializing BedrockLLM: {e}")

# --- Function to load and process PDFs from S3 ---
def load_docs_from_s3(bucket_name, s3_client):
    docs = []
    try:
        for obj in s3_client.list_objects_v2(Bucket=bucket_name)["Contents"]:
            if obj["Key"].endswith(".pdf"):
                # Generate presigned URL
                url = s3_client.generate_presigned_url(
                    ClientMethod='get_object',
                    Params={'Bucket': bucket_name, 'Key': obj["Key"]},
                    ExpiresIn=3600
                )

                loader = PyPDFLoader(url)
                loaded_docs = loader.load()

                # Filter out empty documents
                loaded_docs = [doc for doc in loaded_docs if doc.page_content]

                for doc in loaded_docs:
                    doc.metadata["source"] = obj["Key"]
                docs.extend(loaded_docs)
    except Exception as e:
        st.error(f"Error loading documents from S3: {e}")
    return docs

# --- Streamlit App ---
st.title("PDF Q&A with AWS Bedrock")

# Load PDFs from S3
s3_client = boto3.client("s3")
docs = load_docs_from_s3(S3_BUCKET_NAME, s3_client)

# Create FAISS index
if "faiss_index" not in st.session_state:
    if docs:
        st.session_state.faiss_index = FAISS.from_documents(docs, embeddings)
    else:
        st.error("No PDFs found in the S3 bucket.")

# User query
query = st.text_input("Ask a question about your PDFs:")
if query:
    if "faiss_index" in st.session_state:
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm, chain_type="stuff",
            retriever=st.session_state.faiss_index.as_retriever()
        )
        try:
            response = qa_chain.run(query)
            st.write(response)
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == 'ThrottlingException':
                retry_delay = 1  # Start with a 1-second delay
                for i in range(10):  # Retry up to 10 times (increased retries)
                    time.sleep(retry_delay)
                    try:
                        response = qa_chain.run(query)
                        st.write(response)
                        break  # Exit the loop if successful
                    except botocore.exceptions.ClientError as e:
                        if e.response['Error']['Code'] == 'ThrottlingException':
                            retry_delay *= 2  # Double the delay on each retry
                            st.warning(f"ThrottlingException: Retrying in {retry_delay} seconds...")
                        else:
                            st.error(f"Error generating response: {e}")
                            break  # Exit the loop if it's a different error
            else:
                st.error(f"Error generating response: {e}")

        relevant_docs = st.session_state.faiss_index.similarity_search(query)

        # Store presigned URLs and seen documents
        presigned_urls = {}
        seen_docs = set()

        st.write("**Relevant Sources:**")
        for doc in relevant_docs:
            source = doc.metadata['source']
            if source not in seen_docs:  # Check if document has been seen
                seen_docs.add(source)
                if source not in presigned_urls:
                    presigned_urls[source] = s3_client.generate_presigned_url(
                        ClientMethod='get_object',
                        Params={'Bucket': S3_BUCKET_NAME, 'Key': source},
                        ExpiresIn=3600
                    )
                pdf_url = presigned_urls[source]
                st.markdown(f"- [{source}]({pdf_url})")
    else:
        st.error("FAISS index not created.")