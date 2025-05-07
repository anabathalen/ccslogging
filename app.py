# app.py - Main application file
import streamlit as st
import pandas as pd
from github import Github
import github
import io

# Import page modules
from pages.data_entry import show_data_entry_page
from pages.data_browser import show_data_browser_page
from utils.github_utils import authenticate_github, get_repository, get_existing_data

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

def main():
    """Main function to run the Streamlit app."""
    # Sidebar for GitHub configuration
    with st.sidebar:
        st.header("Database Configuration")
        
        # GitHub configuration
        if "repo_name" not in st.session_state:
            st.session_state.repo_name = ""
        if "csv_path" not in st.session_state:
            st.session_state.csv_path = "data/collision_cross_sections.csv"
            
        repo_name = st.text_input("Repository Name (format: username/repo)", value=st.session_state.repo_name)
        csv_path = st.text_input("CSV File Path", value=st.session_state.csv_path)
        
        # Save configs to session state
        st.session_state.repo_name = repo_name
        st.session_state.csv_path = csv_path
        
        if st.button("Test GitHub Connection"):
            g = authenticate_github()
            if g and repo_name:
                repo = get_repository(g, repo_name)
                if repo:
                    st.success(f"Successfully connected to {repo_name}")
                    st.session_state.github_configured = True
                    
                    # Try to load existing data
                    existing_data = get_existing_data(repo, csv_path)
                    if existing_data is not None:
                        st.session_state.existing_data = existing_data
                        if existing_data.empty:
                            st.info("No existing data found. Database will be created on first submission.")
                        else:
                            st.info(f"Successfully loaded {len(existing_data)} entries from database.")
                else:
                    st.error("Could not access repository. Check the repository name and your permissions.")
                    st.session_state.github_configured = False
            else:
                st.error("Please provide both GitHub token and repository name.")
                st.session_state.github_configured = False
        
        # Navigation
        st.header("Navigation")
        page = st.radio("Select Page", ["Data Entry", "Browse Database"])
        st.session_state.page = page
    
    # Main content based on selected page
    if st.session_state.get("github_configured", False):
        existing_data = st.session_state.get("existing_data", None)
        
        if st.session_state.page == "Data Entry":
            show_data_entry_page(existing_data)
        else:  # Browse Database
            show_data_browser_page(existing_data)
    else:
        st.title("Collision Cross Section Database")
        st.info("⚙️ Please configure your GitHub connection in the sidebar to get started.")
        st.markdown("""
        ### Welcome to the Collision Cross Section Database App
        
        This application allows you to:
        
        1. **Log new collision cross section data** from scientific papers
        2. **Browse and search** the existing database
        3. **Export data** for analysis
        
        To begin, please configure your GitHub repository connection in the sidebar.
        """)

if __name__ == "__main__":
    # Initialize session state variables
    if "github_configured" not in st.session_state:
        st.session_state.github_configured = False
    if "show_full_form" not in st.session_state:
        st.session_state.show_full_form = False
    if "page" not in st.session_state:
        st.session_state.page = "Data Entry"
        
    main()
