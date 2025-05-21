import streamlit as st
import pandas as pd
import re
from datetime import datetime
from utils.github_utils import authenticate_github, get_repository, update_csv_in_github, get_existing_data
import requests

# Validate DOI format using regex
def validate_doi(doi):
    doi_pattern = r'^10\.\d{4,9}/[-._;()/:A-Z0-9]+$'
    return re.match(doi_pattern, doi, re.IGNORECASE) is not None

# Check if DOI exists in current GitHub database
def check_doi_exists(existing_data, doi):
    if existing_data is None or existing_data.empty:
        return False
    return doi in existing_data['doi'].values

# Use CrossRef API to fetch paper details based on DOI
def get_paper_details(doi):
    try:
        url = f"https://api.crossref.org/works/{doi}"
        response = requests.get(url)
        if response.status_code != 200:
            return None
        item = response.json()['message']
        title = item['title'][0] if item.get('title') else "Unknown Title"
        authors = ', '.join([f"{a.get('given', '')} {a.get('family', '')}" for a in item.get('author', [])])
        year = item.get('issued', {}).get('date-parts', [[None]])[0][0]
        journal = item.get('container-title', ["Unknown Journal"])[0]
        return {
            "paper_title": title,
            "authors": authors,
            "doi": doi,
            "publication_year": year,
            "journal": journal
        }
    except Exception as e:
        return None

# ------------------------ APP START ------------------------
def main():
    st.title("Collision Cross Section Logging")

    # Load existing data from GitHub - FIX: Add the required arguments
    repo_name = st.secrets.get("REPO_NAME", "anabathalen/ccslogging")
    csv_path = st.secrets.get("CSV_PATH", "data/ccs_data.csv")
    existing_data = get_existing_data(repo_name, csv_path)

    if "protein_data" not in st.session_state:
        st.session_state.protein_data = []
    if "protein_count" not in st.session_state:
        st.session_state.protein_count = 1
    if "show_form" not in st.session_state:
        st.session_state.show_form = False

    # ---------- DOI CHECK ----------
    with st.expander("Step 1: Check DOI", expanded=True):
        col1, col2 = st.columns([3, 1])
        with col1:
            doi_input = st.text_input("Enter DOI (e.g., 10.1021/example)", key="doi_input")
        with col2:
            check_button = st.button("Check DOI")

        if check_button:
            if not validate_doi(doi_input):
                st.error("Invalid DOI format.")
            else:
                details = get_paper_details(doi_input)
                if details is None:
                    st.error("Could not fetch paper details.")
                else:
                    st.session_state.paper_details = details
                    st.session_state.show_form = True
                    st.success("DOI is valid. You can begin logging proteins.")

    # ---------- PROTEIN ENTRY FORM ----------
    if st.session_state.get("show_form", False):
        st.header(f"Log Protein {st.session_state.protein_count}")

        with st.form(f"protein_form_{st.session_state.protein_count}"):
            # Basic metadata
            protein_name = st.text_input("Protein/Ion Name")
            instrument = st.selectbox("Instrument Used", [
                "Waters Synapt", "Waters Cyclic", "Waters Vion", "Agilent 6560",
                "Bruker timsTOF", "Other (enter)"
            ])
            ims_type = st.selectbox("IMS Type", ["TWIMS", "DTIMS", "CYCLIC", "TIMS", "FAIMS", "Other (enter)"])
            drift_gas = st.selectbox("Drift Gas", ["Nitrogen", "Helium", "Argon", "Other"])
            if drift_gas == "Other":
                drift_gas = st.text_input("Specify Drift Gas")

            polarity = st.radio("Polarity (Ionization Mode)", ["Positive", "Negative"])

            # Optional identifiers
            st.markdown("#### Optional Protein Identifiers (Leave blank if not available)")
            uniprot_id = st.text_input("Uniprot ID")
            pdb_id = st.text_input("PDB ID")
            protein_sequence = st.text_area("Protein Sequence")
            sequence_mass = st.number_input("Sequence Mass (Da)", min_value=0.0, format="%.2f")
            measured_mass = st.number_input("Measured Mass (Da)", min_value=0.0, format="%.2f")

            native = st.radio("Is this a native measurement?", ["Yes", "No"])
            subunit_count = st.number_input("Number of Non-Covalently Linked Subunits", min_value=1, step=1)
            oligomer_type = st.radio("Oligomer Type (if applicable)", ["", "Homo-oligomer", "Hetero-oligomer"])

            # CCS values
            num_ccs = st.number_input("Number of CCS values to log", min_value=1, step=1)
            ccs_data = []
            for i in range(num_ccs):
                charge = st.number_input(f"Charge State {i+1}", min_value=1, step=1, key=f"charge_{i}")
                ccs = st.number_input(f"CCS Value for Charge State {i+1} (Å²)", min_value=0.0, format="%.2f", key=f"ccs_{i}")
                ccs_data.append((charge, ccs))

            notes = st.text_area("Additional Notes")

            # User controls when to submit
            ready_to_submit = st.form_submit_button("Ready to Submit")

        # -------------- FORM SUBMIT HANDLING --------------
        if ready_to_submit:
            entry = {
                "protein_name": protein_name.strip(),
                "instrument": instrument,
                "ims_type": ims_type,
                "drift_gas": drift_gas,
                "polarity": polarity,
                "uniprot": uniprot_id.strip() or None,
                "pdb": pdb_id.strip() or None,
                "sequence": protein_sequence.strip() or None,
                "sequence_mass": sequence_mass if sequence_mass > 0 else None,
                "measured_mass": measured_mass if measured_mass > 0 else None,
                "native_measurement": native,
                "subunit_count": subunit_count,
                "oligomer_type": oligomer_type if oligomer_type else None,
                "ccs_data": ccs_data,
                "additional_notes": notes.strip() or None
            }

            # Remove earlier entry for this protein name (if any)
            st.session_state.protein_data = [
                p for p in st.session_state.protein_data if p["protein_name"] != entry["protein_name"]
            ]
            st.session_state.protein_data.append(entry)

            # Show confirmation
            st.success(f"✅ Protein '{protein_name}' logged.")
            with st.expander("View Submitted Data"):
                st.json(entry)

            # Ask to continue
            next_action = st.radio("Would you like to add another protein?", ["Yes", "No"], key=f"next_{st.session_state.protein_count}")
            if next_action == "Yes":
                st.session_state.protein_count += 1
                st.experimental_rerun()
            else:
                # Submit everything to GitHub
                st.subheader("Submitting Data to GitHub...")
                all_data = []
                for p in st.session_state.protein_data:
                    all_data.append({
                        **st.session_state.paper_details,
                        **p
                    })
                df = pd.DataFrame(all_data)
                st.dataframe(df)

                g = authenticate_github()
                if g:
                    # FIX: Use the same repo_name and csv_path variables
                    repo = get_repository(g, repo_name)
                    if repo:
                        success, message = update_csv_in_github(repo, csv_path, df)
                        if success:
                            st.success("Data submitted successfully to GitHub.")
                        else:
                            st.error(f"Error: {message}")
                else:
                    st.error("GitHub authentication failed.")

# Function to make this module importable from the main app
def show_data_entry_page():
    """
    This function exposes the main functionality to be imported by app.py
    """
    main()

# -------------- RUN --------------
if __name__ == "__main__":
    main()
