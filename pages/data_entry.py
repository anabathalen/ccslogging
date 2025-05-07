import streamlit as st
import pandas as pd
from datetime import datetime

# Utility to reset protein entry state
def reset_protein_state():
    st.session_state.protein_data = []
    st.session_state.current_ccs_values = []
    st.session_state.adding_protein = True
    st.session_state.protein_index = 0

# Start session state variables
if 'protein_data' not in st.session_state:
    reset_protein_state()

if 'new_doi' not in st.session_state:
    st.session_state.new_doi = ''

if 'adding_protein' not in st.session_state:
    st.session_state.adding_protein = True

# Paper metadata entry
st.title("Collision Cross Section Data Entry")

with st.form("paper_form"):
    st.header("Paper Information")
    doi = st.text_input("DOI")
    paper_title = st.text_input("Paper Title")
    authors = st.text_input("Authors")
    publication_year = st.number_input("Publication Year", min_value=1900, max_value=datetime.now().year, step=1)
    journal = st.text_input("Journal")
    submitted = st.form_submit_button("Save Paper Info")

    if submitted:
        if not doi or not paper_title or not authors:
            st.error("Please fill out the required fields (DOI, Title, Authors).")
        else:
            st.session_state.new_doi = doi
            st.success("Paper information saved. You may now add protein entries.")

# Begin protein data entry if paper info is set
if st.session_state.new_doi:

    st.subheader(f"Add Protein Entry #{st.session_state.protein_index + 1}")
    with st.form(f"protein_form_{st.session_state.protein_index}"):

        protein_name = st.text_input("Protein Name")

        instrument = st.selectbox("Instrument Used", [
            "Waters Synapt", "Waters Cyclic", "Waters Vion",
            "Agilent 6560", "Bruker timsTOF", "Other (enter)"
        ])
        if instrument == "Other (enter)":
            instrument = st.text_input("Specify Instrument")

        ims_type = st.selectbox("IMS Type", ["TWIMS", "DTIMS", "CYCLIC", "TIMS", "FAIMS", "Other (enter)"])
        if ims_type == "Other (enter)":
            ims_type = st.text_input("Specify IMS Type")

        drift_gas = st.selectbox("Drift Gas", ["Nitrogen", "Helium", "Argon", "Other"])
        if drift_gas == "Other":
            drift_gas = st.text_input("Specify Drift Gas")

        st.markdown("**Protein Information Provided in Paper**")
        info_fields = {
            "supplier": "Supplier Information",
            "uniprot": "UniProt Identifier",
            "pdb": "PDB Identifier",
            "sequence": "Complete Sequence",
            "sequence_mass": "Sequence Mass",
            "measured_mass": "Measured Mass"
        }

        info_data = {}
        for key, label in info_fields.items():
            if st.checkbox(label):
                info_data[key] = st.text_input(f"Enter {label}")
            else:
                info_data[key] = None

        native = st.radio("Is this a native measurement?", ["Yes", "No"])
        subunit_count = st.number_input("Number of non-covalently linked subunits", min_value=1, step=1)

        oligomer_type = "Monomer"
        if subunit_count > 1:
            oligomer_type = st.radio("Oligomer Type", ["Homo-oligomer", "Hetero-oligomer"])

        ccs_count = st.number_input("Number of CCS values for this protein", min_value=1, step=1)
        ccs_values = []
        for i in range(int(ccs_count)):
            st.markdown(f"**CCS Value #{i + 1}**")
            charge = st.number_input(f"Charge State {i + 1}", step=1)
            ccs = st.number_input(f"CCS Value {i + 1} (Å²)", min_value=0.0, format="%.4f")
            ccs_values.append((charge, ccs))

        notes = st.text_area("Notes on sample, instrument, or paper")

        submitted_protein = st.form_submit_button("Add Protein Entry")

        if submitted_protein:
            st.session_state.protein_data.append({
                "protein_name": protein_name,
                "instrument": instrument,
                "ims_type": ims_type,
                "drift_gas": drift_gas,
                "info_fields": info_data,
                "native": native,
                "subunit_count": subunit_count,
                "oligomer_type": oligomer_type,
                "ccs_values": ccs_values,
                "notes": notes
            })
            st.session_state.protein_index += 1
            st.success("Protein entry added.")

    if st.session_state.protein_data:
        if st.button("Finished Adding Proteins"):
            st.session_state.adding_protein = False

# Show submission preview
if not st.session_state.adding_protein and st.session_state.protein_data:
    st.header("Submission Preview")
    all_entries = []
    for protein in st.session_state.protein_data:
        for charge, ccs in protein["ccs_values"]:
            entry = {
                "doi": st.session_state.new_doi,
                "paper_title": paper_title,
                "authors": authors,
                "publication_year": publication_year,
                "journal": journal,
                "protein_name": protein["protein_name"],
                "instrument": protein["instrument"],
                "ims_type": protein["ims_type"],
                "drift_gas": protein["drift_gas"],
                "native": protein["native"],
                "subunit_count": protein["subunit_count"],
                "oligomer_type": protein["oligomer_type"],
                "charge_state": charge,
                "ccs_value": ccs,
                "notes": protein["notes"],
                "submission_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            entry.update(protein["info_fields"])
            all_entries.append(entry)

    df = pd.DataFrame(all_entries)
    st.dataframe(df)

    if st.button("Submit All Data"):
        from utils.github_utils import authenticate_direct, get_repository, update_csv_in_github
        g = authenticate_direct()
        repo = get_repository(g, st.session_state.repo_name)
        if repo:
            success, message = update_csv_in_github(repo, st.session_state.csv_path, df)
            if success:
                st.success("Data successfully submitted to GitHub.")
                reset_protein_state()
            else:
                st.error(message)
        else:
            st.error("Repository access failed. Check your configuration.")

