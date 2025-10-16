from fastapi import FastAPI, Request
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv
import json
import os
import pathlib

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

# ----------------------------- CONFIG / MAPPINGS -----------------------------
# Map device “statue” names (from your serial switch) to st1..st24
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
    # case 10 was not listed in your switch
    "boat": "st11",
    "tree": "st12",
    "lion": "st13",
    "bardi": "st14",
    "Imhotep": "st15",
    "Osiris": "st16",
    "Tetisheri Stela": "st17",
    "Ain Ghazal 2": "st18",
    "Roman Theatre 2": "st19",
    # case 20 was not listed in your switch
    "Statue of Liberty": "st21",
    "Rosetta Stone": "st22",
    "Van Gogh Self Portrait": "st23",
    "Mona Lisa": "st24",
}

# Map human language names from the device to your keys
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


# --- stored_data = Type 1 ---
@app.post("/postdata")
async def post_data(request: Request):
    """
    Store raw scan in stored_data1, then increment ONE precise counter in stored_data2,
    scoped by device_id (normalized to lowercase):

      - Statue read  -> ONLY increment artifacts.<slot>.<lang>
      - Language read -> ONLY increment language.<lang>   (note: 'language' singular)

    Never increment both on the same request.

    Optional: device can send `event` or `type` as "statue" | "language".
    If absent, we infer: presence of 'statue' => statue read; else if language present => language read.
    """

    # --- Helper for cleaning null-like values ---
    def _nullish(val):
        if val is None:
            return None
        s = str(val).strip().lower()
        return None if s in {"", "null", "none", "n/a", "na", "undefined"} else val

    # --- Parse incoming JSON ---
    data = await request.json()

    raw_device_id = data.get("id")
    if not raw_device_id:
        return {"error": "Missing 'id' in data"}

    # Normalize device id to avoid Es33 vs es33 splits
    device_id = str(raw_device_id).strip().lower()

    # Treat "NULL", "", etc. as None
    statue_name = _nullish(data.get("statue"))
    language_name = _nullish(data.get("language"))
    explicit_event = (data.get("event") or data.get("type") or "").strip().lower()

    print("\n[POSTDATA RECEIVED]", json.dumps(data, indent=2))

    # Keep a raw copy (does not affect aggregates)
    db.collection("stored_data1").document(device_id).set(data)

    # Resolve mappings
    lang_key = LANG_TO_KEY.get(language_name) if language_name else None
    slot = STATUE_TO_SLOT.get(statue_name) if statue_name else None

    # Decide event type
    if explicit_event in {"statue", "language"}:
        event_type = explicit_event
    else:
        # Infer: if statue is missing/null, it's a language read
        event_type = "statue" if slot else ("language" if lang_key else None)

    if not event_type:
        print("⚠️ Unable to infer event type (need 'statue' or 'language'). No counters incremented.\n")
        return {
            "message": "Stored raw scan; could not infer event type. No counters incremented.",
            "data": data,
        }

    doc_ref = db.collection("stored_data2").document(device_id)

    # --- Statue read ---
    if event_type == "statue":
        if not slot:
            print(f"⚠️ Statue '{statue_name}' not mapped to a slot — no increments performed\n")
            return {
                "message": "Stored raw scan; statue unmapped. No counters incremented.",
                "data": data,
            }
        if not lang_key:
            print(f"⚠️ Missing/unknown language '{language_name}' on statue read — no increments performed\n")
            return {
                "message": "Stored raw scan; language unknown/missing for statue read. No counters incremented.",
                "data": data,
            }

        # ✅ nested write (no dotted literal keys)
        doc_ref.set({"artifacts": {slot: {lang_key: firestore.Increment(1)}}}, merge=True)

        print(f"✅ Incremented for device '{device_id}': artifacts.{slot}.{lang_key} +1\n")
        return {
            "message": f"Stored; incremented artifacts.{slot}.{lang_key}",
            "event_type": "statue",
            "device_id": device_id,
            "incremented_paths": [f"artifacts.{slot}.{lang_key}"],
        }

    # --- Language read ---
    if not lang_key:
        print(f"⚠️ Unknown language '{language_name}' — no increments performed\n")
        return {
            "message": "Stored raw scan; unknown language. No counters incremented.",
            "data": data,
        }

    # ✅ nested write (creates the 'language' map if it doesn't exist)
    doc_ref.set({"language": {lang_key: firestore.Increment(1)}}, merge=True)

    print(f"✅ Incremented for device '{device_id}': language.{lang_key} +1\n")
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


# --- stored_data2 = Type 2 ---
@app.post("/poststoreddata")
async def post_stored_data(request: Request):
    """
    Dummy endpoint for testing or debugging.
    Does NOT write to Firestore — only prints and confirms receipt.
    """
    data = await request.json()
    device_id = data.get("id")

    print("\n[POSTSTOREDDATA RECEIVED]", json.dumps(data, indent=2))

    if not device_id:
        print("⚠️ Missing 'id' in data — no action taken.\n")
        return {"error": "Missing 'id' in data"}

    print(f"🧩 Dummy endpoint hit for device '{device_id}'. No Firestore writes performed.\n")

    return {
        "message": "Dummy endpoint: data received but not stored.",
        "data": data,
    }


@app.get("/getstoreddata")
def get_stored_data():
    """Return all data from Firestore (collection: stored_data2)."""
    docs = db.collection("stored_data2").stream()
    all_data = [{"id": d.id, **(d.to_dict() or {})} for d in docs]
    return {"stored_data2": all_data}


# ----------------------------- (OPTIONAL) ONE-TIME MIGRATOR -----------------------------
# If you previously wrote a 'languages' map (plural) and want to move it into the new
# 'language' map (singular), you can run this once to migrate and then delete 'languages'.
@app.post("/migrate_languages_to_language")
def migrate_languages_to_language():
    changed = []
    for snap in db.collection("stored_data2").stream():
        data = snap.to_dict() or {}
        if "languages" in data and isinstance(data["languages"], dict):
            ref = db.collection("stored_data2").document(snap.id)
            # merge old 'languages' into new 'language'
            ref.set({"language": data["languages"]}, merge=True)
            # delete old field
            ref.update({"languages": firestore.DELETE_FIELD})
            changed.append(snap.id)
    return {"migrated_docs": changed}


# --- RUN APP ---
if __name__ == "__main__":
    import uvicorn

    here = pathlib.Path(__file__).parent.resolve()
    os.chdir(here)

    module_name = pathlib.Path(__file__).stem
    uvicorn.run(
        f"{module_name}:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=[str(here)],
    )
