import io
import streamlit as st
import boto3
from langchain_aws import BedrockEmbeddings, BedrockLLM
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain.document_loaders import PyPDFLoader

# --- AWS Configuration ---
AWS_REGION = "us-east-1"  # Replace with your AWS region
S3_BUCKET_NAME = "iotanlyticsdatastreaming"  # Replace with your S3 bucket name
BEDROCK_MODEL_ID = "amazon.titan-embed-text-v1"  # Choose your embedding model

# --- Initialize Bedrock clients ---
bedrock_client = boto3.client("bedrock-runtime", region_name=AWS_REGION)
embeddings = BedrockEmbeddings(client=bedrock_client, model_id=BEDROCK_MODEL_ID)
llm = BedrockLLM(client=bedrock_client, model_id="amazon.titan-text-express-v1") 

# --- Function to load and process PDFs from S3 ---
def load_docs_from_s3(bucket_name, s3_client):
    docs = []
    for obj in s3_client.list_objects_v2(Bucket=bucket_name)["Contents"]:
        if obj["Key"].endswith(".pdf"):
            # Generate presigned URL
            url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket_name, 'Key': obj["Key"]},
                ExpiresIn=3600  # URL expires in 1 hour
            )

            loader = PyPDFLoader(url)
            loaded_docs = loader.load()

            # Add the S3 object key to the metadata
            for doc in loaded_docs:
                doc.metadata["source"] = obj["Key"]
            docs.extend(loaded_docs)
            
    return docs

# --- Streamlit App ---
st.title("PDF Q&A with AWS Bedrock")

# Load PDFs from S3
s3_client = boto3.client("s3")
docs = load_docs_from_s3(S3_BUCKET_NAME, s3_client)

# Create FAISS index
if "faiss_index" not in st.session_state:
    # Check if docs is empty to prevent the error
    if docs:
        st.session_state.faiss_index = FAISS.from_documents(docs, embeddings)
    else:
        st.error("No PDFs found in the S3 bucket. Please check your configuration.")

# User query
query = st.text_input("Ask a question about your PDFs:")
if query:
    # Check if the index exists before running the query
    if "faiss_index" in st.session_state:
        qa_chain = RetrievalQA.from_chain_type(
            llm=llm, chain_type="stuff", 
            retriever=st.session_state.faiss_index.as_retriever()
        )
        response = qa_chain.run(query)

        st.write(response)

        relevant_docs = st.session_state.faiss_index.similarity_search(query)
        st.write("**Relevant Sources:**")
        for doc in relevant_docs:
            pdf_url = f"https://{S3_BUCKET_NAME}.s3.amazonaws.com/{doc.metadata['source']}"
            st.markdown(f"- [{doc.metadata['source']}]({pdf_url})")
    else:
        st.error("FAISS index not created. Please check if PDFs were loaded correctly.")