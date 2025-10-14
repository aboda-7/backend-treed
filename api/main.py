from fastapi import FastAPI, Request
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv
import json
import os

# --- LOAD ENV VARIABLES ---
load_dotenv() 

# --- INIT FASTAPI ---
app = FastAPI()

# --- CORS SETUP ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://tree-d-dashboard.vercel.app/",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- INIT FIREBASE ---
if not firebase_admin._apps:
    firebase_creds = os.getenv("FIREBASE_CREDENTIALS")
    if not firebase_creds:
        raise ValueError("Missing FIREBASE_CREDENTIALS environment variable!")

    cred_dict = json.loads(firebase_creds)
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ----------------------------- ROUTES -----------------------------

@app.get("/gettime")
def get_time():
    """Return current server time and date."""
    now = datetime.now()
    return {
        "current_time": now.strftime("%H:%M:%S"),
        "current_date": now.strftime("%Y-%m-%d"),
        "timestamp": now.isoformat()
    }

# --- stored_data = Type 1 ---
@app.post("/postdata")
async def post_data(request: Request):
    """Store or update device data in Firestore (collection: stored_data1)."""
    data = await request.json()
    device_id = data.get("id")

    if not device_id:
        return {"error": "Missing 'id' in data"}

    doc_ref = db.collection("stored_data1").document(device_id)
    doc_ref.set(data)

    return {"message": "Data stored successfully in stored_data1", "data": data}


@app.get("/getdata")
def get_data():
    """Return all data from Firestore (collection: stored_data2)."""
    docs = db.collection("stored_data2").stream()
    all_data = [doc.to_dict() for doc in docs]
    return {"stored_data": all_data}


# --- stored_data2 = Type 2 ---
@app.post("/poststoreddata")
async def post_stored_data(request: Request):
    """Store or update secondary data in Firestore (collection: stored_data2)."""
    data = await request.json()
    device_id = data.get("id")

    if not device_id:
        return {"error": "Missing 'id' in data"}

    doc_ref = db.collection("stored_data2").document(device_id)
    doc_ref.set(data)

    return {"message": "Data stored successfully in stored_data2", "data": data}


@app.get("/getstoreddata")
def get_stored_data():
    """Return all data from Firestore (collection: stored_data2)."""
    docs = db.collection("stored_data2").stream()
    all_data = [doc.to_dict() for doc in docs]
    return {"stored_data2": all_data}


