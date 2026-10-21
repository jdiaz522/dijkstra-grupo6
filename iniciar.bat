@echo off
cd /d "%~dp0"
python -c "import streamlit" 2>nul || python -m pip install -r requirements.txt
python -m streamlit run app.py
pause
