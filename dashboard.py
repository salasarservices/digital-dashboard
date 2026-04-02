import streamlit as st

# ── MUST be the very first Streamlit call ────────────────────────────────────
st.set_page_config(
    page_title="Salasar Services | Digital Marketing Dashboard",
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
SC_SITE_URL  = "https://www.salasarservices.com/"
LOGO_URL     = "https://ik.imagekit.io/salasarservices/Salasar-Logo-new.png?updatedAt=1771587668127"

# ── Load external stylesheet ──────────────────────────────────────────────
import pathlib
_css_path = pathlib.Path(__file__).parent / "style.css"
if _css_path.exists():
    st.markdown(f"<style>{_css_path.read_text()}</style>", unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ═════════════════════════════════════════════════════════════════════════════

def show_loader(placeholder, message="Fetching data from all sources…"):
    placeholder.markdown(
        f"""<div class="dash-loader">
              <div class="dash-loader-ring"></div>
              <div class="dash-loader-text">{message}</div>
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
    start    = datetime.strptime(sel, "%B %Y").date().replace(day=1)
    end      = start + relativedelta(months=1) - timedelta(days=1)
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


def safe_percent(prev, cur):
    if prev == 0 and cur == 0:
        return 0
    if prev == 0:
        return 100 if cur > 0 else 0
    return ((cur - prev) / abs(prev)) * 100


def _badge(delta, suffix="%"):
    if delta > 0:
        return f"<span class='kpi-badge up'>▲ {abs(delta):.2f}{suffix}</span><span class='kpi-vs'>vs prev month</span>"
    if delta < 0:
        return f"<span class='kpi-badge down'>▼ {abs(delta):.2f}{suffix}</span><span class='kpi-vs'>vs prev month</span>"
    return f"<span class='kpi-badge flat'>— 0.00{suffix}</span><span class='kpi-vs'>vs prev month</span>"


def render_kpi_card(title, value, delta, accent_color, tooltip=None, fmt_value=None, icon=""):
    """Render a modern flat KPI card."""
    tip_html = ""
    if tooltip:
        tip_html = (
            f"<span class='kpi-tooltip'>"
            f"<span class='tip-icon'>?</span>"
            f"<span class='kpi-tip-text'>{tooltip}</span>"
            f"</span>"
        )
    display = fmt_value if fmt_value is not None else f"{int(value):,}"
    badge   = _badge(delta)
    icon_html = f"<span>{icon}</span>" if icon else ""
    st.markdown(
        f"""<div class="kpi-card">
              <div class="kpi-accent" style="background:{accent_color}"></div>
              <div class="kpi-inner">
                <div class="kpi-title">{icon_html}{title}{tip_html}</div>
                <div class="kpi-value">{display}</div>
                <div>{badge}</div>
              </div>
            </div>""",
        unsafe_allow_html=True,
    )


def section_header(icon, title, subtitle="", icon_bg="#1b8fc5"):
    st.markdown(
        f"""<div class="section-header">
              <div class="section-header-icon" style="background:{icon_bg}20;color:{icon_bg}">{icon}</div>
              <div>
                <div class="section-header-title">{title}</div>
                {'<div class="section-header-sub">' + subtitle + '</div>' if subtitle else ''}
              </div>
              <div class="section-header-line"></div>
            </div>""",
        unsafe_allow_html=True,
    )


def get_delta_icon_and_color(val):
    if val > 0:
        return "▲", "#16a34a"
    if val < 0:
        return "▼", "#dc2626"
    return "—", "#94a3b8"


# ═════════════════════════════════════════════════════════════════════════════
# LOGIN
# ═════════════════════════════════════════════════════════════════════════════
_USERNAME = st.secrets["login"]["username"]
_PASSWORD = st.secrets["login"]["password"]


def login():
    # ── Page & form scoped styles (login screen only) ─────────────────────
    st.markdown(
        """<style>
        /* Full-page dark gradient */
        .stApp,
        [data-testid="stAppViewContainer"] {
            background: linear-gradient(150deg, #071b2a 0%, #0f2d44 55%, #0a2236 100%) !important;
        }
        /* Strip the default Streamlit form card chrome */
        [data-testid="stForm"] {
            background: transparent !important;
            border: none !important;
            padding: 0 !important;
            box-shadow: none !important;
        }
        /* Input fields — dark-tinted so they contrast against the dark card */
        [data-testid="stForm"] input {
            background: rgba(255,255,255,0.07) !important;
            border: 1px solid rgba(255,255,255,0.18) !important;
            border-radius: 8px !important;
            color: #e2e8f0 !important;
        }
        [data-testid="stForm"] input::placeholder { color: #64748b !important; }
        [data-testid="stForm"] input:focus {
            border-color: #1b8fc5 !important;
            box-shadow: 0 0 0 3px rgba(27,143,197,.20) !important;
        }
        /* Input labels */
        [data-testid="stForm"] label {
            color: #90bdd8 !important;
            font-size: .82em !important;
            font-weight: 600 !important;
            letter-spacing: .04em !important;
            text-transform: uppercase !important;
        }
        /* Login button — small, brand teal, NOT full-width */
        [data-testid="stForm"] button[kind="primaryFormSubmit"],
        [data-testid="stForm"] button[type="submit"] {
            background: #1b8fc5 !important;
            color: #ffffff !important;
            border: none !important;
            border-radius: 8px !important;
            font-weight: 600 !important;
            font-size: .9em !important;
            padding: 0.45em 1.8em !important;
            width: auto !important;           /* override full-width default */
            min-width: 110px !important;
        }
        [data-testid="stForm"] button:hover {
            background: #1478a8 !important;
        }
        </style>""",
        unsafe_allow_html=True,
    )

    # Vertical breathing room
    st.markdown("<div style='height:8vh'></div>", unsafe_allow_html=True)

    # Three-column centering — card sits in the middle column
    _, card_col, _ = st.columns([1.7, 1, 1.7])

    with card_col:
        # Card header — NO indentation inside the string (4-space indent = markdown code block)
        # NO HTML comments (<!-- --> also confuses Streamlit markdown parser)
        card_header = (
            "<div style='background:#0d2a3e;border-radius:14px 14px 0 0;"
            "padding:28px 28px 20px;border:1px solid rgba(27,143,197,0.25);"
            "border-bottom:none;box-shadow:0 -4px 24px rgba(0,0,0,.4)'>"
            f"<img src='{LOGO_URL}' style='height:48px;margin-bottom:18px;display:block;"
            "filter:brightness(1.1) drop-shadow(0 1px 6px rgba(27,143,197,.3))'>"
            "<div style='font-size:1.2em;font-weight:800;color:#1b8fc5;"
            "text-transform:uppercase;letter-spacing:.06em;margin-bottom:6px'>"
            "Dashboard Login</div>"
            "<div style='font-size:.83em;color:#64748b;font-weight:400;margin-bottom:4px'>"
            "Please sign in to access the dashboard.</div>"
            "</div>"
        )
        st.markdown(card_header, unsafe_allow_html=True)

        # Card body — wraps the Streamlit form widgets
        st.markdown(
            "<div style='background:#0d2a3e;border-radius:0 0 14px 14px;"
            "padding:20px 28px 26px;border:1px solid rgba(27,143,197,0.25);"
            "border-top:none;box-shadow:0 16px 48px rgba(0,0,0,.5)'>",
            unsafe_allow_html=True,
        )
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password",
                                     placeholder="Enter your password")
            submitted = st.form_submit_button("Login")
            if submitted:
                if username == _USERNAME and password == _PASSWORD:
                    st.session_state["logged_in"] = True
                    st.rerun()
                else:
                    st.error("Invalid credentials.")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown(
            "<div style='text-align:left;margin-top:10px;"
            "font-size:.73em;color:#334d63'>© 2026 Salasar Services</div>",
            unsafe_allow_html=True,
        )


if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False

if not st.session_state["logged_in"]:
    login()
    st.stop()


# ═════════════════════════════════════════════════════════════════════════════
# API CLIENTS
# ═════════════════════════════════════════════════════════════════════════════
@st.cache_resource(ttl=3600)
def get_api_clients():
    sa   = st.secrets["gcp"]["service_account"]
    info = json.loads(sa)
    pk   = info.get("private_key", "").replace("\\n", "\n")
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
        new   = int(resp.rows[0].metric_values[1].value)
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
# FACEBOOK DATA FUNCTIONS
# ═════════════════════════════════════════════════════════════════════════════
PAGE_ID      = st.secrets["facebook"]["page_id"]
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
    url    = f"https://graph.facebook.com/v19.0/{page_id}/posts"
    params = {"since": since, "until": until, "limit": 100, "access_token": access_token}
    posts  = []
    try:
        while url:
            resp  = requests.get(url, params=params, timeout=10).json()
            posts.extend(resp.get("data", []))
            paging = resp.get("paging", {})
            url    = paging.get("next") if "next" in paging else None
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
# YOUTUBE DATA FUNCTIONS
# ═════════════════════════════════════════════════════════════════════════════
_YT_CLIENT_ID     = st.secrets["youtube"].get("client_id", "")
_YT_CLIENT_SECRET = st.secrets["youtube"].get("client_secret", "")
_YT_REFRESH_TOKEN = st.secrets["youtube"].get("refresh_token", "")
YOUTUBE_API_KEY   = st.secrets["youtube"].get("api_key", "")
CHANNEL_ID        = st.secrets["youtube"].get("channel_id", "")


@st.cache_resource(ttl=3000)
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



@st.cache_data(ttl=3600)
def get_yt_analytics_summary(channel_id, start_date, end_date, yt_token):
    try:
        resp = requests.get(
            "https://youtubeanalytics.googleapis.com/v2/reports",
            headers=_yt_headers(yt_token),
            params={
                "ids": f"channel=={channel_id}",
                "startDate": start_date.strftime("%Y-%m-%d"),
                "endDate":   end_date.strftime("%Y-%m-%d"),
                "metrics":   "views,estimatedMinutesWatched,subscribersGained,subscribersLost",
            },
            timeout=15,
        ).json()
        if "rows" not in resp:
            return {"views": 0, "watch_time": 0, "subs_gained": 0, "subs_lost": 0}
        row     = resp["rows"][0]
        col_map = {c["name"]: i for i, c in enumerate(resp["columnHeaders"])}
        return {
            "views":       int(row[col_map["views"]]),
            "watch_time":  int(row[col_map["estimatedMinutesWatched"]]),
            "subs_gained": int(row[col_map["subscribersGained"]]),
            "subs_lost":   int(row[col_map["subscribersLost"]]),
        }
    except Exception:
        return {"views": 0, "watch_time": 0, "subs_gained": 0, "subs_lost": 0}


@st.cache_data(ttl=3600)
def get_total_subscribers(channel_id, api_key):
    try:
        url   = f"https://www.googleapis.com/youtube/v3/channels?part=statistics&id={channel_id}&key={api_key}"
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
                "id":        item["id"],
                "title":     item["snippet"]["title"][:60],
                "published": item["snippet"]["publishedAt"][:10],
                "views":     int(item["statistics"].get("viewCount", 0)),
                "likes":     int(item["statistics"].get("likeCount", 0)),
                "comments":  int(item["statistics"].get("commentCount", 0)),
            })
        df  = pd.DataFrame(data).sort_values("views", ascending=False).head(max_results)
        ids = list(df["id"])
        yt_resp = requests.get(
            "https://youtubeanalytics.googleapis.com/v2/reports",
            headers=_yt_headers(yt_token),
            params={
                "ids":       "channel==MINE",
                "startDate": start_date.strftime("%Y-%m-%d"),
                "endDate":   end_date.strftime("%Y-%m-%d"),
                "metrics":   "estimatedMinutesWatched,views,likes,comments",
                "dimensions":"video",
                "filters":   f"video=={','.join(ids)}",
            },
            timeout=15,
        ).json()
        if "rows" in yt_resp:
            wt_dict      = {row[0]: row[1] for row in yt_resp["rows"]}
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

        # Aggregate daily_records across ALL documents in each collection
        analytics_rows, followers_total = [], 0
        for doc in db["lnkd-analytics"].find({}):
            analytics_rows.extend(doc.get("daily_records", []))
            if doc.get("followers_total", 0):
                followers_total = max(followers_total, int(doc["followers_total"]))

        extras_rows = []
        for doc in db["lnkd-extras"].find({}):
            extras_rows.extend(doc.get("daily_records", []))

        client.close()

        df_analytics = pd.DataFrame(analytics_rows) if analytics_rows else pd.DataFrame()
        df_extras    = pd.DataFrame(extras_rows)    if extras_rows    else pd.DataFrame()
        return df_analytics, df_extras, followers_total
    except Exception as e:
        st.error(f"Could not connect to LinkedIn MongoDB: {e}")
        return pd.DataFrame(), pd.DataFrame(), 0


# ═════════════════════════════════════════════════════════════════════════════
# SERVICE-GROUPED FETCH WRAPPERS
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
    st.image(LOGO_URL, width=160)
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    st.markdown(
        "<div style='font-size:.7em;font-weight:700;text-transform:uppercase;"
        "letter-spacing:.1em;color:#90bdd8;margin-bottom:6px'>Report Period</div>",
        unsafe_allow_html=True,
    )

    # ── Date mode toggle ────────────────────────────────────────────────────
    _date_mode = st.radio(
        "Date Mode",
        ["📅 Monthly", "🗓 Custom Range"],
        horizontal=True,
        label_visibility="collapsed",
        key="date_mode",
    )

    if _date_mode == "📅 Monthly":
        month_options = get_month_options()
        if "selected_month" not in st.session_state:
            st.session_state["selected_month"] = month_options[-1]
        sel = st.selectbox(
            "Select month:",
            month_options,
            index=month_options.index(st.session_state["selected_month"]),
            label_visibility="collapsed",
        )
        if sel != st.session_state["selected_month"]:
            st.session_state["selected_month"] = sel
        sd, ed, psd, ped = get_month_range(st.session_state["selected_month"])
    else:
        # ── Custom date range ────────────────────────────────────────────
        _today = date.today()
        _def_start = _today.replace(day=1)
        _cr1, _cr2 = st.columns(2)
        with _cr1:
            sd = st.date_input("From", value=_def_start, max_value=_today, key="custom_start")
        with _cr2:
            ed = st.date_input("To",   value=_today,     max_value=_today, key="custom_end")
        if sd > ed:
            st.error("'From' must be before 'To'.")
            st.stop()
        _range_days = (ed - sd).days + 1
        ped = sd - timedelta(days=1)
        psd = ped - timedelta(days=_range_days - 1)

    st.markdown(
        f"""<div class="period-pill">
              <div style="font-size:.78em;color:#90bdd8;font-weight:600;text-transform:uppercase;letter-spacing:.05em;margin-bottom:6px">Selected Period</div>
              <div style="font-size:.88em"><b style="color:#1b8fc5">Current:</b> <span style="color:#e2e8f0">{sd.strftime('%d %b %Y')} → {ed.strftime('%d %b %Y')}</span></div>
              <div style="font-size:.88em;margin-top:2px"><b style="color:#1b8fc5">Previous:</b> <span style="color:#e2e8f0">{psd.strftime('%d %b %Y')} → {ped.strftime('%d %b %Y')}</span></div>
            </div>""",
        unsafe_allow_html=True,
    )

    if st.button("⟳  Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.cache_resource.clear()
        st.session_state["selected_month"] = month_options[-1]
        st.rerun()

    st.markdown("---")

    # ── LinkedIn DB flush ──────────────────────────────────────────────────
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

    if st.button("🗑  Flush LinkedIn Data", use_container_width=True):
        st.session_state["confirm_lnkd_flush"] = True

    if st.session_state["confirm_lnkd_flush"]:
        st.warning("⚠ Permanently deletes all LinkedIn data. Continue?")
        _c1, _c2 = st.columns(2)
        with _c1:
            if st.button("Delete", type="primary", key="lnkd_yes"):
                if _flush_linkedin_database():
                    st.success("Cleared.")
                    st.cache_data.clear()
                st.session_state["confirm_lnkd_flush"] = False
        with _c2:
            if st.button("Cancel", key="lnkd_no"):
                st.session_state["confirm_lnkd_flush"] = False

    st.markdown("---")

    # ── LinkedIn Excel Upload ──────────────────────────────────────────────
    st.markdown(
        "<div style='font-size:.7em;font-weight:700;text-transform:uppercase;"
        "letter-spacing:.1em;color:#90bdd8;margin-bottom:6px'>Upload LinkedIn Data</div>",
        unsafe_allow_html=True,
    )
    st.caption(
        "Excel file must have two sheets: **analytics** and **extras**. "
        "Rows are appended by date (duplicates skipped)."
    )

    _xlsx_file = st.file_uploader(
        "LinkedIn Excel (.xlsx)",
        type=["xlsx"],
        label_visibility="collapsed",
        key="lnkd_xlsx_upload",
    )

    if _xlsx_file is not None:
        def _upsert_linkedin_excel(xlsx_bytes):
            """
            Parse the uploaded Excel file and upsert into MongoDB.

            Sheet "analytics" expected columns:
                date | total_followers | total_unique_visitors

            Sheet "extras" expected columns:
                date | total_impressions | clicks | engagement_rate

            Strategy: fetch existing daily_records from a single "upload" doc,
            merge by date (new rows win), write back.
            """
            try:
                xls = pd.read_excel(io.BytesIO(xlsx_bytes), sheet_name=None)
            except Exception as exc:
                return False, f"Could not read Excel file: {exc}"

            required_sheets = {"analytics", "extras"}
            missing = required_sheets - {s.lower() for s in xls}
            if missing:
                return False, f"Missing sheet(s): {', '.join(missing)}"

            xls = {k.lower(): v for k, v in xls.items()}

            def _validate_cols(df, cols, sheet):
                missing_c = [c for c in cols if c not in df.columns]
                if missing_c:
                    return f"Sheet '{sheet}' is missing column(s): {', '.join(missing_c)}"
                return None

            err = _validate_cols(
                xls["analytics"],
                ["date", "total_followers", "total_unique_visitors"],
                "analytics",
            )
            if err:
                return False, err
            err = _validate_cols(
                xls["extras"],
                ["date", "total_impressions", "clicks", "engagement_rate"],
                "extras",
            )
            if err:
                return False, err

            def _df_to_records(df):
                df = df.copy()
                df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("%Y-%m-%d")
                df = df.dropna(subset=["date"])
                return df.to_dict(orient="records")

            new_analytics = _df_to_records(xls["analytics"])
            new_extras    = _df_to_records(xls["extras"])

            try:
                client = MongoClient(
                    st.secrets["mongo_uri_linkedin"],
                    serverSelectionTimeoutMS=5000,
                    tlsCAFile=certifi.where(),
                )
                db = client["sal-lnkd"]

                def _merge_into(collection_name, new_rows, date_key="date"):
                    col = db[collection_name]
                    doc = col.find_one({"_source": "excel_upload"}) or {}
                    existing = {r[date_key]: r for r in doc.get("daily_records", [])}
                    for row in new_rows:
                        existing[row[date_key]] = row
                    merged = sorted(existing.values(), key=lambda r: r[date_key])
                    payload = {"_source": "excel_upload", "daily_records": merged}
                    if "followers_total" in doc:
                        payload["followers_total"] = doc["followers_total"]
                    col.replace_one({"_source": "excel_upload"}, payload, upsert=True)

                _merge_into("lnkd-analytics", new_analytics)
                _merge_into("lnkd-extras",    new_extras)
                client.close()
                return True, f"Uploaded {len(new_analytics)} analytics rows and {len(new_extras)} extras rows."
            except Exception as exc:
                return False, f"MongoDB error: {exc}"

        if st.button("⬆  Upload to MongoDB", use_container_width=True, key="lnkd_upload_btn"):
            with st.spinner("Uploading…"):
                _ok, _msg = _upsert_linkedin_excel(_xlsx_file.read())
            if _ok:
                st.success(_msg)
                st.cache_data.clear()
            else:
                st.error(_msg)

    st.markdown("---")
    pdf_report_btn = st.button("📄  Generate PDF Report", use_container_width=True)
    # Placeholder sits right below the generate button in the sidebar.
    # It is populated at the bottom of the file once _generate_pdf() is defined
    # and all data variables (gsc_clicks, _cur_views, _yt_cur …) are in scope.
    _pdf_dl_ph = st.sidebar.empty()

    st.markdown(
        "<div style='position:absolute;bottom:18px;left:0;right:0;text-align:center;"
        "font-size:.72em;color:#4a6b83'>Salasar Services © 2026</div>",
        unsafe_allow_html=True,
    )


# ═════════════════════════════════════════════════════════════════════════════
# PAGE HEADER
# ═════════════════════════════════════════════════════════════════════════════
st.markdown(
    f"""<div class="dash-header">
          <img src="{LOGO_URL}" alt="Salasar Logo">
          <div class="dash-header-text">
            <h1>Digital Marketing Dashboard</h1>
            <p>Salasar Services &nbsp;·&nbsp; Reporting Period: <strong style="color:#a8d55c">{sd.strftime('%B %Y')}</strong> &nbsp;·&nbsp; Compared to <strong style="color:#90bdd8">{psd.strftime('%B %Y')}</strong></p>
          </div>
        </div>""",
    unsafe_allow_html=True,
)


# ═════════════════════════════════════════════════════════════════════════════
# PARALLEL DATA FETCH
# ═════════════════════════════════════════════════════════════════════════════
_loader = st.empty()
show_loader(_loader, "Connecting to Google Analytics, Search Console, LinkedIn & social APIs…")

with ThreadPoolExecutor(max_workers=3) as _pool:
    _f_ga4  = _pool.submit(_fetch_all_ga4, PROPERTY_ID, sd, ed, psd, ped)
    _f_gsc  = _pool.submit(_fetch_all_gsc, SC_SITE_URL, sd, ed, psd, ped)
    _f_lnkd = _pool.submit(load_linkedin_analytics_df)

    (cur_users, prev_users, traf, traf_prev,
     nr_cur, nr_prev, country_data) = _f_ga4.result()

    (gsc_stats_cur, gsc_stats_prev, top_pages_now, top_pages_prev,
     sc_data, sc_data_prev) = _f_gsc.result()

    (df_lnkd_analytics, df_lnkd_extras, lnkd_followers_total) = _f_lnkd.result()

_loader.empty()

# ── Unpack & compute deltas ───────────────────────────────────────────────
gsc_clicks, gsc_impressions, gsc_ctr = gsc_stats_cur
gsc_clicks_prev, gsc_impressions_prev, gsc_ctr_prev = gsc_stats_prev

total_users, new_users, returning_users     = nr_cur
total_users_prev, new_users_prev, returning_users_prev = nr_prev

gsc_clicks_delta = pct_change(gsc_clicks,      gsc_clicks_prev)
gsc_impr_delta   = pct_change(gsc_impressions, gsc_impressions_prev)
gsc_ctr_delta    = pct_change(gsc_ctr,         gsc_ctr_prev)

total_sessions = sum(i["sessions"] for i in traf)
prev_sessions  = sum(i["sessions"] for i in traf_prev)
delta_sessions = pct_change(total_sessions, prev_sessions)

organic_clicks      = sum(r.get("clicks", 0) for r in sc_data)
organic_clicks_prev = sum(r.get("clicks", 0) for r in sc_data_prev)
delta_organic       = pct_change(organic_clicks, organic_clicks_prev)

delta_users     = pct_change(cur_users,      prev_users)
delta_new       = pct_change(new_users,      new_users_prev)
delta_returning = pct_change(returning_users, returning_users_prev)

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

perf_data = [
    ("Total Website Clicks", gsc_clicks,         gsc_clicks_delta, "#e67e22"),
    ("Total Impressions",    gsc_impressions,     gsc_impr_delta,   "#3498db"),
    ("Average CTR",          gsc_ctr * 100,       gsc_ctr_delta,    "#16a085"),
]

# ═════════════════════════════════════════════════════════════════════════════
# SECTION: WEBSITE PERFORMANCE
# ═════════════════════════════════════════════════════════════════════════════
section_header("🌐", "Website Performance",
               "Google Search Console — clicks, impressions & CTR", "#1b8fc5")

_perf_tips = [
    "Total clicks your site received from Google Search results.",
    "Total times your site appeared in Google Search results.",
    "Percentage of impressions that resulted in a click (CTR).",
]
_perf_icons = ["🖱️", "👁️", "📊"]
_perf_cols  = st.columns(3)
for _i, (_title, _value, _delta, _color) in enumerate(perf_data):
    with _perf_cols[_i]:
        _fmt = f"{_value:.2f}%" if _title == "Average CTR" else None
        render_kpi_card(_title, _value, _delta, _color,
                        tooltip=_perf_tips[_i], fmt_value=_fmt, icon=_perf_icons[_i])

section_divider()

# ═════════════════════════════════════════════════════════════════════════════
# SECTION: TOP CONTENT
# ═════════════════════════════════════════════════════════════════════════════
section_header("📄", "Top Content",
               "Highest-clicked pages from Google Search Console", "#5ca832")


def _render_top_content(data):
    df = pd.DataFrame(data)
    if df.empty:
        st.info("No top content data available for this period.")
        return

    def _fmt_clicks(x):
        return f"<span style='font-weight:700;color:#0f2d44;font-family:Fira Code,monospace'>{int(x):,}</span>"

    def _fmt_chg(val):
        pct   = float(val)
        color = "#16a34a" if pct >= 0 else "#dc2626"
        bg    = "#dcfce7" if pct >= 0 else "#fee2e2"
        arrow = "▲" if pct >= 0 else "▼"
        return (f"<span style='background:{bg};color:{color};padding:2px 8px;"
                f"border-radius:12px;font-size:.82em;font-weight:600'>"
                f"{arrow} {abs(pct):.2f}%</span>")

    df["Clicks"]     = df["Clicks"].apply(_fmt_clicks)
    df["Change (%)"] = df["Change (%)"].apply(_fmt_chg)
    st.markdown(df.to_html(escape=False, index=False, classes="dash-table"), unsafe_allow_html=True)


_render_top_content(top_content_data)

section_divider()

# ═════════════════════════════════════════════════════════════════════════════
# SECTION: WEBSITE ANALYTICS
# ═════════════════════════════════════════════════════════════════════════════
section_header("📈", "Website Analytics",
               "GA4 — users, sessions & organic traffic", "#0f2d44")

_analytics_data = [
    ("Total Users",    cur_users,      delta_users,    "#1b8fc5", "👥",
     "Total unique users who visited the website."),
    ("Sessions",       total_sessions, delta_sessions, "#5ca832", "🔄",
     "Total number of sessions (visits) on the website."),
    ("Organic Clicks", organic_clicks, delta_organic,  "#e67e22", "🔍",
     "Clicks on your site from Google Search (organic only)."),
]
_analytics_cols = st.columns(3)
for _i, (_t, _v, _d, _c, _ic, _tip) in enumerate(_analytics_data):
    with _analytics_cols[_i]:
        render_kpi_card(_t, _v, _d, _c, tooltip=_tip, icon=_ic)

st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

# New vs Returning + Country + Channel in one clean row
_left_col, _right_col = st.columns([1, 1])

with _left_col:
    st.markdown(
        "<div style='font-size:.82em;font-weight:700;text-transform:uppercase;"
        "letter-spacing:.06em;color:#64748b;margin-bottom:10px'>New vs Returning Users</div>",
        unsafe_allow_html=True,
    )
    _ret_cols = st.columns(2)
    _ret_data = [
        ("New Users",       new_users,       delta_new,       "#e67e22", "🆕",
         "First-time visitors during this period."),
        ("Returning Users", returning_users, delta_returning, "#1b8fc5", "🔁",
         "Visitors who came back (had a prior session)."),
    ]
    for _i, (_t, _v, _d, _c, _ic, _tip) in enumerate(_ret_data):
        with _ret_cols[_i]:
            render_kpi_card(_t, _v, _d, _c, tooltip=_tip, icon=_ic)

    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
    st.markdown(
        "<div style='font-size:.82em;font-weight:700;text-transform:uppercase;"
        "letter-spacing:.06em;color:#64748b;margin-bottom:10px'>Active Users by Country (Top 5)</div>",
        unsafe_allow_html=True,
    )
    _country_df = pd.DataFrame(country_data)
    if not _country_df.empty:
        def _flag_html(row):
            code = country_name_to_code(row["country"])
            flag = (f'<img src="https://flagcdn.com/16x12/{code}.png" '
                    f'style="height:12px;margin-right:8px;vertical-align:middle;border-radius:2px">')  if code else ""
            return f"{flag}{row['country']}"
        _country_df["Country"]      = _country_df.apply(_flag_html, axis=1)
        _country_df["Active Users"] = _country_df["activeUsers"].apply(lambda x: f"<b>{x:,}</b>")
        _country_df = _country_df[["Country", "Active Users"]]
        st.markdown(_country_df.to_html(escape=False, index=False, classes="dash-table"),
                    unsafe_allow_html=True)

with _right_col:
    st.markdown(
        "<div style='font-size:.82em;font-weight:700;text-transform:uppercase;"
        "letter-spacing:.06em;color:#64748b;margin-bottom:10px'>Traffic Acquisition by Channel</div>",
        unsafe_allow_html=True,
    )
    if not traf_df.empty:
        _traf_show = traf_df.copy()
        _traf_show.columns = ["Channel", "Sessions"]
        _traf_show["Sessions"] = _traf_show["Sessions"].apply(lambda x: f"<b>{int(x):,}</b>")
        st.markdown(_traf_show.to_html(escape=False, index=False, classes="dash-table"),
                    unsafe_allow_html=True)

    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
    st.markdown(
        "<div style='font-size:.82em;font-weight:700;text-transform:uppercase;"
        "letter-spacing:.06em;color:#64748b;margin-bottom:10px'>Top 10 Organic Search Queries</div>",
        unsafe_allow_html=True,
    )
    if not sc_df.empty:
        _sc_show = sc_df[["query", "clicks"]].copy()
        _sc_show.columns = ["Query", "Clicks"]
        _sc_show["Clicks"] = _sc_show["Clicks"].apply(lambda x: f"<b>{int(x):,}</b>")
        st.markdown(_sc_show.to_html(escape=False, index=False, classes="dash-table"),
                    unsafe_allow_html=True)

section_divider()

# ═════════════════════════════════════════════════════════════════════════════
# SECTION: LINKEDIN ANALYTICS
# ═════════════════════════════════════════════════════════════════════════════
def _render_linkedin(df_analytics, df_extras, followers_total, sd, psd):
    section_header("💼", "LinkedIn Analytics",
                   "Impressions, clicks, engagement, followers & visitors", "#0a66c2")

    if df_analytics.empty and df_extras.empty:
        st.info("No LinkedIn analytics data found in MongoDB.")
        return

    def _prep(df, rename=None):
        if rename:
            df = df.rename(columns=rename)
        date_col = "date" if "date" in df.columns else None
        if date_col:
            df["Date"]     = pd.to_datetime(df[date_col], errors="coerce")
            df             = df.dropna(subset=["Date"])
            df["Month"]    = df["Date"].dt.to_period("M")
            df["MonthStr"] = df["Date"].dt.strftime("%B %Y")
        return df

    df_analytics = _prep(df_analytics, rename={
        "total_followers":       "Total followers (Date-wise)",
        "total_unique_visitors": "Total Unique Visitors (Date-wise)",
    })
    df_extras = _prep(df_extras)

    if df_analytics.empty:
        st.error("No valid date records in lnkd-analytics.")
        return
    if df_extras.empty:
        st.error("No valid date records in lnkd-extras.")
        return

    # Use the global sidebar date selection
    _sel_p      = pd.Period(sd, freq="M")
    _prev_p     = pd.Period(psd, freq="M")
    _prev_label = psd.strftime("%B %Y")

    def _mslice(df, col, period, agg="sum"):
        if "Month" not in df.columns or col not in df.columns:
            return 0.0
        slc = df[df["Month"] == period][col]
        if slc.empty:
            return 0.0
        return float(slc.sum() if agg == "sum" else slc.mean())

    def _mslice_net(df, col, period):
        """Net gain = last cumulative value minus first cumulative value in period."""
        if "Month" not in df.columns or col not in df.columns:
            return 0.0
        slc = df[df["Month"] == period].sort_values("Date")[col].dropna()
        if slc.empty:
            return 0.0
        return float(slc.iloc[-1] - slc.iloc[0]) if len(slc) >= 2 else float(slc.iloc[0])

    imp_c = _mslice(df_extras, "total_impressions", _sel_p)
    imp_p = _mslice(df_extras, "total_impressions", _prev_p)
    clk_c = _mslice(df_extras, "clicks", _sel_p)
    clk_p = _mslice(df_extras, "clicks", _prev_p)
    eng_c = _mslice(df_extras, "engagement_rate", _sel_p, "mean")
    eng_p = _mslice(df_extras, "engagement_rate", _prev_p, "mean")
    fol_c = _mslice_net(df_analytics, "Total followers (Date-wise)", _sel_p)
    fol_p = _mslice_net(df_analytics, "Total followers (Date-wise)", _prev_p)
    vis_c = _mslice(df_analytics, "Total Unique Visitors (Date-wise)", _sel_p)
    vis_p = _mslice(df_analytics, "Total Unique Visitors (Date-wise)", _prev_p)

    _lnkd_metrics = [
        ("Impressions",       int(imp_c), safe_percent(imp_p, imp_c), "#0a66c2", "👁️",  None),
        ("Clicks",            int(clk_c), safe_percent(clk_p, clk_c), "#1b8fc5", "🖱️",  None),
        ("Engagement Rate",   eng_c * 100, safe_percent(eng_p, eng_c), "#5ca832", "💬", f"{eng_c*100:.2f}%"),
        ("Followers Gained",  int(fol_c), safe_percent(fol_p, fol_c), "#a8d55c", "➕",  None),
        ("Unique Visitors",   int(vis_c), safe_percent(vis_p, vis_c), "#64748b", "🚶",  None),
    ]

    st.markdown('<div class="platform-metrics-row">', unsafe_allow_html=True)
    _lnkd_cols = st.columns(5)
    for _i, (_t, _v, _d, _c, _ic, _fmt) in enumerate(_lnkd_metrics):
        with _lnkd_cols[_i]:
            render_kpi_card(_t, _v, _d, _c, fmt_value=_fmt, icon=_ic)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown(
        f"<div style='margin-top:4px;padding:10px 14px;background:#f0f9ff;"
        f"border-radius:10px;border:1px solid #bae6fd;display:inline-block;"
        f"font-size:.85em;color:#0369a1'>"
        f"<b>Total Lifetime Followers:</b> {followers_total:,}</div>",
        unsafe_allow_html=True,
    )


_render_linkedin(df_lnkd_analytics, df_lnkd_extras, lnkd_followers_total, sd, psd)

section_divider()

# ═════════════════════════════════════════════════════════════════════════════
# SECTION: FACEBOOK ANALYTICS
# ═════════════════════════════════════════════════════════════════════════════
section_header("📘", "Facebook Page Analytics",
               "Page views, likes, followers & published posts", "#1877f2")

# Use global sidebar date selection directly
_fb_since  = sd.strftime("%Y-%m-%d")
_fb_until  = ed.strftime("%Y-%m-%d")
_fb_psince = psd.strftime("%Y-%m-%d")
_fb_puntil = ped.strftime("%Y-%m-%d")

with ThreadPoolExecutor(max_workers=7) as _fp:
    _fvc = _fp.submit(get_total_metric_value, "page_views_total", _fb_since,  _fb_until,  PAGE_ID, ACCESS_TOKEN)
    _fvp = _fp.submit(get_total_metric_value, "page_views_total", _fb_psince, _fb_puntil, PAGE_ID, ACCESS_TOKEN)
    _flc = _fp.submit(get_total_metric_value, "page_fans",        _fb_since,  _fb_until,  PAGE_ID, ACCESS_TOKEN)
    _flp = _fp.submit(get_total_metric_value, "page_fans",        _fb_psince, _fb_puntil, PAGE_ID, ACCESS_TOKEN)
    _ffl = _fp.submit(get_lifetime_total_followers, PAGE_ID, ACCESS_TOKEN)
    _ffp = _fp.submit(get_previous_lifetime_total_followers, _fb_puntil, PAGE_ID, ACCESS_TOKEN)
    _fpo = _fp.submit(get_posts, _fb_since, _fb_until, PAGE_ID, ACCESS_TOKEN)

    _cur_views  = _fvc.result()
    _prev_views = _fvp.result()
    _cur_likes  = _flc.result()
    _prev_likes = _flp.result()
    _life_foll  = _ffl.result()
    _prev_foll  = _ffp.result()
    _cur_posts  = _fpo.result()

_fb_metrics = [
    ("Page Views",          _cur_views,  safe_percent(_prev_views, _cur_views), "#1877f2", "👀"),
    ("Page Likes",          _cur_likes,  safe_percent(_prev_likes, _cur_likes), "#5ca832", "👍"),
    ("Total Followers",     _life_foll,  safe_percent(_prev_foll,  _life_foll), "#1b8fc5", "👥"),
]
_fb_cols = st.columns(3)
for _i, (_t, _v, _d, _c, _ic) in enumerate(_fb_metrics):
    with _fb_cols[_i]:
        render_kpi_card(_t, _v, _d, _c, icon=_ic)

st.markdown(
    f"<div style='font-size:.95em;font-weight:700;color:#0f2d44;margin:22px 0 10px'>"
    f"Posts Published in {sd.strftime('%B %Y')}</div>",
    unsafe_allow_html=True,
)

if _cur_posts:
    _rows = []
    for _post in _cur_posts:
        _pid = _post["id"]
        _url = f"https://www.facebook.com/{PAGE_ID}/posts/{_pid.split('_')[-1]}"
        _msg = _post.get("message", "")
        _ttl = (_msg[:100] + "…") if len(_msg) > 100 else _msg
        _rows.append({
            "Post":     f"<a href='{_url}' target='_blank' style='color:#1877f2;text-decoration:none'>{_ttl}</a>",
            "👍 Likes":  get_post_likes(_pid, ACCESS_TOKEN),
            "💬 Comments": get_post_comments(_pid, ACCESS_TOKEN),
        })
    _fb_df = pd.DataFrame(_rows)
    _fb_df["👍 Likes"]    = _fb_df["👍 Likes"].apply(lambda x: f"<b>{x:,}</b>")
    _fb_df["💬 Comments"] = _fb_df["💬 Comments"].apply(lambda x: f"<b>{x:,}</b>")
    st.markdown(_fb_df.to_html(escape=False, index=False, classes="dash-table"), unsafe_allow_html=True)
else:
    st.info("No posts published this month.")

st.caption("Data pulled live from Facebook Graph API.")

section_divider()

# ═════════════════════════════════════════════════════════════════════════════
# SECTION: YOUTUBE ANALYTICS
# ═════════════════════════════════════════════════════════════════════════════
section_header("▶️", "YouTube Channel Overview",
               f"Subscribers, views, watch time & top videos — {sd.strftime('%B %Y')}", "#ff0000")

# Use the global sidebar date range (same as all other sections)
with ThreadPoolExecutor(max_workers=3) as _yp:
    _fyc = _yp.submit(get_yt_analytics_summary, CHANNEL_ID, sd,  ed,  YT_ACCESS_TOKEN)
    _fyp = _yp.submit(get_yt_analytics_summary, CHANNEL_ID, psd, ped, YT_ACCESS_TOKEN)
    _fys = _yp.submit(get_total_subscribers, CHANNEL_ID, YOUTUBE_API_KEY)
    _yt_cur     = _fyc.result()
    _yt_prev    = _fyp.result()
    _total_subs = _fys.result()

_yt_net_subs = _yt_cur["subs_gained"] - _yt_cur["subs_lost"]
_yt_metrics  = [
    ("Total Subscribers",     _total_subs,           safe_percent(_yt_prev["subs_gained"], _yt_cur["subs_gained"]), "#ff0000", "📺",
     f"{'+'if _yt_net_subs>=0 else ''}{_yt_net_subs:,} net this period"),
    ("Views",                 _yt_cur["views"],      safe_percent(_yt_prev["views"],      _yt_cur["views"]),       "#e67e22", "👁️", None),
    ("Watch Time (min)",      _yt_cur["watch_time"], safe_percent(_yt_prev["watch_time"], _yt_cur["watch_time"]),  "#16a085", "⏱️", None),
]
_yt_cols = st.columns(3)
for _i, (_lbl, _val, _d, _c, _ic, _fmt) in enumerate(_yt_metrics):
    with _yt_cols[_i]:
        render_kpi_card(_lbl, _val, _d, _c, icon=_ic, fmt_value=_fmt)

st.markdown(
    f"<div style='font-size:.95em;font-weight:700;color:#0f2d44;margin:22px 0 10px'>"
    f"Top 5 Videos — {sd.strftime('%B %Y')}</div>",
    unsafe_allow_html=True,
)
_top_vids = get_top_videos(CHANNEL_ID, YOUTUBE_API_KEY, sd, ed, YT_ACCESS_TOKEN)
if not _top_vids.empty:
    _vdf = _top_vids[["title", "views", "watch_time", "likes", "comments"]].copy()
    _vdf.columns = ["Title", "Views", "Watch Time (min)", "Likes", "Comments"]
    _vdf["Title"] = [
        f'<a href="https://www.youtube.com/watch?v={vid_id}" target="_blank" '
        f'style="color:#ff0000;text-decoration:none">{title}</a>'
        for title, vid_id in zip(_vdf["Title"], _top_vids["id"])
    ]
    for _col in ["Views", "Watch Time (min)", "Likes", "Comments"]:
        _vdf[_col] = _vdf[_col].apply(lambda x: f"<b>{int(x):,}</b>")
    st.markdown(_vdf.to_html(escape=False, index=False, classes="dash-table"), unsafe_allow_html=True)
else:
    st.info("No video data found for this period.")

st.caption("YouTube metrics from YouTube Data & Analytics APIs.")

section_divider()

# ═════════════════════════════════════════════════════════════════════════════
# PDF REPORT GENERATION
# ═════════════════════════════════════════════════════════════════════════════
def _generate_pdf():
    """Industry-standard multi-page PDF report with coloured section banners."""
    from fpdf import FPDF

    # ── Helpers ──────────────────────────────────────────────────────────────
    NAV  = (15, 45, 68)    # #0f2d44 — navbar navy
    TEAL = (27, 143, 197)  # #1b8fc5
    GRN  = (92, 168, 50)   # #5ca832
    AMB  = (230, 126, 34)  # #e67e22
    RED  = (220, 38, 38)   # #dc2626
    LT   = (248, 250, 252) # light row fill
    W    = 190             # usable page width

    def _safe(text):
        """Sanitise any string for fpdf 1.x latin-1 encoding.
        Replaces every character outside latin-1 (e.g. em-dash U+2014,
        smart quotes, bullet chars) with the nearest ASCII equivalent or '?'.
        """
        replacements = {
            "\u2014": "-",  # em dash
            "\u2013": "-",  # en dash
            "\u2018": "'",  # left single quote
            "\u2019": "'",  # right single quote
            "\u201c": '"',  # left double quote
            "\u201d": '"',  # right double quote
            "\u2026": "...",# ellipsis
            "\u00b7": ".",  # middle dot
            "\u2022": "*",  # bullet
            "\u00a0": " ",  # non-breaking space
        }
        s = str(text)
        for src, dst in replacements.items():
            s = s.replace(src, dst)
        # Catch any remaining non-latin-1 characters
        return s.encode("latin-1", errors="replace").decode("latin-1")

    class PDF(FPDF):
        def header(self): pass  # custom header via draw_page_header
        def footer(self):
            self.set_y(-14)
            self.set_font("Arial", "I", 8)
            self.set_text_color(160, 160, 160)
            self.cell(0, 8,
                _safe(f"Salasar Services - Digital Marketing Report - {date.today().strftime('%d %B %Y')}   |   Page {self.page_no()}"),
                0, 0, "C")

    def draw_page_header(pdf, logo_path):
        """Full-width dark header bar with logo + title."""
        pdf.set_fill_color(*NAV)
        pdf.rect(0, 0, 210, 26, "F")
        if logo_path:
            try:
                pdf.image(logo_path, x=8, y=4, h=18)
            except Exception:
                pass
        pdf.set_xy(62, 8)
        pdf.set_font("Arial", "B", 14)
        pdf.set_text_color(255, 255, 255)
        pdf.cell(0, 9, _safe("Digital Marketing Performance Report"), ln=0)
        pdf.set_xy(62, 16)
        pdf.set_font("Arial", "", 9)
        pdf.set_text_color(160, 210, 240)
        pdf.cell(0, 6,
            _safe(f"Period: {format_month_year(sd)}  |  Previous: {format_month_year(psd)}  |  Salasar Services"),
            ln=1)
        pdf.ln(6)

    def section_banner(pdf, title, r, g, b):
        """Coloured full-width section banner."""
        pdf.set_fill_color(r, g, b)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Arial", "B", 11)
        pdf.cell(W, 9, _safe(f"  {title}"), 0, 1, "L", fill=True)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)

    def kpi_row(pdf, metrics):
        """Render a horizontal row of KPI boxes. metrics = list of (label, value, delta%)."""
        n      = len(metrics)
        box_w  = W / n
        box_h  = 22
        x_start = pdf.get_x()
        y_start = pdf.get_y()
        for idx, (label, value, delta) in enumerate(metrics):
            x = x_start + idx * box_w
            # box fill
            pdf.set_fill_color(245, 248, 252)
            pdf.rect(x + 1, y_start, box_w - 2, box_h, "F")
            # value
            pdf.set_xy(x + 2, y_start + 2)
            pdf.set_font("Arial", "B", 13)
            pdf.set_text_color(*NAV)
            pdf.cell(box_w - 4, 7, _safe(value), 0, 0, "C")
            # label
            pdf.set_xy(x + 2, y_start + 9)
            pdf.set_font("Arial", "", 7)
            pdf.set_text_color(100, 116, 139)
            pdf.cell(box_w - 4, 5, _safe(label), 0, 0, "C")
            # delta badge
            if delta is not None:
                try:
                    dv = float(str(delta).replace("%","").replace("+",""))
                    sign   = "+" if dv >= 0 else ""
                    dc     = (22, 163, 74) if dv >= 0 else (220, 38, 38)
                    dtext  = f"{sign}{dv:.1f}% vs prev"
                except Exception:
                    dc    = (100, 116, 139)
                    dtext = str(delta)
                pdf.set_xy(x + 2, y_start + 14)
                pdf.set_font("Arial", "", 6.5)
                pdf.set_text_color(*dc)
                pdf.cell(box_w - 4, 5, _safe(dtext), 0, 0, "C")
        pdf.set_xy(x_start, y_start + box_h + 3)

    def table(pdf, headers, rows, col_widths, alt_fill=(248, 250, 252)):
        """Render a styled table with alternating rows."""
        pdf.set_font("Arial", "B", 8)
        pdf.set_fill_color(*NAV)
        pdf.set_text_color(255, 255, 255)
        for h, w in zip(headers, col_widths):
            pdf.cell(w, 7, _safe(h), 0, 0, "L", fill=True)
        pdf.ln()
        pdf.set_font("Arial", "", 8)
        for ri, row in enumerate(rows):
            fill = ri % 2 == 1
            pdf.set_fill_color(*alt_fill)
            pdf.set_text_color(30, 41, 59)
            for val, w in zip(row, col_widths):
                pdf.cell(w, 6, _safe(str(val))[:60], 0, 0, "L", fill=fill)
            pdf.ln()
        pdf.ln(3)

    def check_page_break(pdf, needed=30):
        if pdf.get_y() > 260:
            pdf.add_page()
            draw_page_header(pdf, logo_path)

    # ── Download logo — cross-platform temp path (fixes Windows /tmp/ crash) ─
    import os, tempfile
    logo_path = None
    try:
        logo_bytes = requests.get(LOGO_URL, timeout=6).content
        logo_path  = os.path.join(tempfile.gettempdir(), "salasar_logo_pdf.png")
        Image.open(io.BytesIO(logo_bytes)).convert("RGBA").save(logo_path)
    except Exception:
        logo_path = None

    # ── Build PDF ────────────────────────────────────────────────────────────
    pdf = PDF()
    pdf.set_margins(10, 10, 10)
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()
    draw_page_header(pdf, logo_path)

    # ── 1. WEBSITE PERFORMANCE ───────────────────────────────────────────────
    section_banner(pdf, "1   Website Performance  (Google Search Console)", *TEAL)
    kpi_row(pdf, [
        ("Total Clicks",    f"{gsc_clicks:,}",         f"{gsc_clicks_delta:+.1f}%"),
        ("Impressions",     f"{gsc_impressions:,}",    f"{gsc_impr_delta:+.1f}%"),
        ("Avg CTR",         f"{gsc_ctr*100:.2f}%",     f"{gsc_ctr_delta:+.1f}%"),
    ])

    # ── 2. WEBSITE ANALYTICS ─────────────────────────────────────────────────
    check_page_break(pdf)
    section_banner(pdf, "2   Website Analytics  (Google Analytics 4)", *NAV)
    kpi_row(pdf, [
        ("Total Users",      f"{cur_users:,}",         f"{delta_users:+.1f}%"),
        ("Sessions",         f"{total_sessions:,}",    f"{delta_sessions:+.1f}%"),
        ("Organic Clicks",   f"{organic_clicks:,}",    f"{delta_organic:+.1f}%"),
        ("New Users",        f"{new_users:,}",         f"{delta_new:+.1f}%"),
        ("Returning Users",  f"{returning_users:,}",   f"{delta_returning:+.1f}%"),
    ])

    # Top Content table
    pdf.set_font("Arial", "B", 8.5)
    pdf.set_text_color(*NAV)
    pdf.cell(0, 6, _safe("Top Content by Clicks"), ln=1)
    pdf.ln(1)
    table(pdf,
        ["Page URL", "Clicks", "Change (%)"],
        [[r["Page"][:80], r["Clicks"], r["Change (%)"] + "%"] for r in top_content_data],
        [130, 30, 30])

    # Country + Channel tables side-by-side
    check_page_break(pdf)
    y_before = pdf.get_y()
    pdf.set_font("Arial", "B", 8.5); pdf.set_text_color(*NAV)
    pdf.cell(90, 6, _safe("Active Users by Country (Top 5)"), ln=0)
    pdf.cell(10, 6, "", ln=0)
    pdf.cell(90, 6, _safe("Traffic by Channel"), ln=1)
    pdf.ln(1)
    # left column — country
    x_left = pdf.get_x()
    y_now  = pdf.get_y()
    pdf.set_font("Arial", "B", 8); pdf.set_fill_color(*NAV); pdf.set_text_color(255, 255, 255)
    pdf.cell(65, 7, "Country",  0, 0, "L", fill=True)
    pdf.cell(25, 7, "Users",    0, 0, "R", fill=True)
    pdf.ln()
    pdf.set_font("Arial", "", 8)
    for ri, c in enumerate(country_data):
        fill = ri % 2 == 1
        pdf.set_fill_color(248, 250, 252); pdf.set_text_color(30, 41, 59)
        pdf.cell(65, 6, _safe(c["country"])[:35], 0, 0, "L", fill=fill)
        pdf.cell(25, 6, _safe(f"{c['activeUsers']:,}"), 0, 0, "R", fill=fill)
        pdf.ln()
    y_after_country = pdf.get_y()
    # right column — channel
    pdf.set_xy(105, y_now)
    pdf.set_font("Arial", "B", 8); pdf.set_fill_color(*NAV); pdf.set_text_color(255, 255, 255)
    pdf.cell(60, 7, "Channel",  0, 0, "L", fill=True)
    pdf.cell(25, 7, "Sessions", 0, 0, "R", fill=True)
    pdf.ln()
    pdf.set_font("Arial", "", 8)
    for ri, (_, row) in enumerate(traf_df.iterrows()):
        fill = ri % 2 == 1
        pdf.set_xy(105, pdf.get_y())
        pdf.set_fill_color(248, 250, 252); pdf.set_text_color(30, 41, 59)
        pdf.cell(60, 6, _safe(str(row.iloc[0]))[:30], 0, 0, "L", fill=fill)
        pdf.cell(25, 6, _safe(f"{int(row.iloc[1]):,}"), 0, 0, "R", fill=fill)
        pdf.ln()
    pdf.set_y(max(y_after_country, pdf.get_y()) + 3)

    # Organic queries table
    check_page_break(pdf)
    pdf.set_font("Arial", "B", 8.5); pdf.set_text_color(*NAV)
    pdf.cell(0, 6, _safe("Top Organic Search Queries"), ln=1); pdf.ln(1)
    table(pdf,
        ["Query", "Clicks"],
        [[row["query"][:90], row["clicks"]] for _, row in sc_df.iterrows()],
        [160, 30])

    # ── 3. LINKEDIN ──────────────────────────────────────────────────────────
    check_page_break(pdf)
    section_banner(pdf, "3   LinkedIn Analytics", 10, 102, 194)

    # ── 4. FACEBOOK ──────────────────────────────────────────────────────────
    check_page_break(pdf)
    section_banner(pdf, "4   Facebook Page Analytics", 24, 119, 242)
    kpi_row(pdf, [
        ("Page Views",      f"{_cur_views:,}",   f"{safe_percent(_prev_views, _cur_views):+.1f}%"),
        ("Page Likes",      f"{_cur_likes:,}",   f"{safe_percent(_prev_likes, _cur_likes):+.1f}%"),
        ("Total Followers", f"{_life_foll:,}",   f"{safe_percent(_prev_foll, _life_foll):+.1f}%"),
    ])

    # ── 5. YOUTUBE ───────────────────────────────────────────────────────────
    check_page_break(pdf)
    section_banner(pdf, "5   YouTube Channel Overview", 255, 0, 0)
    kpi_row(pdf, [
        ("Subscribers",    f"{_total_subs:,}",          None),
        ("Views",          f"{_yt_cur['views']:,}",      f"{safe_percent(_yt_prev['views'], _yt_cur['views']):+.1f}%"),
        ("Watch Time(min)",f"{_yt_cur['watch_time']:,}", f"{safe_percent(_yt_prev['watch_time'], _yt_cur['watch_time']):+.1f}%"),
    ])
    if not _top_vids.empty:
        pdf.set_font("Arial", "B", 8.5); pdf.set_text_color(*NAV)
        pdf.cell(0, 6, _safe(f"Top Videos - {sd.strftime('%B %Y')}"), ln=1); pdf.ln(1)
        table(pdf,
            ["Title", "Views", "Watch Time", "Likes"],
            [[row["title"][:55], f"{int(row['views']):,}",
              f"{int(row['watch_time']):,}", f"{int(row['likes']):,}"]
             for _, row in _top_vids.iterrows()],
            [110, 25, 30, 25])

    # fpdf  (1.x) → output() returns str  → encode to bytes
    # fpdf2 (2.x) → output() returns bytes → use directly
    _raw = pdf.output(dest="S")
    if isinstance(_raw, str):
        _raw = _raw.encode("latin1")
    return io.BytesIO(_raw)


# ── PDF: generate on button click, cache in session state ──────────────────
# _generate_pdf() is defined above; all data variables are now in scope.
# Using session_state means the download button persists across reruns so
# the user can actually click it without it disappearing.
if pdf_report_btn:
    with st.spinner("Building PDF report…"):
        st.session_state["_pdf_cache"] = _generate_pdf()

if "_pdf_cache" in st.session_state:
    _pdf_dl_ph.download_button(
        label="📥  Download PDF",
        data=st.session_state["_pdf_cache"],
        file_name=f"Salasar-Report-{date.today()}.pdf",
        mime="application/pdf",
        use_container_width=True,
    )
