def show_data_entry_page(existing_data):
    """Display data entry page for logging proteins and CCS data."""
    st.title("Collision Cross Section Data Entry")

    # ---------- DOI Section ----------
    with st.expander("DOI Check", expanded=True):
        st.markdown("### Check if paper already exists in database")
        col1, col2 = st.columns([3, 1])
        with col1:
            doi = st.text_input("Enter DOI (e.g., 10.1021/example)")
        with col2:
            check_button = st.button("Check DOI")

        # Handle DOI validation and database check
        if check_button and doi:
            if not validate_doi(doi):
                st.error("Invalid DOI format. Please enter a valid DOI.")
            else:
                paper_details = get_paper_details(doi)
                if check_doi_exists(existing_data, doi):
                    st.warning(f"This paper (DOI: {doi}) already exists in the database!")
                    entries = existing_data[existing_data['doi'] == doi]
                    st.dataframe(entries)
                else:
                    st.success("DOI is valid and not in database. Proceed to data entry.")
                    st.session_state.new_doi = doi
                    st.session_state.show_full_form = True
                    st.session_state.paper_details = paper_details
                    st.session_state.protein_data = []

    # ---------- Main Protein Form ----------
    if st.session_state.get('show_full_form', False):
        st.header(f"Log Protein Data for Paper: {st.session_state.paper_details['paper_title']}")

        # Start the form; protein is only saved when "Ready to Submit" is pressed
        with st.form("protein_entry_form"):
            st.markdown("### Required Information")

            protein_name = st.text_input("Protein/Ion Name")

            instrument = st.selectbox("Instrument Used", [
                "Waters Synapt", "Waters Cyclic", "Waters Vion",
                "Agilent 6560", "Bruker timsTOF", "Other (enter)"
            ])

            ims_type = st.selectbox("IMS Type", ["TWIMS", "DTIMS", "CYCLIC", "TIMS", "FAIMS", "Other (enter)"])

            drift_gas = st.selectbox("Drift Gas", ["Nitrogen", "Helium", "Argon", "Other"])
            if drift_gas == "Other":
                drift_gas = st.text_input("Specify Drift Gas")

            # Polarity mode (positive or negative ion mode)
            polarity = st.radio("Polarity Mode", ["Positive", "Negative"])

            st.markdown("### Optional Protein Metadata (Leave blank if not available)")
            uniprot_id = st.text_input("Uniprot Identifier")
            pdb_id = st.text_input("PDB Identifier")
            protein_sequence = st.text_area("Protein Sequence")
            sequence_mass_value = st.number_input("Sequence Mass (Da)", min_value=0.0, value=0.0, format="%.2f")
            measured_mass_value = st.number_input("Measured Mass (Da)", min_value=0.0, value=0.0, format="%.2f")

            native_measurement = st.radio("Is this a native measurement?", ["Yes", "No"])

            subunit_count = st.number_input("Number of Non-Covalently Linked Subunits", min_value=1, step=1)
            oligomer_type = st.radio(
                "If this is an oligomer (subunit count > 1), is it a homo or hetero-oligomer?",
                ["", "Homo-oligomer", "Hetero-oligomer"]
            )

            st.markdown("### Collision Cross Section (CCS) Data")
            num_ccs_values = st.number_input("Number of CCS values for this protein", min_value=1, step=1)
            ccs_data = []
            for i in range(int(num_ccs_values)):
                charge = st.number_input(f"Charge State {i+1}", min_value=1, step=1, key=f"charge_{i}")
                ccs = st.number_input(f"CCS Value for Charge State {i+1} (Å²)", min_value=0.0, format="%.2f", key=f"ccs_{i}")
                ccs_data.append((charge, ccs))

            additional_notes = st.text_area("Additional Notes (e.g., sample details, conditions)")

            # Final submission button
            ready_to_submit = st.form_submit_button("Ready to Submit Protein")

        # Process form submission
        if ready_to_submit:
            protein_entry = {
                "protein_name": protein_name,
                "instrument": instrument,
                "ims_type": ims_type,
                "drift_gas": drift_gas,
                "polarity": polarity,
                "uniprot": uniprot_id or None,
                "pdb": pdb_id or None,
                "sequence": protein_sequence or None,
                "sequence_mass": sequence_mass_value or None,
                "measured_mass": measured_mass_value or None,
                "native_measurement": native_measurement,
                "subunit_count": subunit_count,
                "oligomer_type": oligomer_type or None,
                "ccs_data": ccs_data,
                "additional_notes": additional_notes
            }
            st.session_state.protein_data.append(protein_entry)
            st.success("Protein entry added.")

        # ---------- Display and Submission ----------
        if st.session_state.get('protein_data'):
            st.subheader("Review Entered Proteins")
            for idx, protein in enumerate(st.session_state.protein_data):
                st.markdown(f"#### Protein {idx+1}")
                st.json(protein)

            submit_all = st.button("Submit All Protein Data to GitHub")

            if submit_all:
                all_data = [
                    {**st.session_state.paper_details, **entry}
                    for entry in st.session_state.protein_data
                ]
                df = pd.DataFrame(all_data)
                st.dataframe(df)

                g = authenticate_github()
                if g:
                    repo = get_repository(g, st.secrets["REPO_NAME"])
                    if repo:
                        success, message = update_csv_in_github(repo, st.secrets["CSV_PATH"], df)
                        if success:
                            st.success(message)
                            st.session_state.show_full_form = False
                            st.session_state.protein_data = []
                        else:
                            st.error(message)
                    else:
                        st.error("Could not access GitHub repository.")
                else:
                    st.error("GitHub authentication failed.")
