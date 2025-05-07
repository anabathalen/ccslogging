# utils/github_utils.py - GitHub integration utilities
import streamlit as st
import pandas as pd
from github import Github
import github
from datetime import datetime
import io

def authenticate_github():
    """Authenticate with GitHub using personal access token."""
    token = st.secrets.get("github_token", None)
    if token is None:
        token = st.text_input("Enter your GitHub Personal Access Token", type="password")
        if not token:
            st.warning("Please enter a valid GitHub token to proceed.")
            return None
    return Github(token)

def get_repository(g, repo_name):
    """Get the GitHub repository."""
    try:
        return g.get_repo(repo_name)
    except github.GithubException as e:
        st.error(f"Error accessing repository: {e}")
        return None

def get_existing_data(repo, file_path):
    """Get existing data from CSV file in GitHub repository."""
    try:
        contents = repo.get_contents(file_path)
        return pd.read_csv(io.StringIO(contents.decoded_content.decode("utf-8")))
    except github.GithubException as e:
        if e.status == 404:  # File not found
            return pd.DataFrame()
        else:
            st.error(f"Error fetching data: {e}")
            return None
    except Exception as e:
        st.error(f"Error reading data: {e}")
        return None

def update_csv_in_github(repo, file_path, data_df):
    """Update CSV file in GitHub repository."""
    try:
        # Try to get the file content first
        try:
            contents = repo.get_contents(file_path)
            existing_data = pd.read_csv(io.StringIO(contents.decoded_content.decode("utf-8")))
            
            # Append new data
            updated_data = pd.concat([existing_data, data_df], ignore_index=True)
            
            # Prepare commit message
            commit_message = f"Update collision cross section data - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            # Convert DataFrame to CSV string
            csv_content = updated_data.to_csv(index=False)
            
            # Update file in repository
            repo.update_file(
                path=contents.path,
                message=commit_message,
                content=csv_content,
                sha=contents.sha
            )
            return True, "Data successfully updated in the repository."
            
        except github.GithubException as e:
            if e.status == 404:  # File not found
                # Create new file
                commit_message = f"Create collision cross section data file - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                csv_content = data_df.to_csv(index=False)
                repo.create_file(
                    path=file_path,
                    message=commit_message,
                    content=csv_content
                )
                return True, "New data file created in the repository."
            else:
                raise e
                
    except Exception as e:
        return False, f"Error updating repository: {str(e)}"
