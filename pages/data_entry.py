# pages/data_entry.py - Streamlit app page for entering protein CCS data

import streamlit as st
import pandas as pd
from datetime import datetime
import re
import requests
from utils.github_utils import authenticate_github, get_repository, update_csv_in_github, get_existing_data

# ----------------------------
# Utility Functions
# ----------------------------

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
    """
    Fetch paper metadata from CrossRef using the DOI.
    Returns a dictionary with paper_title, authors, journal, publication_year, and doi.
    """
    url = f"https://api.crossref.org/works/{doi}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        item = data["message"]

        # Extract title
        title = item.get("title", [""])[0]

        # Extract authors
        authors = item.get("author", [])
        author_names = []
        for author in authors:
            given = author.get("given", "")
            family = author.get("family", "")
            full_name = f"{given} {family}".strip()
            if full_name:
                author_names.append(full_name)
        authors_str = ", ".join(author_names)

        # Extract journal name
        journal = item.get("container-title", [""])[0]

        # Extract publication year
        publication_year = None
        if "published-print" in item and "date-parts" in item["published-print"]:
            publication_year = item["published-print"]["date-parts"][0][0]
        elif "published-online" in item and "date-parts" in item["published-online"]:
            publication_year = item["published-online"]["date-parts"][0][0]
        elif "issued" in item and "date-parts" in item["issued"]:
            publication_year = item["issued"]["date-parts"][0][0]

        return {
            "paper_title": title,
            "authors": authors_str,
            "journal": journal,
            "publication_year": publication_year,
            "doi": doi
        }
    except requests.RequestException as e:
        print(f"Error fetching metadata for DOI {doi}: {e}")
        return {
            "paper_title": "",
            "authors": "",
            "journal": "",
            "publication_year": None,
            "doi": doi
        }


# ----------------------------
# Main App Function
# ----------------------------

def show_data_entry_page(existing_data):
    """Main function to display data entry interface."""
    st.title("Collision Cross Section Data Entry")

    # Step 1: DOI Check
    with st.expander("DOI Check", expanded=True):
        st.markdown("### Check if paper already exists in database")
        col1, col2 = st.columns([3, 1])

        with col1:
            doi = st.text_input("Enter DOI (e.g., 10.1021/example)")

        with col2:
            check_button = st.button("Check DOI")

        if check_button and doi:
            if not validate_doi(doi):
                st.error("Invalid DOI format. Please enter a valid DOI.")
            else:
                paper_details = get_paper_details(doi)
                if check_doi_exists(existing_data, doi):
                    st.warning(f"Paper already exists in the database: {doi}")
                    st.dataframe(existing_data[existing_data['doi'] == doi])
                else:
                    st.success("This DOI is not yet in the database. Proceed with data entry.")
                    st.session_state.new_doi = doi
                    st.session_state.paper_details = paper_details
                    st.session_state.show_full_form = True
                    st.session_state.protein_data = []

    # Step 2: Data Entry Form
    if st.session_state.get('show_full_form', False):
        st.header(f"Enter Protein Data for: {st.session_state.paper_details['paper_title']}")

        # Form for a single protein entry
        with st.form(f"protein_form_{len(st.session_state.protein_data)}"):
            st.markdown("### Required Protein Information")

            protein_name = st.text_input("Protein/Ion Name")
            instrument = st.selectbox("Instrument Used", [
                "Waters Synapt", "Waters Cyclic", "Waters Vion", "Agilent 6560", 
                "Bruker timsTOF", "Other (enter)"
            ])
            ims_type = st.selectbox("IMS Type", ["TWIMS", "DTIMS", "CYCLIC", "TIMS", "FAIMS", "Other (enter)"])
            drift_gas = st.selectbox("Drift Gas", ["Nitrogen", "Helium", "Argon", "Other"])
            if drift_gas == "Other":
                drift_gas = st.text_input("Specify Drift Gas")

            polarity = st.radio("Polarity Mode", ["Positive", "Negative"])

            st.markdown("### Optional Metadata (leave blank if not applicable)")

            uniprot_id = st.text_input("Uniprot Identifier")
            pdb_id = st.text_input("PDB Identifier")
            protein_sequence = st.text_area("Protein Sequence")
            sequence_mass_value = st.number_input("Sequence Mass (Da)", min_value=0.0, value=0.0, format="%.2f")
            measured_mass_value = st.number_input("Measured Mass (Da)", min_value=0.0, value=0.0, format="%.2f")

            native_measurement = st.radio("Is this a native measurement?", ["Yes", "No"])
            subunit_count = st.number_input("Number of Non-Covalently Linked Subunits", min_value=1, step=1)
            oligomer_type = st.radio(
                "Homo/Hetero-Oligomer (only fill if subunit count > 1)", 
                ["", "Homo-oligomer", "Hetero-oligomer"]
            )

            st.markdown("### CCS Data")

            num_ccs_values = st.number_input("Number of CCS values for this protein", min_value=1, step=1)
            ccs_data = []
            for i in range(num_ccs_values):
                charge_state = st.number_input(f"Charge State {i+1}", min_value=1, step=1, key=f"charge_{i}")
                ccs_value = st.number_input(f"CCS Value for Charge State {i+1} (Å²)", min_value=0.0, format="%.2f", key=f"ccs_{i}")
                ccs_data.append((charge_state, ccs_value))

            additional_notes = st.text_area("Additional Notes (sample prep, calibration, etc.)")

            # Final button to confirm submission
            ready_to_submit = st.form_submit_button("✅ Ready to Submit This Protein")

        # Handle protein submission
        if ready_to_submit:
            protein_entry = {
                "protein_name": protein_name,
                "instrument": instrument,
                "ims_type": ims_type,
                "drift_gas": drift_gas,
                "polarity": polarity,
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
            st.success("Protein entry added. You can now log another or submit all.")

    # Step 3: Review and Submit All
    if st.session_state.get('protein_data', []):
        st.subheader("Review Entered Proteins")

        for idx, protein in enumerate(st.session_state.protein_data):
            st.markdown(f"#### Protein {idx+1}: {protein['protein_name']}")
            st.markdown(f"- Instrument: {protein['instrument']}")
            st.markdown(f"- IMS Type: {protein['ims_type']}")
            st.markdown(f"- Drift Gas: {protein['drift_gas']}")
            st.markdown(f"- Polarity: {protein['polarity']}")
            st.markdown(f"- Native Measurement: {protein['native_measurement']}")
            st.markdown(f"- Subunit Count: {protein['subunit_count']}")
            st.markdown(f"- Oligomer Type: {protein['oligomer_type'] or 'N/A'}")
            st.markdown(f"- CCS Values:")
            for charge, ccs in protein["ccs_data"]:
                st.markdown(f"  - Charge {charge}: {ccs} Å²")
            st.markdown(f"- Notes: {protein['additional_notes']}")

        # Final "Submit All" button
        if st.button("📤 Submit All Protein Data to GitHub"):
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
                        st.session_state.protein_data = []  # clear on success
                        st.session_state.show_full_form = False
                    else:
                        st.error(message)
                else:
                    st.error("Could not access GitHub repository.")
            else:
                st.error("GitHub authentication failed.")

