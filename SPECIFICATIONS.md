This document outlines the software specifications, architecture, and business plan for **GoStayPro**. It serves as a living document reflecting the current state and future direction of the project.

***

### **Project Vision:**

You are an expert software architect and product manager. Your task is to build and maintain a comprehensive plan for the web application **"GoStayPro"**.

**GoStayPro** is a room management and booking application designed specifically for small homestay, guesthouse, and B&B owners. The core philosophy is simplicity, affordability, and a powerful, visually-driven calendar interface. The application will be a multi-tenant, subscription-based service.

---

### **1. Business Idea & Value Proposition**

* **Problem:** Small homestay owners often rely on cumbersome spreadsheets, paper calendars, or expensive, overly complex Property Management Systems (PMS). They need a simple, affordable, and centralized way to view room availability, manage bookings, and track guest information.
* **Solution:** GoStayPro provides a clean, calendar-first web application that focuses exclusively on booking management. It's built for low operational costs, allowing for an affordable subscription model.
* **Target Audience:** Owners of small hospitality businesses (1-15 rooms), such as homestays, guesthouses, bed & breakfasts, and boutique inns.
* **Monetization:** A tiered monthly/annual subscription model. For example:
    * **Free Tier:** 1 user, up to 2 rooms.
    * **Basic Tier:** Up to 5 users, up to 10 rooms.
    * **Pro Tier:** Unlimited users, unlimited rooms, plus premium features (e.g., reporting, invoicing).

### **2. MVP (Minimum Viable Product) Features**

Describe the essential features required to launch the first version of GoStayPro.

* **Admin Superuser:**
    * Dashboard to view all registered businesses/users.
    * Ability to manage subscription plans.
    * **Status: Partially Implemented.** The system attempts to send an admin notification on new user registration, but this feature is currently incomplete due to a missing email template (`emails/admin_new_user_notification.html`).
* **Business/Homestay Owner (Tenant):**
    * **Onboarding:** Simple sign-up and creation of their homestay profile (name, address, etc.).
    * **Room Management:** CRUD (Create, Read, Update, Delete) functionality for rooms (e.g., "Queen Room," "Bungalow"). Each room should have attributes like name, capacity, and a default rate.
    * **User Management:** The owner can invite/add staff members (with limited permissions, e.g., cannot delete rooms or manage subscriptions) to their account.
* **Core Feature: Calendar Management:** This is the heart of the application.
    * **Visual Grid View:** A primary dashboard showing a grid with rooms listed vertically on the Y-axis and days of the month horizontally on the X-axis.
    * **Booking Creation:** Clicking and dragging across dates for a specific room should open a modal form to create a new booking.
    * **Booking Details:** The booking form should capture essential information: Guest Name, Contact Info (phone/email), Number of Guests, Agreed Price, and Booking Status.
    * **Booking Status Visualization:** Bookings on the calendar must be color-coded based on their status (e.g., Yellow for 'Tentative', Green for 'Confirmed', Blue for 'Checked-in', Grey for 'Checked-out').
    * **Dynamic Updates (HTMX):** All calendar interactions—creating, updating, or changing the status of a booking—should happen without a full page reload.
    * **Conflict Detection:** The system must prevent double-booking a room for overlapping dates.

### **3. High-Level Architecture**

Provide a simple diagram or description of the overall system architecture.

* **Frontend:** A browser-based interface using standard HTML5 and CSS. All dynamic functionality is powered by HTMX, which makes server requests and swaps HTML content directly in the DOM. No complex JavaScript framework (like React/Vue) is needed for the MVP.
* **Backend:** A monolithic Python web application. This single service will handle user authentication, business logic, database interactions, and rendering of HTML templates (using Jinja2).
* **Database:** A single PostgreSQL database to store all application data, including user info, subscriptions, rooms, and bookings.
* **Deployment Environment:** The entire application (Python backend and database) will be hosted on Railway.
* **Status:** The core architecture is in place and running via Docker Compose. Static file serving for CSS needs verification (`404 Not Found` error observed in logs).

### **4. Detailed Architecture & Component Breakdown**

Break down the Python backend into logical modules or components.

* **Web Framework:** **FastAPI** (preferred for its modern features and performance) or **Flask** (classic simplicity).
* **Web Server:** **Uvicorn** (for FastAPI) or **Gunicorn** (for Flask).
* **Templating:** **Jinja2** for rendering HTML templates on the server.
* **Database Interaction:** **SQLAlchemy** ORM for a structured and safe way to interact with the PostgreSQL database. Use **Alembic** for managing database schema migrations.
* **Authentication:** A simple session-based authentication system. After login, a secure, server-signed cookie is stored in the user's browser.
* **Core Modules (e.g., FastAPI Routers or Flask Blueprints):**
    * `auth_views`: Handles user registration, login, logout, password management, and email verification.
    * `app_views`: Manages the main application logic, including the dashboard and property/room CRUD operations.
    * `calendar_htmx_views`: Contains all the endpoints that respond specifically to HTMX requests. These endpoints will handle fetching calendar data, showing booking forms, saving bookings, and returning HTML fragments to update the UI dynamically. For example: `/htmx/calendar/view`, `/htmx/booking/new`, `/htmx/booking/save`.
    * `admin_views`: Contains routes for the superuser admin panel.

### **5. Data Structure and Relations**

Define the core database tables and their relationships using SQL-like definitions or an ERD description.

* **`users`**:
    * `id` (PK)
    * `email` (UNIQUE)
    * `hashed_password`
    * `is_verified` (BOOLEAN, default: false)
    * `role` (e.g., 'admin', 'owner', 'staff')
    * `homestay_id` (FK to `homestays`, nullable)
    * `created_at`

* **`subscriptions`**:
    * `id` (PK)
    * `owner_id` (FK to `users`, UNIQUE)
    * `plan_name` (e.g., 'free', 'basic', 'pro')
    * `status` (e.g., 'active', 'cancelled', 'expired')
    * `expires_at`

* **`homestays`**:
    * `id` (PK)
    * `owner_id` (FK to `users`)
    * `name`
    * `address`
    * `created_at`

* **`rooms`**:
    * `id` (PK)
    * `homestay_id` (FK to `homestays`)
    * `name` (e.g., "Deluxe Double Room")
    * `capacity` (INTEGER)
    * `default_rate` (DECIMAL)

* **`bookings`**:
    * `id` (PK)
    * `room_id` (FK to `rooms`)
    * `guest_name`
    * `guest_contact`
    * `start_date` (DATE)
    * `end_date` (DATE)
    * `price` (DECIMAL)
    * `status` (ENUM: 'tentative', 'confirmed', 'checked_in', 'checked_out', 'cancelled')
    * `created_by` (FK to `users`)

**Relationships:**
* A `User` (with role 'owner') has one `Homestay` and one `Subscription`.
* A `Homestay` has many `Rooms` and many `Users` (staff).
* A `Room` has many `Bookings`. A `Booking` is created by a `User`.

### **6. Minimal Technology Stack**

List the specific technologies and libraries to be used.

* **Backend Language:** Python 3.10+
* **Web Framework:** FastAPI with Uvicorn
* **Database:** PostgreSQL
* **ORM:** SQLAlchemy 2.0 with Alembic for migrations
* **Frontend Interactivity:** HTMX 1.9+
* **CSS Framework:** Tailwind CSS (for rapid, utility-first styling)
* **Templating:** Jinja2
* **Authentication:** `passlib` with `bcrypt` for password hashing.
* **Deployment:** Docker, Docker Compose. (Initially planned for Railway, currently running locally with Docker).