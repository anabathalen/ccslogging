# pages/data_browser.py - Data browser page
import streamlit as st
import pandas as pd
import base64

def show_data_browser_page(existing_data):
    """Display interface for browsing the database."""
    st.title("Browse Collision Cross Section Database")
    
    if existing_data is None or existing_data.empty:
        st.info("No data found in the database. Please add some entries first.")
        return
        
    # Display stats
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Entries", len(existing_data))
    with col2:
        st.metric("Unique Papers", len(existing_data['doi'].unique()))
    with col3:
        st.metric("Unique Molecules", len(existing_data['molecule'].unique()))
    
    # Filters
    st.subheader("Filter Data")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        journals = ["All"] + sorted(existing_data['journal'].unique().tolist())
        selected_journal = st.selectbox("Journal", journals)
    
    with col2:
        methods = ["All"] + sorted(existing_data['method'].unique().tolist())
        selected_method = st.selectbox("Method", methods)
        
    with col3:
        gases = ["All"] + sorted(existing_data['buffer_gas'].unique().tolist())
        selected_gas = st.selectbox("Buffer Gas", gases)
    
    # Year range slider if we have publication years
    if 'publication_year' in existing_data.columns:
        min_year = int(existing_data['publication_year'].min())
        max_year = int(existing_data['publication_year'].max())
        year_range = st.slider("Publication Year Range", 
                              min_value=min_year, 
                              max_value=max_year, 
                              value=(min_year, max_year))
    
    # Apply filters
    filtered_data = existing_data.copy()
    if selected_journal != "All":
        filtered_data = filtered_data[filtered_data['journal'] == selected_journal]
    if selected_method != "All":
        filtered_data = filtered_data[filtered_data['method'] == selected_method]
    if selected_gas != "All":
        filtered_data = filtered_data[filtered_data['buffer_gas'] == selected_gas]
    if 'publication_year' in existing_data.columns:
        filtered_data = filtered_data[(filtered_data['publication_year'] >= year_range[0]) & 
                                     (filtered_data['publication_year'] <= year_range[1])]
    
    # Search
    search_term = st.text_input("Search by molecule, author, or title")
    if search_term:
        search_mask = (
            filtered_data['molecule'].str.contains(search_term, case=False, na=False) |
            filtered_data['authors'].str.contains(search_term, case=False, na=False) |
            filtered_data['paper_title'].str.contains(search_term, case=False, na=False)
        )
        filtered_data = filtered_data[search_mask]
    
    # Data visualization options
    st.subheader("Data Visualization")
    viz_option = st.selectbox("Choose visualization", 
                             ["None", "CCS Distribution", "Publications by Year", "Methods Comparison"])
    
    if viz_option != "None" and not filtered_data.empty:
        if viz_option == "CCS Distribution":
            st.subheader("Distribution of Collision Cross Section Values")
            # Create a histogram of CCS values
            hist_values = filtered_data['ccs_value'].dropna()
            if not hist_values.empty:
                st.bar_chart(hist_values.value_counts(bins=20).sort_index())
            else:
                st.info("No CCS values available for visualization")
                
        elif viz_option == "Publications by Year" and 'publication_year' in filtered_data.columns:
            st.subheader("Publications by Year")
            year_counts = filtered_data['publication_year'].value_counts().sort_index()
            st.bar_chart(year_counts)
            
        elif viz_option == "Methods Comparison":
            st.subheader("Measurement Methods Used")
            method_counts = filtered_data['method'].value_counts()
            st.bar_chart(method_counts)
    
    # Display data
    st.subheader(f"Results ({len(filtered_data)} entries)")
    
    # Allow column selection
    all_columns = filtered_data.columns.tolist()
    default_columns = ["paper_title", "authors", "doi", "molecule", "ccs_value", "method", "buffer_gas"]
    # Make sure all default columns exist in the dataframe
    default_columns = [col for col in default_columns if col in all_columns]
    
    selected_columns = st.multiselect("Select columns to display", all_columns, default=default_columns)
    if selected_columns:
        st.dataframe(filtered_data[selected_columns])
    else:
        st.dataframe(filtered_data)
    
    # Download options
    csv = filtered_data.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    st.download_button(
        label="Download Results as CSV",
        data=csv,
        file_name="collision_cross_sections.csv",
        mime="text/csv"
    )
    
    # DOI summary for easier references
    if len(filtered_data['doi'].unique()) > 0:
        st.subheader("Paper References")
        dois = filtered_data[['doi', 'paper_title', 'authors', 'publication_year']].drop_duplicates()
        st.dataframe(dois)
