import streamlit as st
import pandas as pd
from datetime import datetime
import re
from utils.github_utils import authenticate_github, get_repository, update_csv_in_github, get_existing_data

def validate_doi(doi):
    """Validate DOI format."""
    doi_pattern = r'^10\.\d{4,9}/[-._;()/:A-Z0-9]+$'
    return re.match(doi_pattern, doi, re.IGNORECASE) is not None

def check_doi_exists(existing_data, doi):
    """Check if DOI already exists in the database."""
    if existing_data is None or existing_data.empty:
        return False
    return doi in existing_data['doi'].values

def get_paper_details(doi):
    """Fetch paper details based on DOI (you can integrate an external API like CrossRef or other)."""
    return {
        "paper_title": "Sample Paper Title",
        "authors": "Author1, Author2",
        "doi": doi,
        "publication_year": 2022,
        "journal": "Sample Journal"
    }

def show_data_entry_page(existing_data):
    """Display data entry page for logging proteins and CCS data."""
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

    if st.session_state.get('show_full_form', False):
        if 'protein_data' not in st.session_state:
            st.session_state.protein_data = []  # Initialize protein data

        protein_data = st.session_state.protein_data  # Use existing session data

        # Protein data entry form
        st.header(f"Log Protein Data for Paper: {st.session_state.paper_details['paper_title']}")

        with st.form(f"protein_form_{len(protein_data)}"):  # Ensure each form has a unique key
            protein_name = st.text_input("Protein/Ion Name")
            instrument = st.selectbox("Instrument Used", [
                "Waters Synapt", "Waters Cyclic", "Waters Vion", "Agilent 6560", 
                "Bruker timsTOF", "Other (enter)"
            ])
            ims_type = st.selectbox("IMS Type", ["TWIMS", "DTIMS", "CYCLIC", "TIMS", "FAIMS", "Other (enter)"])
            drift_gas = st.selectbox("Drift Gas", ["Nitrogen", "Helium", "Argon", "Other"])
            if drift_gas == "Other":
                drift_gas = st.text_input("Specify Drift Gas")
            
            # Protein identifiers with Yes/No radio buttons
            uniprot = st.radio("Include Uniprot Identifier?", ["No", "Yes"])
            pdb = st.radio("Include PDB Identifier?", ["No", "Yes"])
            sequence = st.radio("Include Complete Sequence?", ["No", "Yes"])
            sequence_mass = st.radio("Include Sequence Mass?", ["No", "Yes"])
            measured_mass = st.radio("Include Measured Mass?", ["No", "Yes"])
            
            # Show input fields if "Yes" is selected
            if uniprot == "Yes":
                uniprot_id = st.text_input("Enter Uniprot Identifier")
            if pdb == "Yes":
                pdb_id = st.text_input("Enter PDB Identifier")
            if sequence == "Yes":
                protein_sequence = st.text_area("Enter Protein Sequence")
            if sequence_mass == "Yes":
                sequence_mass_value = st.number_input("Enter Sequence Mass (Da)", min_value=0.0)
            if measured_mass == "Yes":
                measured_mass_value = st.number_input("Enter Measured Mass (Da)", min_value=0.0)

            # Non-covalently linked subunits
            native_measurement = st.radio("Is this a native measurement?", ["Yes", "No"])
            subunit_count = st.number_input("Number of Non-Covalently Linked Subunits", min_value=1)

            if subunit_count > 1:
                oligomer_type = st.radio("Is this a homo or hetero-oligomer?", ["Homo-oligomer", "Hetero-oligomer"])

            # CCS values
            num_ccs_values = st.number_input("How many CCS values for this protein?", min_value=1)
            ccs_data = []
            for i in range(num_ccs_values):
                charge_state = st.number_input(f"Charge State {i+1}", min_value=1)
                ccs_value = st.number_input(f"CCS Value for Charge State {i+1} (Å²)", min_value=0.0)
                ccs_data.append((charge_state, ccs_value))

            additional_notes = st.text_area("Additional Notes")

            apply_button = st.form_submit_button("Apply Protein Data")

            if apply_button:
                protein_entry = {
                    "protein_name": protein_name,
                    "instrument": instrument,
                    "ims_type": ims_type,
                    "drift_gas": drift_gas,
                    "uniprot": uniprot_id if uniprot == "Yes" else None,
                    "pdb": pdb_id if pdb == "Yes" else None,
                    "sequence": protein_sequence if sequence == "Yes" else None,
                    "sequence_mass": sequence_mass_value if sequence_mass == "Yes" else None,
                    "measured_mass": measured_mass_value if measured_mass == "Yes" else None,
                    "native_measurement": native_measurement,
                    "subunit_count": subunit_count,
                    "oligomer_type": oligomer_type if subunit_count > 1 else None,
                    "ccs_data": ccs_data,
                    "additional_notes": additional_notes
                }
                protein_data.append(protein_entry)

                st.session_state.protein_data = protein_data  # Save back to session

                # Ask if there are more proteins to log
                more_proteins = st.radio("Do you want to log another protein?", ["Yes", "No"])
                if more_proteins == "No":
                    st.session_state.show_full_form = False
                    st.session_state.show_summary = True  # Move to summary after logging

        # Display logged proteins and allow submission
        if st.session_state.get('show_summary', False):
            st.subheader("Review Entered Data")
            for protein in st.session_state.protein_data:
                st.write(f"**Protein Name**: {protein['protein_name']}")
                st.write(f"**Instrument Used**: {protein['instrument']}")
                st.write(f"**IMS Type**: {protein['ims_type']}")
                st.write(f"**Drift Gas**: {protein['drift_gas']}")
                st.write(f"**CCS Values**: {', '.join([f'Charge State {c[0]}: {c[1]}' for c in protein['ccs_data']])}")
                st.write(f"**Additional Notes**: {protein['additional_notes']}")

            submit_button = st.button("Submit All Data")

            if submit_button:
                # Create a DataFrame from all logged proteins
                all_proteins = []
                for protein in st.session_state.protein_data:
                    all_proteins.append({
                        **st.session_state.paper_details,
                        **protein
                    })
                df = pd.DataFrame(all_proteins)
                st.dataframe(df)

                # Attempt to update CSV on GitHub
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
                        st.error("Could not access the configured GitHub repository.")
                else:
                    st.error("GitHub authentication failed. Check your Streamlit secrets.")


