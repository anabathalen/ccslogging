# pages/data_entry.py - Data entry page
import streamlit as st
import pandas as pd
from datetime import datetime
import re
import os

DATA_PATH = "data/local_data.csv"  # Path to save local CSV data

def validate_doi(doi):
    """Validate DOI format."""
    doi_pattern = r'^10\.\d{4,9}/[-._;()/:A-Z0-9]+$'
    return re.match(doi_pattern, doi, re.IGNORECASE) is not None

def check_doi_exists(existing_data, doi):
    """Check if DOI already exists in the database."""
    if existing_data is None or existing_data.empty:
        return False
    return doi in existing_data['doi'].values

def show_data_entry_page(existing_data):
    """Display data entry page with DOI check and data form."""
    st.title("Collision Cross Section Data Entry")
    
    with st.expander("DOI Check", expanded=True):
        st.markdown("### Check if paper already exists in database")
        col1, col2 = st.columns([3, 1])
        
        with col1:
            doi = st.text_input("Enter DOI (e.g., 10.1021/example)")
        
        with col2:
            check_button = st.button("Check DOI")
        
        if check_button and doi:
            if not validate_doi(doi):
                st.error("Invalid DOI format. Please enter a valid DOI (e.g., 10.1021/example)")
            elif check_doi_exists(existing_data, doi):
                st.warning(f"This paper (DOI: {doi}) already exists in the database!")
                paper_entries = existing_data[existing_data['doi'] == doi]
                st.write(f"Found {len(paper_entries)} entries from this paper:")
                st.dataframe(paper_entries)
            else:
                st.success(f"This paper (DOI: {doi}) is not yet in the database. Please proceed with data entry.")
                st.session_state.new_doi = doi
                st.session_state.show_full_form = True

    if st.session_state.get('show_full_form', False):
        with st.form("ccs_form"):
            st.header("Enter Collision Cross Section Data")
            st.markdown(f"Adding data for DOI: **{st.session_state.new_doi}**")
            
            col1, col2 = st.columns(2)
            with col1:
                paper_title = st.text_input("Paper Title")
                authors = st.text_input("Authors")
                publication_year = st.number_input("Publication Year", min_value=1900, max_value=datetime.now().year, step=1)
                journal = st.text_input("Journal")
            
            with col2:
                molecule = st.text_input("Molecule/Ion")
                ccs_value = st.number_input("Collision Cross Section Value (Å²)", min_value=0.0, format="%.4f")
                uncertainty = st.number_input("Uncertainty (±)", min_value=0.0, format="%.4f")
                buffer_gas = st.selectbox("Buffer Gas", ["He", "N2", "CO2", "Ar", "Other"])
                if buffer_gas == "Other":
                    buffer_gas = st.text_input("Specify Buffer Gas")
                temperature = st.number_input("Temperature (K)", min_value=0.0)
                method = st.selectbox("Measurement Method", ["Drift Tube", "TIMS", "TWIMS", "Theoretical", "Other"])
                if method == "Other":
                    method = st.text_input("Specify Method")

            additional_notes = st.text_area("Additional Notes")

            submitted = st.form_submit_button("Submit Data")

            if submitted:
                if not paper_title or not authors or not molecule or ccs_value <= 0:
                    st.error("Please fill in all required fields (Title, Authors, Molecule, CCS Value).")
                    return

                data = {
                    "paper_title": [paper_title],
                    "authors": [authors],
                    "doi": [st.session_state.new_doi],
                    "publication_year": [publication_year],
                    "journal": [journal],
                    "molecule": [molecule],
                    "ccs_value": [ccs_value],
                    "uncertainty": [uncertainty],
                    "buffer_gas": [buffer_gas],
                    "temperature": [temperature],
                    "method": [method],
                    "additional_notes": [additional_notes],
                    "submission_date": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
                }

                df = pd.DataFrame(data)

                st.subheader("Data to be submitted:")
                st.dataframe(df)

                try:
                    if os.path.exists(DATA_PATH):
                        existing_df = pd.read_csv(DATA_PATH)
                        df = pd.concat([existing_df, df], ignore_index=True)
                    
                    df.to_csv(DATA_PATH, index=False)
                    st.success("Data saved successfully to local CSV.")
                    st.session_state.show_full_form = False
                    st.session_state.pop('new_doi', None)
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"Error saving data: {e}")

