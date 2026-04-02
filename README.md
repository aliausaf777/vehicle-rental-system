# 🚗 Vehicle Rental System

A full-stack web application for managing vehicle rentals, built with Python (Flask) and MySQL.

## 🛠️ Tech Stack
- **Backend:** Python, Flask
- **Database:** MySQL (Relational Database)
- **Frontend:** HTML, CSS, JavaScript
- **Tools:** VS Code, MySQL Workbench

## ✨ Features
- User registration, login & session management
- Browse available vehicles with real-time availability
- Book vehicles with automatic cost calculation
- Simulated payment processing (UPI, Card, Netbanking)
- Admin dashboard to manage vehicles & monitor all bookings
- Fully normalized relational database (Customers, Cars, Rentals)

## 🗄️ Database Design
- `customers` — stores user accounts
- `cars` — stores vehicle details and availability
- `rentals` — stores booking records with foreign keys to customers and cars

## 🚀 How to Run
1. Clone the repo
2. Install dependencies: `pip install flask mysql-connector-python`
3. Set up MySQL database and update credentials in `app.py`
4. Run: `python app.py`
5. Open browser at `http://localhost:5000`

## 📸 Screenshots
Home Page | Login | Booking | Admin Dashboard

## 👨‍💻 Author
Mohammed Azhad Ali Ausaf — B.Tech CSE Data Science, Aurora Deemed University
