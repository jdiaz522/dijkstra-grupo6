@echo off
cd /d "%~dp0"
python -c "import streamlit, plotly, openpyxl" 2>nul || python -m pip install -r requirements.txt
python -m streamlit run app.py
pause
