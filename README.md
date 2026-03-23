# CuraMind AI 🧠

![CuraMind Banner](https://img.shields.io/badge/Status-Active-brightgreen) ![Django](https://img.shields.io/badge/Django-4.2-092E20?style=flat&logo=django&logoColor=white) ![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white) ![TailwindCSS](https://img.shields.io/badge/TailwindCSS-3.0-38B2AC?style=flat&logo=tailwind-css&logoColor=white)

**CuraMind AI** is an advanced, role-based healthcare workflow and tele-radiology platform built with Django. It bridges the gap between patients, specialized doctors (such as radiologists), and system administrators by providing an intuitive, secure, and AI-assisted environment for uploading, reviewing, and managing medical scans, appointments, and secure communications.

---

## 🏗️ System Architecture

CuraMind follows a modern **Model-View-Template (MVT)** architecture powered by the Django framework, designed with separation of concerns and data security in mind.

### Core Architecture Components

1. **Role-Based Authentication (RBAC):**
   A custom user configuration residing in the `accounts` app enforces strict segregation between `PATIENT`, `DOCTOR`, and `ADMIN` roles. Custom decorators (`@patient_required`, etc.) secure the routing logic.
   
2. **AI-Assisted Scan Processing Module:**
   The `records` app manages medical uploads (X-Rays, MRIs, CT Scans). While the system is built to integrate with an external computer vision/ML pipeline, it currently simulates AI inference by attaching **Confidence Scores** (High/Medium/Low priority) and generating context-aware anomaly flags to assist doctors in triage.

3. **Secure Audit & Logging System:**
   Every sensitive action across the platform (logging in, finalizing a review, access denials) is persistently recorded in the `audit` app to ensure simulated **HIPAA Compliance** tracing. 

4. **Frontend Architecture:**
   The UI completely relies on fully responsive, utility-first **TailwindCSS** with dark-mode support and custom animations, all embedded within rich Django HTML templates for seamless server-side rendering.

### Application Topology (Apps)
- `accounts/` – Core authentication, role definitions, and access control decorators.
- `appointments/` – Logic for scheduling, doctor availability slots, and status management (Pending/Approved/Completed).
- `audit/` – Immutable system audit trails, metrics generation, global settings, and admin oversight views.
- `doctors/` – The Radiologist workflow: review queues, reporting analytics, performance metrics, and patient messaging.
- `patients/` – The Patient portal: upload pipelines, interactive appointment booking, feedback mechanisms, and chart tracking.
- `records/` – The backbone model for `MedicalRecord` storage, AI status tracking, and doctor review states.

---

## 🌟 Comprehensive Feature Breakdown

### 🧑‍⚕️ For Patients
The Patient Portal is designed to give users full transparency and control over their healthcare journey.
* **Scan Upload Pipeline:** Securely upload image files (or PDFs) of medical scans.
* **Live AI Processing Status:** Track exactly where their upload sits in the pipeline (Uploaded -> Processing -> Completed).
* **Interactive Scheduling:** Browse registered doctors and instantly book appointments based on real-time calculated slot availability.
* **Secure Messaging:** Send and receive secure messages directly with their healthcare providers. 
* **Feedback & Rating System:** Leave detailed feedback and start ratings (1-5) for doctors based on past appointments and interactions.

### 🩺 For Doctors (Radiologists/Specialists)
Doctors get an optimized dashboard built for triage, speed, and analytical insight.
* **AI-Triage Review Queue:** Scans are automatically flagged by the system as *Normal*, *Moderate*, or *High-Risk/Critical*. High-risk scans get prioritized UI indicators.
* **Medical Record Review:** Dedicated interfaces to examine uploaded scans, save review notes, request peer reviews, and finalize diagnoses.
* **Performance Reports & Analytics:** Generate 24h, 7-day, or 30-day productivity reports showing their throughput growth, approval rates, and department efficiency (CT vs MRI vs X-Ray).
* **Patient Feedback Dashboard:** Dedicated sidebar tab summarizing all patient reviews, ratings, and comments.
* **Integrated Inbox:** A consolidated view of all patient messages requiring attention.

### 🔐 For Administrators
Admins have access to overarching governance tools to keep the platform reliable.
* **Platform Overview:** Real-time metrics showing total patients, specialized doctors, processed scans, and operational compliance.
* **User Management:** A master list of all accounts. Admins can instantaneously suspend (block) or activate user accounts.
* **System Logs & Audit Trails:** Advanced queryable tables tracking `LOGIN`, `PERMISSION_DENIED`, `FINALIZE_REVIEW`, and more globally. Includes export functionally.
* **Global Feedback Oversight:** Capable of reading all feedback submitted platform-wide to monitor doctor performance and patient satisfaction.

---

## 🚀 Setup & Installation

Follow these steps to get CuraMind AI running on your local machine.

### Prerequisites
- Python 3.10+
- `pip` package manager

### 1. Clone the Repository
```powershell
git clone https://github.com/45Hitman18/CuraMind.git
cd CuraMind
```

### 2. Create and Activate a Virtual Environment
```powershell
# Create it
python -m venv .venv

# Activate it (Windows)
.\.venv\Scripts\Activate.ps1

# Activate it (Mac/Linux)
source .venv/bin/activate
```

### 3. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 4. Apply Database Migrations
CuraMind uses SQLite (`db.sqlite3`) tightly integrated with Django's ORM out-of-the-box.
```powershell
python manage.py makemigrations
python manage.py migrate
```

### 5. Create a Superuser (Admin)
To access the Admin panel, you will need a master account.
```powershell
python manage.py createsuperuser
```
*(Follow the prompt to set your Username, Email, and Password).*

### 6. Run the Development Server
```powershell
python manage.py runserver
```
The application will now be running actively. Navigate to `http://127.0.0.1:8000/` in your browser.

---

## 📁 File Storage Notes
- Uploaded patient medical scans and chat attachments are safely stored locally in the dynamically generated `media/` directory. 
- For production environments, it is highly recommended to configure an S3 bucket or equivalent secure blob storage inside `settings.py`.

## 🛠️ Tech Stack Quick-Glance
* **Backend:** Python, Django 4.2+
* **Frontend:** HTML5, TailwindCSS (CDN), Django HTML Templating
* **Database:** SQLite (Dev) / Ready for PostgreSQL (Prod)
* **Design Philosophy:** Glassmorphism, highly-responsive grid layouts, seamless UX.
