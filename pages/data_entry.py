import streamlit as st
import pandas as pd
import re
from datetime import datetime
import requests
from utils.github_utils import authenticate_github, get_repository, update_csv_in_github

# Function to validate DOI format
def validate_doi(doi):
    """Validate DOI format using regular expression."""
    doi_pattern = r'^10\.\d{4,9}/[-._;()/:A-Z0-9]+$'
    return re.match(doi_pattern, doi, re.IGNORECASE) is not None

# Function to check if DOI already exists in the database
def check_doi_exists(existing_data, doi):
    """Check if DOI is already in the database."""
    if existing_data is None or existing_data.empty:
        return False
    return doi in existing_data['doi'].values

# Function to fetch paper details using DOI (CrossRef API)
def get_paper_details(doi):
    """Fetch paper details from CrossRef using DOI."""
    response = requests.get(f"https://api.crossref.org/works/{doi}")
    if response.status_code == 200:
        data = response.json()['message']
        return {
            "paper_title": data.get("title", ["No title"])[0],
            "authors": ', '.join([author['given'] + " " + author['family'] for author in data.get('author', [])]),
            "doi": doi,
            "publication_year": data.get("published", {}).get("date-parts", [[None]])[0][0],
            "journal": data.get("container-title", ["No journal"])[0]
        }
    else:
        return {
            "paper_title": "Unknown Paper Title",
            "authors": "Unknown Authors",
            "doi": doi,
            "publication_year": "Unknown Year",
            "journal": "Unknown Journal"
        }

# Function to show the data entry page
def show_data_entry_page(existing_data):
    """Display the data entry form and handle the submission process."""
    st.title("Collision Cross Section Data Entry")

    # DOI check section
    with st.expander("DOI Check", expanded=True):
        st.markdown("### Check if paper already exists in database")
        col1, col2 = st.columns([3, 1])

        with col1:
            doi = st.text_input("Enter DOI (e.g., 10.1021/example)")

        with col2:
            check_button = st.button("Check DOI")

        # Check DOI and show paper details
        if check_button and doi:
            if not validate_doi(doi):
                st.error("Invalid DOI format. Please enter a valid DOI (e.g., 10.1021/example)")
            else:
                paper_details = get_paper_details(doi)
                if check_doi_exists(existing_data, doi):
                    st.warning(f"This paper (DOI: {doi}) already exists in the database!")
                    paper_entries = existing_data[existing_data['doi'] == doi]
                    st.write(f"Found {len(paper_entries)} entries from this paper:")
                    st.dataframe(paper_entries)
                else:
                    st.success(f"This paper (DOI: {doi}) is not yet in the database. Please proceed with data entry.")
                    st.session_state.new_doi = doi
                    st.session_state.show_full_form = True
                    st.session_state.paper_details = paper_details
                    st.session_state.protein_data = []
                    st.session_state.protein_counter = 1  # Start at protein 1

    # If form for data entry is ready
    if st.session_state.get('show_full_form', False):
        protein_number = st.session_state.get("protein_counter", 1)

        st.header(f"Log Protein {protein_number} Data for Paper: {st.session_state.paper_details['paper_title']}")

        # Start the form without submitting until explicitly pressed 'Ready to Submit'
        with st.form("protein_form", clear_on_submit=False):
            # Collect protein details
            protein_name = st.text_input("Protein/Ion Name", key="protein_name")
            instrument = st.selectbox("Instrument Used", ["Waters Synapt", "Waters Cyclic", "Waters Vion", "Agilent 6560", 
                                                        "Bruker timsTOF", "Other (enter)"], key="instrument")
            ims_type = st.selectbox("IMS Type", ["TWIMS", "DTIMS", "CYCLIC", "TIMS", "FAIMS", "Other (enter)"], key="ims_type")
            drift_gas = st.selectbox("Drift Gas", ["Nitrogen", "Helium", "Argon", "Other"], key="drift_gas")
            if drift_gas == "Other":
                drift_gas = st.text_input("Specify Drift Gas", key="drift_gas_other")

            # Protein identifiers section
            st.markdown("#### Optional Protein Identifiers (Leave blank if not available)")
            uniprot_id = st.text_input("Uniprot Identifier", key="uniprot_id")
            pdb_id = st.text_input("PDB Identifier", key="pdb_id")
            protein_sequence = st.text_area("Protein Sequence", key="protein_sequence")
            sequence_mass_value = st.number_input("Sequence Mass (Da)", min_value=0.0, value=0.0, format="%.2f", key="sequence_mass_value")
            measured_mass_value = st.number_input("Measured Mass (Da)", min_value=0.0, value=0.0, format="%.2f", key="measured_mass_value")

            # Native measurement and subunit count
            native_measurement = st.radio("Is this a native measurement?", ["Yes", "No"], key="native_measurement")
            subunit_count = st.number_input("Number of Non-Covalently Linked Subunits", min_value=1, step=1, key="subunit_count")

            # Oligomer type, only if subunit count > 1
            oligomer_type = ""
            if subunit_count > 1:
                oligomer_type = st.radio("If this is an oligomer (subunit count > 1), is it a homo or hetero-oligomer?", 
                                        ["", "Homo-oligomer", "Hetero-oligomer"], key="oligomer_type")

            # Charge states and CCS values
            num_ccs_values = st.number_input("How many CCS values for this protein?", min_value=1, step=1, key="num_ccs_values")
            ccs_data = []
            for i in range(num_ccs_values):
                charge_state = st.number_input(f"Charge State {i+1}", min_value=1, step=1, key=f"charge_{i}")
                ccs_value = st.number_input(f"CCS Value for Charge State {i+1} (Å²)", min_value=0.0, format="%.2f", key=f"ccs_{i}")
                ccs_data.append((charge_state, ccs_value))

            additional_notes = st.text_area("Additional Notes (sample, instrument, etc.)", key="additional_notes")

            # 'Ready to Submit' button (this is the only submit action)
            submit_protein = st.form_submit_button("Ready to Submit")

            # Store form data in session state only when "Ready to Submit" is clicked
            if submit_protein:
                # Store data in session state
                protein_entry = {
                    "protein_name": protein_name,
                    "instrument": instrument,
                    "ims_type": ims_type,
                    "drift_gas": drift_gas,
                    "uniprot": uniprot_id if uniprot_id else None,
                    "pdb": pdb_id if pdb_id else None,
                    "sequence": protein_sequence if protein_sequence else None,
                    "sequence_mass": sequence_mass_value if sequence_mass_value > 0 else None,
                    "measured_mass": measured_mass_value if measured_mass_value > 0 else None,
                    "native_measurement": native_measurement,
                    "subunit_count": subunit_count,
                    "oligomer_type": oligomer_type if oligomer_type else None,
                    "ccs_data": ccs_data,
                    "additional_notes": additional_notes
                }
                st.session_state.protein_data.append(protein_entry)

                # Ask if more proteins need to be entered
                more_proteins = st.radio("Would you like to log another protein?", ["Yes", "No"], key="more_proteins")
                if more_proteins == "Yes":
                    st.session_state.protein_counter += 1  # Increment the protein counter for next entry
                    st.session_state.show_full_form = True  # Continue showing the form
                else:
                    st.session_state.show_full_form = False  # Stop the process

        # If no more proteins need to be logged, submit the data
        if not st.session_state.get('show_full_form', True) and st.session_state.get('protein_data', []):
            st.subheader("All Protein Data Submitted")
            st.write(st.session_state.protein_data)

            # Button to submit all protein data
            submit_all = st.button("Submit All Protein Data")

            if submit_all:
                # Submit the data (save to CSV, GitHub, etc.)
                all_proteins = []
                for protein in st.session_state.protein_data:
                    all_proteins.append({
                        **st.session_state.paper_details,
                        **protein
                    })
                df = pd.DataFrame(all_proteins)
                st.dataframe(df)

                # GitHub push
                g = authenticate_github()
                if g:
                    repo = get_repository(g, st.secrets["REPO_NAME"])
                    if repo:
                        success, message = update_csv_in_github(repo, st.secrets["CSV_PATH"], df)
                        if success:
                            st.success(message)
                        else:
                            st.error(message)
                    else:
                        st.error("Could not access GitHub repository.")
                else:
                    st.error("GitHub authentication failed.")

