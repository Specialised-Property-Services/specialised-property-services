import time
import requests
import streamlit as st
import pandas as pd
from dateutil.parser import parse
from fuzzywuzzy import fuzz
import json
import os

# Streamlit Secrets (used on Streamlit Cloud)
CLIENT_ID = st.secrets["simpro_client_id"]
CLIENT_SECRET = st.secrets["simpro_client_secret"]
SIMPRO_DOMAIN = f"https://{st.secrets['simpro_tenant']}.simprosuite.com"
SIMPRO_API_BASE = "https://api-uk.simprocloud.com"

MATCH_FILE = "confirmed_matches.json"

# Retry wrapper for API GETs
def safe_get(url, headers, retries=3, timeout=10):
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            st.warning(f"⏳ Attempt {attempt + 1}/{retries} failed: {e}")
            time.sleep(2)
    st.error(f"❌ Failed to get data from Simpro after {retries} attempts.")
    return None

# Simpro OAuth2 token request
def get_access_token():
    token_url = f"{SIMPRO_DOMAIN}/oauth2/token"
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = {
        'grant_type': 'client_credentials',
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET
    }

    try:
        response = requests.post(token_url, headers=headers, data=data, timeout=10)
        response.raise_for_status()
        return response.json()['access_token']
    except Exception as e:
        st.error(f"❌ Failed to get token: {e}")
        return None

def get_headers():
    token = get_access_token()
    if not token:
        st.stop()
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

def get_company_id(headers):
    url = f"{SIMPRO_API_BASE}/api/v1.0/companies"
    st.write(f"🔗 Requesting company info from: {url}")

    response = safe_get(url, headers)
    if not response:
        return None

    try:
        data = response.json()
    except:
        st.error("❌ Could not decode company info JSON.")
        return None

    if not data:
        st.error("⚠️ No companies returned.")
        return None

    st.success(f"✅ Got company ID: {data[0]['ID']}")
    return data[0]['ID']

def get_all_contacts(headers):
    st.write("📞 Fetching contacts...")
    company_id = get_company_id(headers)
    if not company_id:
        return []

    contacts = []
    page = 1

    while True:
        url = f"{SIMPRO_API_BASE}/api/v1.0/companies/{company_id}/contacts?page={page}&pageSize=100"
        st.write(f"📄 Page {page}")
        response = safe_get(url, headers)
        if not response:
            return []

        page_data = response.json()
        if not page_data:
            break

        contacts.extend(page_data)
        page += 1

    st.success(f"✅ Retrieved {len(contacts)} contacts.")
    return contacts

def load_confirmed_matches():
    if os.path.exists(MATCH_FILE):
        with open(MATCH_FILE, "r") as f:
            return json.load(f)
    return {}

# Dummy contact creation (stub for now)
def create_contact(first, last, mobile, headers):
    st.info(f"🧪 Would create contact: {first} {last}")
    return {"ID": f"dummy_{first}_{last}"}

# Dummy site creation (stub for now)
def create_site(job_name, address, city, postcode, cid, headers):
    return {"ID": f"site_{cid}_{job_name}"}

# Dummy job creation (stub for now)
def create_job(site_id, cid, job_name, date, notes, job_count, headers):
    return {"ID": f"job_{cid}_{job_name}"}

# Dummy add charge (stub for now)
def add_charge_to_job(job_id, description, charge_total, headers):
    return True

# Dummy matching logic (stub)
def match_contact(contacts, first, last):
    for c in contacts:
        if c.get("FirstName", "").lower() == first.lower() and c.get("LastName", "").lower() == last.lower():
            return c
    return None

# Dummy fuzzy match
def fuzzy_match_contact(contacts, first, last, row_index):
    for c in contacts:
        if fuzz.ratio(first.lower(), c.get("FirstName", "").lower()) > 80 and \
           fuzz.ratio(last.lower(), c.get("LastName", "").lower()) > 80:
            return c
    return None

# --- UI ---

st.title("🔐 Simpro Uploader (Streamlit Edition)")
uploaded_file = st.file_uploader("Upload Excel File", type=[".xlsx"])

if 'confirmed_matches' not in st.session_state:
    st.session_state.confirmed_matches = load_confirmed_matches()

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    st.success("File loaded successfully.")

    headers = list(df.columns)
    expected = [
        "W/O First Name", "W/O Last Name", "W/O Mobile", "Contract Number", "Date Required",
        "Address Of Visit", "City of Visit", "Postcode", "Shutter required y/n", "Lock type"
    ]

    col_map = {}
    for target in expected:
        match = max(headers, key=lambda h: fuzz.ratio(h.lower(), target.lower()))
        if fuzz.ratio(match.lower(), target.lower()) < 90:
            st.error(f"Column '{target}' not matched confidently.")
            st.stop()
        col_map[target] = match

    st.write("## Preview")
    st.dataframe(df.head())

    headers_api = get_headers()
    st.write("✅ Token acquired.")
    contacts = get_all_contacts(headers_api)
    st.success("Fetched all contacts.")
    submitted = st.button("🚀 Start Upload")

    if submitted:
        charge_log = []
        scheduled = {}
        daily_job_count = {}

        for i, row in df.iterrows():
            first = str(row[col_map['W/O First Name']]).strip()
            last = str(row[col_map['W/O Last Name']]).strip()
            mobile = str(row[col_map['W/O Mobile']]).strip()
            job_name = str(row[col_map['Contract Number']]).strip()
            address = str(row[col_map['Address Of Visit']]).strip()
            city = str(row[col_map['City of Visit']]).strip()
            postcode = str(row[col_map['Postcode']]).strip()
            shutter = str(row[col_map['Shutter required y/n']]).strip().upper()
            locks = str(row[col_map['Lock type']]).strip()
            notes = " | ".join(filter(None, ["SHUTTER" if shutter == 'Y' else "", f"LOCKS: {locks}" if locks else ""]))

            try:
                date_required = parse(str(row[col_map['Date Required']]), dayfirst=True)
            except:
                st.warning(f"⏭️ Skipping invalid date: {row[col_map['Date Required']]}")
                continue

            job_date_str = date_required.strftime("%Y-%m-%d")
            contact_key = f"{first.lower()}_{last.lower()}_{job_date_str}"
            daily_job_count.setdefault(contact_key, 0)
            daily_job_count[contact_key] += 1

            contact = match_contact(contacts, first, last) or fuzzy_match_contact(contacts, first, last, i)
            if not contact:
                contact = create_contact(first, last, mobile, headers_api)
                if contact:
                    contacts.append(contact)
                else:
                    st.warning(f"⚠️ Contact creation failed for {first} {last}")
                    continue

            cid = contact['ID']
            scheduled.setdefault(cid, 0)
            site = create_site(job_name, address, city, postcode, cid, headers_api)

            if site:
                job = create_job(site['ID'], cid, job_name, date_required, notes, scheduled[cid], headers_api)
                if job:
                    job_id = job['ID']
                    st.success(f"✅ Job created: {job_name} for {first} {last}")
                    scheduled[cid] += 1

                    charge_total = 0
                    messages = []

                    if daily_job_count[contact_key] == 1:
                        charge_total += 111.50
                        messages.append("Standard daily callout (£111.50)")
                    elif daily_job_count[contact_key] > 1 and scheduled[cid] == 1:
                        charge_total += 223
                        messages.append("Multiple job day flat rate (£223.00)")

                    if shutter == 'Y':
                        charge_total += 137.50
                        messages.append("Shutter charge (£137.50)")

                    if charge_total > 0:
                        description = " + ".join(messages)
                        if add_charge_to_job(job_id, description, charge_total, headers_api):
                            st.success(f"💰 Charge added: {description} | £{charge_total:.2f}")
                            charge_log.append({
                                "Contact": f"{first} {last}",
                                "Job Name": job_name,
                                "Date": job_date_str,
                                "Charge Description": description,
                                "Total (£)": charge_total
                            })
                        else:
                            st.warning("⚠️ Charge could not be added.")
            else:
                st.error(f"❌ Site creation failed: {job_name} for {first} {last}")

        if charge_log:
            st.write("## 💼 Charge Summary")
            st.dataframe(pd.DataFrame(charge_log))
        else:
            st.info("No charges were applied to any jobs.")

# Optional Simpro ping test
if st.button("🌐 Test Simpro API Connection"):
    headers = get_headers()
    try:
        test_url = "https://api-uk.simprocloud.com/api/v1.0/companies?pageSize=1"
        response = requests.get(test_url, headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            st.success(f"✅ Connected! Company name: {data[0]['Name']} (ID: {data[0]['ID']})")
        else:
            st.error(f"❌ Simpro responded with status: {response.status_code}")
            st.text(response.text)
    except Exception as e:
        st.error(f"❌ Could not reach Simpro API: {e}")
