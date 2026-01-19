import streamlit as st
import pandas as pd
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import random
import os

# ---------------- CONFIG ---------------- #

LIVE_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

MAX_WORKERS = 5
REQUEST_TIMEOUT = 15

# ---------------- STREAMLIT ---------------- #

icon_path = "icons/icon.png"
page_icon = icon_path if os.path.exists(icon_path) else None

st.set_page_config(
    page_title="Ads.txt / App-ads.txt Validator",
    layout="wide",
    page_icon=page_icon
)

# ---------------- SESSION ---------------- #

if "results_df" not in st.session_state:
    st.session_state.results_df = None

# ---------------- HTTP ---------------- #

def create_session():
    s = requests.Session()
    s.headers.update({
        "User-Agent": LIVE_UA,
        "Accept": "text/plain,text/html;q=0.9,*/*;q=0.8",
        "Cache-Control": "no-cache",
    })
    return s

# ---------------- FETCH ---------------- #

def fetch_ads_file(session, domain, filename):
    domain = domain.strip().replace("https://", "").replace("http://", "").split("/")[0]

    urls = [
        f"https://{domain}/{filename}",
        f"http://{domain}/{filename}",
    ]

    for url in urls:
        try:
            time.sleep(random.uniform(0.4, 1.2))
            r = session.get(url, timeout=REQUEST_TIMEOUT, allow_redirects=True)

            content_type = r.headers.get("Content-Type", "").lower()

            if r.status_code == 200:
                if "text/html" in content_type:
                    return None, "HTML instead of TXT", True
                return r.text, "OK", False

            if r.status_code in (403, 404):
                return None, f"HTTP {r.status_code}", True

        except requests.exceptions.SSLError:
            try:
                r = session.get(url, timeout=REQUEST_TIMEOUT, verify=False)
                if r.status_code == 200:
                    return r.text, "OK (SSL ignored)", False
            except Exception:
                pass
        except Exception as e:
            return None, str(e), True

    return None, "File not accessible", True

# ---------------- PARSING ---------------- #

def parse_ads_txt(content):
    records = []

    if not content:
        return records

    for raw in content.splitlines():
        line = raw.lstrip("\ufeff").split("#")[0].strip()
        if not line:
            continue

        parts = [p.strip() for p in line.split(",")]

        if len(parts) < 2:
            continue

        records.append({
            "domain": parts[0].lower(),
            "id": parts[1].lower(),
            "type": parts[2].upper() if len(parts) >= 3 else None,
            "cert": parts[3].lower() if len(parts) >= 4 else None,
        })

    return records


def parse_reference(line):
    parts = [p.strip() for p in line.split(",")]

    if len(parts) < 2:
        return None

    return {
        "domain": parts[0].lower(),
        "id": parts[1].lower(),
        "type": parts[2].upper() if len(parts) >= 3 else None,
        "cert": parts[3].lower() if len(parts) >= 4 else None,
        "original": line,
    }

# ---------------- VALIDATION ---------------- #

def validate_domain(domain, filename, references):
    session = create_session()
    content, status, error = fetch_ads_file(session, domain, filename)

    results = []

    if error:
        for ref in references:
            results.append({
                "URL": domain,
                "File": filename,
                "Result": "Error",
                "Details": status,
                "Reference": ref["original"],
            })
        return results

    records = parse_ads_txt(content)

    for ref in references:
        found = False
        final_status = "Not found"
        details = "No matching Domain + ID"

        for rec in records:
            if rec["domain"] == ref["domain"] and rec["id"] == ref["id"]:
                found = True

                # IAB logic
                if not ref["type"]:
                    final_status = "Valid"
                    details = "Matched (type not required)"
                elif not rec["type"]:
                    final_status = "Valid"
                    details = "Matched (type missing in file)"
                elif rec["type"] == ref["type"]:
                    final_status = "Valid"
                    details = "Full match"
                else:
                    final_status = "Valid"
                    details = f"Type differs (found {rec['type']})"
                break

        results.append({
            "URL": domain,
            "File": filename,
            "Result": final_status,
            "Details": details,
            "Reference": ref["original"],
        })

    return results

# ---------------- UI ---------------- #

st.title("Ads.txt / App-ads.txt Validator")

file_type = st.radio("File Type", ("app-ads.txt", "ads.txt"))
view_mode = st.radio("View", ("Show All Results", "Errors / Warnings Only"), index=1)

col1, col2 = st.columns(2)

with col1:
    targets_raw = st.text_area("Target Domains", height=300)

with col2:
    refs_raw = st.text_area("Reference Lines", height=300)

if st.button("Start Validation"):
    targets = [t.strip() for t in targets_raw.splitlines() if t.strip()]
    references = [parse_reference(r) for r in refs_raw.splitlines() if parse_reference(r)]

    all_results = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [
            executor.submit(validate_domain, t, file_type, references)
            for t in targets
        ]

        for future in as_completed(futures):
            all_results.extend(future.result())

    df = pd.DataFrame(all_results)

    if view_mode == "Errors / Warnings Only":
        df = df[df["Result"] != "Valid"]

    st.session_state.results_df = df

# ---------------- OUTPUT ---------------- #

if st.session_state.results_df is not None:
    st.dataframe(st.session_state.results_df, use_container_width=True)

    csv = st.session_state.results_df.to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", csv, "report.csv", "text/csv")
