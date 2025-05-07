import streamlit as st
import os

# Define credentials - for development only
# In production, use environment variables (shown below)
default_credentials = {
    "username": ["admin", "user1"],
    "password": ["admin123", "user123"]
}

def get_credentials():
    """Get credentials from environment variables or use defaults for development"""
    credentials = {"username": [], "password": []}
    
    # Check for environment variables
    users_env = os.environ.get("AUTH_USERNAMES", "")
    passwords_env = os.environ.get("AUTH_PASSWORDS", "")
    
    if users_env and passwords_env:
        # Using environment variables (more secure for production)
        credentials["username"] = users_env.split(",")
        credentials["password"] = passwords_env.split(",")
    else:
        # Using default credentials for development
        credentials = default_credentials
        
    return credentials

def check_password():
    """Returns `True` if the user has entered correct credentials."""
    
    # Get credentials
    credentials = get_credentials()
    
    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["username"] in credentials["username"]:
            idx = credentials["username"].index(st.session_state["username"])
            if st.session_state["password"] == credentials["password"][idx]:
                st.session_state["password_correct"] = True
                st.session_state["current_user"] = st.session_state["username"]
                del st.session_state["password"]  # Don't store password
                return True
            else:
                st.session_state["password_correct"] = False
        else:
            st.session_state["password_correct"] = False
        return False

    # Return True if the password is validated
    if st.session_state.get("password_correct", False):
        return True

    # Show login inputs and validate
    st.title("CCS Logging")
    st.subheader("Login")
    
    # Create login form
    col1, col2 = st.columns([1, 1])
    col1.text_input("Username", key="username")
    col2.text_input("Password", type="password", key="password")
    
    if st.button("Login"):
        if password_entered():
            st.success("Logged in successfully")
            st.experimental_rerun()
        else:
            st.error("Invalid username or password")
    
    return False

def is_admin():
    """Check if current user is admin"""
    return st.session_state.get("current_user") == "admin"

def logout():
    """Log out the current user"""
    if st.button("Logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.experimental_rerun()
