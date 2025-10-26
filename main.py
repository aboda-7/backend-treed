from fastapi import FastAPI, Request, Depends, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore, auth as firebase_auth
from dotenv import load_dotenv
import os, json, pathlib

# ----------------------------------------------------------------
#  --- LOAD ENV ---
# ----------------------------------------------------------------
load_dotenv()

# ----------------------------------------------------------------
#  --- INIT FASTAPI ---
# ----------------------------------------------------------------
app = FastAPI(title="Tree-D Backend", version="2.0")

# ----------------------------------------------------------------
#  --- CORS ---
# ----------------------------------------------------------------
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

# ----------------------------------------------------------------
#  --- INIT FIREBASE ---
# ----------------------------------------------------------------
if not firebase_admin._apps:
    firebase_creds = os.getenv("FIREBASE_CREDENTIALS")
    if not firebase_creds:
        raise ValueError("Missing FIREBASE_CREDENTIALS env variable!")
    cred_dict = json.loads(firebase_creds)
    cred = credentials.Certificate(cred_dict)
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ----------------------------------------------------------------
#  --- AUTH MIDDLEWARE (Firebase Token Check) ---
# ----------------------------------------------------------------
async def verify_firebase_token(authorization: str = Header(None)):
    """
    Verifies the Firebase ID token from the Authorization header.
    Expected format: 'Bearer <token>'
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token format")

    token = authorization.split("Bearer ")[1]

    try:
        decoded_token = firebase_auth.verify_id_token(token)
        return decoded_token  # includes uid, email, etc.
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid or expired token: {e}")

# ----------------------------------------------------------------
#  --- MUSEUM LOGIC ---
# ----------------------------------------------------------------
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

# Audio lengths in seconds for each artifact/language combo
# YOU NEED TO FILL THIS WITH YOUR ACTUAL AUDIO LENGTHS
AUDIO_LENGTHS = {
    "st1": {"ar": 10, "en": 110, "fr": 115, "sp": 118, "de": 112, "ja": 125, "ko": 122, "ru": 117, "nl": 113, "zh": 121},
    "st2": {"ar": 5, "en": 85, "fr": 88, "sp": 92, "de": 87, "ja": 95, "ko": 93, "ru": 89, "nl": 86, "zh": 94},
    "st3": {"ar": 10, "en": 110, "fr": 115, "sp": 118, "de": 112, "ja": 125, "ko": 122, "ru": 117, "nl": 113, "zh": 121},
    "st4": {"ar": 5, "en": 85, "fr": 88, "sp": 92, "de": 87, "ja": 95, "ko": 93, "ru": 89, "nl": 86, "zh": 94},
    "st5": {"ar": 10, "en": 110, "fr": 115, "sp": 118, "de": 112, "ja": 125, "ko": 122, "ru": 117, "nl": 113, "zh": 121},
    "st6": {"ar": 5, "en": 85, "fr": 88, "sp": 92, "de": 87, "ja": 95, "ko": 93, "ru": 89, "nl": 86, "zh": 94},
    "st7": {"ar": 10, "en": 110, "fr": 115, "sp": 118, "de": 112, "ja": 125, "ko": 122, "ru": 117, "nl": 113, "zh": 121},
    "st8": {"ar": 5, "en": 85, "fr": 88, "sp": 92, "de": 87, "ja": 95, "ko": 93, "ru": 89, "nl": 86, "zh": 94},
    "st9": {"ar": 10, "en": 110, "fr": 115, "sp": 118, "de": 112, "ja": 125, "ko": 122, "ru": 117, "nl": 113, "zh": 121},
    "st11": {"ar": 5, "en": 85, "fr": 88, "sp": 92, "de": 87, "ja": 95, "ko": 93, "ru": 89, "nl": 86, "zh": 94},
    "st12": {"ar": 10, "en": 110, "fr": 115, "sp": 118, "de": 112, "ja": 125, "ko": 122, "ru": 117, "nl": 113, "zh": 121},
    "st13": {"ar": 5, "en": 85, "fr": 88, "sp": 92, "de": 87, "ja": 95, "ko": 93, "ru": 89, "nl": 86, "zh": 94},
    "st14": {"ar": 5, "en": 85, "fr": 88, "sp": 92, "de": 87, "ja": 95, "ko": 93, "ru": 89, "nl": 86, "zh": 94},
    "st15": {"ar": 5, "en": 85, "fr": 88, "sp": 92, "de": 87, "ja": 95, "ko": 93, "ru": 89, "nl": 86, "zh": 94},
    "st16": {"ar": 5, "en": 85, "fr": 88, "sp": 92, "de": 87, "ja": 95, "ko": 93, "ru": 89, "nl": 86, "zh": 94},
    "st17": {"ar": 5, "en": 85, "fr": 88, "sp": 92, "de": 87, "ja": 95, "ko": 93, "ru": 89, "nl": 86, "zh": 94},
    "st18": {"ar": 5, "en": 85, "fr": 88, "sp": 92, "de": 87, "ja": 95, "ko": 93, "ru": 89, "nl": 86, "zh": 94},
    "st19": {"ar": 5, "en": 85, "fr": 88, "sp": 92, "de": 87, "ja": 95, "ko": 93, "ru": 89, "nl": 86, "zh": 94},
    "st21": {"ar": 5, "en": 85, "fr": 88, "sp": 92, "de": 87, "ja": 95, "ko": 93, "ru": 89, "nl": 86, "zh": 94},
    "st22": {"ar": 5, "en": 85, "fr": 88, "sp": 92, "de": 87, "ja": 95, "ko": 93, "ru": 89, "nl": 86, "zh": 94},
    "st23": {"ar": 5, "en": 85, "fr": 88, "sp": 92, "de": 87, "ja": 95, "ko": 93, "ru": 89, "nl": 86, "zh": 94},
    "st24": {"ar": 5, "en": 85, "fr": 88, "sp": 92, "de": 87, "ja": 95, "ko": 93, "ru": 89, "nl": 86, "zh": 94},
    
}

# ----------------------------------------------------------------
#  --- ROUTES ---
# ----------------------------------------------------------------

@app.get("/gettime")
def get_time():
    now = datetime.now()
    return {
        "current_time": now.strftime("%H:%M:%S"),
        "current_date": now.strftime("%Y-%m-%d"),
        "timestamp": now.isoformat()
    }


@app.post("/postdata")
async def post_data(request: Request):
    data = await request.json()
    raw_device_id = data.get("id")
    if not raw_device_id:
        return {"error": "Missing 'id' in data"}

    device_id = str(raw_device_id).strip().lower()
    statue_name = (data.get("statue") or "").strip()
    language_name = (data.get("language") or "").strip()
    explicit_event = (data.get("event") or data.get("type") or "").strip().lower()

    # Store raw data
    db.collection("stored_data1").document(device_id).set(data)
    
    lang_key = LANG_TO_KEY.get(language_name)
    slot = STATUE_TO_SLOT.get(statue_name)

    if explicit_event in {"statue", "language"}:
        event_type = explicit_event
    else:
        event_type = "statue" if slot else ("language" if lang_key else None)

    doc_ref = db.collection("stored_data2").document(device_id)
    
    # Store individual scan event for completion tracking
    if event_type == "statue" and slot and lang_key:
        # Increment counter (existing logic)
        doc_ref.set({"artifacts": {slot: {lang_key: firestore.Increment(1)}}}, merge=True)
        
        # NEW: Store individual scan event with timestamp
        scan_event = {
            "device_id": device_id,
            "artifact": slot,
            "language": lang_key,
            "timestamp": firestore.SERVER_TIMESTAMP,
            "statue_name": statue_name,
            "language_name": language_name
        }
        db.collection("scan_events").add(scan_event)
        
        return {"message": f"Incremented artifacts.{slot}.{lang_key}"}

    if event_type == "language" and lang_key:
        doc_ref.set({"language": {lang_key: firestore.Increment(1)}}, merge=True)
        return {"message": f"Incremented language.{lang_key}"}

    return {"message": "No increment performed"}


@app.get("/getdata")
def get_data(user=Depends(verify_firebase_token)):
    """
    Secure endpoint — requires valid Firebase auth token.
    """
    docs = db.collection("stored_data2").stream()
    all_data = [{"id": d.id, **(d.to_dict() or {})} for d in docs]
    return {"stored_data": all_data, "user_uid": user["uid"]}


@app.get("/analytics/completion-rates")
def get_completion_rates(user=Depends(verify_firebase_token)):
    """
    Calculate completion rates for each artifact/language combo.
    Returns % of users who listened to 90%+ of the audio.
    """
    
    print("\n" + "="*80)
    print("🔍 STARTING COMPLETION RATE CALCULATION")
    print("="*80)
    
    # Get all scan events ordered by timestamp
    scan_events = db.collection("scan_events").order_by("timestamp").stream()
    
    # Group scans by device_id
    device_scans = {}
    total_events = 0
    for event in scan_events:
        event_data = event.to_dict()
        device_id = event_data.get("device_id")
        total_events += 1
        
        if device_id not in device_scans:
            device_scans[device_id] = []
        
        device_scans[device_id].append({
            "artifact": event_data.get("artifact"),
            "language": event_data.get("language"),
            "timestamp": event_data.get("timestamp"),
        })
    
    print(f"\n📊 Total scan events found: {total_events}")
    print(f"👥 Unique devices: {len(device_scans)}")
    
    # Calculate completion rates per artifact/language
    completion_stats = {}
    
    for device_id, scans in device_scans.items():
        print(f"\n{'='*60}")
        print(f"📱 Device: {device_id}")
        print(f"   Total scans: {len(scans)}")
        
        for i in range(len(scans) - 1):
            current_scan = scans[i]
            next_scan = scans[i + 1]
            
            artifact = current_scan["artifact"]
            language = current_scan["language"]
            
            print(f"\n   Scan {i+1} -> {i+2}:")
            print(f"   Current: {artifact} ({language})")
            print(f"   Next: {next_scan['artifact']} ({next_scan['language']})")
            
            # Skip if we don't have audio length data
            if artifact not in AUDIO_LENGTHS or language not in AUDIO_LENGTHS[artifact]:
                print(f"   ⚠️  SKIPPED - No audio length data for {artifact}_{language}")
                continue
            
            audio_length = AUDIO_LENGTHS[artifact][language]
            threshold = audio_length * 0.9  # 90% threshold
            
            # Calculate time between scans
            time_diff = (next_scan["timestamp"] - current_scan["timestamp"]).total_seconds()
            
            print(f"   ⏱️  Audio length: {audio_length}s")
            print(f"   ⏱️  90% threshold: {threshold}s")
            print(f"   ⏱️  Time between scans: {time_diff}s")
            
            # Initialize stats for this artifact/language combo
            key = f"{artifact}_{language}"
            if key not in completion_stats:
                completion_stats[key] = {
                    "artifact": artifact,
                    "language": language,
                    "total_listens": 0,
                    "completed_listens": 0,
                    "audio_length": audio_length
                }
            
            completion_stats[key]["total_listens"] += 1
            
            # Check if they listened to 90%+ of the audio
            if time_diff >= threshold:
                completion_stats[key]["completed_listens"] += 1
                print(f"   ✅ COMPLETED (time >= threshold)")
            else:
                print(f"   ❌ NOT COMPLETED (time < threshold)")
                print(f"   📉 Listened to only {(time_diff/audio_length)*100:.1f}% of audio")
    
    # Calculate completion rate percentages
    results = []
    for key, stats in completion_stats.items():
        completion_rate = 0
        if stats["total_listens"] > 0:
            completion_rate = (stats["completed_listens"] / stats["total_listens"]) * 100
        
        results.append({
            "artifact": stats["artifact"],
            "language": stats["language"],
            "total_listens": stats["total_listens"],
            "completed_listens": stats["completed_listens"],
            "completion_rate": round(completion_rate, 2),
            "audio_length_seconds": stats["audio_length"]
        })
    
    # Sort by completion rate descending
    results.sort(key=lambda x: x["completion_rate"], reverse=True)
    
    return {
        "completion_rates": results,
        "total_artifacts_tracked": len(results),
        "user_uid": user["uid"]
    }


@app.get("/analytics/completion-summary")
def get_completion_summary(user=Depends(verify_firebase_token)):
    """
    Get overall completion rate across all artifacts/languages.
    """
    completion_data = get_completion_rates(user)
    
    if not completion_data["completion_rates"]:
        return {
            "overall_completion_rate": 0,
            "total_listens": 0,
            "completed_listens": 0,
            "user_uid": user["uid"]
        }
    
    total_listens = sum(item["total_listens"] for item in completion_data["completion_rates"])
    completed_listens = sum(item["completed_listens"] for item in completion_data["completion_rates"])
    
    overall_rate = (completed_listens / total_listens * 100) if total_listens > 0 else 0
    
    return {
        "overall_completion_rate": round(overall_rate, 2),
        "total_listens": total_listens,
        "completed_listens": completed_listens,
        "by_artifact": completion_data["completion_rates"],
        "user_uid": user["uid"]
    }


@app.post("/migrate_languages_to_language")
def migrate_languages_to_language():
    changed = []
    for snap in db.collection("stored_data2").stream():
        data = snap.to_dict() or {}
        if "languages" in data and isinstance(data["languages"], dict):
            ref = db.collection("stored_data2").document(snap.id)
            ref.set({"language": data["languages"]}, merge=True)
            ref.update({"languages": firestore.DELETE_FIELD})
            changed.append(snap.id)
    return {"migrated_docs": changed}


# ----------------------------------------------------------------
#  --- SERVER RUN ---
# ----------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn
    here = pathlib.Path(__file__).parent.resolve()
    os.chdir(here)
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=[str(here)],
    )