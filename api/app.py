#!/usr/bin/env python3
"""
SailingSA API - User verification and profile management
"""
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import Optional
import mysql.connector
from mysql.connector import Error
import hashlib
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import os

app = FastAPI(title="SailingSA API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://timadvisor.co.za", "https://www.timadvisor.co.za", "https://sailingsa.co.za"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'sailingsa_user',
    'password': 'SailSA2026SecurePass',
    'database': 'sailingsa_db'
}

# Email configuration (update with your SMTP settings)
SMTP_CONFIG = {
    'host': 'smtp.gmail.com',  # Update with your SMTP server
    'port': 587,
    'username': os.getenv('SMTP_USER', 'your-email@gmail.com'),
    'password': os.getenv('SMTP_PASS', 'your-app-password')
}

def get_db_connection():
    """Get database connection"""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except Error as e:
        print(f"Database connection error: {e}")
        raise HTTPException(status_code=500, detail="Database connection failed")

def hash_password(password: str) -> str:
    """Hash password using SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()

def generate_verification_token() -> str:
    """Generate secure verification token"""
    return secrets.token_urlsafe(32)

def send_verification_email(email: str, token: str, first_name: str):
    """Send verification email"""
    try:
        verification_url = f"https://sailingsa.co.za/verify?token={token}"
        
        msg = MIMEMultipart()
        msg['From'] = SMTP_CONFIG['username']
        msg['To'] = email
        msg['Subject'] = "Verify Your SailingSA Account"
        
        body = f"""
        Hello {first_name},
        
        Thank you for registering with SailingSA!
        
        Please verify your email address by clicking the link below:
        {verification_url}
        
        This link will expire in 24 hours.
        
        If you did not create this account, please ignore this email.
        
        Best regards,
        SailingSA Team
        """
        
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(SMTP_CONFIG['host'], SMTP_CONFIG['port'])
        server.starttls()
        server.login(SMTP_CONFIG['username'], SMTP_CONFIG['password'])
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Email sending error: {e}")
        return False

# Pydantic models
class SearchRequest(BaseModel):
    search_type: str  # 'sasid' or 'name'
    sas_id: Optional[str] = None
    first_name: Optional[str] = None
    surname: Optional[str] = None

class UserRegistration(BaseModel):
    sas_id: str
    email: EmailStr
    contact_number: str
    password: str

class VerifyRequest(BaseModel):
    token: str

# API endpoints
@app.get("/")
def root():
    return {"status": "SailingSA API is running"}

@app.get("/api/autocomplete/names")
def get_autocomplete_names():
    """Get common first names and surnames for autocomplete"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get top 50 most common first names and surnames
        cursor.execute("""
            SELECT DISTINCT first_name 
            FROM sa_id_table 
            ORDER BY first_name 
            LIMIT 50
        """)
        first_names = [row[0] for row in cursor.fetchall()]
        
        cursor.execute("""
            SELECT DISTINCT surname 
            FROM sa_id_table 
            ORDER BY surname 
            LIMIT 50
        """)
        surnames = [row[0] for row in cursor.fetchall()]
        
        return {"firstNames": first_names, "surnames": surnames}
    except Error as e:
        return {"firstNames": [], "surnames": []}
    finally:
        cursor.close()
        conn.close()

@app.post("/api/search")
def search_user(request: SearchRequest):
    """Search for user by SAS ID or name (exact match only)"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        if request.search_type == 'sasid':
            if not request.sas_id:
                raise HTTPException(status_code=400, detail="SAS ID required")
            query = "SELECT id, sas_id, first_name, surname FROM sa_id_table WHERE sas_id = %s"
            cursor.execute(query, (request.sas_id,))
        else:
            if not request.first_name or not request.surname:
                raise HTTPException(status_code=400, detail="First name and surname required")
            query = "SELECT id, sas_id, first_name, surname FROM sa_id_table WHERE LOWER(first_name) = LOWER(%s) AND LOWER(surname) = LOWER(%s)"
            cursor.execute(query, (request.first_name, request.surname))
        
        results = cursor.fetchall()
        return {"results": results, "count": len(results)}
    except Error as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        cursor.close()
        conn.close()

@app.post("/api/register")
def register_user(user: UserRegistration):
    """Register new user and send verification email"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Check if SAS ID exists
        cursor.execute("SELECT id, first_name, surname FROM sa_id_table WHERE sas_id = %s", (user.sas_id,))
        sa_record = cursor.fetchone()
        if not sa_record:
            raise HTTPException(status_code=404, detail="SAS ID not found in database")
        
        # Check if email already exists
        cursor.execute("SELECT id FROM users WHERE email = %s", (user.email,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Email already registered")
        
        # Generate verification token
        token = generate_verification_token()
        token_expires = datetime.now() + timedelta(hours=24)
        password_hash = hash_password(user.password)
        
        # Insert user
        cursor.execute("""
            INSERT INTO users (sas_id, first_name, surname, email, contact_number, password_hash, verification_token, token_expires)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (user.sas_id, sa_record[1], sa_record[2], user.email, user.contact_number, password_hash, token, token_expires))
        
        conn.commit()
        user_id = cursor.lastrowid
        
        # Send verification email
        if send_verification_email(user.email, token, sa_record[1]):
            return {"success": True, "message": "Registration successful. Please check your email for verification."}
        else:
            return {"success": True, "message": "Registration successful, but email verification failed. Please contact support."}
            
    except HTTPException:
        raise
    except Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        cursor.close()
        conn.close()

@app.post("/api/verify")
def verify_email(request: VerifyRequest):
    """Verify user email with token"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT id, email FROM users 
            WHERE verification_token = %s 
            AND token_expires > NOW() 
            AND email_verified = FALSE
        """, (request.token,))
        
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=400, detail="Invalid or expired verification token")
        
        # Update verification status
        cursor.execute("UPDATE users SET email_verified = TRUE, verification_token = NULL WHERE id = %s", (user[0],))
        conn.commit()
        
        return {"success": True, "message": "Email verified successfully"}
    except HTTPException:
        raise
    except Error as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
