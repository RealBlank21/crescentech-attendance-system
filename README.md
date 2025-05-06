# Crescentech Attendance System

A web-based attendance management app created for Crescentech IT Solutions and Services during my internship from 6 January 2025 to 31 May 2025, built with Flask to track employee attendance, manage leaves, and monitor working hours.

## Features

- **User Authentication**
  - Secure login with JWT tokens
  - Role-based access control (Admin/Staff)
  - 90-day session persistence

- **Staff Dashboard**
  - Time in/out tracking
  - Daily attendance notes
  - Leave management
  - Time balance tracking
  - Timesheet history with date filtering

- **Admin Dashboard**
  - Real-time staff attendance overview
  - Leave request management
  - Working hours configuration
  - Staff time balance monitoring
  - User management (Add/Delete staff)

- **Leave Management**
  - Multiple leave types (Medical, Vacation, Personal)
  - Document upload support
  - Leave approval workflow
  - Automatic timesheet integration for approved leaves

## Tech Stack

- **Backend**: Python / Flask  
- **Database**: MySQL  
- **Authentication**: JWT + bcrypt  
- **Frontend**: HTML / CSS + JavaScript  
- **Container**: Docker  

## Prerequisites

- Python 3.11+
- MySQL 8.0+
- Docker (optional)
