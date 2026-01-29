# Ads.txt / App-ads.txt line Checker

A high-performance Streamlit application designed for AdOps professionals to validate `ads.txt` and `app-ads.txt` files across multiple domains simultaneously. 

This tool allows you to check if specific partner lines (Reference Lines) are correctly implemented on target publishers' websites, filtering out mismatches, missing IDs, or wrong account types.

## Key Features

* **Bulk Validation:** Scan hundreds of domains in parallel using multithreading.
* **Dual Mode:** Support for both `ads.txt` (Web) and `app-ads.txt` (Mobile Apps).
* **Advanced Parsing:**
    * Handles redirects and SSL errors automatically.
    * Detects "Soft 404s" (where a server returns an HTML page instead of a text file).
    * Normalizes URLs (adds `http/https` if missing).
* **Flexible Reporting:**
    * **Vertical Layout:** Standard row-by-row analysis.
    * **Horizontal Layout:** Aggregated view showing all reference checks per domain in one row.
* **Smart Filtering:** * Filter by specific error types (e.g., "RESELLER vs DIRECT" mismatches).
    * Hide valid results to focus only on problems.
* **CSV Export:** Download detailed reports for offline analysis.
* **Dark Mode:** Custom UI styled for comfortable usage in low-light environments.

## Installation

### Prerequisites
* Python 3.8+
* pip

### Setup

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/your-username/ads.txt-app-ads.txt-line-checker.git](https://github.com/your-username/ads.txt-app-ads.txt-line-checker.git)
    cd ads-txt-validator
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run the application:**
    ```bash
    streamlit run app.py
    ```

4.  The app will open in your browser at `http://localhost:8501`.

## How to Use

### 1. Settings
* **File Type:** Choose between `app-ads.txt` or `ads.txt`.
* **Output View:**
    * *Show All Results:* Displays every check, including successful ones.
    * *Errors / Warnings Only:* Filters the table to show only missing lines or mismatches.
* **Result Layout:** Switch between a detailed vertical list or a compact horizontal matrix.

### 2. Input Data
* **Target Websites:** Enter the list of domains you want to scan (one per line).
    ```text
    example.com
    mysite.org
    subdomain.game.net
    ```
* **Reference Lines (Rules):** Enter the lines you expect to find on those websites.
    Format: `Domain, Publisher ID, Account Type`
    ```text
    google.com, pub-123456789, DIRECT
    appnexus.com, 1234, RESELLER
    ```

### 3. Analyze Results
Click **Start Validation**. The progress bar will indicate the status.
* **Green:** Valid match.
* **Black/Teal:** Partial match (e.g., ID matches but Type is wrong).
* **Dark Grey:** Not found.
* **Red/Grey:** Connection error or invalid file format.

## Project Structure

```text
├── app.py              # Main application logic
├── requirements.txt    # Python dependencies
├── config.toml         # Streamlit theme configuration
├── icons/              # Folder for application icons
│   └── icon.png        # App favicon
└── README.md           # Documentation
