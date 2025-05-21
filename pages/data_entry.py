# pages/data_entry.py

import streamlit as st
import pandas as pd

# Initialize session state for protein data
if "protein_data" not in st.session_state:
    st.session_state.protein_data = {}

if "show_full_form" not in st.session_state:
    st.session_state.show_full_form = False

def show_data_entry_page(existing_data: pd.DataFrame):
    st.title("Protein CCS Data Entry")

    st.markdown("Enter metadata for each protein below. Leave optional fields blank if not applicable.")

    with st.form(key="protein_entry_form"):
        protein_name = st.text_input("Protein Name*", key="protein_name_input")
        instrument = st.text_input("Instrument")
        ims_type = st.text_input("IMS Type")
        drift_gas = st.text_input("Drift Gas")
        polarity = st.selectbox("Polarity", ["", "Positive", "Negative"])

        charge_states = st.text_area("Charge States and CCS values",
                                     help="Enter charge state and CCS pairs like:\n+5  1234\n+6  1300")

        submit_button = st.form_submit_button("Ready to Submit")

        if submit_button:
            if not protein_name:
                st.warning("Protein name is required.")
                st.stop()

            # Parse charge states
            parsed_charges = []
            for line in charge_states.strip().split("\n"):
                if line.strip():
                    try:
                        charge, ccs = line.strip().split()
                        parsed_charges.append({"charge_state": charge, "ccs": float(ccs)})
                    except ValueError:
                        st.error(f"Could not parse line: '{line}'. Expected format: +5 1234")
                        st.stop()

            # Save entry keyed by protein name
            st.session_state.protein_data[protein_name] = {
                "protein_name": protein_name,
                "instrument": instrument,
                "ims_type": ims_type,
                "drift_gas": drift_gas,
                "polarity": polarity,
                "ccs_data": parsed_charges,
            }

            st.success(f"Protein entry for '{protein_name}' saved.")

    # Show current entries
    if st.session_state.protein_data:
        st.markdown("---")
        st.subheader("Current Protein Entries")
        for name, entry in st.session_state.protein_data.items():
            st.markdown(f"**{name}**")
            st.json(entry)

# Only run this block if the file is executed directly (not imported)
if __name__ == "__main__":
    show_data_entry_page(existing_data=pd.DataFrame())
