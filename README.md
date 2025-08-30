sudo apt update && sudo apt install poppler-utils -y

# to run the app

pip install -r requirements.txt

uvicorn pdftojpg:app --reload

# Create venv inside your project folder

python3 -m venv venv

# Activate it

source venv/bin/activate

# Install FastAPI and Uvicorn inside venv

pip install -r requirements.txt
