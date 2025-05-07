from github import Github
import pandas as pd
from io import StringIO
import streamlit as st
import base64

def authenticate_github():
    """Authenticate to GitHub using a token stored in Streamlit secrets."""
    token = st.secrets.get("GITHUB_TOKEN")
    if token:
        return Github(token)
    return None

def get_repository(g, repo_name):
    """Get the GitHub repository object."""
    try:
        return g.get_repo(repo_name)
    except Exception as e:
        st.error(f"Failed to access repository: {e}")
        return None

def get_existing_data(repo, csv_path):
    """Download and return the existing CSV data from GitHub as a DataFrame."""
    try:
        file = repo.get_contents(csv_path)
        content = file.decoded_content.decode("utf-8")
        return pd.read_csv(StringIO(content))
    except Exception as e:
        st.warning(f"Could not load existing data: {e}")
        return pd.DataFrame()

def update_csv_in_github(repo, csv_path, new_data):
    """Update or create the CSV file in GitHub with new data."""
    try:
        # Load existing data
        existing_df = get_existing_data(repo, csv_path)
        updated_df = pd.concat([existing_df, new_data], ignore_index=True)

        # Convert DataFrame to CSV string
        csv_string = updated_df.to_csv(index=False)
        encoded_content = csv_string.encode("utf-8")

        # Commit update
        try:
            contents = repo.get_contents(csv_path)
            repo.update_file(
                path=csv_path,
                message="Update CCS data via Streamlit app",
                content=encoded_content,
                sha=contents.sha
            )
        except:
            # File doesn't exist, so create it
            repo.create_file(
                path=csv_path,
                message="Create CCS database via Streamlit app",
                content=encoded_content
            )
        return True, "✅ Data successfully updated to GitHub."
    except Exception as e:
        return False, f"❌ Failed to update GitHub: {e}"

