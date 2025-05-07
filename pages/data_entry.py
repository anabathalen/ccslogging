# pages/data_entry.py - Data entry page
import streamlit as st
import pandas as pd
from datetime import datetime
import re

from utils.github_utils import authenticate_github, get_repository, update_csv_in_github

def validate_doi(doi):
    """Validate DOI format."""
    # Basic DOI format validation - can be enhanced
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
                
                # Find and display existing entries
                paper_entries = existing_data[existing_data['doi'] == doi]
                st.write(f"Found {len(paper_entries)} entries from this paper:")
                st.dataframe(paper_entries)
            else:
                st.success(f"This paper (DOI: {doi}) is not yet in the database. Please proceed with data entry.")
                # Store DOI in session state for the form
                st.session_state.new_doi = doi
                st.session_state.show_full_form = True
    
    # Only show full form if DOI check passed
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
                # Validate required fields
                if not paper_title or not authors or not molecule or ccs_value <= 0:
                    st.error("Please fill in all required fields (Title, Authors, Molecule, CCS Value).")
                    return
                    
                # Create a DataFrame with the form data
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
                
                # Display the entered data
                st.subheader("Data to be submitted:")
                st.dataframe(df)
                
                # Try to update the GitHub repository
                if st.session_state.get("github_configured", False):
                    g = authenticate_github()
                    if g:
                        repo = get_repository(g, st.session_state.repo_name)
                        if repo:
                            success, message = update_csv_in_github(repo, st.session_state.csv_path, df)
                            if success:
                                st.success(message)
                                # Reset the form state
                                st.session_state.show_full_form = False
                                st.session_state.pop('new_doi', None)
                                st.experimental_rerun()
                            else:
                                st.error(message)
                        else:
                            st.error("Repository configuration issue. Please check your repository settings.")
                    else:
                        st.error("GitHub authentication failed. Please check your token.")
                else:
                    st.warning("Please configure and test your GitHub connection in the sidebar before submitting data.")
