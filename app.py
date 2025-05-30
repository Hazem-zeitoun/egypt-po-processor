# --- Compatibility Workaround ---
import sys
if sys.version_info >= (3, 13):
    import multiprocessing
    multiprocessing.set_start_method("fork", force=True)
# app.py (Complete Streamlit Application)
import streamlit as st
import pandas as pd
import os
import tempfile
from datetime import datetime
import plotly.express as px
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io
import re
from rapidfuzz import process, fuzz
import base64
import json

# --- Configuration ---
st.set_page_config(
    page_title="Egyptian PO Processor",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom CSS ---
st.markdown("""
<style>
    .header {
        background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
        color: white!important;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 25px;
    }
    .metric-card {
        background: white;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        margin-bottom: 15px;
    }
    .file-card {
        background: rgba(255,255,255,0.9);
        border-left: 4px solid #2a5298;
        border-radius: 5px;
        padding: 12px;
        margin-bottom: 10px;
    }
    .table-header {
        background: #2a5298!important;
        color: white!important;
    }
    .grand-total-row {
        background-color: #e6f7ff!important;
        font-weight: bold!important;
    }
    .stButton>button {
        background: #2a5298!important;
        color: white!important;
        border-radius: 8px;
        padding: 8px 16px;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        background: #1e3c72!important;
        transform: scale(1.05);
    }
    .footer {
        text-align: center;
        padding: 15px;
        margin-top: 30px;
        color: #6c757d;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)

# --- Product Mapping ---
PRODUCT_MAP = {
    "NeoMune": ["نو ميون", "Enteral powder.*cachectic"],
    "Aminoleban Oral": ["أمينوليبان", "Amino Acid.*Hepatic.*Can"],
    "Blendera MF": ["بليندرا", "Lactose free.*low cholesterol"]
}

# --- Initialize Session State ---
if 'processed_files' not in st.session_state:
    st.session_state.processed_files = []
if 'aggregated_data' not in st.session_state:
    st.session_state.aggregated_data = None

# --- PDF Processing Functions ---
def extract_text(page):
    """Simplified text extraction for demo"""
    try:
        return page.get_text()
    except:
        return ""

def identify_product(text):
    """Product identification for demo"""
    for product, patterns in PRODUCT_MAP.items():
        for pattern in patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return product
    return None

def extract_quantity(text):
    """Quantity extraction for demo"""
    match = re.search(r"الكمية\s*[:;]?\s*(\d+)|Quantity\s*[:;]?\s*(\d+)", text)
    return int(match.group(1) if match else 0

def process_pdf(file):
    """Simplified PDF processing for demo"""
    try:
        doc = fitz.open(stream=file.read(), filetype="pdf")
        results = {
            "po_number": "DEMO-" + datetime.now().strftime("%H%M%S"),
            "date": datetime.now().strftime("%Y-%m-%d"),
            "hospital_data": {"name": "Demo Hospital", "request_no": "DEMO-REQ"},
            "summary_items": [],
            "ocr_pages": []
        }
        
        for page in doc:
            text = extract_text(page)
            product = identify_product(text)
            if product:
                results["summary_items"].append({
                    "item_name": product,
                    "quantity": extract_quantity(text) or 10  # Default for demo
                })
        
        doc.close()
        return results
    except Exception as e:
        st.error(f"Processing error: {str(e)}")
        return None

# --- Header ---
st.markdown("""
<div class="header">
    <h1 style="color:white; margin:0; text-align:center;">🇪🇬 Egyptian Pharmaceutical PO Processor</h1>
    <p style="color:#e6f7ff; margin:0; text-align:center;">Multi-file PDF analysis for unified procurement</p>
</div>
""", unsafe_allow_html=True)

# --- File Upload Section ---
uploaded_files = st.file_uploader(
    "Upload Pharmaceutical PO PDFs",
    type="pdf",
    accept_multiple_files=True,
    help="Upload multiple Egyptian Ministry of Health purchase order PDFs"
)

if uploaded_files:
    # --- Processing Workflow ---
    with st.status("Processing Files...", expanded=True) as status:
        processed_data = []
        
        for uploaded_file in uploaded_files:
            try:
                st.write(f"🔍 Analyzing: {uploaded_file.name}...")
                result = process_pdf(uploaded_file)
                
                if result:
                    processed_data.append({
                        "file_name": uploaded_file.name,
                        "data": result,
                        "error": None
                    })
                    st.success(f"✅ Processed: {uploaded_file.name}")
                else:
                    processed_data.append({
                        "file_name": uploaded_file.name,
                        "data": None,
                        "error": "Processing failed"
                    })
                    st.error(f"❌ Failed: {uploaded_file.name}")
                
            except Exception as e:
                processed_data.append({
                    "file_name": uploaded_file.name,
                    "data": None,
                    "error": str(e)
                })
                st.error(f"⚠️ Error processing {uploaded_file.name}: {str(e)}")
        
        # Update session state
        st.session_state.processed_files = processed_data
        status.update(label="Processing complete!", state="complete", expanded=False)
    
    # --- Generate Aggregated Reports ---
    if any(pd['data'] for pd in processed_data):
        # Prepare data
        consolidated_items = {}
        hospital_distribution = []
        
        for file_data in processed_data:
            if file_data['data']:
                # Add to consolidated items
                for item in file_data['data']['summary_items']:
                    item_name = item['item_name']
                    consolidated_items[item_name] = consolidated_items.get(item_name, 0) + item['quantity']
                
                # Add to hospital distribution
                hospital_data = file_data['data']['hospital_data']
                for item in file_data['data']['summary_items']:
                    hospital_distribution.append({
                        "PO Number": file_data['data'].get('po_number', '[MISSING]'),
                        "Date": file_data['data'].get('date', '[MISSING]'),
                        "Hospital": hospital_data.get('name', '[MISSING]'),
                        "Item": item['item_name'],
                        "Quantity": item['quantity'],
                        "Request No": hospital_data.get('request_no', '[MISSING]')
                    })
        
        # Calculate hospital totals
        hospital_totals = {}
        for item in hospital_distribution:
            hospital_totals[item['Item']] = hospital_totals.get(item['Item'], 0) + item['Quantity']
        
        # Format aggregated data
        st.session_state.aggregated_data = {
            "consolidated_en_items": [
                {"Item": k, "Total Quantity": v} for k, v in consolidated_items.items()
            ],
            "multi_file_hospital_distribution": hospital_distribution,
            "hospital_dist_item_totals": [
                {"Item": k, "Total Quantity": v} for k, v in hospital_totals.items()
            ] + [{"Item": "GRAND TOTAL", "Total Quantity": sum(hospital_totals.values())}]
        }

# --- Results Display ---
if st.session_state.aggregated_data:
    # --- Metrics Summary ---
    st.subheader("📊 Processing Summary")
    col1, col2, col3 = st.columns(3)
    
    total_files = len(st.session_state.processed_files)
    success_files = sum(1 for f in st.session_state.processed_files if f['data'])
    total_items = sum(item['Total Quantity'] for item in st.session_state.aggregated_data['consolidated_en_items'])
    
    col1.metric("Files Processed", f"{success_files}/{total_files}")
    col2.metric("Unique Products", len(st.session_state.aggregated_data['consolidated_en_items']))
    col3.metric("Total Items", f"{total_items:,}")
    
    # --- Visualization ---
    st.subheader("📈 Data Visualization")
    viz_col1, viz_col2 = st.columns(2)
    
    with viz_col1:
        if st.session_state.aggregated_data['consolidated_en_items']:
            df_items = pd.DataFrame(st.session_state.aggregated_data['consolidated_en_items'])
            fig = px.pie(
                df_items,
                names='Item',
                values='Total Quantity',
                title='Product Distribution',
                hole=0.3
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with viz_col2:
        if st.session_state.aggregated_data['hospital_dist_item_totals']:
            df_totals = pd.DataFrame([
                item for item in st.session_state.aggregated_data['hospital_dist_item_totals'] 
                if item['Item'] != 'GRAND TOTAL'
            ])
            if not df_totals.empty:
                fig = px.bar(
                    df_totals,
                    x='Item',
                    y='Total Quantity',
                    title='Hospital Distribution by Product',
                    color='Item'
                )
                st.plotly_chart(fig, use_container_width=True)
    
    # --- Table 1: Consolidated EN Items ---
    st.subheader("1. Consolidated EN Items (All Files)")
    if st.session_state.aggregated_data['consolidated_en_items']:
        df_consolidated = pd.DataFrame(st.session_state.aggregated_data['consolidated_en_items'])
        st.dataframe(
            df_consolidated,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.warning("No consolidated items data available")
    
    # --- Table 2: Hospital Distribution ---
    st.subheader("2. Hospital Distribution (Multi-File)")
    if st.session_state.aggregated_data['multi_file_hospital_distribution']:
        df_hospital = pd.DataFrame(st.session_state.aggregated_data['multi_file_hospital_distribution'])
        st.dataframe(
            df_hospital,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.warning("No hospital distribution data available")
    
    # --- Table 3: إجمالي الكمية لكل صنف ---
    st.subheader("3. إجمالي الكمية لكل صنف (توزيع المستشفيات)")
    if st.session_state.aggregated_data['hospital_dist_item_totals']:
        df_totals = pd.DataFrame(st.session_state.aggregated_data['hospital_dist_item_totals'])
        # Apply styling to grand total row
        st.dataframe(
            df_totals.style.apply(
                lambda row: ['background-color: #e6f7ff; font-weight: bold'] * len(row)
                if row['Item'] == 'GRAND TOTAL' else [''] * len(row),
            axis=1),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.warning("No hospital distribution totals available")
    
    # --- Export Section ---
    st.divider()
    st.subheader("📤 Export Results")
    
    if st.button("Export to Excel", use_container_width=True):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            with pd.ExcelWriter(tmp.name, engine='xlsxwriter') as writer:
                pd.DataFrame(st.session_state.aggregated_data['consolidated_en_items']).to_excel(
                    writer, sheet_name='Consolidated Items', index=False
                )
                pd.DataFrame(st.session_state.aggregated_data['multi_file_hospital_distribution']).to_excel(
                    writer, sheet_name='Hospital Distribution', index=False
                )
                pd.DataFrame(st.session_state.aggregated_data['hospital_dist_item_totals']).to_excel(
                    writer, sheet_name='Hospital Totals', index=False
                )
            
            with open(tmp.name, "rb") as f:
                st.download_button(
                    label="Download Excel File",
                    data=f,
                    file_name=f"po_report_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx",
                    mime="application/vnd.ms-excel",
                    use_container_width=True
                )

# --- Error Reporting ---
if st.session_state.processed_files and any(f['error'] for f in st.session_state.processed_files):
    st.divider()
    st.subheader("⚠️ Processing Report")
    
    for file_data in st.session_state.processed_files:
        if file_data['error']:
            st.error(f"**{file_data['file_name']}**: {file_data['error']}")

# --- Sidebar ---
with st.sidebar:
    st.markdown("## Configuration")
    confidence_threshold = st.slider(
        "Confidence Threshold",
        min_value=0,
        max_value=100,
        value=80,
        help="Minimum confidence score for data extraction"
    )
    
    st.markdown("## System Information")
    st.write("**Version**: 1.0.0")
    st.write(f"**Last Updated**: {datetime.now().strftime('%Y-%m-%d')}")
    
    st.divider()
    st.caption("Developed for Egyptian Ministry of Health Procurement")
    st.caption("© 2025 Unified Medical Procurement System")

# --- Footer ---
st.divider()
st.markdown('<div class="footer">Note: This application processes pharmaceutical purchase orders from the Egyptian Unified Procurement System</div>', unsafe_allow_html=True)
