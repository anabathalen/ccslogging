# app.py - Main application file
import streamlit as st
import pandas as pd
import os

# Import page modules
from pages.data_entry import show_data_entry_page
from pages.data_browser import show_data_browser_page

# Import authentication module
from auth import check_password, is_admin, logout

# Constants
LOCAL_DATA_PATH = "data/local_data.csv"

# Set page configuration
st.set_page_config(
    page_title="Collision Cross Section Database",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Set up styling
st.markdown("""
<style>
    .main {
        padding: 2rem;
    }
    .stForm {
        background-color: #f8f9fa;
        padding: 2rem;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    h1 {
        color: #1f77b4;
    }
    .doi-check {
        background-color: #e9f7ef;
        padding: 1.5rem;
        border-radius: 8px;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

def load_local_data():
    """Load existing data from local CSV if it exists."""
    if os.path.exists(LOCAL_DATA_PATH):
        try:
            return pd.read_csv(LOCAL_DATA_PATH)
        except Exception as e:
            st.error(f"Error loading local data: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

def main():
    """Main function to run the Streamlit app."""
    if not check_password():
        return

    # Sidebar: Logout + Navigation
    with st.sidebar:
        logout()
        st.header("Navigation")
        page = st.radio("Select Page", ["Data Entry", "Browse Database"])
        st.session_state.page = page

    # Load local data
    existing_data = load_local_data()

    # Main content based on selected page
    if st.session_state.page == "Data Entry":
        show_data_entry_page()
    else:
        show_data_browser_page(existing_data)

if __name__ == "__main__":
    if "show_full_form" not in st.session_state:
        st.session_state.show_full_form = False
    if "page" not in st.session_state:
        st.session_state.page = "Data Entry"
    if "password_correct" not in st.session_state:
        st.session_state.password_correct = False

    main()

