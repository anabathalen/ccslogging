# Try to update the GitHub repository
g = authenticate_github()
if g:
    repo = get_repository(g, st.secrets["REPO_NAME"])
    if repo:
        success, message = update_csv_in_github(repo, st.secrets["CSV_PATH"], df)
        if success:
            st.success(message)
            st.session_state.show_full_form = False
            st.session_state.pop('new_doi', None)
            st.experimental_rerun()
        else:
            st.error(message)
    else:
        st.error("Repository configuration issue.")
else:
    st.error("GitHub authentication failed. Check your Streamlit secrets.")

