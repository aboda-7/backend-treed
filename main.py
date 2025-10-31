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
    "st15": {"ar": 10, "en": 85, "fr": 88, "sp": 92, "de": 87, "ja": 95, "ko": 93, "ru": 89, "nl": 86, "zh": 94},
    "st16": {"ar": 5, "en": 85, "fr": 88, "sp": 92, "de": 87, "ja": 95, "ko": 93, "ru": 89, "nl": 86, "zh": 94},
    "st17": {"ar": 5, "en": 85, "fr": 88, "sp": 92, "de": 87, "ja": 95, "ko": 93, "ru": 89, "nl": 86, "zh": 94},
    "st18": {"ar": 5, "en": 85, "fr": 88, "sp": 92, "de": 87, "ja": 95, "ko": 93, "ru": 89, "nl": 86, "zh": 94},
    "st19": {"ar": 5, "en": 85, "fr": 88, "sp": 92, "de": 87, "ja": 95, "ko": 93, "ru": 89, "nl": 86, "zh": 94},
    "st21": {"ar": 5, "en": 85, "fr": 88, "sp": 92, "de": 87, "ja": 95, "ko": 93, "ru": 89, "nl": 86, "zh": 94},
    "st22": {"ar": 5, "en": 85, "fr": 88, "sp": 92, "de": 87, "ja": 95, "ko": 93, "ru": 89, "nl": 86, "zh": 94},
    "st23": {"ar": 5, "en": 85, "fr": 88, "sp": 92, "de": 87, "ja": 95, "ko": 93, "ru": 89, "nl": 86, "zh": 94},
    "st24": {"ar": 10, "en": 5, "fr": 88, "sp": 92, "de": 87, "ja": 95, "ko": 93, "ru": 89, "nl": 86, "zh": 94},
    
}

@app.get("/gettime")
def get_time():
    now = datetime.now()
    print(f"⏰ [DEBUG] Time requested: {now}")
    return {
        "current_time": now.strftime("%H:%M:%S"),
        "current_date": now.strftime("%Y-%m-%d"),
        "timestamp": now.isoformat()
    }


@app.post("/postdata")
async def post_data(request: Request):
    data = await request.json()
    print(f"\n🛰️ [POSTDATA] Incoming data: {data}")

    raw_device_id = data.get("id")
    if not raw_device_id:
        print("⚠️ [ERROR] Missing device ID")
        return {"error": "Missing 'id' in data"}

    device_id = str(raw_device_id).strip().lower()
    statue_name = (data.get("statue") or "").strip()
    language_name = (data.get("language") or "").strip()
    explicit_event = (data.get("event") or data.get("type") or "").strip().lower()

    print(f"📱 Device ID: {device_id}")
    print(f"🗿 Statue: {statue_name} | 🗣️ Language: {language_name} | 📍 Event: {explicit_event}")

    lang_key = LANG_TO_KEY.get(language_name)
    slot = STATUE_TO_SLOT.get(statue_name)

    if explicit_event in {"statue", "language"}:
        event_type = explicit_event
    else:
        event_type = "statue" if slot else ("language" if lang_key else None)

    print(f"🧠 Event type resolved: {event_type}")

    prev_doc = db.collection("stored_data1").document(device_id).get()
    prev_data = prev_doc.to_dict() if prev_doc.exists else None
    print(f"📦 Previous scan: {prev_data}")

    is_turnoff = statue_name == "NULL" and language_name == "NULL"
    print(f"🔌 Turnoff detected: {is_turnoff}")

    # --- COMPLETION TRACKING ---
    if event_type == "statue" and slot and lang_key and prev_data:
        prev_statue = prev_data.get("statue", "")
        prev_language = prev_data.get("language", "")
        prev_was_turnoff = prev_statue == "NULL" and prev_language == "NULL"

        if not prev_was_turnoff:
            prev_slot = STATUE_TO_SLOT.get(prev_statue)
            prev_lang = LANG_TO_KEY.get(prev_language)
            prev_time = prev_data.get("timestamp")
            print(f"🕓 Prev slot/lang: {prev_slot}/{prev_lang}, time={prev_time}")

            if prev_slot and prev_lang and prev_time:
                current_time = datetime.now()
                prev_datetime = datetime.fromisoformat(prev_time.replace('Z', '+00:00')) if isinstance(prev_time, str) else prev_time
                time_diff = (current_time - prev_datetime).total_seconds()
                print(f"⏱️ Time diff: {time_diff}s")

                if prev_slot in AUDIO_LENGTHS and prev_lang in AUDIO_LENGTHS[prev_slot]:
                    audio_length = AUDIO_LENGTHS[prev_slot][prev_lang]
                    threshold = audio_length * 0.9
                    print(f"🎧 Audio length={audio_length}s, threshold={threshold}s")

                    if time_diff >= threshold:
                        print(f"✅ Completed listen detected for {prev_slot}-{prev_lang}")
                        completion_ref = db.collection("stored_data2").document(device_id)
                        completion_ref.set({
                            "completions": {
                                prev_slot: {
                                    prev_lang: firestore.Increment(1)
                                }
                            }
                        }, merge=True)

    elif is_turnoff and prev_data:
        prev_statue = prev_data.get("statue", "")
        prev_language = prev_data.get("language", "")
        prev_was_turnoff = prev_statue == "NULL" and prev_language == "NULL"

        if not prev_was_turnoff:
            prev_slot = STATUE_TO_SLOT.get(prev_statue)
            prev_lang = LANG_TO_KEY.get(prev_language)
            prev_time = prev_data.get("timestamp")
            print(f"⚡ Turnoff -> Prev slot/lang: {prev_slot}/{prev_lang}, time={prev_time}")

            if prev_slot and prev_lang and prev_time:
                current_time = datetime.now()
                prev_datetime = datetime.fromisoformat(prev_time.replace('Z', '+00:00')) if isinstance(prev_time, str) else prev_time
                time_diff = (current_time - prev_datetime).total_seconds()
                print(f"⏱️ Turnoff Time diff: {time_diff}s")

                if prev_slot in AUDIO_LENGTHS and prev_lang in AUDIO_LENGTHS[prev_slot]:
                    audio_length = AUDIO_LENGTHS[prev_slot][prev_lang]
                    threshold = audio_length * 0.9

                    if time_diff >= threshold:
                        print(f"✅ Completed listen (turnoff) for {prev_slot}-{prev_lang}")
                        completion_ref = db.collection("stored_data2").document(device_id)
                        completion_ref.set({
                            "completions": {
                                prev_slot: {
                                    prev_lang: firestore.Increment(1)
                                }
                            }
                        }, merge=True)

    data["timestamp"] = datetime.now().isoformat()
    db.collection("stored_data1").document(device_id).set(data)
    print(f"💾 [DB] Stored current scan for {device_id}")

    doc_ref = db.collection("stored_data2").document(device_id)

    if event_type == "statue" and slot and lang_key:
        print(f"📊 Incrementing artifacts.{slot}.{lang_key}")
        doc_ref.set({"artifacts": {slot: {lang_key: firestore.Increment(1)}}}, merge=True)
        return {"message": f"Incremented artifacts.{slot}.{lang_key}"}

    if event_type == "language" and lang_key:
        print(f"📊 Incrementing language.{lang_key}")
        doc_ref.set({"language": {lang_key: firestore.Increment(1)}}, merge=True)
        return {"message": f"Incremented language.{lang_key}"}

    print("ℹ️ No increment performed.")
    return {"message": "No increment performed"}


@app.get("/getdata")
def get_data(user=Depends(verify_firebase_token)):
    print(f"📤 [GETDATA] Requested by UID: {user['uid']}")
    docs = db.collection("stored_data2").stream()
    all_data = [{"id": d.id, **(d.to_dict() or {})} for d in docs]
    print(f"🧾 Retrieved {len(all_data)} documents.")
    return {"stored_data": all_data, "user_uid": user["uid"]}


@app.get("/analytics/completion-rates")
def get_completion_rates(user=Depends(verify_firebase_token)):
    print(f"📈 [ANALYTICS] Completion rates requested by UID: {user['uid']}")
    docs = db.collection("stored_data2").stream()
    
    results = []
    for doc in docs:
        data = doc.to_dict() or {}
        completions = data.get("completions", {})
        artifacts = data.get("artifacts", {})
        for artifact in artifacts:
            for language in artifacts[artifact]:
                total = artifacts[artifact][language]
                completed = completions.get(artifact, {}).get(language, 0)
                rate = (completed / total * 100) if total > 0 else 0
                results.append({
                    "artifact": artifact,
                    "language": language,
                    "total_scans": total,
                    "completed_listens": completed,
                    "completion_rate": round(rate, 2)
                })
    print(f"✅ Computed {len(results)} completion records.")
    results.sort(key=lambda x: x["completion_rate"], reverse=True)
    return {"completion_rates": results, "user_uid": user["uid"]}


@app.get("/analytics/completion-summary")
def get_completion_summary(user=Depends(verify_firebase_token)):
    print(f"📊 [SUMMARY] Requested by UID: {user['uid']}")
    completion_data = get_completion_rates(user)

    if not completion_data["completion_rates"]:
        print("📭 No completion data found.")
        return {
            "overall_completion_rate": 0,
            "total_listens": 0,
            "completed_listens": 0,
            "user_uid": user["uid"]
        }

    total_listens = sum(item["total_scans"] for item in completion_data["completion_rates"])
    completed_listens = sum(item["completed_listens"] for item in completion_data["completion_rates"])
    overall_rate = (completed_listens / total_listens * 100) if total_listens > 0 else 0
    print(f"📊 Overall completion: {overall_rate:.2f}% ({completed_listens}/{total_listens})")

    return {
        "overall_completion_rate": round(overall_rate, 2),
        "total_listens": total_listens,
        "completed_listens": completed_listens,
        "by_artifact": completion_data["completion_rates"],
        "user_uid": user["uid"]
    }

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
