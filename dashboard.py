import streamlit as st

# ── MUST be the very first Streamlit call ────────────────────────────────────
st.set_page_config(
    page_title="Salasar Services Digital Marketing Dashboard",
    layout="wide",
    page_icon="📊",
)

# ── Standard library ─────────────────────────────────────────────────────────
import io
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, date, timedelta

# ── Third-party ──────────────────────────────────────────────────────────────
import certifi
import pandas as pd
import pycountry
import requests
from dateutil.relativedelta import relativedelta
from fpdf import FPDF
from PIL import Image
from pymongo import MongoClient

# ── Google APIs ──────────────────────────────────────────────────────────────
from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.auth.transport.requests import Request as GAuthRequest
from google.oauth2 import service_account
from googleapiclient.discovery import build

# ── Constants ─────────────────────────────────────────────────────────────────
SCOPES = [
    "https://www.googleapis.com/auth/analytics.readonly",
    "https://www.googleapis.com/auth/webmasters.readonly",
]
PROPERTY_ID = "356205245"
SC_SITE_URL = "https://www.salasarservices.com/"

# ═════════════════════════════════════════════════════════════════════════════
# GLOBAL CSS  (single consolidated block)
# ═════════════════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Lato:wght@300;400;700&family=Fira+Code:wght@400;500;700&display=swap');

/* ── Loader ── */
.loader{position:relative;width:2.5em;height:2.5em;transform:rotate(165deg);margin:0 auto}
.loader:before,.loader:after{content:"";position:absolute;top:50%;left:50%;display:block;width:.5em;height:.5em;border-radius:.25em;transform:translate(-50%,-50%)}
.loader:before{animation:before8 2s infinite}
.loader:after{animation:after6 2s infinite}
@keyframes before8{
  0%{width:.5em;box-shadow:1em -.5em rgba(225,20,98,.75),-1em .5em rgba(111,202,220,.75)}
  35%{width:2.5em;box-shadow:0 -.5em rgba(225,20,98,.75),0 .5em rgba(111,202,220,.75)}
  70%{width:.5em;box-shadow:-1em -.5em rgba(225,20,98,.75),1em .5em rgba(111,202,220,.75)}
  100%{box-shadow:1em -.5em rgba(225,20,98,.75),-1em .5em rgba(111,202,220,.75)}
}
@keyframes after6{
  0%{height:.5em;box-shadow:.5em 1em rgba(61,184,143,.75),-.5em -1em rgba(233,169,32,.75)}
  35%{height:2.5em;box-shadow:.5em 0 rgba(61,184,143,.75),-.5em 0 rgba(233,169,32,.75)}
  70%{height:.5em;box-shadow:.5em -1em rgba(61,184,143,.75),-.5em 1em rgba(233,169,32,.75)}
  100%{box-shadow:.5em 1em rgba(61,184,143,.75),-.5em -1em rgba(233,169,32,.75)}
}

/* ── Bounce-in animation for circles ── */
@keyframes bounceIn{
  0%{transform:scale(.7);opacity:.5}
  60%{transform:scale(1.15)}
  80%{transform:scale(.95)}
  100%{transform:scale(1);opacity:1}
}

/* ── Metric circles ── */
.animated-circle{
  width:110px;height:110px;border-radius:50%;
  display:flex;align-items:center;justify-content:center;
  font-family:'Fira Code',monospace!important;
  font-size:2.1em;font-weight:500!important;color:#fff;
  background:#2d448d;
  box-shadow:0 4px 12px rgba(0,0,0,.10);
  transition:transform .18s cubic-bezier(.4,2,.3,1),box-shadow .22s;
  margin:0 auto;padding:1em;
  animation:bounceIn .6s cubic-bezier(.4,2,.3,1);
  will-change:transform;
}
.animated-circle:hover{transform:scale(1.09);box-shadow:0 8px 24px rgba(44,68,141,.15),0 2px 8px rgba(0,0,0,.07)}
.animated-circle-value{font-family:'Fira Code',monospace!important;font-size:.8em;font-weight:500;padding:.5em .6em;background:transparent;border-radius:.7em;display:inline-block;letter-spacing:.02em}

/* ── Section headers ── */
.section-header{
  font-weight:700!important;font-size:1.7em!important;
  margin-top:1.2em;margin-bottom:.6em;color:#2d448d;
  font-family:'Lato',Arial,sans-serif;
  border-left:5px solid #459fda;padding-left:.6em;
}

/* ── Section divider ── */
.section-divider{border:none;border-top:1.5px solid #e8eaf0;margin:2.2em 0 1.5em 0}

/* ── Tooltip ── */
.tooltip{display:inline-block;position:relative;cursor:pointer;vertical-align:super}
.tooltip .tooltiptext{visibility:hidden;width:240px;background:#222;color:#fff;text-align:left;border-radius:6px;padding:8px 10px;position:absolute;z-index:10;bottom:120%;left:50%;margin-left:-120px;opacity:0;transition:opacity .2s;font-size:.80em;font-weight:300!important;line-height:1.4}
.tooltip:hover .tooltiptext{visibility:visible;opacity:1}
.questionmark{font-weight:500!important;font-size:.72em;background:#e3e8f0;color:#2d448d;border-radius:50%;padding:0 3px;margin-left:4px;border:1px solid #d1d5db;box-shadow:0 1.5px 3px rgba(44,44,44,.08);display:inline-block;vertical-align:super;line-height:1em}

/* ── Tables ── */
.styled-table{border-collapse:collapse;width:100%;border-radius:5px 5px 0 0;overflow:hidden}
.styled-table thead tr{background-color:#2d448d;color:#fff;text-transform:uppercase;border-bottom:4px solid #459fda}
.styled-table th{color:#fff;text-transform:uppercase;text-align:center;padding:10px 15px}
.styled-table td{padding:12px 15px;color:#2d448d!important}
.styled-table tbody tr:nth-of-type(even){background-color:#f3f3f3}
.styled-table tbody tr:nth-of-type(odd){background-color:#fff}
.styled-table tbody tr:hover{background-color:#a6ce39!important}

/* ── LinkedIn circles ── */
.analytics-circles-row{display:flex;flex-direction:row;justify-content:center;align-items:flex-start;gap:60px;margin-top:2.1em;margin-bottom:2.2em;flex-wrap:wrap}
.circle-block{display:flex;flex-direction:column;align-items:center;min-width:220px;max-width:260px}
.impressions-circle{background:linear-gradient(135deg,#a29bfe 0%,#dfe6e9 100%)}
.clicks-circle{background:linear-gradient(135deg,#00b894 0%,#55efc4 100%)}
.engagement-circle{background:linear-gradient(135deg,#ffeaa7 0%,#fdcb6e 100%)}
.followers-circle{background:linear-gradient(135deg,#3f8ae0 0%,#6cd4ff 100%)}
.visitors-circle{background:linear-gradient(135deg,#13c4a3 0%,#69f0ae 100%)}
.impressions-circle,.clicks-circle,.engagement-circle,.followers-circle,.visitors-circle{
  border-radius:50%;width:140px;height:140px;display:flex;align-items:center;justify-content:center;
  font-size:2.4em;font-weight:bold;color:#fff;
  box-shadow:0 4px 18px rgba(162,155,254,.14);
  transition:transform .17s cubic-bezier(.4,2,.55,.44);
  cursor:pointer;margin-bottom:.7em;
  animation:bounceIn .6s cubic-bezier(.4,2,.3,1);
}
.impressions-circle:hover,.clicks-circle:hover,.engagement-circle:hover,.followers-circle:hover,.visitors-circle:hover{transform:scale(1.13);box-shadow:0 8px 32px rgba(0,0,0,.14)}
.circle-inline-label{text-align:center;font-weight:600;font-size:1.08em;margin-bottom:.28em;color:#2d448d;display:inline-block}
.circle-delta-row{text-align:center;font-size:.98em;font-weight:600;margin-top:.14em;margin-bottom:.1em}
.circle-delta-value{font-size:1.09em;font-weight:700;margin-right:4px}
.circle-delta-label{color:#888;font-size:.94em;font-weight:400;margin-left:2px}

/* ── Facebook ── */
.fb-metric-row{display:flex;flex-direction:row;justify-content:center;align-items:flex-start;gap:50px;margin-top:2em;margin-bottom:2em;flex-wrap:wrap}
.fb-metric-block{display:flex;flex-direction:column;align-items:center;min-width:220px;max-width:260px}
.fb-circle{background:linear-gradient(135deg,#459fda 0%,#a6ce39 100%);border-radius:50%;width:130px;height:130px;display:flex;align-items:center;justify-content:center;font-size:2.5em;font-weight:bold;color:#fff;box-shadow:0 4px 18px rgba(69,159,218,.14);transition:transform .17s cubic-bezier(.4,2,.55,.44);cursor:pointer;margin-bottom:.7em;animation:bounceIn .6s cubic-bezier(.4,2,.3,1)}
.fb-circle:hover{transform:scale(1.13);box-shadow:0 8px 32px rgba(69,159,218,.18)}
.fb-label{text-align:center;font-weight:600;font-size:1.08em;margin-bottom:.28em;color:#2d448d}
.fb-delta-row{text-align:center;font-size:.99em;font-weight:600;margin-top:.14em;margin-bottom:.11em}
.fb-delta-up{color:#2ecc40;font-weight:700}
.fb-delta-down{color:#ff4136;font-weight:700}
.fb-delta-same{color:#888;font-weight:700}
.fb-delta-note{color:#888;font-size:.94em;font-weight:400;margin-left:2px}
.fb-post-table{border-collapse:collapse;width:100%;margin-top:18px}
.fb-post-table th{background-color:#2d448d!important;color:#fff!important;font-weight:bold!important;font-size:1.09em!important;text-align:left!important;padding:10px 15px!important;border-bottom:2px solid #eaeaea!important}
.fb-post-table td{font-size:1.07em!important;color:#222!important;padding:8px 15px!important;border-bottom:1px solid #eaeaea!important;word-break:break-word}
.fb-post-table tr:nth-child(even){background-color:#f5f7fa!important}
.fb-post-table tr:nth-child(odd){background-color:#fff!important}
.fb-post-table a{color:#2061b2!important;text-decoration:underline!important}

/* ── YouTube ── */
.yt-metric-circle{transition:transform .18s cubic-bezier(.4,2,.55,.44);cursor:pointer;animation:bounceIn .6s cubic-bezier(.4,2,.3,1)}
.yt-metric-circle:hover{transform:scale(1.13);box-shadow:0 6px 20px rgba(44,68,141,.18)}
.yt-table th,.yt-table td{padding:7px 13px;font-size:1.01em}
.yt-table th{background:#2d448d;color:#fff}
.yt-table tr:nth-child(even){background:#f3f3f3}
.yt-table tr:nth-child(odd){background:#fff}

/* ── Responsive ── */
@media(max-width:1200px){
  .fb-metric-block,.circle-block{min-width:150px;max-width:180px}
  .fb-circle{width:80px;height:80px;font-size:1.2em}
  .impressions-circle,.clicks-circle,.engagement-circle,.followers-circle,.visitors-circle{width:100px;height:100px;font-size:1.8em}
}
@media(max-width:850px){
  .analytics-circles-row,.fb-metric-row{gap:1.1rem;flex-wrap:wrap}
  .fb-circle{width:60px;height:60px;font-size:.97em}
}
</style>
""", unsafe_allow_html=True)

# ═════════════════════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ═════════════════════════════════════════════════════════════════════════════

def show_loader(placeholder, message="Loading..."):
    placeholder.markdown(
        f"""<div style="width:100%;text-align:center;margin:1.7em 0;">
            <div class="loader"></div>
            <div style="margin-top:.8em;font-size:1.05em;color:#2d448d;font-weight:500;">{message}</div>
        </div>""",
        unsafe_allow_html=True,
    )


def pct_change(current, previous):
    return 0 if previous == 0 else (current - previous) / previous * 100


def get_month_options():
    months, today, d = [], date.today(), date(2025, 1, 1)
    while d <= today:
        months.append(d)
        d += relativedelta(months=1)
    return [m.strftime("%B %Y") for m in months]


def get_month_range(sel):
    start = datetime.strptime(sel, "%B %Y").date().replace(day=1)
    end = start + relativedelta(months=1) - timedelta(days=1)
    prev_end = start - timedelta(days=1)
    prev_start = prev_end.replace(day=1)
    return start, end, prev_start, prev_end


def format_month_year(d):
    return d.strftime("%B %Y")


def country_name_to_code(name):
    try:
        return pycountry.countries.lookup(name).alpha_2.lower()
    except LookupError:
        for c in pycountry.countries:
            if name.lower() in c.name.lower():
                return c.alpha_2.lower()
        return None


def section_divider():
    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)


def render_metric_circle(col, title, value, delta, color, tooltip=None, fmt_value=None):
    """Render a metric circle — CSS-animated, no blocking sleep loops."""
    with col:
        tip_html = (
            f"<span class='tooltip'><span class='questionmark'>?</span>"
            f"<span class='tooltiptext'>{tooltip}</span></span>"
            if tooltip else ""
        )
        st.markdown(
            f"<div style='text-align:center;font-weight:500;font-size:22px;margin-bottom:.2em'>"
            f"{title}{tip_html}</div>",
            unsafe_allow_html=True,
        )
        display = fmt_value if fmt_value is not None else f"{int(value):,}"
        st.markdown(
            f"""<div style='margin:0 auto;display:flex;align-items:center;justify-content:center;height:120px;'>
              <div class='animated-circle' style='background:{color};'>
                <span class='animated-circle-value'>{display}</span>
              </div>
            </div>""",
            unsafe_allow_html=True,
        )
        pct_color = "#2ecc40" if delta >= 0 else "#ff4136"
        icon = "↑" if delta >= 0 else "↓"
        st.markdown(
            f"<div style='text-align:center;font-size:17px;margin-top:.3em;color:{pct_color};font-weight:500;margin-bottom:.8em'>"
            f"{icon} {abs(delta):.2f}%"
            f"<span style='color:#666;font-size:.9em;margin-left:.4em'>(vs. Previous Month)</span>"
            f"</div>",
            unsafe_allow_html=True,
        )


def get_delta_icon_and_color(val):
    if val > 0:
        return "↑", "#2ecc40"
    if val < 0:
        return "↓", "#ff4136"
    return "", "#aaa"


def safe_percent(prev, cur):
    if prev == 0 and cur == 0:
        return 0
    if prev == 0:
        return 100 if cur > 0 else 0
    return ((cur - prev) / abs(prev)) * 100


# ═════════════════════════════════════════════════════════════════════════════
# LOGIN
# ═════════════════════════════════════════════════════════════════════════════
_USERNAME = st.secrets["login"]["username"]
_PASSWORD = st.secrets["login"]["password"]


def login():
    st.markdown(
        "<div style='max-width:400px;margin:5em auto;padding:2em;background:#fff;"
        "border-radius:12px;box-shadow:0 4px 24px rgba(44,68,141,.12);'>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<h2 style='color:#2d448d;text-align:center;margin-bottom:1em'>🔐 Dashboard Login</h2>",
        unsafe_allow_html=True,
    )
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Login", use_container_width=True):
            if username == _USERNAME and password == _PASSWORD:
                st.session_state["logged_in"] = True
                st.rerun()
            else:
                st.error("Invalid username or password.")
    st.markdown("</div>", unsafe_allow_html=True)


if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    login()
    st.stop()

# ═════════════════════════════════════════════════════════════════════════════
# API CLIENTS  (cached resource — one initialisation per Streamlit worker)
# ═════════════════════════════════════════════════════════════════════════════
@st.cache_resource(ttl=3600)
def get_api_clients():
    sa = st.secrets["gcp"]["service_account"]
    info = json.loads(sa)
    pk = info.get("private_key", "").replace("\\n", "\n")
    if not pk.endswith("\n"):
        pk += "\n"
    info["private_key"] = pk
    creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    creds.refresh(GAuthRequest())
    return BetaAnalyticsDataClient(credentials=creds), build("searchconsole", "v1", credentials=creds)


ga4_client, sc_client = get_api_clients()

# ═════════════════════════════════════════════════════════════════════════════
# GA4 DATA FUNCTIONS
# ═════════════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=3600)
def get_total_users(pid, sd, ed):
    try:
        resp = ga4_client.run_report(request={
            "property": f"properties/{pid}",
            "date_ranges": [{"start_date": sd.strftime("%Y-%m-%d"), "end_date": ed.strftime("%Y-%m-%d")}],
            "metrics": [{"name": "totalUsers"}],
        })
        return int(resp.rows[0].metric_values[0].value)
    except Exception:
        return 0


@st.cache_data(ttl=3600)
def get_traffic(pid, sd, ed):
    try:
        resp = ga4_client.run_report(request={
            "property": f"properties/{pid}",
            "date_ranges": [{"start_date": sd.strftime("%Y-%m-%d"), "end_date": ed.strftime("%Y-%m-%d")}],
            "dimensions": [{"name": "sessionDefaultChannelGroup"}],
            "metrics": [{"name": "sessions"}],
        })
        return [{"channel": r.dimension_values[0].value, "sessions": int(r.metric_values[0].value)} for r in resp.rows]
    except Exception:
        return []


@st.cache_data(ttl=3600)
def get_new_returning_users(pid, sd, ed):
    try:
        resp = ga4_client.run_report(request={
            "property": f"properties/{pid}",
            "date_ranges": [{"start_date": sd.strftime("%Y-%m-%d"), "end_date": ed.strftime("%Y-%m-%d")}],
            "metrics": [{"name": "totalUsers"}, {"name": "newUsers"}],
        })
        total = int(resp.rows[0].metric_values[0].value)
        new = int(resp.rows[0].metric_values[1].value)
        return total, new, total - new
    except Exception:
        return 0, 0, 0


@st.cache_data(ttl=3600)
def get_active_users_by_country(pid, sd, ed, top_n=5):
    try:
        resp = ga4_client.run_report(request={
            "property": f"properties/{pid}",
            "date_ranges": [{"start_date": sd.strftime("%Y-%m-%d"), "end_date": ed.strftime("%Y-%m-%d")}],
            "dimensions": [{"name": "country"}],
            "metrics": [{"name": "activeUsers"}],
            "order_bys": [{"metric": {"metric_name": "activeUsers"}, "desc": True}],
            "limit": top_n,
        })
        return [{"country": r.dimension_values[0].value, "activeUsers": int(r.metric_values[0].value)} for r in resp.rows]
    except Exception:
        return []


# ═════════════════════════════════════════════════════════════════════════════
# GOOGLE SEARCH CONSOLE DATA FUNCTIONS
# ═════════════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=3600)
def get_gsc_site_stats(site, sd, ed):
    try:
        body = {"startDate": sd.strftime("%Y-%m-%d"), "endDate": ed.strftime("%Y-%m-%d"), "rowLimit": 1}
        resp = sc_client.searchanalytics().query(siteUrl=site, body=body).execute()
        if not resp.get("rows"):
            return 0, 0, 0.0
        row = resp["rows"][0]
        return row.get("clicks", 0), row.get("impressions", 0), row.get("ctr", 0.0)
    except Exception:
        return 0, 0, 0.0


@st.cache_data(ttl=3600)
def get_gsc_pages_clicks(site, sd, ed, limit=5):
    try:
        body = {"startDate": sd.strftime("%Y-%m-%d"), "endDate": ed.strftime("%Y-%m-%d"),
                "dimensions": ["page"], "rowLimit": limit}
        rows = sc_client.searchanalytics().query(siteUrl=site, body=body).execute().get("rows", [])
        return [{"page": r["keys"][0], "clicks": r.get("clicks", 0)} for r in rows]
    except Exception:
        return []


@st.cache_data(ttl=3600)
def get_search_console(site, sd, ed):
    try:
        body = {"startDate": sd.strftime("%Y-%m-%d"), "endDate": ed.strftime("%Y-%m-%d"),
                "dimensions": ["page", "query"], "rowLimit": 500}
        return sc_client.searchanalytics().query(siteUrl=site, body=body).execute().get("rows", [])
    except Exception:
        return []


# ═════════════════════════════════════════════════════════════════════════════
# FACEBOOK DATA FUNCTIONS  (explicit params → correct cache keying + @cache_data)
# ═════════════════════════════════════════════════════════════════════════════
PAGE_ID = st.secrets["facebook"]["page_id"]
ACCESS_TOKEN = st.secrets["facebook"]["access_token"]


@st.cache_data(ttl=3600)
def get_total_metric_value(metric, since, until, page_id, access_token):
    url = f"https://graph.facebook.com/v19.0/{page_id}/insights/{metric}"
    try:
        resp = requests.get(
            url, params={"since": since, "until": until, "access_token": access_token}, timeout=10
        ).json()
        if "data" in resp and resp["data"] and "values" in resp["data"][0]:
            return sum(v["value"] for v in resp["data"][0]["values"])
        return 0
    except Exception:
        return 0


@st.cache_data(ttl=3600)
def get_lifetime_total_followers(page_id, access_token):
    url = f"https://graph.facebook.com/v19.0/{page_id}/insights/page_follows"
    try:
        resp = requests.get(url, params={"access_token": access_token}, timeout=10).json()
        if "data" in resp and resp["data"] and "values" in resp["data"][0]:
            return resp["data"][0]["values"][-1]["value"]
        return 0
    except Exception:
        return 0


@st.cache_data(ttl=3600)
def get_previous_lifetime_total_followers(prev_period_end, page_id, access_token):
    url = f"https://graph.facebook.com/v19.0/{page_id}/insights/page_follows"
    try:
        resp = requests.get(
            url, params={"since": prev_period_end, "until": prev_period_end, "access_token": access_token}, timeout=10
        ).json()
        if "data" in resp and resp["data"] and "values" in resp["data"][0]:
            return resp["data"][0]["values"][-1]["value"]
        return 0
    except Exception:
        return 0


@st.cache_data(ttl=3600)
def get_posts(since, until, page_id, access_token):
    url = f"https://graph.facebook.com/v19.0/{page_id}/posts"
    params = {"since": since, "until": until, "limit": 100, "access_token": access_token}
    posts = []
    try:
        while url:
            resp = requests.get(url, params=params, timeout=10).json()
            posts.extend(resp.get("data", []))
            paging = resp.get("paging", {})
            url = paging.get("next") if "next" in paging else None
            params = {}
        return posts
    except Exception:
        return []


@st.cache_data(ttl=3600)
def get_post_likes(post_id, access_token):
    url = f"https://graph.facebook.com/v19.0/{post_id}?fields=likes.summary(true)&access_token={access_token}"
    try:
        return requests.get(url, timeout=10).json().get("likes", {}).get("summary", {}).get("total_count", 0)
    except Exception:
        return 0


@st.cache_data(ttl=3600)
def get_post_comments(post_id, access_token):
    url = f"https://graph.facebook.com/v19.0/{post_id}/comments?summary=true&access_token={access_token}"
    try:
        return requests.get(url, timeout=10).json().get("summary", {}).get("total_count", 0)
    except Exception:
        return 0


# ═════════════════════════════════════════════════════════════════════════════
# YOUTUBE DATA FUNCTIONS  (access token cached with short TTL to auto-refresh)
# ═════════════════════════════════════════════════════════════════════════════
_YT_CLIENT_ID = st.secrets["youtube"].get("client_id", "")
_YT_CLIENT_SECRET = st.secrets["youtube"].get("client_secret", "")
_YT_REFRESH_TOKEN = st.secrets["youtube"].get("refresh_token", "")
YOUTUBE_API_KEY = st.secrets["youtube"].get("api_key", "")
CHANNEL_ID = st.secrets["youtube"].get("channel_id", "")


@st.cache_resource(ttl=3000)  # 50 min — refreshes before 1-hour expiry
def _get_yt_access_token(client_id, client_secret, refresh_token):
    if not refresh_token or refresh_token == "YOUR_REFRESH_TOKEN":
        st.error("Missing YouTube refresh token. Add it to .streamlit/secrets.toml under [youtube].")
        st.stop()
    resp = requests.post(
        "https://oauth2.googleapis.com/token",
        data={"client_id": client_id, "client_secret": client_secret,
              "refresh_token": refresh_token, "grant_type": "refresh_token"},
        timeout=10,
    )
    if resp.status_code != 200:
        st.error(f"YouTube OAuth error: {resp.text}")
        st.stop()
    return resp.json()["access_token"]


YT_ACCESS_TOKEN = _get_yt_access_token(_YT_CLIENT_ID, _YT_CLIENT_SECRET, _YT_REFRESH_TOKEN)


def _yt_headers(token):
    return {"Authorization": f"Bearer {token}", "Accept": "application/json"}


def get_yt_date_ranges():
    today = date.today()
    end_cur = today
    start_cur = today - timedelta(days=27)
    end_prev = start_cur - timedelta(days=1)
    start_prev = end_prev - timedelta(days=27)
    return start_cur, end_cur, start_prev, end_prev


@st.cache_data(ttl=3600)
def get_yt_analytics_summary(channel_id, start_date, end_date, yt_token):
    try:
        resp = requests.get(
            "https://youtubeanalytics.googleapis.com/v2/reports",
            headers=_yt_headers(yt_token),
            params={
                "ids": f"channel=={channel_id}",
                "startDate": start_date.strftime("%Y-%m-%d"),
                "endDate": end_date.strftime("%Y-%m-%d"),
                "metrics": "views,estimatedMinutesWatched,subscribersGained,subscribersLost",
            },
            timeout=15,
        ).json()
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
    except Exception:
        return {"views": 0, "watch_time": 0, "subs_gained": 0, "subs_lost": 0}


@st.cache_data(ttl=3600)
def get_total_subscribers(channel_id, api_key):
    try:
        url = f"https://www.googleapis.com/youtube/v3/channels?part=statistics&id={channel_id}&key={api_key}"
        items = requests.get(url, timeout=10).json().get("items", [])
        return int(items[0]["statistics"].get("subscriberCount", 0)) if items else 0
    except Exception:
        return 0


@st.cache_data(ttl=3600)
def get_top_videos(channel_id, api_key, start_date, end_date, yt_token, max_results=5):
    try:
        search_url = (f"https://www.googleapis.com/youtube/v3/search"
                      f"?key={api_key}&channelId={channel_id}&part=id&order=date&type=video&maxResults=50")
        video_ids = [item["id"]["videoId"] for item in requests.get(search_url, timeout=15).json().get("items", [])]
        if not video_ids:
            return pd.DataFrame()
        stats_url = (f"https://www.googleapis.com/youtube/v3/videos"
                     f"?key={api_key}&id={','.join(video_ids)}&part=snippet,statistics")
        data = []
        for item in requests.get(stats_url, timeout=15).json().get("items", []):
            data.append({
                "id": item["id"],
                "title": item["snippet"]["title"][:60],
                "published": item["snippet"]["publishedAt"][:10],
                "views": int(item["statistics"].get("viewCount", 0)),
                "likes": int(item["statistics"].get("likeCount", 0)),
                "comments": int(item["statistics"].get("commentCount", 0)),
            })
        df = pd.DataFrame(data).sort_values("views", ascending=False).head(max_results)
        ids = list(df["id"])
        yt_resp = requests.get(
            "https://youtubeanalytics.googleapis.com/v2/reports",
            headers=_yt_headers(yt_token),
            params={
                "ids": "channel==MINE",
                "startDate": start_date.strftime("%Y-%m-%d"),
                "endDate": end_date.strftime("%Y-%m-%d"),
                "metrics": "estimatedMinutesWatched,views,likes,comments",
                "dimensions": "video",
                "filters": f"video=={','.join(ids)}",
            },
            timeout=15,
        ).json()
        if "rows" in yt_resp:
            wt_dict = {row[0]: row[1] for row in yt_resp["rows"]}
            df["watch_time"] = df["id"].map(wt_dict).fillna(0)
        else:
            df["watch_time"] = 0
        return df
    except Exception:
        return pd.DataFrame()


# ═════════════════════════════════════════════════════════════════════════════
# LINKEDIN DATA FUNCTIONS
# ═════════════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=3600)
def load_linkedin_analytics_df():
    try:
        client = MongoClient(
            st.secrets["mongo_uri_linkedin"],
            serverSelectionTimeoutMS=5000,
            tlsCAFile=certifi.where(),
        )
        db = client["sal-lnkd"]
        doc_analytics = db["lnkd-analytics"].find_one({})
        doc_extras = db["lnkd-extras"].find_one({})
        client.close()

        df_analytics = (
            pd.DataFrame(doc_analytics["daily_records"])
            if doc_analytics and "daily_records" in doc_analytics
            else pd.DataFrame()
        )
        followers_total = int(doc_analytics.get("followers_total", 0)) if doc_analytics else 0
        df_extras = (
            pd.DataFrame(doc_extras["daily_records"])
            if doc_extras and "daily_records" in doc_extras
            else pd.DataFrame()
        )
        return df_analytics, df_extras, followers_total
    except Exception as e:
        st.error(f"Could not connect to LinkedIn MongoDB: {e}")
        return pd.DataFrame(), pd.DataFrame(), 0


# ═════════════════════════════════════════════════════════════════════════════
# SERVICE-GROUPED FETCH WRAPPERS
# Each wrapper keeps calls to the same API client sequential (thread-safe),
# while different wrappers run in parallel threads.
# ═════════════════════════════════════════════════════════════════════════════
def _fetch_all_ga4(property_id, sd, ed, psd, ped):
    return (
        get_total_users(property_id, sd, ed),
        get_total_users(property_id, psd, ped),
        get_traffic(property_id, sd, ed),
        get_traffic(property_id, psd, ped),
        get_new_returning_users(property_id, sd, ed),
        get_new_returning_users(property_id, psd, ped),
        get_active_users_by_country(property_id, sd, ed),
    )


def _fetch_all_gsc(site, sd, ed, psd, ped):
    return (
        get_gsc_site_stats(site, sd, ed),
        get_gsc_site_stats(site, psd, ped),
        get_gsc_pages_clicks(site, sd, ed, 5),
        get_gsc_pages_clicks(site, psd, ped, 20),
        get_search_console(site, sd, ed),
        get_search_console(site, psd, ped),
    )


# ═════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.image("https://www.salasarservices.com/assets/Frontend/images/logo-black.png", width=170)
    st.title("Report Filters")

    month_options = get_month_options()
    if "selected_month" not in st.session_state:
        st.session_state["selected_month"] = month_options[-1]

    sel = st.selectbox(
        "Select report month:",
        month_options,
        index=month_options.index(st.session_state["selected_month"]),
    )
    if sel != st.session_state["selected_month"]:
        st.session_state["selected_month"] = sel

    sd, ed, psd, ped = get_month_range(st.session_state["selected_month"])
    st.markdown(
        f"""<div style="border-left:4px solid #459fda;background:#f0f7fa;padding:1em 1.2em;
            margin-bottom:1em;border-radius:6px;">
            <span style="font-size:1.05em;color:#2d448d;">
            <b>Current:</b> {sd.strftime('%B %Y')}<br>
            <b>Previous:</b> {psd.strftime('%B %Y')}
            </span></div>""",
        unsafe_allow_html=True,
    )

    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.session_state["selected_month"] = month_options[-1]
        st.rerun()

    st.markdown("---")

    # ── LinkedIn DB flush with mandatory confirmation ──────────────────────
    def _flush_linkedin_database():
        try:
            client = MongoClient(
                st.secrets["mongo_uri_linkedin"],
                serverSelectionTimeoutMS=5000,
                tlsCAFile=certifi.where(),
            )
            db = client["sal-lnkd"]
            for col_name in db.list_collection_names():
                db[col_name].delete_many({})
            client.close()
            return True
        except Exception as e:
            st.error(f"Could not flush LinkedIn database: {e}")
            return False

    if "confirm_lnkd_flush" not in st.session_state:
        st.session_state["confirm_lnkd_flush"] = False

    if st.button("🗑️ Flush LinkedIn Data", use_container_width=True):
        st.session_state["confirm_lnkd_flush"] = True

    if st.session_state["confirm_lnkd_flush"]:
        st.warning("⚠️ This permanently deletes all LinkedIn analytics data. Are you sure?")
        _c1, _c2 = st.columns(2)
        with _c1:
            if st.button("Yes, Delete", type="primary", key="lnkd_yes"):
                if _flush_linkedin_database():
                    st.success("Cleared.")
                    st.cache_data.clear()
                st.session_state["confirm_lnkd_flush"] = False
        with _c2:
            if st.button("Cancel", key="lnkd_no"):
                st.session_state["confirm_lnkd_flush"] = False

    st.markdown("---")
    pdf_report_btn = st.button("📄 Download PDF Report", use_container_width=True)

# ═════════════════════════════════════════════════════════════════════════════
# PAGE HEADER
# ═════════════════════════════════════════════════════════════════════════════
st.markdown(
    """<div style="display:flex;align-items:center;margin-bottom:1.5em;
        padding-bottom:1em;border-bottom:2px solid #e8eaf0;">
        <img src="https://www.salasarservices.com/assets/Frontend/images/logo-black.png"
             style="height:48px;margin-right:28px;">
        <span style="font-family:'Lato',Arial,sans-serif;font-size:2.2em;font-weight:700;color:#2d448d;">
            Salasar Services Digital Marketing Dashboard
        </span>
    </div>""",
    unsafe_allow_html=True,
)

# ═════════════════════════════════════════════════════════════════════════════
# PARALLEL DATA FETCH
# GA4, GSC, and LinkedIn run in separate threads (each group uses its own client)
# ═════════════════════════════════════════════════════════════════════════════
_loader = st.empty()
show_loader(_loader, "Fetching analytics data from all sources…")

with ThreadPoolExecutor(max_workers=3) as _pool:
    _f_ga4 = _pool.submit(_fetch_all_ga4, PROPERTY_ID, sd, ed, psd, ped)
    _f_gsc = _pool.submit(_fetch_all_gsc, SC_SITE_URL, sd, ed, psd, ped)
    _f_lnkd = _pool.submit(load_linkedin_analytics_df)

    (cur_users, prev_users, traf, traf_prev,
     nr_cur, nr_prev, country_data) = _f_ga4.result()

    (gsc_stats_cur, gsc_stats_prev, top_pages_now, top_pages_prev,
     sc_data, sc_data_prev) = _f_gsc.result()

    (df_lnkd_analytics, df_lnkd_extras, lnkd_followers_total) = _f_lnkd.result()

_loader.empty()

# Unpack GSC stats
gsc_clicks, gsc_impressions, gsc_ctr = gsc_stats_cur
gsc_clicks_prev, gsc_impressions_prev, gsc_ctr_prev = gsc_stats_prev

# Unpack new/returning users
total_users, new_users, returning_users = nr_cur
total_users_prev, new_users_prev, returning_users_prev = nr_prev

# Compute deltas
gsc_clicks_delta = pct_change(gsc_clicks, gsc_clicks_prev)
gsc_impr_delta   = pct_change(gsc_impressions, gsc_impressions_prev)
gsc_ctr_delta    = pct_change(gsc_ctr, gsc_ctr_prev)

total_sessions  = sum(i["sessions"] for i in traf)
prev_sessions   = sum(i["sessions"] for i in traf_prev)
delta_sessions  = pct_change(total_sessions, prev_sessions)

organic_clicks      = sum(r.get("clicks", 0) for r in sc_data)
organic_clicks_prev = sum(r.get("clicks", 0) for r in sc_data_prev)
delta_organic       = pct_change(organic_clicks, organic_clicks_prev)

delta_users     = pct_change(cur_users, prev_users)
delta_new       = pct_change(new_users, new_users_prev)
delta_returning = pct_change(returning_users, returning_users_prev)

# Build top content table data
prev_clicks_dict = {p["page"]: p["clicks"] for p in top_pages_prev}
top_content_data = []
for entry in top_pages_now:
    page = entry["page"]
    clks = entry["clicks"]
    prev = prev_clicks_dict.get(page, 0)
    diff = 0 if prev == 0 else (clks - prev) / prev * 100
    top_content_data.append({"Page": page, "Clicks": clks, "Change (%)": f"{diff:+.2f}"})

traf_df = pd.DataFrame(traf).head(5)
sc_df   = pd.DataFrame([
    {"page": r["keys"][0], "query": r["keys"][1], "clicks": r.get("clicks", 0)}
    for r in sc_data
]).head(10)

# Tuple list reused by PDF
perf_data = [
    ("Total Website Clicks", gsc_clicks,     gsc_clicks_delta, "#e67e22"),
    ("Total Impressions",    gsc_impressions, gsc_impr_delta,   "#3498db"),
    ("Average CTR",          gsc_ctr * 100,  gsc_ctr_delta,    "#16a085"),
]

# ═════════════════════════════════════════════════════════════════════════════
# SECTION: WEBSITE PERFORMANCE
# ═════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">Website Performance</div>', unsafe_allow_html=True)

_perf_tips = [
    "Total clicks from Google Search results during the selected period.",
    "Total times your website appeared in Google Search results (regardless of clicks).",
    "Percentage of impressions that resulted in a click (Click-Through Rate).",
]
_perf_cols = st.columns(3)
for _i, (_title, _value, _delta, _color) in enumerate(perf_data):
    _fmt = f"{_value:.2f}%" if _title == "Average CTR" else None
    render_metric_circle(_perf_cols[_i], _title, _value, _delta, _color, tooltip=_perf_tips[_i], fmt_value=_fmt)

section_divider()

# ═════════════════════════════════════════════════════════════════════════════
# SECTION: TOP CONTENT
# ═════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">Top Content</div>', unsafe_allow_html=True)


def _render_top_content(data):
    df = pd.DataFrame(data)
    if df.empty:
        st.warning("No top content data available for this period.")
        return
    df["Clicks"] = df["Clicks"].apply(lambda x: f"<span style='font-size:1.15em;font-weight:600'>{int(x):,}</span>")

    def _fmt_chg(val):
        pct = float(val)
        color = "#2ecc40" if pct >= 0 else "#ff4136"
        arrow = "↑" if pct >= 0 else "↓"
        return f"<span style='color:{color};font-size:1.1em;font-weight:600'>{arrow} {pct:+.2f}%</span>"

    df["Change (%)"] = df["Change (%)"].apply(_fmt_chg)
    st.markdown(df.to_html(escape=False, index=False, classes="styled-table"), unsafe_allow_html=True)


_render_top_content(top_content_data)

section_divider()

# ═════════════════════════════════════════════════════════════════════════════
# SECTION: WEBSITE ANALYTICS
# ═════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">Website Analytics</div>', unsafe_allow_html=True)

_analytics_data = [
    ("Total Users",    cur_users,      delta_users,    "#2d448d", "Number of people who visited your website."),
    ("Sessions",       total_sessions, delta_sessions, "#a6ce39", "Total number of visits to your website."),
    ("Organic Clicks", organic_clicks, delta_organic,  "#459fda", "Times people clicked on your website in Google Search."),
]
_analytics_cols = st.columns(3)
for _i, (_t, _v, _d, _c, _tip) in enumerate(_analytics_data):
    render_metric_circle(_analytics_cols[_i], _t, _v, _d, _c, tooltip=_tip)

section_divider()

# ═════════════════════════════════════════════════════════════════════════════
# SECTION: NEW VS RETURNING USERS
# ═════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">New vs Returning Users</div>', unsafe_allow_html=True)

_ret_data = [
    ("New Users",       new_users,       delta_new,       "#e67e22",
     "Users visiting your website for the first time during this period."),
    ("Returning Users", returning_users, delta_returning, "#3498db",
     "Users who came back (not their first visit) during this period."),
]
_ret_cols = st.columns(2)
for _i, (_t, _v, _d, _c, _tip) in enumerate(_ret_data):
    render_metric_circle(_ret_cols[_i], _t, _v, _d, _c, tooltip=_tip)

_tc1, _tc2 = st.columns(2)
with _tc1:
    st.subheader("Active Users by Country (Top 5)")
    _country_df = pd.DataFrame(country_data)
    if not _country_df.empty:
        def _flag_html(row):
            code = country_name_to_code(row["country"])
            flag = f'<img src="https://flagcdn.com/16x12/{code}.png" style="height:12px;margin-right:7px;vertical-align:middle;">' if code else ""
            return f"{flag}{row['country']}"
        _country_df["Country"] = _country_df.apply(_flag_html, axis=1)
        _country_df = _country_df[["Country", "activeUsers"]].rename(columns={"activeUsers": "Active Users"})
        st.markdown(_country_df.to_html(escape=False, index=False, classes="styled-table"), unsafe_allow_html=True)

with _tc2:
    st.subheader("Traffic Acquisition by Channel")
    if not traf_df.empty:
        st.markdown(traf_df.to_html(index=False, classes="styled-table"), unsafe_allow_html=True)

section_divider()

# ═════════════════════════════════════════════════════════════════════════════
# SECTION: LINKEDIN ANALYTICS
# ═════════════════════════════════════════════════════════════════════════════
def _render_linkedin(df_analytics, df_extras, followers_total):
    if df_analytics.empty and df_extras.empty:
        st.info("No LinkedIn analytics data found in MongoDB.")
        return

    def _prep(df, rename=None):
        if rename:
            df = df.rename(columns=rename)
        date_col = "date" if "date" in df.columns else None
        if date_col:
            df["Date"] = pd.to_datetime(df[date_col], errors="coerce")
            df = df.dropna(subset=["Date"])
            df["Month"] = df["Date"].dt.to_period("M")
            df["MonthStr"] = df["Date"].dt.strftime("%B %Y")
        return df

    df_analytics = _prep(df_analytics, rename={
        "total_followers": "Total followers (Date-wise)",
        "total_unique_visitors": "Total Unique Visitors (Date-wise)",
    })
    df_extras = _prep(df_extras)

    if df_analytics.empty:
        st.error("No valid date records in lnkd-analytics.")
        return
    if df_extras.empty:
        st.error("No valid date records in lnkd-extras.")
        return

    _last12 = [(date.today().replace(day=1) - relativedelta(months=i)).strftime("%B %Y") for i in range(12)]
    _all_months = sorted(
        set(_last12)
        | set(df_analytics.get("MonthStr", pd.Series(dtype=str)).dropna())
        | set(df_extras.get("MonthStr", pd.Series(dtype=str)).dropna()),
        key=lambda d: datetime.strptime(d, "%B %Y"),
        reverse=True,
    )
    _sel = st.selectbox("Select month", _all_months, index=0, key="lnkd_month")
    _sel_p = pd.Period(datetime.strptime(_sel, "%B %Y"), freq="M")
    _prev_p = _sel_p - 1
    _prev_label = _prev_p.strftime("%B %Y")

    def _mslice(df, col, period, agg="sum"):
        if "Month" not in df.columns or col not in df.columns:
            return 0.0
        slc = df[df["Month"] == period][col]
        if slc.empty:
            return 0.0
        return float(slc.sum() if agg == "sum" else slc.mean())

    imp_c = _mslice(df_extras, "total_impressions", _sel_p)
    imp_p = _mslice(df_extras, "total_impressions", _prev_p)
    clk_c = _mslice(df_extras, "clicks", _sel_p)
    clk_p = _mslice(df_extras, "clicks", _prev_p)
    eng_c = _mslice(df_extras, "engagement_rate", _sel_p, "mean")
    eng_p = _mslice(df_extras, "engagement_rate", _prev_p, "mean")
    fol_c = _mslice(df_analytics, "Total followers (Date-wise)", _sel_p)
    fol_p = _mslice(df_analytics, "Total followers (Date-wise)", _prev_p)
    vis_c = _mslice(df_analytics, "Total Unique Visitors (Date-wise)", _sel_p)
    vis_p = _mslice(df_analytics, "Total Unique Visitors (Date-wise)", _prev_p)

    def _drow(delta, prev_lbl):
        color = "#2ecc40" if delta > 0 else "#ff4136" if delta < 0 else "#888"
        sign  = "+" if delta > 0 else ""
        icon  = "↑" if delta > 0 else "↓" if delta < 0 else ""
        return (f"<div class='circle-delta-row'>"
                f"<span class='circle-delta-value' style='color:{color}'>{sign}{int(delta):,} {icon}</span>"
                f"<span class='circle-delta-label'>vs. {prev_lbl}</span></div>")

    st.markdown('<div class="section-header">LinkedIn Analytics</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="analytics-circles-row">
      <div class="circle-block">
        <div class="impressions-circle">{int(imp_c):,}</div>
        <div class="circle-inline-label">Impressions — <b>{_sel}</b>: {int(imp_c):,}</div>
        {_drow(imp_c - imp_p, _prev_label)}
      </div>
      <div class="circle-block">
        <div class="clicks-circle">{int(clk_c):,}</div>
        <div class="circle-inline-label">Clicks — <b>{_sel}</b>: {int(clk_c):,}</div>
        {_drow(clk_c - clk_p, _prev_label)}
      </div>
      <div class="circle-block">
        <div class="engagement-circle" style="color:#555">{eng_c * 100:.2f}%</div>
        <div class="circle-inline-label">Engagement — <b>{_sel}</b>: {eng_c * 100:.2f}%</div>
        <div class="circle-delta-row">
          <span class="circle-delta-value" style="color:{'#2ecc40' if eng_c>eng_p else '#ff4136' if eng_c<eng_p else '#888'}">
            {'+'if eng_c > eng_p else ''}{(eng_c - eng_p) * 100:.2f}%
          </span>
          <span class="circle-delta-label">vs. {_prev_label}</span>
        </div>
      </div>
    </div>
    <div class="analytics-circles-row">
      <div class="circle-block">
        <div class="followers-circle">{followers_total:,}</div>
        <div class="circle-inline-label">Total Followers (Lifetime): <b>{followers_total:,}</b></div>
        <div class="circle-inline-label" style="margin-top:.3em">Gained in {_sel}: <b>{int(fol_c):,}</b></div>
        {_drow(fol_c - fol_p, _prev_label)}
      </div>
      <div class="circle-block">
        <div class="visitors-circle">{int(vis_c):,}</div>
        <div class="circle-inline-label">Unique Visitors in {_sel}: <b>{int(vis_c):,}</b></div>
        {_drow(vis_c - vis_p, _prev_label)}
      </div>
    </div>
    """, unsafe_allow_html=True)


_render_linkedin(df_lnkd_analytics, df_lnkd_extras, lnkd_followers_total)

section_divider()

# ═════════════════════════════════════════════════════════════════════════════
# SECTION: FACEBOOK ANALYTICS
# ═════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">Facebook Page Analytics</div>', unsafe_allow_html=True)

_fb_opts = list(dict.fromkeys(
    [(datetime.today().replace(day=1) - timedelta(days=30 * i)).strftime("%B %Y") for i in range(12)]
))
_fb_sel = st.selectbox("Select Month", _fb_opts, index=0, key="fb_month")
_fb_dt = datetime.strptime(_fb_sel, "%B %Y")
_fb_cs = _fb_dt.replace(day=1)
_fb_ce = (_fb_cs + timedelta(days=32)).replace(day=1) - timedelta(days=1)
_fb_ps = (_fb_cs - timedelta(days=1)).replace(day=1)
_fb_pe = _fb_cs - timedelta(days=1)

_fb_since = _fb_cs.strftime("%Y-%m-%d")
_fb_until = _fb_ce.strftime("%Y-%m-%d")
_fb_psince = _fb_ps.strftime("%Y-%m-%d")
_fb_puntil = _fb_pe.strftime("%Y-%m-%d")

# Facebook calls are pure HTTP → safe to parallelise
with ThreadPoolExecutor(max_workers=7) as _fp:
    _fvc = _fp.submit(get_total_metric_value, "page_views_total", _fb_since, _fb_until, PAGE_ID, ACCESS_TOKEN)
    _fvp = _fp.submit(get_total_metric_value, "page_views_total", _fb_psince, _fb_puntil, PAGE_ID, ACCESS_TOKEN)
    _flc = _fp.submit(get_total_metric_value, "page_fans", _fb_since, _fb_until, PAGE_ID, ACCESS_TOKEN)
    _flp = _fp.submit(get_total_metric_value, "page_fans", _fb_psince, _fb_puntil, PAGE_ID, ACCESS_TOKEN)
    _ffl = _fp.submit(get_lifetime_total_followers, PAGE_ID, ACCESS_TOKEN)
    _ffp = _fp.submit(get_previous_lifetime_total_followers, _fb_puntil, PAGE_ID, ACCESS_TOKEN)
    _fpo = _fp.submit(get_posts, _fb_since, _fb_until, PAGE_ID, ACCESS_TOKEN)

    _cur_views = _fvc.result()
    _prev_views = _fvp.result()
    _cur_likes = _flc.result()
    _prev_likes = _flp.result()
    _life_foll = _ffl.result()
    _prev_foll = _ffp.result()
    _cur_posts = _fpo.result()

_vd = _cur_views - _prev_views
_ld = _cur_likes - _prev_likes
_fd = _life_foll - _prev_foll
_vi, _vc = get_delta_icon_and_color(_vd)
_li, _lc = get_delta_icon_and_color(_ld)
_fi, _fc = get_delta_icon_and_color(_fd)

st.markdown(f"""
<div class="fb-metric-row">
  <div class="fb-metric-block">
    <div class="fb-label">Total Views ({_fb_sel})</div>
    <div class="fb-circle">{_cur_views:,}</div>
    <div class="fb-delta-row">
      <span class="{'fb-delta-up' if _vd>0 else 'fb-delta-down' if _vd<0 else 'fb-delta-same'}">{_vi} {_vd:+,}</span>
      <span class="fb-delta-note">(vs. Previous Month)</span>
    </div>
  </div>
  <div class="fb-metric-block">
    <div class="fb-label">Total Page Likes ({_fb_sel})</div>
    <div class="fb-circle">{_cur_likes:,}</div>
    <div class="fb-delta-row">
      <span class="{'fb-delta-up' if _ld>0 else 'fb-delta-down' if _ld<0 else 'fb-delta-same'}">{_li} {_ld:+,}</span>
      <span class="fb-delta-note">(vs. Previous Month)</span>
    </div>
  </div>
  <div class="fb-metric-block">
    <div class="fb-label">Total Followers (Lifetime)</div>
    <div class="fb-circle">{_life_foll:,}</div>
    <div class="fb-delta-row">
      <span class="{'fb-delta-up' if _fd>0 else 'fb-delta-down' if _fd<0 else 'fb-delta-same'}">{_fi} {_fd:+,}</span>
      <span class="fb-delta-note">(since Previous Month)</span>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown(f"<h3 style='color:#2d448d;margin-top:1em'>Posts Published in {_fb_sel}</h3>", unsafe_allow_html=True)

if _cur_posts:
    _rows = []
    for _post in _cur_posts:
        _pid = _post["id"]
        _url = f"https://www.facebook.com/{PAGE_ID}/posts/{_pid.split('_')[-1]}"
        _msg = _post.get("message", "")
        _ttl = (_msg[:100] + "…") if len(_msg) > 100 else _msg
        _rows.append({
            "Title":    f"<a href='{_url}' target='_blank'>{_ttl}</a>",
            "Likes":    get_post_likes(_pid, ACCESS_TOKEN),
            "Comments": get_post_comments(_pid, ACCESS_TOKEN),
        })
    st.markdown(pd.DataFrame(_rows).to_html(escape=False, index=False, classes="fb-post-table"), unsafe_allow_html=True)
else:
    st.info("No posts published this month.")

st.caption("Data pulled live from Facebook Graph API. Credentials loaded securely from Streamlit secrets.")

section_divider()

# ═════════════════════════════════════════════════════════════════════════════
# SECTION: YOUTUBE ANALYTICS
# ═════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="section-header">YouTube Channel Overview</div>', unsafe_allow_html=True)

_yt_sc, _yt_ec, _yt_sp, _yt_ep = get_yt_date_ranges()

with ThreadPoolExecutor(max_workers=3) as _yp:
    _fyc = _yp.submit(get_yt_analytics_summary, CHANNEL_ID, _yt_sc, _yt_ec, YT_ACCESS_TOKEN)
    _fyp = _yp.submit(get_yt_analytics_summary, CHANNEL_ID, _yt_sp, _yt_ep, YT_ACCESS_TOKEN)
    _fys = _yp.submit(get_total_subscribers, CHANNEL_ID, YOUTUBE_API_KEY)
    _yt_cur = _fyc.result()
    _yt_prev = _fyp.result()
    _total_subs = _fys.result()


def _yt_delta_html(cur, prev):
    delta = cur - prev
    pct = 0 if prev == 0 else delta / prev * 100
    color = "#2ecc40" if delta > 0 else "#ff4136" if delta < 0 else "#888"
    sign = "+" if delta > 0 else ""
    return f"<span style='color:{color};font-weight:bold;'>{sign}{abs(delta):,} ({pct:.1f}%)</span>"


def _yt_subs_html(gained, lost):
    net = gained - lost
    color = "#2ecc40" if net > 0 else "#ff4136" if net < 0 else "#888"
    label = "new" if net > 0 else ("unsubscribed" if net < 0 else "no change")
    return f"<span style='color:{color};font-weight:bold;'>{'+'if net>0 else ''}{net:,} {label}</span>"


_yt_metrics = [
    ("Subscribers (Total)",   _total_subs,           _yt_subs_html(_yt_cur["subs_gained"], _yt_cur["subs_lost"]), "#ffe1c8", "#e67e22"),
    ("Total Views (28 days)", _yt_cur["views"],       _yt_delta_html(_yt_cur["views"],      _yt_prev["views"]),    "#c8e6fa", "#3498db"),
    ("Watch Time (28d, min)", _yt_cur["watch_time"],  _yt_delta_html(_yt_cur["watch_time"], _yt_prev["watch_time"]),"#a7f1df","#16a085"),
]
_yt_cols = st.columns(3)
for _i, (_lbl, _val, _detail, _bg, _fg) in enumerate(_yt_metrics):
    with _yt_cols[_i]:
        st.markdown(
            f"""<div style='text-align:center;font-weight:500;font-size:23px;margin-bottom:.2em;color:#2d448d'>{_lbl}</div>
            <div style='margin:0 auto;display:flex;align-items:center;justify-content:center;height:120px;'>
              <div class="yt-metric-circle" style='background:{_bg};border-radius:50%;width:105px;height:105px;
                   display:flex;align-items:center;justify-content:center;box-shadow:0 4px 12px rgba(0,0,0,.12);'>
                <span style='color:{_fg};font-size:1.9em;font-family:Fira Code,monospace;font-weight:bold;'>{_val:,}</span>
              </div>
            </div>
            <div style='text-align:center;font-size:16px;margin-top:.4em;min-height:1.5em;'>{_detail}</div>""",
            unsafe_allow_html=True,
        )

st.markdown('<div class="section-header" style="margin-top:1.5em">Top 5 Videos (Last 28 Days)</div>', unsafe_allow_html=True)
_top_vids = get_top_videos(CHANNEL_ID, YOUTUBE_API_KEY, _yt_sc, _yt_ec, YT_ACCESS_TOKEN)
if not _top_vids.empty:
    _vdf = _top_vids[["title", "views", "watch_time", "likes", "comments"]].copy()
    _vdf.columns = ["Title", "Views", "Watch Time (min)", "Likes", "Comments"]
    _vdf["Title"] = [
        f'<a href="https://www.youtube.com/watch?v={vid_id}" target="_blank">{title}</a>'
        for title, vid_id in zip(_vdf["Title"], _top_vids["id"])
    ]
    st.markdown(_vdf.to_html(escape=False, index=False, classes="yt-table"), unsafe_allow_html=True)
else:
    st.info("No video data found for this period.")

st.caption("YouTube metrics from YouTube Data & Analytics APIs. Credentials loaded securely from Streamlit secrets.")

# ═════════════════════════════════════════════════════════════════════════════
# PDF REPORT GENERATION
# ═════════════════════════════════════════════════════════════════════════════
def _generate_pdf():
    pdf = FPDF()
    pdf.add_page()
    try:
        logo_bytes = requests.get(
            "https://www.salasarservices.com/assets/Frontend/images/logo-black.png", timeout=5
        ).content
        logo_path = "logo_temp.png"
        Image.open(io.BytesIO(logo_bytes)).convert("RGBA").save(logo_path)
        pdf.image(logo_path, x=10, y=8, w=50)
    except Exception:
        pass

    pdf.set_xy(65, 15)
    pdf.set_font("Arial", "B", 17)
    pdf.set_text_color(45, 68, 141)
    pdf.cell(0, 12, "Salasar Services Digital Marketing Dashboard", ln=1)
    pdf.set_font("Arial", "", 12)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(8)
    pdf.cell(0, 10, f"Reporting Period: {format_month_year(sd)} | Previous: {format_month_year(psd)}", ln=1)

    # Website Performance
    pdf.set_font("Arial", "B", 14); pdf.set_text_color(45, 68, 141)
    pdf.cell(0, 12, "Website Performance", ln=1)
    pdf.set_font("Arial", "", 12); pdf.set_text_color(0, 0, 0)
    for title, value, delta, _ in perf_data:
        val_str = f"{value:.2f}%" if title == "Average CTR" else f"{int(value):,}"
        pdf.cell(0, 10, f"{title}: {val_str} ({delta:+.2f}% vs previous month)", ln=1)
    pdf.ln(2)

    # Top Content
    pdf.set_font("Arial", "B", 14); pdf.set_text_color(45, 68, 141)
    pdf.cell(0, 10, "Top Content", ln=1)
    pdf.set_font("Arial", "B", 12); pdf.set_text_color(0, 0, 0)
    pdf.cell(110, 8, "Page", border=1)
    pdf.cell(30, 8, "Clicks", border=1)
    pdf.cell(35, 8, "Change (%)", border=1, ln=1)
    pdf.set_font("Arial", "", 12)
    for row in top_content_data:
        pdf.cell(110, 8, row["Page"][:65], border=1)
        pdf.cell(30, 8, str(row["Clicks"]), border=1)
        pdf.cell(35, 8, row["Change (%)"], border=1, ln=1)
    pdf.ln(4)

    # Website Analytics
    pdf.set_font("Arial", "B", 14); pdf.set_text_color(45, 68, 141)
    pdf.cell(0, 10, "Website Analytics", ln=1)
    pdf.set_font("Arial", "", 12); pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 8, f"Total Users: {cur_users:,} ({delta_users:+.2f}%)", ln=1)
    pdf.cell(0, 8, f"Sessions: {total_sessions:,} ({delta_sessions:+.2f}%)", ln=1)
    pdf.cell(0, 8, f"Organic Clicks: {organic_clicks:,} ({delta_organic:+.2f}%)", ln=1)
    pdf.ln(1)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 9, "New vs Returning Users", ln=1)
    pdf.set_font("Arial", "", 12)
    pdf.cell(0, 8, f"New Users: {new_users:,} ({delta_new:+.2f}%)", ln=1)
    pdf.cell(0, 8, f"Returning Users: {returning_users:,} ({delta_returning:+.2f}%)", ln=1)
    pdf.ln(1)

    pdf.set_font("Arial", "B", 12); pdf.cell(0, 9, "Active Users by Country (Top 5)", ln=1)
    pdf.set_font("Arial", "", 12)
    for c in country_data:
        pdf.cell(0, 7, f"{c['country']}: {c['activeUsers']:,}", ln=1)
    pdf.ln(1)

    pdf.set_font("Arial", "B", 12); pdf.cell(0, 9, "Traffic Acquisition by Channel", ln=1)
    pdf.set_font("Arial", "", 12)
    for _, row in traf_df.iterrows():
        pdf.cell(0, 7, f"{row['channel']}: {row['sessions']:,}", ln=1)
    pdf.ln(1)

    pdf.set_font("Arial", "B", 12); pdf.cell(0, 9, "Top 10 Organic Queries", ln=1)
    pdf.set_font("Arial", "", 12)
    for _, row in sc_df.iterrows():
        pdf.cell(0, 7, f"{row['query']} ({row['clicks']:,} clicks)", ln=1)

    pdf.set_y(-25)
    pdf.set_font("Arial", "I", 8); pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 10, "Generated by Salasar Services Digital Marketing Dashboard", 0, 0, "C")
    return io.BytesIO(pdf.output(dest="S").encode("latin1"))


if pdf_report_btn:
    _pdf = _generate_pdf()
    st.sidebar.download_button(
        label="📥 Download PDF",
        data=_pdf,
        file_name=f"Salasar-Report-{date.today()}.pdf",
        mime="application/pdf",
        use_container_width=True,
    )
