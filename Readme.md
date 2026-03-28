# 💸 Bill Splitter

A clean, simple Flask web app that helps groups split bills fairly — no more awkward math or chasing people for money.

---

## 🚀 Features

* 🔐 **User Authentication** — Secure registration & login (passwords hashed)
* 🧾 **Multiple Bills** — Create and manage separate bills with different groups
* 💱 **Currency Support** — KSH, USD, EUR, GBP, UGX, TZS
* ✏️ **Full Control** — Add, edit, and delete payments easily
* ⚖️ **Smart Settlements** — Minimizes transactions (who owes who)
* 📊 **Visual Insights** — Spending charts powered by Chart.js
* 📁 **CSV Export** — Download any bill as a CSV file
* 🔌 **JSON API** — Access bill data programmatically

---

## 🛠️ Tech Stack

* **Backend:** Flask (Python)
* **Frontend:** HTML, CSS, JavaScript
* **Database:** SQLite
* **Charts:** Chart.js
* **Deployment:** Render

---

## ⚡ Live Demo

👉 **Try it here:**
[https://bill-splitter-t26y.onrender.com](https://bill-splitter-t26y.onrender.com)

---

## 📦 Setup (Local Development)

### 1. Install dependencies

```
pip install -r requirements.txt
```

### 2. Run the app

```
python app.py
```

### 3. Open in browser

```
http://127.0.0.1:5000
```

### 4. Start using

* Register an account
* Create your first bill
* Add participants and payments

---

## 📁 Project Structure

```
billsplitter/
├── app.py                  # Core app logic and routes
├── requirements.txt
├── db.sqlite               # Auto-created database
├── static/
│   └── style.css
└── templates/
    ├── base.html           # Shared layout/navbar
    ├── register.html
    ├── login.html
    ├── index.html          # Dashboard
    ├── new_bill.html
    ├── bill.html           # Bill details + charts
    └── edit_payment.html
```

---

## 🔌 API

### Get bill data

```
GET /api/bill/<id>
```

📌 Returns bill summary as JSON *(authentication required)*

---

## 🌐 Deployment (Render)

### Steps:

1. Push your project to GitHub
2. Create a **Web Service** on Render
3. Set build command:

```
pip install -r requirements.txt
```

4. Set start command:

```
gunicorn app:app
```

5. Add environment variable:

```
SECRET_KEY = your-secure-random-string
```

⚠️ Make sure your app reads it like this:

```python
app.secret_key = os.environ.get("SECRET_KEY")
```

---

## 🧠 What This Project Demonstrates

* Backend architecture with Flask
* Authentication and session handling
* Database design with SQLite
* REST API design
* Data visualization
* Deployment workflow

---

## 📌 Next Improvements (Ideas)

* Add email notifications
* Support group invitations
* Mobile-responsive UI improvements
* Add expense categories

---

## 🤝 Contributing

Pull requests are welcome. For major changes, open an issue first to discuss.

---

## 📄 License

This project is open-source and available under the MIT License.