# menu.py
import streamlit as st
from upload_doc import upload_doc
from display_data import display_data

def main():
    st.sidebar.title("Menu")
    option = st.sidebar.radio("Select an option:", ("Upload Doc", "Display Data"))
    
    if option == "Upload Doc":
        upload_doc()
    elif option == "Display Data":
        display_data()

if __name__ == "__main__":
    main()
