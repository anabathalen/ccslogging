import streamlit as st
import pandas as pd
import re
from datetime import datetime
from utils.github_utils import authenticate_github, get_repository, update_csv_in_github, get_existing_data
import requests

# ---------- DOI Validation ----------
def validate_doi(doi):
    pattern = r'^10\.\d{4,9}/[-._;()/:A-Z0-9]+$'
    return re.match(pattern, doi, re.IGNORECASE) is not None

# ---------- Check for Existing DOI ----------
def check_doi_exists(existing_data, doi):
    if existing_data is None or existing_data.empty:
        return False
    return doi in existing_data['doi'].values

# ---------- Fetch Paper Metadata ----------
def get_paper_details(doi):
    try:
        url = f"https://api.crossref.org/works/{doi}"
        response = requests.get(url)
        if response.status_code != 200:
            return None
        item = response.json()['message']
        return {
            "paper_title": item.get("title", ["Unknown Title"])[0],
            "authors": ', '.join([f"{a.get('given', '')} {a.get('family', '')}" for a in item.get("author", [])]),
            "doi": doi,
            "publication_year": item.get("issued", {}).get("date-parts", [[None]])[0][0],
            "journal": item.get("container-title", ["Unknown Journal"])[0]
        }
    except Exception:
        return None

# ---------- Main Entry Point ----------
def main():
    st.title("Collision Cross Section Logging")

    repo_name = st.secrets.get("REPO_NAME", "anabathalen/ccslogging")
    csv_path = st.secrets.get("CSV_PATH", "data/ccs_data.csv")
    existing_data = get_existing_data(repo_name, csv_path)

    # State Initialization
    if "protein_data" not in st.session_state:
        st.session_state.protein_data = {}
    if "protein_count" not in st.session_state:
        st.session_state.protein_count = 1
    if "show_form" not in st.session_state:
        st.session_state.show_form = False

    # ---------- DOI STEP ----------
    with st.expander("Step 1: Check DOI", expanded=True):
        doi_input = st.text_input("Enter DOI (e.g., 10.1021/example)")
        if st.button("Check DOI"):
            if not validate_doi(doi_input):
                st.error("Invalid DOI format.")
            elif check_doi_exists(existing_data, doi_input):
                st.warning("This DOI already exists in the database.")
            else:
                details = get_paper_details(doi_input)
                if not details:
                    st.error("Failed to fetch paper details.")
                else:
                    st.session_state.paper_details = details
                    st.session_state.show_form = True
                    st.success("DOI is valid. Proceed to protein logging.")

    # ---------- PROTEIN ENTRY FORM ----------
    if st.session_state.get("show_form", False):
        st.header(f"Log Protein {st.session_state.protein_count}")

        with st.form(f"protein_form_{st.session_state.protein_count}"):
            # Required Fields
            protein_name = st.text_input("Protein/Ion Name").strip()
            if not protein_name:
                st.warning("Protein Name is required to proceed.")

            instrument = st.selectbox("Instrument Used", [
                "Waters Synapt", "Waters Cyclic", "Waters Vion", "Agilent 6560", "Bruker timsTOF", "Other (enter)"
            ])
            ims_type = st.selectbox("IMS Type", ["TWIMS", "DTIMS", "CYCLIC", "TIMS", "FAIMS", "Other (enter)"])
            drift_gas = st.selectbox("Drift Gas", ["Nitrogen", "Helium", "Argon", "Other"])
            if drift_gas == "Other":
                drift_gas = st.text_input("Specify Drift Gas")

            polarity = st.radio("Polarity (Ionization Mode)", ["Positive", "Negative"])

            # Optional Identifiers
            st.markdown("#### Optional Protein Identifiers (Leave blank if not available)")
            uniprot_id = st.text_input("Uniprot ID")
            pdb_id = st.text_input("PDB ID")
            protein_sequence = st.text_area("Protein Sequence")
            sequence_mass = st.number_input("Sequence Mass (Da)", min_value=0.0, format="%.2f")
            measured_mass = st.number_input("Measured Mass (Da)", min_value=0.0, format="%.2f")

            native = st.radio("Is this a native measurement?", ["Yes", "No"])
            subunit_count = st.number_input("Number of Non-Covalently Linked Subunits", min_value=1, step=1)
            oligomer_type = st.radio("Oligomer Type (if applicable)", ["", "Homo-oligomer", "Hetero-oligomer"])

            # CCS Data
            num_ccs = st.number_input("Number of CCS values to log", min_value=1, step=1)
            ccs_data = []
            for i in range(num_ccs):
                charge = st.number_input(f"Charge State {i+1}", min_value=1, step=1, key=f"charge_{i}")
                ccs = st.number_input(f"CCS Value for Charge State {i+1} (Å²)", min_value=0.0, format="%.2f", key=f"ccs_{i}")
                ccs_data.append((charge, ccs))

            notes = st.text_area("Additional Notes")

            # Submit Button
            ready = st.form_submit_button("Ready to Submit")

        # ---------- PROCESS SUBMISSION ----------
        if ready:
            if not protein_name:
                st.error("Protein name is required.")
                st.stop()

            # Save entry in dict to avoid duplicates
            st.session_state.protein_data[protein_name] = {
                "protein_name": protein_name,
                "instrument": instrument,
                "ims_type": ims_type,
                "drift_gas": drift_gas,
                "polarity": polarity,
                "uniprot": uniprot_id or None,
                "pdb": pdb_id or None,
                "sequence": protein_sequence or None,
                "sequence_mass": sequence_mass if sequence_mass > 0 else None,
                "measured_mass": measured_mass if measured_mass > 0 else None,
                "native_measurement": native,
                "subunit_count": subunit_count,
                "oligomer_type": oligomer_type or None,
                "ccs_data": ccs_data,
                "additional_notes": notes or None
            }

            st.success(f"✅ Protein '{protein_name}' logged.")
            st.json(st.session_state.protein_data[protein_name])

            next_action = st.radio("Add another protein?", ["Yes", "No"], key=f"next_{st.session_state.protein_count}")
            if next_action == "Yes":
                st.session_state.protein_count += 1
                st.experimental_rerun()
            else:
                # Submit all data
                st.subheader("Submitting to GitHub...")

                # Prepare DataFrame
                full_data = []
                for entry in st.session_state.protein_data.values():
                    full_data.append({**st.session_state.paper_details, **entry})
                df = pd.DataFrame(full_data)

                # Merge with existing
                if existing_data is not None and not existing_data.empty:
                    df = pd.concat([existing_data, df], ignore_index=True)

                st.dataframe(df)

                g = authenticate_github()
                if g:
                    repo = get_repository(g, repo_name)
                    if repo:
                        success, msg = update_csv_in_github(repo, csv_path, df)
                        if success:
                            st.success("✅ Data submitted to GitHub.")
                        else:
                            st.error(f"GitHub update failed: {msg}")
                    else:
                        st.error("Could not access GitHub repo.")
                else:
                    st.error("GitHub authentication failed.")

# ---------- Expose for Main App ----------
def show_data_entry_page():
    main()

if __name__ == "__main__":
    main()
