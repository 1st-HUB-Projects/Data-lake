import io
import streamlit as st
import boto3
from langchain_aws import BedrockEmbeddings, BedrockLLM
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
from langchain.document_loaders import PyPDFLoader

# --- AWS Configuration ---
s3 = boto3.client('s3')
bucket_name = 'iotanlyticsdatastreaming' 
llm = BedrockLLM(model_id="amazon.titan-text-generate-v1")
embeddings = BedrockEmbeddings(model_id="amazon.titan-embed-text-v1")

# --- Function to load and process PDFs from S3 ---
def load_pdfs_from_s3(bucket_name):
    pdf_docs = []
    try:
        # List objects (PDFs) in the bucket
        objects = s3.list_objects_v2(Bucket=bucket_name)
        for obj in objects['Contents']:
            if obj['Key'].endswith('.pdf'):
                # Download PDF from S3
                file_obj = io.BytesIO()
                s3.download_fileobj(bucket_name, obj['Key'], file_obj)
                file_obj.seek(0)  # Reset file pointer to the beginning

                # Load and process the PDF
                pdf_loader = PyPDFLoader(file_obj)
                pdf_docs.extend(pdf_loader.load()) 
    except Exception as e:
        st.error(f"Error loading PDFs from S3: {e}")
        return None
    return pdf_docs

# --- Streamlit UI ---
st.title("Arabic PDF Query with AWS Bedrock")

# --- Load PDFs from S3 ---
documents = load_pdfs_from_s3(bucket_name)

if documents:
    # --- Embedding and Storage ---
    docsearch = FAISS.from_documents(documents, embeddings)

    # --- Query Handling ---
    query = st.text_input("Enter your query in Arabic:")
    if query:
        docs = docsearch.similarity_search(query)
        chain = RetrievalQA.from_chain_type(llm=llm, chain_type="stuff", retriever=docsearch.as_retriever())
        response = chain.run(query)
        st.write(response)
else:
    st.warning("No PDFs found in the S3 bucket.")