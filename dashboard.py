import streamlit as st
import pandas as pd
import numpy as np
import time
import io
import json
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from pymongo import MongoClient
import certifi
import requests
import pycountry
import plotly.express as px
from PIL import Image
from fpdf import FPDF
import streamlit_authenticator as stauth
from streamlit_js_eval import streamlit_js_eval

# Google Analytics & Auth imports (grouped together)
from google.oauth2 import service_account
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from googleapiclient.discovery import build
from google.auth.transport.requests import Request as GAuthRequest
from google_auth_oauthlib.flow import InstalledAppFlow

# --- Loader CSS and helper ---
st.markdown("""
<style>
.loader {
 position: relative;
 width: 2.5em;
 height: 2.5em;
 transform: rotate(165deg);
 margin: 0 auto;
}
.loader:before, .loader:after {
 content: "";
 position: absolute;
 top: 50%;
 left: 50%;
 display: block;
 width: 0.5em;
 height: 0.5em;
 border-radius: 0.25em;
 transform: translate(-50%, -50%);
}
.loader:before {
 animation: before8 2s infinite;
}
.loader:after {
 animation: after6 2s infinite;
}
@keyframes before8 {
 0% { width: 0.5em; box-shadow: 1em -0.5em rgba(225, 20, 98, 0.75), -1em 0.5em rgba(111, 202, 220, 0.75);}
 35% { width: 2.5em; box-shadow: 0 -0.5em rgba(225, 20, 98, 0.75), 0 0.5em rgba(111, 202, 220, 0.75);}
 70% { width: 0.5em; box-shadow: -1em -0.5em rgba(225, 20, 98, 0.75), 1em 0.5em rgba(111, 202, 220, 0.75);}
 100% { box-shadow: 1em -0.5em rgba(225, 20, 98, 0.75), -1em 0.5em rgba(111, 202, 220, 0.75);}
}
@keyframes after6 {
 0% { height: 0.5em; box-shadow: 0.5em 1em rgba(61, 184, 143, 0.75), -0.5em -1em rgba(233, 169, 32, 0.75);}
 35% { height: 2.5em; box-shadow: 0.5em 0 rgba(61, 184, 143, 0.75), -0.5em 0 rgba(233, 169, 32, 0.75);}
 70% { height: 0.5em; box-shadow: 0.5em -1em rgba(61, 184, 143, 0.75), -0.5em 1em rgba(233, 169, 32, 0.75);}
 100% { box-shadow: 0.5em 1em rgba(61, 184, 143, 0.75), -0.5em -1em rgba(233, 169, 32, 0.75);}
}
</style>
""", unsafe_allow_html=True)

def show_loader(placeholder, message="Loading..."):
    placeholder.markdown(
        f"""
        <div style="width:100%;text-align:center;margin:1.7em 0;">
            <div class="loader"></div>
            <div style="margin-top:0.8em; font-size:1.05em; color:#2d448d; font-weight:500;">{message}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

# =========================
# LOGIN FUNCTION
# =========================

USERNAME = st.secrets["login"]["username"]
PASSWORD = st.secrets["login"]["password"]

def login():
    st.title("Login")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        if submitted:
            if username == USERNAME and password == PASSWORD:
                st.session_state["logged_in"] = True
                st.success("Login successful!")
                st.rerun()
            else:
                st.error("Invalid username or password.")

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    login()
    st.stop()

# =========================
# PAGE CONFIG & STYLES
# =========================
st.set_page_config(
    page_title='Salasar Services Digital Marketing Reporting Dashboard',
    layout='wide'
)

st.markdown("""
<div style="display:flex; align-items:center; margin-bottom: 1.5em;">
    <img src="https://www.salasarservices.com/assets/Frontend/images/logo-black.png" style="height:48px; margin-right:28px;">
    <span style="font-family:'Lato',Arial,sans-serif; font-size:2.2em; font-weight:700; color:#2d448d;">
        Salasar Services Digital Marketing Reporting Dashboard
    </span>
</div>
""", unsafe_allow_html=True)

# =========================
# CSS for bounce/zoom animation
# =========================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Lato:wght@300;400;700&family=Fira+Code:wght@400;500;700&display=swap');

@keyframes bounceIn {
  0% { transform: scale(0.7); opacity: 0.5;}
  60% { transform: scale(1.15);}
  80% { transform: scale(0.95);}
  100% { transform: scale(1); opacity: 1;}
}
.animated-circle, .fb-animated-circle {
    width: 110px;
    height: 110px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: 'Fira Code', monospace !important;
    font-size: 2.1em;
    font-weight: 500 !important;
    color: white;
    background: #2d448d;
    box-shadow: 0 4px 12px rgba(0,0,0,0.10);
    transition: transform 0.18s cubic-bezier(.4,2,.3,1), box-shadow 0.22s;
    margin: 0 auto;
    padding: 1em;
    animation: bounceIn 0.6s cubic-bezier(.4,2,.3,1);
    will-change: transform;
}
.animated-circle:hover, .fb-animated-circle:hover {
    transform: scale(1.09);
    box-shadow: 0 8px 24px rgba(44,68,141,0.15), 0 2px 8px rgba(0,0,0,0.07);
}

.animated-circle-value { font-family: 'Fira Code', monospace !important; font-size: 0.8em; font-weight: 500; padding: 0.5em 0.6em; background: transparent; border-radius: 0.7em; width: auto; display: inline-block; letter-spacing: 0.02em; }
.section-header { font-weight: 700 !important; font-size: 1.7em !important; margin-top: 0.4em; margin-bottom: 0.4em; color: #2d448d; }
.styled-table th { font-weight: 500 !important; }
.styled-table td { font-weight: 400 !important; }
.tooltip .tooltiptext { font-size: 0.80em; font-weight: 300 !important; line-height: 1.4; }
.tooltip .questionmark { font-weight: 500 !important; font-size: 0.72em; background: #e3e8f0; color: #2d448d; border-radius: 50%; padding: 0 3px; margin-left: 4px; border: 1px solid #d1d5db; box-shadow: 0 1.5px 3px rgba(44,44,44,0.08); display: inline-block; vertical-align: super; line-height: 1em; }
.styled-table { border-collapse: collapse; width: 100%; border-radius: 5px 5px 0 0; overflow: hidden; }
.styled-table thead tr { background-color: #2d448d; color: #ffffff; text-transform: uppercase; border-bottom: 4px solid #459fda; }
.styled-table th { color: #ffffff; text-transform: uppercase; text-align: center; }
.styled-table td { padding: 12px 15px; color: #2d448d !important; }
.styled-table tbody tr:nth-of-type(even) { background-color: #f3f3f3; }
.styled-table tbody tr:nth-of-type(odd) { background-color: #ffffff; }
.styled-table tbody tr:hover { background-color: #a6ce39 !important; }
.tooltip { display: inline-block; position: relative; cursor: pointer; vertical-align: super; }
.tooltip .tooltiptext { visibility: hidden; width: 240px; background-color: #222; color: #fff; text-align: left; border-radius: 6px; padding: 8px 10px; position: absolute; z-index: 10; bottom: 120%; left: 50%; margin-left: -120px; opacity: 0; transition: opacity 0.2s; }
.tooltip:hover .tooltiptext { visibility: visible; opacity: 1; }

.fb-section-header {
    font-weight: 700 !important;
    font-size: 1.7em !important;
    margin-top: 1.3em;
    margin-bottom: 0.8em;
    color: #2d448d;
    font-family: 'Lato', Arial, sans-serif !important;
}
.fb-metric-row {
    display: flex;
    flex-wrap: nowrap;
    justify-content: center;
    gap: 2.5rem;
    margin-bottom: 2.2rem;
    margin-top: 1.0rem;
}
.fb-metric-card {
    background: transparent;
    text-align: center;
    flex: 0 0 240px;
    max-width: 270px;
    min-width: 180px;
}
.fb-metric-label {
    font-size: 1.32rem;
    font-weight: 600;
    margin-bottom: 0.6rem;
    margin-top: 0.2rem;
    color: #2d448d;
    letter-spacing: 0.09px;
    font-family: 'Lato', Arial, sans-serif;
}
.fb-delta-row {
    font-size: 1.1rem;
    font-weight: 500;
    min-height: 30px;
    display: flex;
    align-items: center;
    gap: 0.45rem;
    justify-content: center;
}
.fb-delta-up {
    color: #2ecc40;
    font-weight: 700;
    margin-right: 0.2rem;
    letter-spacing: 0.5px;
}
.fb-delta-down {
    color: #ff4136;
    font-weight: 700;
    margin-right: 0.2rem;
    letter-spacing: 0.5px;
}
.fb-delta-same {
    color: #aaa;
    font-weight: 500;
    margin-right: 0.2rem;
    letter-spacing: 0.5px;
}
.fb-delta-note {
    color: #666;
    font-size: 0.98rem;
    font-weight: 400;
    margin-left: 0.3rem;
    letter-spacing: 0.15px;
}
@media (max-width: 1200px) {
    .fb-metric-row { gap: 1.1rem; }
    .fb-metric-card { flex: 1 1 150px; max-width: 180px;}
    .fb-animated-circle { width:80px; height:80px; font-size:1.2em;}
    .fb-metric-label { font-size: 1rem;}
}
@media (max-width: 850px) {
    .fb-metric-row { flex-wrap: wrap; gap: 1.1rem;}
    .fb-metric-card { flex: 1 1 130px; max-width: 150px;}
    .fb-animated-circle { width:60px; height:60px; font-size:0.97em;}
    .fb-metric-label { font-size: 0.82rem;}
}
</style>
""", unsafe_allow_html=True)

# =========================
# HELPER AND DATA FUNCTIONS
# =========================
def pct_change(current, previous):
    return 0 if previous == 0 else (current - previous) / previous * 100

def get_month_options():
    months, today, d = [], date.today(), date(2025,1,1)
    while d <= today:
        months.append(d)
        d += relativedelta(months=1)
    return [m.strftime('%B %Y') for m in months]

def get_month_range(sel):
    start = datetime.strptime(sel, '%B %Y').date().replace(day=1)
    end = start + relativedelta(months=1) - timedelta(days=1)
    prev_end = start - timedelta(days=1)
    prev_start = prev_end.replace(day=1)
    return start, end, prev_start, prev_end

def format_month_year(d):
    return d.strftime('%B %Y')

@st.cache_resource
def get_credentials():
    sa = st.secrets['gcp']['service_account']
    info = json.loads(sa)
    pk = info.get('private_key', '').replace('\\n', '\n')
    if not pk.endswith('\n'):
        pk += '\n'
    info['private_key'] = pk
    creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    creds.refresh(GAuthRequest())
    return creds

@st.cache_data(ttl=3600)
def get_total_users(pid, sd, ed):
    try:
        req = {
            'property': f'properties/{pid}',
            'date_ranges': [{'start_date': sd.strftime('%Y-%m-%d'), 'end_date': ed.strftime('%Y-%m-%d')}],
            'metrics': [{'name': 'totalUsers'}]
        }
        resp = ga4.run_report(request=req)
        return int(resp.rows[0].metric_values[0].value)
    except Exception as e:
        st.error(f"Error fetching total users: {e}")
        return 0

@st.cache_data(ttl=3600)
def get_traffic(pid, sd, ed):
    try:
        req = {
            'property': f'properties/{pid}',
            'date_ranges': [{'start_date': sd.strftime('%Y-%m-%d'), 'end_date': ed.strftime('%Y-%m-%d')}],
            'dimensions': [{'name': 'sessionDefaultChannelGroup'}],
            'metrics': [{'name': 'sessions'}]
        }
        resp = ga4.run_report(request=req)
        return [{'channel': r.dimension_values[0].value, 'sessions': int(r.metric_values[0].value)} for r in resp.rows]
    except Exception as e:
        st.error(f"Error fetching traffic data: {e}")
        return []

@st.cache_data(ttl=3600)
def get_search_console(site, sd, ed):
    try:
        body = {
            'startDate': sd.strftime('%Y-%m-%d'),
            'endDate': ed.strftime('%Y-%m-%d'),
            'dimensions': ['page','query'],
            'rowLimit': 500
        }
        resp = sc.searchanalytics().query(siteUrl=site, body=body).execute()
        return resp.get('rows', [])
    except Exception as e:
        st.error(f"Error fetching Search Console data: {e}")
        return []

@st.cache_data(ttl=3600)
def get_active_users_by_country(pid, sd, ed, top_n=5):
    try:
        req = {
            'property': f'properties/{pid}',
            'date_ranges': [{'start_date': sd.strftime('%Y-%m-%d'), 'end_date': ed.strftime('%Y-%m-%d')}],
            'dimensions': [{'name': 'country'}],
            'metrics': [{'name': 'activeUsers'}],
            'order_bys': [{'metric': {'metric_name': 'activeUsers'}, 'desc': True}],
            'limit': top_n
        }
        resp = ga4.run_report(request=req)
        return [{'country': r.dimension_values[0].value, 'activeUsers': int(r.metric_values[0].value)} for r in resp.rows]
    except Exception as e:
        st.error(f"Error fetching country data: {e}")
        return []

@st.cache_data(ttl=3600)
def get_gsc_site_stats(site, sd, ed):
    try:
        body = {
            'startDate': sd.strftime('%Y-%m-%d'),
            'endDate': ed.strftime('%Y-%m-%d'),
            'rowLimit': 1
        }
        resp = sc.searchanalytics().query(siteUrl=site, body=body).execute()
        if not resp.get('rows'):
            return 0, 0, 0.0
        row = resp['rows'][0]
        return row.get('clicks', 0), row.get('impressions', 0), row.get('ctr', 0.0)
    except Exception as e:
        st.error(f"Error fetching GSC site stats: {e}")
        return 0, 0, 0.0

@st.cache_data(ttl=3600)
def get_new_returning_users(pid, sd, ed):
    try:
        req = {
            'property': f'properties/{pid}',
            'date_ranges': [{'start_date': sd.strftime('%Y-%m-%d'), 'end_date': ed.strftime('%Y-%m-%d')}],
            'metrics': [{'name': 'totalUsers'}, {'name': 'newUsers'}]
        }
        resp = ga4.run_report(request=req)
        total_users = int(resp.rows[0].metric_values[0].value)
        new_users = int(resp.rows[0].metric_values[1].value)
        returning_users = total_users - new_users
        return total_users, new_users, returning_users
    except Exception as e:
        st.error(f"Error fetching new/returning users: {e}")
        return 0, 0, 0

def render_table(df):
    if df.empty:
        st.warning("No data available for this period.")
    else:
        html = df.to_html(index=False, classes='styled-table')
        st.markdown(html, unsafe_allow_html=True)

def country_name_to_code(name):
    try:
        country = pycountry.countries.lookup(name)
        return country.alpha_2.lower()
    except LookupError:
        for country in pycountry.countries:
            if name.lower() in country.name.lower():
                return country.alpha_2.lower()
        return None
# =========================
# SIDEBAR & FILTERS
# =========================
with st.sidebar:
    st.image("https://www.salasarservices.com/assets/Frontend/images/logo-black.png", width=170)
    st.title('Report Filters')

    def get_month_options():
        months, today, d = [], date.today(), date(2025,1,1)
        while d <= today:
            months.append(d)
            d += relativedelta(months=1)
        return [m.strftime('%B %Y') for m in months]

    month_options = get_month_options()
    if "selected_month" not in st.session_state:
        st.session_state["selected_month"] = month_options[-1]
    sel = st.selectbox('Select report month:', month_options, index=month_options.index(st.session_state["selected_month"]))
    if sel != st.session_state["selected_month"]:
        st.session_state["selected_month"] = sel

    def get_month_range(sel):
        start = datetime.strptime(sel, '%B %Y').date().replace(day=1)
        end = start + relativedelta(months=1) - timedelta(days=1)
        prev_end = start - timedelta(days=1)
        prev_start = prev_end.replace(day=1)
        return start, end, prev_start, prev_end

    sd, ed, psd, ped = get_month_range(st.session_state["selected_month"])
    st.markdown(
        f"""
        <div style="border-left: 4px solid #459fda; background: #f0f7fa; padding: 1em 1.2em; margin-bottom: 1em; border-radius: 6px;">
            <span style="font-size: 1.1em; color: #2d448d;">
            <b>Current period:</b> {sd.strftime('%B %Y')}<br>
            <b>Previous period:</b> {psd.strftime('%B %Y')}
            </span>
        </div>
        """,
        unsafe_allow_html=True
    )

    if st.button("Refresh Data (Clear Cache)"):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.session_state["selected_month"] = month_options[-1]
        st.session_state["refresh"] = True

    # --- FLUSH LEADS DATABASE FUNCTION ---
    def flush_mongo_database():
        try:
            mongo_uri_leads = st.secrets["mongo_uri_leads"]
            db_name = "sal-leads"  # Change to your actual database name if different
            client = MongoClient(mongo_uri_leads)
            db = client[db_name]
            for collection_name in db.list_collection_names():
                db[collection_name].delete_many({})
            client.close()
            return True
        except Exception as e:
            st.error(f"Could not flush database: {e}")
            return False

    # --- FLUSH LINKEDIN DATABASE FUNCTION ---
    def flush_linkedin_database():
        try:
            mongo_uri_linkedin = st.secrets["mongo_uri_linkedin"]
            db_name = "sallnkddata"  # Use your actual LinkedIn DB name
            client = MongoClient(mongo_uri_linkedin)
            db = client[db_name]
            for collection_name in db.list_collection_names():
                db[collection_name].delete_many({})
            client.close()
            return True
        except Exception as e:
            st.error(f"Could not flush LinkedIn database: {e}")
            return False

    # Place the flush buttons after "Refresh Data" and before the PDF button!
    flush_btn = st.button("Flush Mongo 🗑️")
    if flush_btn:
        if flush_mongo_database():
            st.success("All data in the leads database has been deleted!")
        else:
            st.error("Failed to flush leads database.")

    flush_linkedin_btn = st.button("Flush Linkedin 🗑️")
    if flush_linkedin_btn:
        if flush_linkedin_database():
            st.success("All data in the LinkedIn database has been deleted!")
        else:
            st.error("Failed to flush LinkedIn database.")

    pdf_report_btn = st.button("Download PDF Report")

if st.session_state.get("refresh", False):
    st.session_state["refresh"] = False
    st.rerun()

# =========================
# AUTHENTICATION & CONFIG
# =========================
SCOPES = [
    'https://www.googleapis.com/auth/analytics.readonly',
    'https://www.googleapis.com/auth/webmasters.readonly'
]
PROPERTY_ID = '356205245'
SC_SITE_URL = 'https://www.salasarservices.com/'

# --- Loader for credentials setup ---
credentials_placeholder = st.empty()
show_loader(credentials_placeholder, "Authenticating and initializing analytics APIs...")
def get_credentials():
    sa = st.secrets['gcp']['service_account']
    info = json.loads(sa)
    pk = info.get('private_key', '').replace('\\n', '\n')
    if not pk.endswith('\n'):
        pk += '\n'
    info['private_key'] = pk
    creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    creds.refresh(GAuthRequest())
    return creds
creds = get_credentials()
ga4 = BetaAnalyticsDataClient(credentials=creds)
sc = build('searchconsole', 'v1', credentials=creds)
credentials_placeholder.empty()

# --- Loader for all metric data ---
metrics_placeholder = st.empty()
show_loader(metrics_placeholder, "Fetching dashboard data...")
# (All your data metrics and calculations here.)
def pct_change(current, previous):
    return 0 if previous == 0 else (current - previous) / previous * 100

def get_gsc_site_stats(site, sd, ed):
    try:
        body = {
            'startDate': sd.strftime('%Y-%m-%d'),
            'endDate': ed.strftime('%Y-%m-%d'),
            'rowLimit': 1
        }
        resp = sc.searchanalytics().query(siteUrl=site, body=body).execute()
        if not resp.get('rows'):
            return 0, 0, 0.0
        row = resp['rows'][0]
        return row.get('clicks', 0), row.get('impressions', 0), row.get('ctr', 0.0)
    except Exception as e:
        st.error(f"Error fetching GSC site stats: {e}")
        return 0, 0, 0.0

gsc_clicks, gsc_impressions, gsc_ctr = get_gsc_site_stats(SC_SITE_URL, sd, ed)
gsc_clicks_prev, gsc_impressions_prev, gsc_ctr_prev = get_gsc_site_stats(SC_SITE_URL, psd, ped)
gsc_clicks_delta = pct_change(gsc_clicks, gsc_clicks_prev)
gsc_impr_delta = pct_change(gsc_impressions, gsc_impressions_prev)
gsc_ctr_delta = pct_change(gsc_ctr, gsc_ctr_prev)

perf_circles = [
    {
        "title": "Total Website Clicks",
        "value": gsc_clicks,
        "delta": gsc_clicks_delta,
        "color": "#e67e22",
    },
    {
        "title": "Total Impressions",
        "value": gsc_impressions,
        "delta": gsc_impr_delta,
        "color": "#3498db",
    },
    {
        "title": "Average CTR",
        "value": gsc_ctr * 100,
        "delta": gsc_ctr_delta,
        "color": "#16a085",
    }
]
# ... [all your other data calculations here for tables, analytics, leads, fb, etc]
# For brevity, assume all previous calculations (top_content_data, cur, prev, delta, etc) are here.
time.sleep(1.2)
metrics_placeholder.empty()

# Now render all dashboard sections as before (remove/reduce per-section time.sleep):
# [Website Performance Circles]
# [Top Content Table]
# [Website Analytics Circles]
# [New vs Returning Users]
# [Leads Section]
# [Facebook Analytics Circles]
# (All as in your last working code.)

# The loader will show while all heavy data fetching happens, and disappear before UI rendering.

# =========================
# DATA COLLECTION FOR PDF
# =========================
gsc_clicks, gsc_impressions, gsc_ctr = get_gsc_site_stats(SC_SITE_URL, sd, ed)
gsc_clicks_prev, gsc_impressions_prev, gsc_ctr_prev = get_gsc_site_stats(SC_SITE_URL, psd, ped)
gsc_clicks_delta = pct_change(gsc_clicks, gsc_clicks_prev)
gsc_impr_delta = pct_change(gsc_impressions, gsc_impressions_prev)
gsc_ctr_delta = pct_change(gsc_ctr, gsc_ctr_prev)

perf_circles = [
    {
        "title": "Total Website Clicks",
        "value": gsc_clicks,
        "delta": gsc_clicks_delta,
        "color": "#e67e22",
    },
    {
        "title": "Total Impressions",
        "value": gsc_impressions,
        "delta": gsc_impr_delta,
        "color": "#3498db",
    },
    {
        "title": "Average CTR",
        "value": gsc_ctr * 100,
        "delta": gsc_ctr_delta,
        "color": "#16a085",
    }
]

def get_gsc_pages_clicks(site, sd, ed, limit=5):
    try:
        body = {
            "startDate": sd.strftime('%Y-%m-%d'),
            "endDate": ed.strftime('%Y-%m-%d'),
            "dimensions": ["page"],
            "rowLimit": limit
        }
        resp = sc.searchanalytics().query(siteUrl=site, body=body).execute()
        rows = resp.get("rows", [])
        return [{"page": r["keys"][0], "clicks": r.get("clicks", 0)} for r in rows]
    except Exception as e:
        st.error(f"Error fetching top content from Search Console: {e}")
        return []

top_pages_now = get_gsc_pages_clicks(SC_SITE_URL, sd, ed, limit=5)
top_pages_prev = get_gsc_pages_clicks(SC_SITE_URL, psd, ped, limit=20)
prev_clicks_dict = {p["page"]: p["clicks"] for p in top_pages_prev}
top_content_data = []
for entry in top_pages_now:
    page = entry["page"]
    clicks = entry["clicks"]
    prev_clicks = prev_clicks_dict.get(page, 0)
    diff_pct = 0 if prev_clicks == 0 else ((clicks - prev_clicks) / prev_clicks * 100)
    top_content_data.append({
        "Page": page,
        "Clicks": clicks,
        "Change (%)": f"{diff_pct:+.2f}"
    })

cur = get_total_users(PROPERTY_ID, sd, ed)
prev = get_total_users(PROPERTY_ID, psd, ped)
delta = pct_change(cur, prev)
traf = get_traffic(PROPERTY_ID, sd, ed)
total = sum(item['sessions'] for item in traf)
prev_total = sum(item['sessions'] for item in get_traffic(PROPERTY_ID, psd, ped))
delta2 = pct_change(total, prev_total)
sc_data = get_search_console(SC_SITE_URL, sd, ed)
clicks = sum(r.get('clicks',0) for r in sc_data)
prev_clicks = sum(r.get('clicks',0) for r in get_search_console(SC_SITE_URL, psd, ped))
delta3 = pct_change(clicks, prev_clicks)
country_data = get_active_users_by_country(PROPERTY_ID, sd, ed)
traf_df = pd.DataFrame(traf).head(5)
sc_df = pd.DataFrame([{'page': r['keys'][0], 'query': r['keys'][1], 'clicks': r.get('clicks', 0)} for r in sc_data]).head(10)

# NEW: New vs Returning Users (data collection)
total_users, new_users, returning_users = get_new_returning_users(PROPERTY_ID, sd, ed)
total_users_prev, new_users_prev, returning_users_prev = get_new_returning_users(PROPERTY_ID, psd, ped)
delta_new = pct_change(new_users, new_users_prev)
delta_returning = pct_change(returning_users, returning_users_prev)

returning_new_users_circles = [
    {
        "title": "New Users",
        "value": new_users,
        "delta": delta_new,
        "color": "#e67e22",
    },
    {
        "title": "Returning Users",
        "value": returning_users,
        "delta": delta_returning,
        "color": "#3498db",
    }
]
returning_new_tooltips = [
    "Number of users who visited your website for the first time during the period.",
    "Number of users who returned to your website (not their first visit) during the period.",
]

# =========================
# PDF GENERATION LOGIC (unchanged)
# =========================
def generate_pdf_report():
    pdf = FPDF()
    pdf.add_page()
    logo_url = "https://www.salasarservices.com/assets/Frontend/images/logo-black.png"
    try:
        logo_bytes = requests.get(logo_url, timeout=5).content
        logo_img = Image.open(io.BytesIO(logo_bytes)).convert("RGBA")
        logo_path = "logo_temp.png"
        logo_img.save(logo_path)
        pdf.image(logo_path, x=10, y=8, w=50)
    except Exception:
        pass

    pdf.set_xy(65, 15)
    pdf.set_font("Arial", 'B', 17)
    pdf.set_text_color(45, 68, 141)
    pdf.cell(0, 12, "Salasar Services Digital Marketing Reporting Dashboard", ln=1)

    pdf.set_font("Arial", '', 12)
    pdf.set_text_color(0,0,0)
    pdf.ln(8)
    pdf.cell(0, 10, f"Reporting Period: {format_month_year(sd)} | Previous: {format_month_year(psd)}", ln=1)

    pdf.set_font("Arial", 'B', 14)
    pdf.set_text_color(45, 68, 141)
    pdf.cell(0, 12, "Website Performance", ln=1)
    pdf.set_font("Arial", '', 12)
    pdf.set_text_color(0,0,0)
    for metric in perf_circles:
        val = f"{metric['value']:.2f}" if metric["title"]=="Average CTR" else str(metric['value'])
        pdf.cell(0, 10, f"{metric['title']}: {val} ({metric['delta']:+.2f} % from previous month)", ln=1)
    pdf.ln(2)

    pdf.set_font("Arial", 'B', 14)
    pdf.set_text_color(45, 68, 141)
    pdf.cell(0, 10, "Top Content", ln=1)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(110, 8, "Page", border=1)
    pdf.cell(30, 8, "Clicks", border=1)
    pdf.cell(35, 8, "Change (%)", border=1, ln=1)
    pdf.set_font("Arial", '', 12)
    for row in top_content_data:
        pdf.cell(110, 8, row['Page'][:65], border=1)
        pdf.cell(30, 8, str(row['Clicks']), border=1)
        pdf.cell(35, 8, row['Change (%)'], border=1, ln=1)
    pdf.ln(4)

    pdf.set_font("Arial", 'B', 14)
    pdf.set_text_color(45, 68, 141)
    pdf.cell(0, 10, "Website Analytics", ln=1)
    pdf.set_font("Arial", '', 12)
    pdf.cell(60, 8, f"Total Users: {cur} ({delta:+.2f}%)", ln=1)
    pdf.cell(60, 8, f"Sessions: {total} ({delta2:+.2f}%)", ln=1)
    pdf.cell(60, 8, f"Organic Clicks: {clicks} ({delta3:+.2f}%)", ln=1)
    pdf.ln(1)

    # New vs Returning Users for PDF
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 9, "New vs Returning Users", ln=1)
    pdf.set_font("Arial", '', 12)
    pdf.cell(60, 8, f"New Users: {new_users} ({delta_new:+.2f}%)", ln=1)
    pdf.cell(60, 8, f"Returning Users: {returning_users} ({delta_returning:+.2f}%)", ln=1)
    pdf.ln(1)

    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 9, "Active Users by Country (Top 5)", ln=1)
    pdf.set_font("Arial", '', 12)
    for c in country_data:
        pdf.cell(0, 7, f"{c['country']}: {c['activeUsers']}", ln=1)
    pdf.ln(1)

    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 9, "Traffic Acquisition by Channel", ln=1)
    pdf.set_font("Arial", '', 12)
    for idx,row in traf_df.iterrows():
        pdf.cell(0, 7, f"{row['channel']}: {row['sessions']}", ln=1)
    pdf.ln(1)

    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 9, "Top 10 Organic Queries", ln=1)
    pdf.set_font("Arial", '', 12)
    for idx,row in sc_df.iterrows():
        pdf.cell(0, 7, f"{row['query']} ({row['clicks']} clicks)", ln=1)
    pdf.ln(2)

    pdf.set_y(-25)
    pdf.set_font("Arial", 'I', 8)
    pdf.set_text_color(150,150,150)
    pdf.cell(0, 10, "Generated by Salasar Services Digital Marketing Reporting Dashboard", 0, 0, 'C')
    pdf_bytes = pdf.output(dest='S').encode('latin1')
    return io.BytesIO(pdf_bytes)

if pdf_report_btn:
    pdf_bytes = generate_pdf_report()
    st.sidebar.download_button(
        label="Download PDF",
        data=pdf_bytes,
        file_name=f"Salasar-Services-Report-{date.today()}.pdf",
        mime="application/pdf"
    )

# =========================
# WEBSITE PERFORMANCE SECTION
# =========================
st.markdown('<div class="section-header">Website Performance</div>', unsafe_allow_html=True)
cols_perf = st.columns(3)
animation_duration = 0.5
perf_tooltips = [
    "The total number of times users clicked your website's listing in Google Search results during the selected period.",
    "The total number of times your website appeared in Google Search results (regardless of clicks) for any query.",
    "The percentage of impressions that resulted in a click (Click-Through Rate) for your website in Google Search results during the selected period."
]
for i, col in enumerate(cols_perf):
    entry = perf_circles[i]
    with col:
        st.markdown(
            f"""<div style='text-align:center; font-weight:500; font-size:22px; margin-bottom:0.2em'>
                {entry["title"]}
                <span class='tooltip'>
                  <span class='questionmark'>?</span>
                  <span class='tooltiptext'>{perf_tooltips[i]}</span>
                </span>
            </div>""",
            unsafe_allow_html=True
        )
        placeholder = st.empty()
        steps = 45
        for n in range(steps + 1):
            if entry["title"] == "Average CTR":
                display_val = f"{entry['value'] * n / steps:.2f}%"
            else:
                display_val = int(entry["value"] * n / steps)
            placeholder.markdown(
                f"""
                <div style='margin:0 auto; display:flex; align-items:center; justify-content:center; height:110px;'>
                  <div class='animated-circle' style='background:{entry["color"]};'>
                    <span class='animated-circle-value'>{display_val}</span>
                  </div>
                </div>
                """,
                unsafe_allow_html=True
            )
            time.sleep(animation_duration / steps)
        pct_color = "#2ecc40" if entry["delta"] >= 0 else "#ff4136"
        pct_icon = (
            "↑" if entry["delta"] >= 0 else "↓"
        )
        pct_icon_colored = (
            f"<span style='color:{pct_color}; font-size:1.05em; vertical-align:middle;'>{pct_icon}</span>"
        )
        # UPDATED LINE BELOW
        pct_delta_text = (
            f"{pct_icon_colored} <span class='animated-circle-value' style='color:{pct_color}; font-size:1.1em;'>{abs(entry['delta']):.2f}%</span> <span class='animated-circle-delta-note'>(vs. Previous Month)</span>"
        )
        st.markdown(
            f"<div style='text-align:center; font-size:18px; margin-top:0.2em; color:{pct_color}; font-weight:500'>{pct_delta_text}</div>",
            unsafe_allow_html=True
        )

# =========================
# TOP CONTENT SECTION
# =========================
st.markdown('<div class="section-header">Top Content</div>', unsafe_allow_html=True)
def render_top_content_table(data):
    df = pd.DataFrame(data)
    if not df.empty:
        df["Clicks"] = df["Clicks"].apply(lambda x: f"<span class='animated-circle-value' style='font-size:1.2em'>{x}</span>")
        def fmt_change(val):
            pct = float(val)
            color = "#2ecc40" if pct >= 0 else "#ff4136"
            arrow = "↑" if pct >= 0 else "↓"
            return f"<span class='animated-circle-value' style='color:{color};font-size:1.15em'>{arrow} {pct:+.2f}%</span>"
        df["Change (%)"] = df["Change (%)"].apply(fmt_change)
        st.markdown(df.to_html(escape=False, index=False, classes="styled-table"), unsafe_allow_html=True)
    else:
        st.warning("No top content data available for this period.")
render_top_content_table(top_content_data)

# =========================
# WEBSITE ANALYTICS SECTION
# =========================
st.markdown('<div class="section-header">Website Analytics</div>', unsafe_allow_html=True)

circle_colors = ["#2d448d", "#a6ce39", "#459fda"]
titles = [
    "Total Users",
    "Sessions",
    "Organic Clicks"
]
tooltips = [
    "Number of people who visited your website.",
    "Total number of visits to your website.",
    "Times people clicked on your website in Google search."
]
values = [cur, total, clicks]
deltas = [delta, delta2, delta3]
cols = st.columns(3)
animation_duration = 0.5
for i, col in enumerate(cols):
    with col:
        st.markdown(
            f"""<div style='text-align:center; font-weight:500; font-size:22px; margin-bottom:0.2em'>
                {titles[i]}
                <span class='tooltip'>
                  <span class='questionmark'>?</span>
                  <span class='tooltiptext'>{tooltips[i]}</span>
                </span>
            </div>""",
            unsafe_allow_html=True
        )
        placeholder = st.empty()
        steps = 45
        for n in range(steps + 1):
            display_val = int(values[i] * n / steps)
            placeholder.markdown(
                f"""
                <div style='margin:0 auto; display:flex; align-items:center; justify-content:center; height:110px;'>
                  <div class='animated-circle' style='background:{circle_colors[i]};'>
                    <span class='animated-circle-value'>{display_val}</span>
                  </div>
                </div>
                """,
                unsafe_allow_html=True
            )
            time.sleep(animation_duration / steps)
        pct_color = "#2ecc40" if deltas[i] >= 0 else "#ff4136"
        pct_icon = (
            "↑" if deltas[i] >= 0 else "↓"
        )
        pct_icon_colored = (
            f"<span style='color:{pct_color}; font-size:1.05em; vertical-align:middle;'>{pct_icon}</span>"
        )
        st.markdown(
            f"<div style='text-align:center; font-size:18px; margin-top:0.2em; color:{pct_color}; font-weight:500'>{pct_icon_colored} <span class='animated-circle-value' style='color:{pct_color}; font-size:1.1em;'>{abs(deltas[i]):.2f}%</span> <span class='animated-circle-delta-note'>(vs. Previous Month)</span></div>",
            unsafe_allow_html=True
        )

# =========================
# NEW VS RETURNING USERS SECTION
# =========================
st.markdown('<div class="section-header">New vs Returning Users</div>', unsafe_allow_html=True)
cols_ret = st.columns(2)
animation_duration = 0.5
for i, col in enumerate(cols_ret):
    entry = returning_new_users_circles[i]
    with col:
        st.markdown(
            f"""<div style='text-align:center; font-weight:500; font-size:22px; margin-bottom:0.2em'>
                {entry["title"]}
                <span class='tooltip'>
                  <span class='questionmark'>?</span>
                  <span class='tooltiptext'>{returning_new_tooltips[i]}</span>
                </span>
            </div>""",
            unsafe_allow_html=True
        )
        placeholder = st.empty()
        steps = 45
        for n in range(steps + 1):
            display_val = int(entry["value"] * n / steps)
            placeholder.markdown(
                f"""
                <div style='margin:0 auto; display:flex; align-items:center; justify-content:center; height:110px;'>
                  <div class='animated-circle' style='background:{entry["color"]};'>
                    <span class='animated-circle-value'>{display_val}</span>
                  </div>
                </div>
                """,
                unsafe_allow_html=True
            )
            time.sleep(animation_duration / steps)
        pct_color = "#2ecc40" if entry["delta"] >= 0 else "#ff4136"
        pct_icon = "↑" if entry["delta"] >= 0 else "↓"
        pct_icon_colored = (
            f"<span style='color:{pct_color}; font-size:1.05em; vertical-align:middle;'>{pct_icon}</span>"
        )
        st.markdown(
            f"<div style='text-align:center; font-size:18px; margin-top:0.2em; color:{pct_color}; font-weight:500'>{pct_icon_colored} <span class='animated-circle-value' style='color:{pct_color}; font-size:1.1em;'>{abs(entry['delta']):.2f}%</span> <span class='animated-circle-delta-note'>(vs. Previous Month)</span></div>",
            unsafe_allow_html=True
        )
        
# --- Two side-by-side tables ---
col1, col2 = st.columns(2)
with col1:
    st.subheader('Active Users by Country (Top 5)')
    country_df = pd.DataFrame(country_data)
    def flag_html(row):
        code = country_name_to_code(row['country'])
        flag_url = f"https://flagcdn.com/16x12/{code}.png" if code else ""
        flag_img = f'<img src="{flag_url}" style="height:12px;margin-right:7px;vertical-align:middle;">' if code else ""
        return f"{flag_img}{row['country']}"
    country_df['Country'] = country_df.apply(flag_html, axis=1)
    country_df = country_df[['Country', 'activeUsers']]
    country_df.rename(columns={'activeUsers': 'Active Users'}, inplace=True)
    st.markdown(country_df.to_html(escape=False, index=False, classes='styled-table'), unsafe_allow_html=True)

with col2:
    st.subheader('Traffic Acquisition by Channel')
    render_table(traf_df)

# =========================
# LEADS SECTION
# =========================

def get_leads_from_mongodb():
    try:
        mongo_uri_leads = st.secrets["mongo_uri_leads"]
        from pymongo import MongoClient
        client = MongoClient(mongo_uri_leads)
        db = client["sal-leads"]
        leads_collection = db["leads"]
        leads = list(leads_collection.find({}, {"_id": 0}))
        client.close()
        return leads
    except Exception as e:
        st.error(f"Could not fetch leads: {e}")
        return []

def date_to_mon_yy(date_val):
    try:
        if isinstance(date_val, pd.Timestamp):
            dt = date_val
        elif isinstance(date_val, (int, float)):
            dt = pd.to_datetime(str(int(date_val)), format="%Y%m%d", errors="coerce")
        else:
            dt = pd.to_datetime(str(date_val), errors="coerce")
        if pd.isnull(dt):
            return ""
        return dt.strftime("%b %y")
    except Exception:
        return ""

def get_month_color(month_label):
    pastel_palette = [
        "#F7F1D5", "#FBE4EB", "#D3FBE4", "#E4EAFF", "#FFE4F1",
        "#E4FFF6", "#F5E4FF", "#F1FFE4", "#FFE4E4", "#E4F1FF"
    ]
    idx = abs(hash(month_label)) % len(pastel_palette)
    return pastel_palette[idx]

def lead_status_pill(status):
    status_clean = str(status).strip()
    pill_colors = {
        "Interested": "#ffe9a8",
        "Not Interested": "#ffb1b1",
        "Closed": "#c8f7b5"
    }
    text_colors = {
        "Interested": "#a67c00",
        "Not Interested": "#b30000",
        "Closed": "#227a00"
    }
    color = pill_colors.get(status_clean, "#e0e0e0")
    tcolor = text_colors.get(status_clean, "#444")
    return (f"<span class='lead-pill' style='display:inline-block; padding:3px 16px; border-radius:15px; "
            f"background:{color}; color:{tcolor}; font-weight:600; font-size:0.93em; "
            f"letter-spacing:0.5px; border:1px solid #eee;'>{status_clean}</span>")

def format_brokerage_circle_value(val):
    if val >= 10000000:
        return f"₹ {val/10000000:.1f}Cr"
    elif val >= 100000:
        return f"₹ {val/100000:.1f}L"
    elif val >= 10000:
        return f"₹ {val/1000:.0f}K"
    elif val >= 1000:
        return f"₹ {val/1000:.1f}K"
    else:
        return f"₹ {val:.2f}"

st.markdown("## Leads Dashboard")

leads = get_leads_from_mongodb()
if leads:
    df = pd.DataFrame(leads)
    if "Date" in df.columns:
        df["MonYY"] = df["Date"].apply(date_to_mon_yy)
        months = df["MonYY"].fillna("").astype(str).unique()
        months = [m for m in months if m.strip() != ""]
        months.sort()
        month_to_color = {m: get_month_color(m) for m in months}
    else:
        df["MonYY"] = ""
        month_to_color = {}
    if "Brokerage Received" in df.columns:
        df["Brokerage Received"] = pd.to_numeric(df["Brokerage Received"], errors="coerce").fillna(0)
        total_brokerage = df["Brokerage Received"].sum()
    else:
        df["Brokerage Received"] = 0.0
        total_brokerage = 0.0
    if "Lead Status" in df.columns:
        df["Lead Status Clean"] = df["Lead Status"].astype(str).str.strip()
        interested_count = (df["Lead Status Clean"] == "Interested").sum()
        not_interested_count = (df["Lead Status Clean"] == "Not Interested").sum()
        closed_count = (df["Lead Status Clean"] == "Closed").sum()
        df["Lead Status Pill"] = df["Lead Status"].apply(lead_status_pill)
    else:
        interested_count = not_interested_count = closed_count = 0
        df["Lead Status Pill"] = ""
    total_leads = len(df)
else:
    df = pd.DataFrame()
    total_leads = interested_count = not_interested_count = closed_count = 0
    total_brokerage = 0.0
    month_to_color = {}

display_brokerage = format_brokerage_circle_value(total_brokerage)

# Dashboard circles (unchanged)
st.markdown("""
<style>
.circles-row {
    display: flex;
    justify-content: center;
    gap: 33px;
    margin-bottom: 20px;
    flex-wrap: wrap;
}
.circle-animate {
    width: 88px;
    height: 88px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.49rem;
    color: #fff;
    font-weight: bold;
    box-shadow: 0 2px 8px rgba(250, 190, 88, 0.18);
    animation: pop 1s ease;
    margin-bottom: 4px;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
    text-shadow: 0 1px 3px #2227;
    letter-spacing: 0.5px;
}
.circle-animate:hover { transform: scale(1.08); }
.circle-leads    { background: linear-gradient(135deg, #f6d365 0%, #fda085 100%);}
.circle-int      { background: linear-gradient(135deg, #FFD700 0%, #FFB200 100%);}
.circle-notint   { background: linear-gradient(135deg, #FB4141 0%, #C91F1F 100%);}
.circle-closed   { background: linear-gradient(135deg, #B4E50D 0%, #7BA304 100%);}
.circle-brokerage { background: linear-gradient(135deg, #0dbe62 0%, #1ff1a7 100%);}
.lead-label {
    text-align:center; 
    font-weight:600;
    font-size: 0.95rem;
    color: #888;
    letter-spacing: 0.5px;
    margin-bottom: 0.7rem;
}
.lead-pill {
    display: inline-block;
    padding: 3px 16px;
    border-radius: 15px;
    font-weight: 600;
    font-size: 0.93em;
    letter-spacing: 0.5px;
    border: 1px solid #eee;
    box-shadow: 0 1px 4px 0 #eee;
    transition: box-shadow 0.17s;
}
.lead-pill:hover {
    box-shadow: 0 2px 10px 0 #e1e1e1;
}
@keyframes pop {
    0% { transform: scale(0.5);}
    80% { transform: scale(1.11);}
    100% { transform: scale(1);}
}
</style>
""", unsafe_allow_html=True)

st.markdown(f"""
<div class="circles-row">
    <div>
        <div class="circle-animate circle-leads">{total_leads}</div>
        <div class="lead-label">Total Leads</div>
    </div>
    <div>
        <div class="circle-animate circle-int">{interested_count}</div>
        <div class="lead-label">Interested</div>
    </div>
    <div>
        <div class="circle-animate circle-notint">{not_interested_count}</div>
        <div class="lead-label">Not Interested</div>
    </div>
    <div>
        <div class="circle-animate circle-closed">{closed_count}</div>
        <div class="lead-label">Closed</div>
    </div>
    <div>
        <div class="circle-animate circle-brokerage">{display_brokerage}</div>
        <div class="lead-label">Total Brokerage received</div>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("### Leads Data")

if not df.empty:
    # Prepare columns for display: MonYY, main cols..., Lead Status Pill (before Brokerage Received), Brokerage Received
    display_cols = []
    if "MonYY" in df.columns:
        display_cols.append("MonYY")
    main_cols = [col for col in df.columns if col not in ("Date", "MonYY", "Lead Status Pill", "Lead Status Clean", "Brokerage Received")]
    display_cols.extend(main_cols)
    if "Lead Status Pill" in df.columns and "Brokerage Received" in df.columns:
        if "Brokerage Received" not in display_cols:
            display_cols.append("Brokerage Received")
        else:
            b_idx = display_cols.index("Brokerage Received")
            display_cols.insert(b_idx, "Lead Status Pill")
    elif "Lead Status Pill" in df.columns:
        display_cols.append("Lead Status Pill")
    if "Brokerage Received" in df.columns and "Brokerage Received" not in display_cols:
        display_cols.append("Brokerage Received")
    df_display = df[display_cols]

    # HTML table render with pill badges
    def df_to_colored_html(df):
        headers = df.columns.tolist()
        html = '<div class="leads-table-wrapper"><table class="leads-table-min">\n<thead><tr>'
        for h in headers:
            if h == "MonYY":
                html += f'<th style="min-width:54px;">Month</th>'
            elif h == "Lead Status Pill":
                html += f'<th>Lead Status</th>'
            elif h == "Brokerage Received":
                html += f'<th>Brokerage Received</th>'
            else:
                html += f'<th>{h}</th>'
        html += '</tr></thead>\n<tbody>'
        for idx, row in df.iterrows():
            html += '<tr>'
            for ih, cell in enumerate(row):
                h = headers[ih]
                if h == "MonYY":
                    month = str(cell).strip()
                    bgcolor = f'background-color: {month_to_color.get(month, "#fafafa")}; font-weight: bold;'
                    html += f'<td style="{bgcolor}; text-align:center;">{cell}</td>'
                elif h == "Lead Status Pill":
                    html += f'<td style="text-align:center;">{cell}</td>'
                elif h == "Brokerage Received":
                    val = 0.0 if pd.isnull(cell) else cell
                    html += f'<td>₹ {val:.2f}</td>'
                else:
                    html += f'<td>{cell}</td>'
            html += '</tr>'
        html += '</tbody></table></div>'
        return html

    st.markdown("""
    <style>
    .leads-table-wrapper { width:99vw; max-width:1100px; overflow-x:auto; }
    .leads-table-min {
        border-collapse:separate;
        border-spacing:0;
        width:100%;
        font-size:0.82rem;
        background:#fff;
        border-radius:9px;
        overflow:hidden;
        margin:0;
    }
    .leads-table-min th, .leads-table-min td {
        padding:3.8px 6.5px 3.1px 6.5px;
        white-space:nowrap;
        font-size:0.84rem;
    }
    .leads-table-min th {
        background: #31406e;
        color:#fff;
        font-weight:600;
        border-bottom:1.2px solid #e3e6eb;
        text-align:left;
        letter-spacing:0.01em;
        position:sticky;
        top:0;
        z-index:2;
    }
    .leads-table-min td {
        border-bottom:1px solid #f1f2f6;
        background:#fff;
        vertical-align:middle;
        color:#222;
        line-height:1.15;
    }
    .leads-table-min tr:hover td { background:#f5f7fa; }
    .leads-table-min tr:last-child td { border-bottom:none; }
    </style>
    """, unsafe_allow_html=True)
    st.write(df_to_colored_html(df_display), unsafe_allow_html=True)
else:
    st.info("No leads data found in MongoDB.")
# =========================
# SOCIAL MEDIA ANALYTICS REPORTING DASHBOARD STARTS
# =========================

# =========================
# LINKEDIN ANALYTICS
# =========================
def get_last_12_month_options():
    today = date.today().replace(day=1)
    months = [today - relativedelta(months=i) for i in range(12)]
    return [d.strftime('%B %Y') for d in months]

def load_linkedin_analytics_df():
    try:
        mongo_uri_linkedin = st.secrets["mongo_uri_linkedin"]
        db_name = "sal-lnkd"
        client = MongoClient(mongo_uri_linkedin, serverSelectionTimeoutMS=5000, tlsCAFile=certifi.where())
        db = client[db_name]
        doc_analytics = db["lnkd-analytics"].find_one({})
        if doc_analytics and "daily_records" in doc_analytics:
            df_analytics = pd.DataFrame(doc_analytics["daily_records"])
            followers_total = int(doc_analytics.get("followers_total", 0))
        else:
            df_analytics = pd.DataFrame()
            followers_total = 0
        doc_extras = db["lnkd-extras"].find_one({})
        if doc_extras and "daily_records" in doc_extras:
            df_extras = pd.DataFrame(doc_extras["daily_records"])
        else:
            df_extras = pd.DataFrame()
        client.close()
        return df_analytics, df_extras, followers_total
    except Exception as e:
        st.error(f"Could not connect to LinkedIn MongoDB: {e}")
        return pd.DataFrame(), pd.DataFrame(), 0

def render_linkedin_analytics():
    df_analytics, df_extras, followers_total = load_linkedin_analytics_df()
    if df_analytics.empty and df_extras.empty:
        st.info("No LinkedIn analytics data found in MongoDB.")
        return

    # lnkd-analytics
    if not df_analytics.empty:
        rename_map = {}
        if "date" in df_analytics.columns:
            rename_map["date"] = "Date"
        if "total_followers" in df_analytics.columns:
            rename_map["total_followers"] = "Total followers (Date-wise)"
        if "total_unique_visitors" in df_analytics.columns:
            rename_map["total_unique_visitors"] = "Total Unique Visitors (Date-wise)"
        df_analytics = df_analytics.rename(columns=rename_map)
        if "Date" in df_analytics.columns:
            df_analytics["Date"] = pd.to_datetime(df_analytics["Date"], errors="coerce")
            df_analytics = df_analytics.dropna(subset=["Date"])
            df_analytics["Month"] = df_analytics["Date"].dt.to_period("M")
            df_analytics["MonthStr"] = df_analytics["Date"].dt.strftime('%B %Y')
        else:
            st.error("No 'date' field found in daily_records for lnkd-analytics collection.")
            return
    else:
        st.error("No records found in lnkd-analytics collection.")
        return

    # lnkd-extras
    if not df_extras.empty:
        if "date" in df_extras.columns:
            df_extras["Date"] = pd.to_datetime(df_extras["date"], errors="coerce")
            df_extras = df_extras.dropna(subset=["Date"])
            df_extras["Month"] = df_extras["Date"].dt.to_period("M")
            df_extras["MonthStr"] = df_extras["Date"].dt.strftime('%B %Y')
        else:
            st.error("No 'date' field found in daily_records for lnkd-extras collection.")
            return
    else:
        st.error("No records found in lnkd-extras collection.")
        return

    months_analytics = set(df_analytics.get("MonthStr", pd.Series([])))
    months_extras = set(df_extras.get("MonthStr", pd.Series([])))
    month_options = sorted(
        set(get_last_12_month_options()) | months_analytics | months_extras,
        key=lambda d: datetime.strptime(d, "%B %Y"),
        reverse=True
    )
    latest_month = month_options[0]
    default_index = month_options.index(latest_month) if latest_month in month_options else 0

    st.markdown("""
    <h2 style='text-align:center; font-size:2.2em; color:#2d448d; margin-bottom:0.7em; margin-top:0.1em;'>Linkedin Analytics</h2>
    """, unsafe_allow_html=True)

    selected_month_str = st.selectbox("Select month", month_options, index=default_index, key="analytics_month")
    selected_period = pd.Period(datetime.strptime(selected_month_str, "%B %Y").date(), freq="M")
    prev_period = selected_period - 1
    prev_month_str = prev_period.strftime('%B %Y')

    def get_delta_color(val, pos_color, neg_color):
        if val > 0: return pos_color
        if val < 0: return neg_color
        return "#888"

    # ROW 1: Impressions, Clicks, Engagement Rate (from lnkd-extras)
    impressions_month_rows = df_extras[df_extras["Month"] == selected_period]
    impressions_prev_rows = df_extras[df_extras["Month"] == prev_period]
    impressions_cur = int(impressions_month_rows.get("total_impressions", pd.Series([0])).sum()) if "total_impressions" in df_extras.columns else 0
    impressions_prev = int(impressions_prev_rows.get("total_impressions", pd.Series([0])).sum()) if "total_impressions" in df_extras.columns else 0
    impressions_delta = impressions_cur - impressions_prev
    impressions_delta_sign = "+" if impressions_delta > 0 else ""
    impressions_delta_color = "#2ecc40" if impressions_delta > 0 else "#ff4136" if impressions_delta < 0 else "#888"
    impressions_arrow = "↑" if impressions_delta > 0 else ("↓" if impressions_delta < 0 else "")
    impressions_delta_text = f"{impressions_delta_sign}{impressions_delta:,}"

    clicks_month_rows = df_extras[df_extras["Month"] == selected_period]
    clicks_prev_rows = df_extras[df_extras["Month"] == prev_period]
    clicks_cur = int(clicks_month_rows.get("clicks", pd.Series([0])).sum()) if "clicks" in df_extras.columns else 0
    clicks_prev = int(clicks_prev_rows.get("clicks", pd.Series([0])).sum()) if "clicks" in df_extras.columns else 0
    clicks_delta = clicks_cur - clicks_prev
    clicks_delta_sign = "+" if clicks_delta > 0 else ""
    clicks_delta_color = get_delta_color(clicks_delta, "#16a085", "#e74c3c")
    clicks_arrow = "↑" if clicks_delta > 0 else ("↓" if clicks_delta < 0 else "")
    clicks_delta_text = f"{clicks_delta_sign}{clicks_delta:,}"

    engagement_month_rows = df_extras[df_extras["Month"] == selected_period]
    engagement_prev_rows = df_extras[df_extras["Month"] == prev_period]
    engagement_cur = engagement_month_rows["engagement_rate"].mean() if "engagement_rate" in df_extras.columns and not engagement_month_rows.empty else 0.0
    engagement_prev = engagement_prev_rows["engagement_rate"].mean() if "engagement_rate" in df_extras.columns and not engagement_prev_rows.empty else 0.0
    engagement_delta = engagement_cur - engagement_prev
    engagement_delta_sign = "+" if engagement_delta > 0 else ""
    engagement_delta_color = "#2ecc40" if engagement_delta > 0 else "#ff4136" if engagement_delta < 0 else "#888"
    engagement_arrow = "↑" if engagement_delta > 0 else ("↓" if engagement_delta < 0 else "")
    engagement_cur_display = f"{engagement_cur*100:.2f}%"
    engagement_delta_display = f"{engagement_delta_sign}{engagement_delta*100:.2f}%"

    # ROW 2: Followers, Unique Visitors (from lnkd-analytics)
    followers_month_rows = df_analytics[df_analytics["Month"] == selected_period]
    followers_prev_rows = df_analytics[df_analytics["Month"] == prev_period]
    followers_gained_cur = int(followers_month_rows.get("Total followers (Date-wise)", pd.Series([0])).sum()) if "Total followers (Date-wise)" in df_analytics.columns else 0
    followers_gained_prev = int(followers_prev_rows.get("Total followers (Date-wise)", pd.Series([0])).sum()) if "Total followers (Date-wise)" in df_analytics.columns else 0
    followers_delta = followers_gained_cur - followers_gained_prev
    followers_delta_sign = "+" if followers_delta > 0 else ""
    followers_delta_color = get_delta_color(followers_delta, "#2ecc40", "#ff4136")
    followers_delta_text = f"{followers_delta_sign}{followers_delta:,}"

    total_unique_visitors = int(df_analytics.get("Total Unique Visitors (Date-wise)", pd.Series([0])).sum()) if "Total Unique Visitors (Date-wise)" in df_analytics.columns else 0
    visitors_month_rows = df_analytics[df_analytics["Month"] == selected_period]
    visitors_prev_rows = df_analytics[df_analytics["Month"] == prev_period]
    visitors_gained_cur = int(visitors_month_rows.get("Total Unique Visitors (Date-wise)", pd.Series([0])).sum()) if "Total Unique Visitors (Date-wise)" in df_analytics.columns else 0
    visitors_gained_prev = int(visitors_prev_rows.get("Total Unique Visitors (Date-wise)", pd.Series([0])).sum()) if "Total Unique Visitors (Date-wise)" in df_analytics.columns else 0
    visitors_delta = visitors_gained_cur - visitors_gained_prev
    visitors_delta_sign = "+" if visitors_delta > 0 else ""
    visitors_delta_color = get_delta_color(visitors_delta, "#13c4a3", "#ff4136")
    visitors_delta_text = f"{visitors_delta_sign}{visitors_delta:,}"

    # --------------- Styling for Circles and Layout (no line-breaks, zoom-on-hover, extra space between texts) -----------------
    st.markdown(f"""
    <style>
    .analytics-circles-row {{
        display: flex;
        flex-direction: row;
        justify-content: center;
        align-items: flex-start;
        gap: 60px;
        margin-top: 2.1em;
        margin-bottom: 2.2em;
        flex-wrap: wrap;
    }}
    .circle-block {{
        display: flex;
        flex-direction: column;
        align-items: center;
        min-width: 220px;
        max-width: 260px;
    }}
    .impressions-circle, .clicks-circle, .engagement-circle, .followers-circle, .visitors-circle {{
        border-radius: 50%;
        width: 140px;
        height: 140px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 2.7em;
        font-weight: bold;
        color: #fff;
        box-shadow: 0 4px 18px rgba(162,155,254,0.14);
        transition: transform 0.17s cubic-bezier(.4,2,.55,.44);
        cursor:pointer;
        margin-bottom: 0.7em;
    }}
    .impressions-circle {{ background: linear-gradient(135deg, #a29bfe 0%, #dfe6e9 100%); }}
    .clicks-circle {{ background: linear-gradient(135deg, #00b894 0%, #55efc4 100%); }}
    .engagement-circle {{ background: linear-gradient(135deg, #ffeaa7 0%, #fdcb6e 100%); color: #fff; }}
    .followers-circle {{ background: linear-gradient(135deg, #3f8ae0 0%, #6cd4ff 100%); }}
    .visitors-circle {{ background: linear-gradient(135deg, #13c4a3 0%, #69f0ae 100%); }}
    .impressions-circle:hover, .clicks-circle:hover, .engagement-circle:hover, .followers-circle:hover, .visitors-circle:hover {{
        transform: scale(1.13);
        box-shadow: 0 8px 32px rgba(0,0,0,0.14);
    }}
    .circle-inline-label {{
        text-align: center;
        font-weight: 600;
        font-size: 1.08em;
        margin-bottom: 0.28em;
        color: #2d448d;
        display: inline-block;
        white-space: nowrap;
    }}
    .circle-delta-row {{
        text-align: center;
        font-size: 0.98em;
        font-weight: 600;
        margin-top: 0.14em;
        margin-bottom: 0.1em;
        white-space: nowrap;
    }}
    .circle-delta-value {{
        font-size: 1.09em;
        font-weight: 700;
        margin-right: 4px;
    }}
    .circle-delta-label {{
        color: #888;
        font-size: 0.94em;
        font-weight: 400;
        margin-left: 2px;
    }}
    /* Extra space between text blocks for row 2 below circles */
    .analytics-circles-row.row2 .two-labels-inline {{
        display: flex;
        justify-content: center;
        gap: 60px;
        margin-bottom: 0.2em;
        margin-top: 0.1em;
    }}
    </style>
    """, unsafe_allow_html=True)

    # ----------- ROW 1: Total Impressions, Clicks, Engagement Rate -----------
    st.markdown(f"""
    <div class="analytics-circles-row">
        <div class="circle-block">
            <div class="impressions-circle">{impressions_cur:,}</div>
            <div class="circle-inline-label">
                Impressions in <span style="font-weight:700;">{selected_month_str}</span>: <b>{impressions_cur:,}</b>
            </div>
            <div class="circle-delta-row">
                <span class="circle-delta-value" style="color:{impressions_delta_color};">{impressions_delta_text}</span>
                <span style="color:{impressions_delta_color};font-size:1.01em;">
                    {impressions_arrow}
                </span>
                <span class="circle-delta-label">vs. previous month ({prev_month_str})</span>
            </div>
        </div>
        <div class="circle-block">
            <div class="clicks-circle">{clicks_cur:,}</div>
            <div class="circle-inline-label">
                Clicks in <span style="font-weight:700;">{selected_month_str}</span>: <b>{clicks_cur:,}</b>
            </div>
            <div class="circle-delta-row">
                <span class="circle-delta-value" style="color:{clicks_delta_color};">{clicks_delta_text}</span>
                <span style="color:{clicks_delta_color};font-size:1.01em;">
                    {clicks_arrow}
                </span>
                <span class="circle-delta-label">vs. previous month ({prev_month_str})</span>
            </div>
        </div>
        <div class="circle-block">
            <div class="engagement-circle">{engagement_cur_display}</div>
            <div class="circle-inline-label">
                Engagement Rate in <span style="font-weight:700;">{selected_month_str}</span>: <b>{engagement_cur_display}</b>
            </div>
            <div class="circle-delta-row">
                <span class="circle-delta-value" style="color:{engagement_delta_color};">{engagement_delta_display}</span>
                <span style="color:{engagement_delta_color};font-size:1.01em;">
                    {engagement_arrow}
                </span>
                <span class="circle-delta-label">vs. previous month ({prev_month_str})</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ----------- ROW 2: Total Followers, Total Unique Visitors with space between text blocks -----------
    st.markdown(f"""
    <div class="analytics-circles-row row2">
        <div class="circle-block">
            <div class="followers-circle">{followers_total:,}</div>
        </div>
        <div class="circle-block">
            <div class="visitors-circle">{total_unique_visitors:,}</div>
        </div>
    </div>
    <div class="analytics-circles-row row2">
        <div class="two-labels-inline">
            <div class="circle-inline-label">
                Followers gained in <span style="font-weight:700;">{selected_month_str}</span>: <b>{followers_gained_cur:,}</b>
            </div>
            <div class="circle-inline-label">
                Unique Visitors gained in <span style="font-weight:700;">{selected_month_str}</span>: <b>{visitors_gained_cur:,}</b>
            </div>
        </div>
    </div>
    <div class="analytics-circles-row row2">
        <div class="two-labels-inline">
            <div class="circle-delta-row">
                <span class="circle-delta-value" style="color:{followers_delta_color};">{followers_delta_text}</span>
                <span style="color:{followers_delta_color};font-size:1.01em;">
                    {"↑" if followers_delta > 0 else "↓" if followers_delta < 0 else ""}
                </span>
                <span class="circle-delta-label">vs. previous month ({prev_month_str})</span>
            </div>
            <div class="circle-delta-row">
                <span class="circle-delta-value" style="color:{visitors_delta_color};">{visitors_delta_text}</span>
                <span style="color:{visitors_delta_color};font-size:1.01em;">
                    {"↑" if visitors_delta > 0 else "↓" if visitors_delta < 0 else ""}
                </span>
                <span class="circle-delta-label">vs. previous month ({prev_month_str})</span>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

render_linkedin_analytics()
# =========================
# FACEBOOK ANALYTICS
# =========================
PAGE_ID = st.secrets["facebook"]["page_id"]
ACCESS_TOKEN = st.secrets["facebook"]["access_token"]

def get_total_metric_value(metric, since, until):
    url = f"https://graph.facebook.com/v19.0/{PAGE_ID}/insights/{metric}"
    params = {
        "since": since,
        "until": until,
        "access_token": ACCESS_TOKEN
    }
    try:
        resp = requests.get(url, params=params).json()
        if (
            "data" in resp and len(resp["data"]) > 0
            and "values" in resp["data"][0] and len(resp["data"][0]["values"]) > 0
        ):
            return sum(v["value"] for v in resp["data"][0]["values"])
        else:
            print(f"[DEBUG] No data for metric {metric} between {since} and {until}. Response: {resp}")
        return 0
    except Exception as e:
        print(f"[ERROR] Exception in get_total_metric_value: {e}")
        return 0

def get_lifetime_total_followers():
    url = f"https://graph.facebook.com/v19.0/{PAGE_ID}/insights/page_follows"
    params = {
        "access_token": ACCESS_TOKEN
    }
    try:
        resp = requests.get(url, params=params).json()
        if (
            "data" in resp and len(resp["data"]) > 0
            and "values" in resp["data"][0] and len(resp["data"][0]["values"]) > 0
        ):
            return resp["data"][0]["values"][-1]["value"]
        else:
            print(f"[DEBUG] No data for lifetime followers. Response: {resp}")
        return 0
    except Exception as e:
        print(f"[ERROR] Exception in get_lifetime_total_followers: {e}")
        return 0

def get_previous_lifetime_total_followers(prev_period_end):
    url = f"https://graph.facebook.com/v19.0/{PAGE_ID}/insights/page_follows"
    params = {
        "since": prev_period_end,
        "until": prev_period_end,
        "access_token": ACCESS_TOKEN
    }
    try:
        resp = requests.get(url, params=params).json()
        if (
            "data" in resp and len(resp["data"]) > 0
            and "values" in resp["data"][0] and len(resp["data"][0]["values"]) > 0
        ):
            return resp["data"][0]["values"][-1]["value"]
        else:
            print(f"[DEBUG] No data for previous lifetime followers. Response: {resp}")
        return 0
    except Exception as e:
        print(f"[ERROR] Exception in get_previous_lifetime_total_followers: {e}")
        return 0

def get_posts(since, until):
    url = f"https://graph.facebook.com/v19.0/{PAGE_ID}/posts"
    params = {
        "since": since,
        "until": until,
        "limit": 100,
        "access_token": ACCESS_TOKEN
    }
    posts = []
    try:
        while url:
            resp = requests.get(url, params=params).json()
            posts.extend(resp.get('data', []))
            paging = resp.get('paging', {})
            url = paging.get('next') if 'next' in paging else None
            params = {}
        return posts
    except Exception as e:
        print(f"[ERROR] Exception in get_posts: {e}")
        return []

def get_post_likes(post_id, access_token):
    url = f"https://graph.facebook.com/v19.0/{post_id}?fields=likes.summary(true)&access_token={access_token}"
    try:
        resp = requests.get(url).json()
        return resp.get('likes', {}).get('summary', {}).get('total_count', 0)
    except Exception as e:
        print(f"[ERROR] Exception in get_post_likes: {e}")
        return 0

def get_post_comments(post_id, access_token):
    url = f"https://graph.facebook.com/v19.0/{post_id}/comments?summary=true&access_token={access_token}"
    try:
        resp = requests.get(url).json()
        return resp.get('summary', {}).get('total_count', 0)
    except Exception as e:
        print(f"[ERROR] Exception in get_post_comments: {e}")
        return 0

def safe_percent(prev, cur):
    try:
        if prev == 0 and cur == 0:
            return 0
        elif prev == 0:
            return 100 if cur > 0 else 0
        return ((cur - prev) / abs(prev)) * 100
    except Exception:
        return 0

def get_delta_icon_and_color(val):
    if val > 0:
        return "↑", "#2ecc40"
    elif val < 0:
        return "↓", "#ff4136"
    else:
        return "", "#aaa"

# ------------------------
# Date logic for month selection
# ------------------------
today = datetime.today()
month_options = [ (today.replace(day=1) - timedelta(days=30*i)).strftime('%B %Y') for i in range(12)]
month_options = list(dict.fromkeys(month_options))  # remove dups

st.markdown('<h2 style="color:#2d448d; text-align:center; margin-top:1.2em; margin-bottom:0.5em;">Facebook Page Analytics</h2>', unsafe_allow_html=True)
selected_month_str = st.selectbox("Select Month", month_options, index=0)

selected_month_dt = datetime.strptime(selected_month_str, "%B %Y")
cur_start = selected_month_dt.replace(day=1)
cur_end = (cur_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
prev_start = (cur_start - timedelta(days=1)).replace(day=1)
prev_end = cur_start - timedelta(days=1)

cur_since = cur_start.strftime('%Y-%m-%d')
cur_until = cur_end.strftime('%Y-%m-%d')
prev_since = prev_start.strftime('%Y-%m-%d')
prev_until = prev_end.strftime('%Y-%m-%d')

cur_views = get_total_metric_value("page_views_total", cur_since, cur_until)
prev_views = get_total_metric_value("page_views_total", prev_since, prev_until)
views_delta = cur_views - prev_views
views_percent = safe_percent(prev_views, cur_views)
views_icon, views_color = get_delta_icon_and_color(views_delta)

cur_total_likes = get_total_metric_value("page_fans", cur_since, cur_until)
prev_total_likes = get_total_metric_value("page_fans", prev_since, prev_until)
likes_delta = cur_total_likes - prev_total_likes
likes_percent = safe_percent(prev_total_likes, cur_total_likes)
likes_icon, likes_color = get_delta_icon_and_color(likes_delta)

lifetime_total_followers = get_lifetime_total_followers()
prev_lifetime_total_followers = get_previous_lifetime_total_followers(prev_until)
followers_delta = lifetime_total_followers - prev_lifetime_total_followers
followers_icon, followers_color = get_delta_icon_and_color(followers_delta)

cur_posts_list = get_posts(cur_since, cur_until)
cur_posts = len(cur_posts_list)

st.markdown("""
<style>
.fb-metric-row {
    display: flex;
    flex-direction: row;
    justify-content: center;
    align-items: flex-start;
    gap: 50px;
    margin-top: 2em;
    margin-bottom: 2em;
    flex-wrap: wrap;
}
.fb-metric-block {
    display: flex;
    flex-direction: column;
    align-items: center;
    min-width: 220px;
    max-width: 260px;
}
.fb-circle {
    background: linear-gradient(135deg, #459fda 0%, #a6ce39 100%);
    border-radius: 50%;
    width: 130px;
    height: 130px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 2.5em;
    font-weight: bold;
    color: #fff;
    box-shadow: 0 4px 18px rgba(69,159,218,0.14);
    transition: transform 0.17s cubic-bezier(.4,2,.55,.44);
    cursor:pointer;
    margin-bottom: 0.7em;
}
.fb-circle:hover {
    transform: scale(1.13);
    box-shadow: 0 8px 32px rgba(69,159,218,0.18);
}
.fb-label {
    text-align: center;
    font-weight: 600;
    font-size: 1.08em;
    margin-bottom: 0.28em;
    color: #2d448d;
}
.fb-delta-row {
    text-align: center;
    font-size: 0.99em;
    font-weight: 600;
    margin-top: 0.14em;
    margin-bottom: 0.11em;
}
.fb-delta-up {
    color: #2ecc40;
    font-weight: 700;
}
.fb-delta-down {
    color: #ff4136;
    font-weight: 700;
}
.fb-delta-same {
    color: #888;
    font-weight: 700;
}
.fb-delta-note {
    color: #888;
    font-size: 0.94em;
    font-weight: 400;
    margin-left: 2px;
}
.fb-post-table {
    border-collapse: collapse;
    width: 100%;
    margin-top: 18px;
}
.fb-post-table th {
    background-color: #2d448d !important;
    color: #fff !important;
    font-weight: bold !important;
    font-size: 1.09em !important;
    text-align: left !important;
    padding: 10px 15px !important;
    border-bottom: 2px solid #eaeaea !important;
}
.fb-post-table td {
    font-size: 1.07em !important;
    color: #222 !important;
    padding: 8px 15px !important;
    border-bottom: 1px solid #eaeaea !important;
    word-break: break-word;
}
.fb-post-table tr:nth-child(even) {
    background-color: #f5f7fa !important;
}
.fb-post-table tr:nth-child(odd) {
    background-color: #fff !important;
}
.fb-post-table a {
    color: #2061b2 !important;
    text-decoration: underline !important;
}
</style>
""", unsafe_allow_html=True)

st.markdown(f"""
<div class="fb-metric-row">
    <div class="fb-metric-block">
        <div class="fb-label">Total Views ({selected_month_str})</div>
        <div class="fb-circle">{cur_views:,}</div>
        <div class="fb-delta-row">
            <span class="{ 'fb-delta-up' if views_delta > 0 else ('fb-delta-down' if views_delta < 0 else 'fb-delta-same') }">{views_icon} {views_delta:+}</span>
            <span class="fb-delta-note">(vs. Previous Month)</span>
        </div>
    </div>
    <div class="fb-metric-block">
        <div class="fb-label">Total Page Likes ({selected_month_str})</div>
        <div class="fb-circle">{cur_total_likes:,}</div>
        <div class="fb-delta-row">
            <span class="{ 'fb-delta-up' if likes_delta > 0 else ('fb-delta-down' if likes_delta < 0 else 'fb-delta-same') }">{likes_icon} {likes_delta:+}</span>
            <span class="fb-delta-note">(vs. Previous Month)</span>
        </div>
    </div>
    <div class="fb-metric-block">
        <div class="fb-label">Total Followers (Lifetime)</div>
        <div class="fb-circle">{lifetime_total_followers:,}</div>
        <div class="fb-delta-row">
            <span class="{ 'fb-delta-up' if followers_delta > 0 else ('fb-delta-down' if followers_delta < 0 else 'fb-delta-same') }">{followers_icon} {followers_delta:+}</span>
            <span class="fb-delta-note">(since Previous Month)</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown(f"<h3 style='color:#2d448d;'>Posts Published in {selected_month_str}</h3>", unsafe_allow_html=True)

if cur_posts > 0:
    post_table = []
    for post in cur_posts_list:
        post_id = post["id"]
        post_url = f"https://www.facebook.com/{PAGE_ID}/posts/{post_id.split('_')[-1]}"
        message = post.get("message", "")
        title_text = (message[:100] + "...") if len(message) > 100 else message
        likes = get_post_likes(post_id, ACCESS_TOKEN)
        comments = get_post_comments(post_id, ACCESS_TOKEN)
        post_table.append({
            "Title": f"<a href='{post_url}' target='_blank'>{title_text}</a>",
            "Likes": likes,
            "Comments": comments,
        })
    df = pd.DataFrame(post_table)
    st.markdown(df.to_html(escape=False, index=False, classes="fb-post-table"), unsafe_allow_html=True)
else:
    st.info("No posts published this month.")

st.caption("All data is pulled live from Facebook Graph API. Tokens and IDs are loaded securely from Streamlit secrets.")
# =========================
# YOUTUBE ANALYTICS
# =========================
def get_access_token(client_id, client_secret, refresh_token):
    """Dynamically fetches an access token using your refresh_token."""
    if not refresh_token or refresh_token == "YOUR_REFRESH_TOKEN":
        st.error(
            "Missing refresh token! Please generate a new refresh token using the OAuth flow "
            "and add it to your .streamlit/secrets.toml under [youtube]."
        )
        st.stop()
    url = "https://oauth2.googleapis.com/token"
    data = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token"
    }
    response = requests.post(url, data=data)
    if response.status_code != 200:
        st.error(f"OAuth error: {response.text}")
        st.stop()
    return response.json()["access_token"]

def get_auth_headers(access_token):
    """Sets headers for OAuth requests."""
    return {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}

def get_date_ranges():
    """Gets start and end dates for current and previous period (last 28 days granularity)."""
    today = date.today()
    end_cur = today
    start_cur = today - timedelta(days=27)
    end_prev = start_cur - timedelta(days=1)
    start_prev = end_prev - timedelta(days=27)
    return start_cur, end_cur, start_prev, end_prev

# Read credentials from Streamlit secrets
client_id = st.secrets["youtube"].get("client_id", "YOUR_CLIENT_ID")
client_secret = st.secrets["youtube"].get("client_secret", "YOUR_CLIENT_SECRET")
refresh_token = st.secrets["youtube"].get("refresh_token", "YOUR_REFRESH_TOKEN")

# Obtain access token dynamically
YT_ACCESS_TOKEN = get_access_token(client_id, client_secret, refresh_token)

YOUTUBE_API_KEY = st.secrets["youtube"].get("api_key", "YOUR_API_KEY")
CHANNEL_ID = st.secrets["youtube"].get("channel_id", "YOUR_CHANNEL_ID")

def get_yt_analytics_summary(start_date, end_date):
    endpoint = "https://youtubeanalytics.googleapis.com/v2/reports"
    params = {
        "ids": f"channel=={CHANNEL_ID}",
        "startDate": start_date.strftime("%Y-%m-%d"),
        "endDate": end_date.strftime("%Y-%m-%d"),
        "metrics": "views,estimatedMinutesWatched,subscribersGained,subscribersLost",
        "dimensions": "",
    }
    resp = requests.get(endpoint, headers=get_auth_headers(YT_ACCESS_TOKEN), params=params).json()
    if "rows" not in resp:
        return {"views": 0, "watch_time": 0, "subs_gained": 0, "subs_lost": 0}
    row = resp["rows"][0]
    col_map = {c["name"]: i for i, c in enumerate(resp["columnHeaders"])}
    return {
        "views": int(row[col_map["views"]]),
        "watch_time": int(row[col_map["estimatedMinutesWatched"]]),
        "subs_gained": int(row[col_map["subscribersGained"]]),
        "subs_lost": int(row[col_map["subscribersLost"]]),
    }

def get_total_subscribers():
    url = f"https://www.googleapis.com/youtube/v3/channels?part=statistics&id={CHANNEL_ID}&key={YOUTUBE_API_KEY}"
    resp = requests.get(url).json()
    if "items" in resp and len(resp["items"]) > 0:
        return int(resp["items"][0]["statistics"].get("subscriberCount", 0))
    return 0

def get_new_subs_text(subs_gained, subs_lost):
    net = subs_gained - subs_lost
    if net > 0:
        color = "#2ecc40"  # green
        sign = "+"
        text = f"<span style='color:{color}; font-weight:bold;'>{sign}{net} new</span>"
    elif net < 0:
        color = "#ff4136"  # red
        sign = "-"
        text = f"<span style='color:{color}; font-weight:bold;'>{sign}{abs(net)} unsubscribed</span>"
    else:
        color = "#888"
        text = f"<span style='color:{color}; font-weight:bold;'>0 (no change)</span>"
    return text

start_cur, end_cur, start_prev, end_prev = get_date_ranges()
overview_cur = get_yt_analytics_summary(start_cur, end_cur)
overview_prev = get_yt_analytics_summary(start_prev, end_prev)
total_subscribers = get_total_subscribers()

st.markdown("""
<style>
.section-header {
    font-size: 2.1em !important;
    font-weight: bold !important;
    color: #2d448d !important;
    margin-bottom: 0.5em;
}
.yt-metric-circle {
    transition: transform 0.18s cubic-bezier(.4,2,.55,.44);
    cursor: pointer;
}
.yt-metric-circle:hover {
    transform: scale(1.13);
    box-shadow: 0 6px 20px rgba(44,68,141,0.18);
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="section-header">YouTube Channel Overview</div>', unsafe_allow_html=True)
overview_cols = st.columns(3)

subs_gained = overview_cur["subs_gained"]
subs_lost = overview_cur["subs_lost"]
net_new = subs_gained - subs_lost

subs_text = get_new_subs_text(subs_gained, subs_lost)

def get_delta_text(current, previous):
    delta = current - previous
    if previous == 0:
        percent = 0
    else:
        percent = delta / previous * 100
    if delta > 0:
        color = "#2ecc40"  # green
        sign = "+"
        text = f"<span style='color:{color}; font-weight:bold;'>{sign}{delta} ({percent:.1f}%)</span>"
    elif delta < 0:
        color = "#ff4136"  # red
        sign = "-"
        text = f"<span style='color:{color}; font-weight:bold;'>{sign}{abs(delta)} ({percent:.1f}%)</span>"
    else:
        color = "#888"
        text = f"<span style='color:{color}; font-weight:bold;'>0</span>"
    return text

subs_current_net = overview_cur["subs_gained"] - overview_cur["subs_lost"]
subs_prev_net = overview_prev["subs_gained"] - overview_prev["subs_lost"]
views_delta = overview_cur["views"] - overview_prev["views"]
watch_delta = overview_cur["watch_time"] - overview_prev["watch_time"]

overview_metrics = [
    {
        "label": "Subscribers (Net)",
        "value": total_subscribers,
        "subs_text": get_new_subs_text(overview_cur["subs_gained"], overview_cur["subs_lost"]),
        "delta_text": "",
        "color": "#ffe1c8",
        "circle_color": "#e67e22",
    },
    {
        "label": "Total Views",
        "value": overview_cur["views"],
        "subs_text": "",
        "delta_text": get_delta_text(overview_cur["views"], overview_prev["views"]),
        "color": "#c8e6fa",
        "circle_color": "#3498db",
    },
    {
        "label": "Watch Time (min)",
        "value": overview_cur["watch_time"],
        "subs_text": "",
        "delta_text": get_delta_text(overview_cur["watch_time"], overview_prev["watch_time"]),
        "color": "#a7f1df",
        "circle_color": "#16a085",
    },
]

for i, col in enumerate(overview_cols):
    metric = overview_metrics[i]
    with col:
        st.markdown(
            f"""
            <div style='text-align:center; font-weight:500; font-size:23px; margin-bottom:0.2em; color:#2d448d'>
                {metric["label"]}
            </div>
            <div style='margin:0 auto; display:flex; align-items:center; justify-content:center; height:110px;'>
                <div class="yt-metric-circle" style='background:{metric["color"]}; border-radius:50%; width:100px; height:100px; display:flex; align-items:center; justify-content:center; box-shadow: 0 4px 12px rgba(0,0,0,0.12);'>
                    <span style='color:{metric["circle_color"]}; font-size:2em; font-family: Fira Code, monospace; font-weight:bold;'>{metric["value"]}</span>
                </div>
            </div>
            <div style='text-align:center; font-size:16px; margin-top:0.3em; min-height:1.5em;'>
                {metric["subs_text"] if metric["subs_text"] else metric["delta_text"]}
            </div>
            """,
            unsafe_allow_html=True
        )

def get_top_videos(start_date, end_date, max_results=5):
    video_url = f"https://www.googleapis.com/youtube/v3/search?key={YOUTUBE_API_KEY}&channelId={CHANNEL_ID}&part=id&order=date&type=video&maxResults=50"
    resp = requests.get(video_url).json()
    video_ids = [item["id"]["videoId"] for item in resp.get("items", [])]
    if not video_ids:
        return pd.DataFrame()
    stats_url = f"https://www.googleapis.com/youtube/v3/videos?key={YOUTUBE_API_KEY}&id={','.join(video_ids)}&part=snippet,statistics"
    stats_resp = requests.get(stats_url).json()
    data = []
    for item in stats_resp.get("items", []):
        published = item["snippet"]["publishedAt"][:10]
        vid_id = item["id"]
        title = item["snippet"]["title"][:60]
        views = int(item["statistics"].get("viewCount", 0))
        likes = int(item["statistics"].get("likeCount", 0))
        comments = int(item["statistics"].get("commentCount", 0))
        data.append({
            "id": vid_id,
            "title": title,
            "published": published,
            "views": views,
            "likes": likes,
            "comments": comments
        })
    df = pd.DataFrame(data).sort_values("views", ascending=False).head(max_results)
    ids = list(df["id"])
    if not ids:
        return df
    endpoint = "https://youtubeanalytics.googleapis.com/v2/reports"
    params = {
        "ids": "channel==MINE",
        "startDate": start_date.strftime("%Y-%m-%d"),
        "endDate": end_date.strftime("%Y-%m-%d"),
        "metrics": "estimatedMinutesWatched,views,likes,comments",
        "dimensions": "video",
        "filters": f"video=={','.join(ids)}"
    }
    resp = requests.get(endpoint, headers=get_auth_headers(YT_ACCESS_TOKEN), params=params).json()
    if "rows" not in resp:
        df["watch_time"] = 0
    else:
        wt_dict = {row[0]: row[1] for row in resp["rows"]}
        df["watch_time"] = df["id"].map(wt_dict).fillna(0)
    return df

top_videos_df = get_top_videos(start_cur, end_cur, max_results=5)

st.markdown('<div class="section-header">Top 5 Videos (Current Period)</div>', unsafe_allow_html=True)
if not top_videos_df.empty:
    st.markdown("""
    <style>
    .yt-table th, .yt-table td {padding: 7px 13px; font-size: 1.01em;}
    .yt-table th {background: #2d448d; color:#fff;}
    .yt-table tr:nth-child(even) {background: #f3f3f3;}
    .yt-table tr:nth-child(odd) {background: #fff;}
    </style>
    """, unsafe_allow_html=True)
    
    display_df = top_videos_df[["title", "views", "watch_time", "likes", "comments"]].copy()
    display_df.columns = ["Title", "Views", "Watch Time (min)", "Likes", "Comments"]
    display_df["Title"] = [
        f'<a href="https://www.youtube.com/watch?v={vid_id}" target="_blank">{title}</a>'
        for title, vid_id in zip(display_df["Title"], top_videos_df["id"])
    ]
    st.markdown(
        display_df.to_html(escape=False, index=False, classes="yt-table"),
        unsafe_allow_html=True
    )
else:
    st.info("No video data found for this period.")



st.caption("All YouTube metrics are updated live from YouTube Data & Analytics APIs. Credentials are loaded securely from Streamlit secrets.")

# END OF DASHBOARD


