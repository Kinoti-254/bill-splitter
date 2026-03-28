# Bill Splitter

A Flask web app to split bills among friends, with user accounts, multiple bills, charts, CSV export, and a JSON API.

## Features
- User registration and login (passwords are hashed)
- Create multiple named bills with currency selection (KSH, USD, EUR, GBP, UGX, TZS)
- Add, edit, and delete individual payments
- Auto-calculates who owes whom (minimum transactions algorithm)
- Bar chart showing spending per person (Chart.js)
- Export any bill to CSV
- JSON API endpoint for every bill

## Setup

1. Install dependencies:
   pip install -r requirements.txt

2. Run the app:
   python app.py

3. Open http://127.0.0.1:5000 in your browser

4. Register an account and create your first bill.

## Project structure

billsplitter/
├── app.py                  # All routes and logic
├── requirements.txt
├── db.sqlite               # Auto-created on first run
├── static/
│   └── style.css
└── templates/
    ├── base.html           # Shared navbar/layout
    ├── register.html
    ├── login.html
    ├── index.html          # Dashboard (all bills)
    ├── new_bill.html
    ├── bill.html           # Bill detail + chart + settlements
    └── edit_payment.html

## API

GET /api/bill/<id>   — returns bill summary as JSON (must be logged in)

## Deployment (Render.com)

1. Push to GitHub
2. Create a new Web Service on render.com
3. Set build command:  pip install -r requirements.txt
4. Set start command:  gunicorn app:app
5. Add environment variable: SECRET_KEY = (a long random string)
   and update app.secret_key to read from os.environ.get("SECRET_KEY")