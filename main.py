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
        "https://tree-d-dashboard.vercel.app",
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

# ----------------------------- CONFIG / MAPPINGS -----------------------------
STATUE_TO_SLOT = {
    "Ain Ghazal": "st1",
    "Atargatis": "st2",
    "Misha Stele": "st3",
    "roman": "st4",
    "Jordan 1": "st5",
    "Jordan 2": "st6",
    "Jordan 3": "st7",
    "Jordan 4": "st8",
    "church": "st9",
    "boat": "st11",
    "tree": "st12",
    "lion": "st13",
    "bardi": "st14",
    "Imhotep": "st15",
    "Osiris": "st16",
    "Tetisheri Stela": "st17",
    "Ain Ghazal 2": "st18",
    "Roman Theatre 2": "st19",
    "Statue of Liberty": "st21",
    "Rosetta Stone": "st22",
    "Van Gogh Self Portrait": "st23",
    "Mona Lisa": "st24",
}

LANG_TO_KEY = {
    "Arabic": "ar",
    "English": "en",
    "French": "fr",
    "Spanish": "sp",
    "German": "de",
    "Japanese": "ja",
    "Korean": "ko",
    "Russian": "ru",
    "Dutch": "nl",
    "Chinese": "zh",
}

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


@app.post("/postdata")
async def post_data(request: Request):
    """
    Store raw scan in stored_data1, then increment ONE precise counter in stored_data2.
    """

    def _nullish(val):
        if val is None:
            return None
        s = str(val).strip().lower()
        return None if s in {"", "null", "none", "n/a", "na", "undefined"} else val

    data = await request.json()

    raw_device_id = data.get("id")
    if not raw_device_id:
        return {"error": "Missing 'id' in data"}

    device_id = str(raw_device_id).strip().lower()
    statue_name = _nullish(data.get("statue"))
    language_name = _nullish(data.get("language"))
    explicit_event = (data.get("event") or data.get("type") or "").strip().lower()

    print("\n[POSTDATA RECEIVED]", json.dumps(data, indent=2))

    db.collection("stored_data1").document(device_id).set(data)

    lang_key = LANG_TO_KEY.get(language_name) if language_name else None
    slot = STATUE_TO_SLOT.get(statue_name) if statue_name else None

    if explicit_event in {"statue", "language"}:
        event_type = explicit_event
    else:
        event_type = "statue" if slot else ("language" if lang_key else None)

    if not event_type:
        print("⚠️ Could not infer event type.")
        return {
            "message": "Stored raw scan; could not infer event type. No counters incremented.",
            "data": data,
        }

    doc_ref = db.collection("stored_data2").document(device_id)

    if event_type == "statue":
        if not slot:
            print(f"⚠️ Statue '{statue_name}' not mapped to a slot.")
            return {
                "message": "Stored raw scan; statue unmapped. No counters incremented.",
                "data": data,
            }
        if not lang_key:
            print(f"⚠️ Missing/unknown language '{language_name}' on statue read.")
            return {
                "message": "Stored raw scan; language unknown. No counters incremented.",
                "data": data,
            }

        doc_ref.set({"artifacts": {slot: {lang_key: firestore.Increment(1)}}}, merge=True)
        print(f"✅ Incremented: artifacts.{slot}.{lang_key}")
        return {
            "message": f"Stored; incremented artifacts.{slot}.{lang_key}",
            "event_type": "statue",
            "device_id": device_id,
            "incremented_paths": [f"artifacts.{slot}.{lang_key}"],
        }

    if not lang_key:
        print(f"⚠️ Unknown language '{language_name}' — no increments performed.")
        return {
            "message": "Stored raw scan; unknown language. No counters incremented.",
            "data": data,
        }

    doc_ref.set({"language": {lang_key: firestore.Increment(1)}}, merge=True)
    print(f"✅ Incremented: language.{lang_key}")
    return {
        "message": f"Stored; incremented language.{lang_key}",
        "event_type": "language",
        "device_id": device_id,
        "incremented_paths": [f"language.{lang_key}"],
    }


@app.get("/getdata")
def get_data():
    """Return all data from Firestore (collection: stored_data2)."""
    docs = db.collection("stored_data2").stream()
    all_data = [{"id": d.id, **(d.to_dict() or {})} for d in docs]
    return {"stored_data": all_data}


@app.post("/poststoreddata")
async def post_stored_data(request: Request):
    """Dummy endpoint for testing or debugging."""
    data = await request.json()
    device_id = data.get("id")

    print("\n[POSTSTOREDDATA RECEIVED]", json.dumps(data, indent=2))

    if not device_id:
        return {"error": "Missing 'id' in data"}

    print(f"🧩 Dummy endpoint hit for device '{device_id}'.")
    return {"message": "Dummy endpoint: data received but not stored.", "data": data}


@app.get("/getstoreddata")
def get_stored_data():
    """Return all data from Firestore (collection: stored_data2)."""
    docs = db.collection("stored_data2").stream()
    all_data = [{"id": d.id, **(d.to_dict() or {})} for d in docs]
    return {"stored_data2": all_data}


@app.post("/migrate_languages_to_language")
def migrate_languages_to_language():
    """Migrate old 'languages' field into 'language' field."""
    changed = []
    for snap in db.collection("stored_data2").stream():
        data = snap.to_dict() or {}
        if "languages" in data and isinstance(data["languages"], dict):
            ref = db.collection("stored_data2").document(snap.id)
            ref.set({"language": data["languages"]}, merge=True)
            ref.update({"languages": firestore.DELETE_FIELD})
            changed.append(snap.id)
    return {"migrated_docs": changed}
