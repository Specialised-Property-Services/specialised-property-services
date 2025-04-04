# Specialised Property Services – Simpro Job Uploader

A streamlined, web-based tool built with Streamlit to automate job scheduling for Specialised Property Services.  
This app integrates directly with Simpro to process daily warrant reports, assign locksmiths, and handle job creation with smart pricing rules.

## 🚀 Features

- 🔍 Fuzzy contact matching with confirmation and memory across sessions
- 📋 Automated job scheduling and charge calculations:
  - £111.50 for a single job per contact per day
  - £223 for multiple jobs per contact per day
  - £137.50 per shutter if marked
- 📂 Upload CSV warrant reports directly in-browser
- 🧠 Learns from user input to improve future matches
- ☁️ Hosted on Streamlit Cloud — no installation required

## 🛠 Technologies

- Python + Streamlit
- Simpro API (UK-based account)
- Pandas for data handling
- FuzzyWuzzy for contact matching

## 🧪 How to Use

1. Upload your daily warrant CSV report
2. Confirm or adjust fuzzy matches as needed
3. Review job summary and totals
4. Click **"Sync with Simpro"** to create jobs
5. Done!

## 📁 Folder Structure (once project is populated)

📂 specialised-property-services/ │ ├── app.py # Main Streamlit app ├── utils/ │ ├── simpro_api.py # Handles Simpro integration │ ├── match_engine.py # Fuzzy logic and contact learning │ └── charges.py # Job charge rules ├── data/ │ └── contact_matches.json # Persistent match memory ├── requirements.txt └── README.md

## 📄 License

This project is licensed under the MIT License – see the [LICENSE](LICENSE) file for details.
</details>
Add initial README.md with project overview and usage
