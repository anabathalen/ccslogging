import streamlit as st
import pandas as pd
from datetime import datetime
import re
from utils.github_utils import authenticate_github, get_repository, update_csv_in_github, get_existing_data

def validate_doi(doi):
    doi_pattern = r'^10\.\d{4,9}/[-._;()/:A-Z0-9]+$'
    return re.match(doi_pattern, doi, re.IGNORECASE) is not None

def check_doi_exists(existing_data, doi):
    if existing_data is None or existing_data.empty:
        return False
    return doi in existing_data['doi'].values

def get_paper_details(doi):
    return {
        "paper_title": "Sample Paper Title",
        "authors": "Author1, Author2",
        "doi": doi,
        "publication_year": 2022,
        "journal": "Sample Journal"
    }

def show_data_entry_page(existing_data):
    st.title("Collision Cross Section Data Entry")

    if "protein_data" not in st.session_state:
        st.session_state.protein_data = []

    if "current_protein_entry" not in st.session_state:
        st.session_state.current_protein_entry = {}

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
        st.header(f"Log Protein Data for Paper: {st.session_state.paper_details['paper_title']}")
        with st.form("protein_entry_form"):
            protein_name = st.text_input("Protein/Ion Name")
            instrument = st.selectbox("Instrument Used", [
                "Waters Synapt", "Waters Cyclic", "Waters Vion", "Agilent 6560", 
                "Bruker timsTOF", "Other (enter)"
            ])
            ims_type = st.selectbox("IMS Type", ["TWIMS", "DTIMS", "CYCLIC", "TIMS", "FAIMS", "Other (enter)"])
            drift_gas = st.selectbox("Drift Gas", ["Nitrogen", "Helium", "Argon", "Other"])
            if drift_gas == "Other":
                drift_gas = st.text_input("Specify Drift Gas")

            st.markdown("#### Optional Protein Identifiers (Leave blank if not available)")
            uniprot_id = st.text_input("Uniprot Identifier")
            pdb_id = st.text_input("PDB Identifier")
            protein_sequence = st.text_area("Protein Sequence")
            sequence_mass_value = st.number_input("Sequence Mass (Da)", min_value=0.0, value=0.0, format="%.2f")
            measured_mass_value = st.number_input("Measured Mass (Da)", min_value=0.0, value=0.0, format="%.2f")

            native_measurement = st.radio("Is this a native measurement?", ["Yes", "No"])
            subunit_count = st.number_input("Number of Non-Covalently Linked Subunits", min_value=1, step=1)
            oligomer_type = st.radio("If this is an oligomer, is it homo or hetero?", ["", "Homo-oligomer", "Hetero-oligomer"])

            num_ccs_values = st.number_input("How many CCS values for this protein?", min_value=1, step=1)
            ccs_data = []
            for i in range(int(num_ccs_values)):
                charge_state = st.number_input(f"Charge State {i+1}", min_value=1, step=1, key=f"charge_{i}")
                ccs_value = st.number_input(f"CCS Value for Charge State {i+1} (Å²)", min_value=0.0, format="%.2f", key=f"ccs_{i}")
                ccs_data.append((charge_state, ccs_value))

            additional_notes = st.text_area("Additional Notes (sample, instrument, etc.)")

            ready = st.form_submit_button("Review This Protein")

        if ready:
            st.session_state.current_protein_entry = {
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

    if st.session_state.get("current_protein_entry"):
        st.subheader("Review Current Protein Entry")
        p = st.session_state.current_protein_entry
        st.write(f"**Protein Name**: {p['protein_name']}")
        st.write(f"**Instrument**: {p['instrument']}")
        st.write(f"**IMS Type**: {p['ims_type']}")
        st.write(f"**Drift Gas**: {p['drift_gas']}")
        st.write(f"**Subunit Count**: {p['subunit_count']}")
        st.write(f"**Oligomer Type**: {p['oligomer_type']}")
        st.write(f"**CCS Values**:")
        for charge, val in p["ccs_data"]:
            st.markdown(f"- Charge {charge}: {val} Å²")
        st.write(f"**Notes**: {p['additional_notes']}")

        confirm_add = st.button("Add Protein to Entry List")
        if confirm_add:
            st.session_state.protein_data.append(p)
            st.session_state.current_protein_entry = {}  # Clear for next entry
            st.success("Protein added.")

    if st.session_state.get("protein_data"):
        st.subheader("All Logged Proteins")
        for i, protein in enumerate(st.session_state.protein_data):
            st.markdown(f"**#{i+1}: {protein['protein_name']}**")
            st.write(protein)

        if st.button("Submit All Protein Data"):
            all_proteins = [
                {**st.session_state.paper_details, **protein}
                for protein in st.session_state.protein_data
            ]
            df = pd.DataFrame(all_proteins)
            st.dataframe(df)

            g = authenticate_github()
            if g:
                repo = get_repository(g, st.secrets["REPO_NAME"])
                if repo:
                    success, message = update_csv_in_github(repo, st.secrets["CSV_PATH"], df)
                    if success:
                        st.success(message)
                        st.session_state.protein_data = []
                    else:
                        st.error(message)
                else:
                    st.error("Could not access GitHub repository.")
            else:
                st.error("GitHub authentication failed.")


