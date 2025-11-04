import streamlit as st
import pandas as pd
import io
import mysql.connector
from mysql.connector import Error
import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy import text

# Using one of the suggested PDF handling libraries
# from streamlit_pdf_viewer import pdf_viewer 
from PyPDF2 import PdfReader # For basic text extraction/processing

import tempfile
from cv_parser import main 

# --- Configuration ---
st.set_page_config(layout="wide", page_title="PDF Analyzer & Data Viewer")
conn = ""
# --- MySQL Connection Function ---
#@st.cache_resource
def get_mysql_connection():
    """Initializes and returns a cached database connection."""
    # Uses st.connection with the 'mysql' connection name from secrets.toml
    #st.write(st.secrets)
    try:
        conn = ""
        conn = st.connection("mysql", type="sql")
        return conn
    except Exception as e:
        st.error(f"Failed to connect to MySQL: {e}")
        st.write(f"Failed to connect to MySQL: {e}")
        return None


conn = ""
conn = get_mysql_connection()

# --- Main Page Layout ---
st.title("Unified Data & Document Viewer")

col1, col2 = st.columns(2)

# ==================================
# COLUMN 1: PDF Input & Display
# ==================================
with col1:
    st.header("📄 PDF Input")
    
    uploaded_file = st.file_uploader(
        "Upload a PDF file", 
        type=("pdf")
    )
    
    if uploaded_file is not None:
        st.success(f"File uploaded: {uploaded_file.name}")
        
    if uploaded_file:
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(uploaded_file.read())
            tmp_path = tmp.name

        output = main(tmp_path)
        st.write(output)
        
        # --- Option 1: Display PDF (Requires custom component like streamlit-pdf-viewer) ---
        # if st.button("Display PDF"):
        #     pdf_viewer(uploaded_file.getvalue())

        # --- Option 2: Extract and display text (Using PyPDF2) ---
        if st.checkbox("Extract and Show PDF Text"):
            try:
                # Read file as a BytesIO object
                pdf_reader = PdfReader(uploaded_file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() or "" # extract_text might return None
                
                # Show extracted text in an expander
                with st.expander("Extracted Text Preview"):
                    st.text_area("PDF Content", text, height=300)
            
            except Exception as e:
                st.error(f"Error processing PDF: {e}")

# ==================================
# COLUMN 2: MySQL Table Display
# ==================================
#if st.button("Display MySQL"):
conn = ""
with col2:
    conn = ""
    conn = get_mysql_connection()    
    st.header("📊 MySQL Data")

    if conn is not None:
        # Get list of tables (optional, for flexibility)
        try:
            # Query to get table names from the current database
            #st.write(conn)
            #st.write('test')
            try:
                tables_df = conn.query("SHOW TABLES;")
            except Exception as eq:
                st.write(f"Query failed:{eq}")
            #st.write(tables_df)
            #result = conn.execute(text("SHOW TABLES;"))
            #tables_df = pd.DataFrame(result.fetchall(), columns=result.keys())
            #if tables_df is not None:
            # Check if tables_df is not None and contains data            
            if tables_df is not None and not tables_df.empty:
                table_names = tables_df.iloc[:, 0].tolist() # Assuming single column result
                st.write(table_names)
            else:
                #st.write(f"in eRRRRRR")    
                raise Exception
        except Exception as e:
            #st.write(f"eRRRRRR")
            st.warning(f"Could not fetch table list. Error: {e}")
            table_names = ["mytable", "another_table"] # Use hardcoded list as fallback

        if table_names:
            # Dropdown for selecting a table
            selected_table = st.selectbox(
                "Select a table to view:",
                table_names
            )
            
            # Fetch data for the selected table
            if st.button(f"Load Data from {selected_table}"):
                #st.write(f"SELECT * FROM {selected_table};")
                try:
                    query = f"SELECT * FROM {selected_table};"
                    df = conn.query(query, ttl=600) # Cache results for 10 minutes (600s)
                    
                    st.subheader(f"Data from '{selected_table}'")
                    st.dataframe(df) # Display as an interactive table
                    st.info(f"Loaded {len(df)} rows.")
                    
                except Exception as e:
                    st.error(f"Error fetching data from '{selected_table}': {e}")
    else:
        st.warning("Database connection is not available.")
        #st.error("Database connection is not available.")
        #st.write("Database connection is not available.")

