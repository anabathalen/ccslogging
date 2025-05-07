import streamlit as st
import pandas as pd
import re
from utils.github_utils import authenticate_github, get_repository, update_csv_in_github

def validate_doi(doi):
    doi_pattern = r'^10\.\d{4,9}/[-._;()/:A-Z0-9]+$'
    return re.match(doi_pattern, doi, re.IGNORECASE) is not None

def check_doi_exists(existing_data, doi):
    return doi in existing_data['doi'].values if existing_data is not None and not existing_data.empty else False

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

    # Session state setup
    if 'protein_data' not in st.session_state:
        st.session_state.protein_data = []
    if 'show_full_form' not in st.session_state:
        st.session_state.show_full_form = False

    with st.expander("DOI Check", expanded=True):
        col1, col2 = st.columns([3, 1])
        with col1:
            doi = st.text_input("Enter DOI (e.g., 10.1021/example)")
        with col2:
            check_button = st.button("Check DOI")

        if check_button and doi:
            if not validate_doi(doi):
                st.error("Invalid DOI format.")
            else:
                paper_details = get_paper_details(doi)
                if check_doi_exists(existing_data, doi):
                    st.warning("Paper already exists.")
                    st.dataframe(existing_data[existing_data['doi'] == doi])
                else:
                    st.session_state.paper_details = paper_details
                    st.session_state.show_full_form = True
                    st.success("DOI is valid and new. Proceed to data entry.")

    # Protein entry form
    if st.session_state.get("show_full_form", False):
        st.header("Log Protein Data")

        with st.form("protein_entry_form"):
            st.subheader("Basic Information")
            protein_name = st.text_input("Protein/Ion Name")
            instrument = st.selectbox("Instrument Used", ["Waters Synapt", "Waters Cyclic", "Waters Vion", "Agilent 6560", "Bruker timsTOF", "Other"])
            ims_type = st.selectbox("IMS Type", ["TWIMS", "DTIMS", "CYCLIC", "TIMS", "FAIMS", "Other"])
            drift_gas = st.selectbox("Drift Gas", ["Nitrogen", "Helium", "Argon", "Other"])
            if drift_gas == "Other":
                drift_gas = st.text_input("Specify Drift Gas")

            st.subheader("Optional Identifiers (Leave blank if not applicable)")
            uniprot_id = st.text_input("Uniprot ID")
            pdb_id = st.text_input("PDB ID")
            protein_sequence = st.text_area("Protein Sequence")
            sequence_mass = st.number_input("Sequence Mass (Da)", min_value=0.0, format="%.2f")
            measured_mass = st.number_input("Measured Mass (Da)", min_value=0.0, format="%.2f")

            st.subheader("Structural Info")
            native = st.radio("Native Measurement?", ["Yes", "No"])
            subunit_count = st.number_input("Number of Subunits", min_value=1, step=1)
            oligomer_type = st.selectbox("Oligomer Type (fill only if >1 subunits)", ["", "Homo-oligomer", "Hetero-oligomer"])

            st.subheader("CCS Measurements")
            num_ccs = st.number_input("How many CCS values?", min_value=1, step=1, key="ccs_count")
            ccs_data = []
            for i in range(int(num_ccs)):
                charge = st.number_input(f"Charge State {i+1}", min_value=1, step=1, key=f"charge_{i}")
                ccs = st.number_input(f"CCS Value {i+1} (Å²)", min_value=0.0, format="%.2f", key=f"ccs_{i}")
                ccs_data.append((charge, ccs))

            additional_notes = st.text_area("Additional Notes")

            submitted = st.form_submit_button("Add Protein Entry")

        if submitted:
            entry = {
                "protein_name": protein_name,
                "instrument": instrument,
                "ims_type": ims_type,
                "drift_gas": drift_gas,
                "uniprot": uniprot_id or None,
                "pdb": pdb_id or None,
                "sequence": protein_sequence or None,
                "sequence_mass": sequence_mass or None,
                "measured_mass": measured_mass or None,
                "native_measurement": native,
                "subunit_count": subunit_count,
                "oligomer_type": oligomer_type or None,
                "ccs_data": ccs_data,
                "additional_notes": additional_notes
            }
            st.session_state.protein_data.append(entry)
            st.success("Protein entry added.")

        st.write("### Current Protein Entries:")
        for i, p in enumerate(st.session_state.protein_data):
            st.write(f"**{i+1}. {p['protein_name']}** - {p['instrument']} - {p['ims_type']}")
            for c, ccs in p["ccs_data"]:
                st.write(f"- Charge {c}: {ccs} Å²")

        if len(st.session_state.protein_data) > 0:
            if st.button("Submit All Data to GitHub"):
                df = pd.DataFrame([
                    {**st.session_state.paper_details, **protein} 
                    for protein in st.session_state.protein_data
                ])
                st.dataframe(df)

                g = authenticate_github()
                if g:
                    repo = get_repository(g, st.secrets["REPO_NAME"])
                    if repo:
                        success, msg = update_csv_in_github(repo, st.secrets["CSV_PATH"], df)
                        st.success(msg) if success else st.error(msg)
                    else:
                        st.error("Repo access failed.")
                else:
                    st.error("GitHub authentication failed.")

