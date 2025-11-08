from fastapi import FastAPI, Request, Depends, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta, timezone
import firebase_admin
from firebase_admin import credentials, firestore, auth as firebase_auth
from dotenv import load_dotenv
import os, json, pathlib
from pydantic import BaseModel, EmailStr
from typing import Optional
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

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
        return decoded_token
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid or expired token: {e}")

# ----------------------------------------------------------------
#  --- MODELS ---
# ----------------------------------------------------------------
class InviteRequest(BaseModel):
    email: EmailStr
    role: str = "normal"  # "admin" or "normal"

class TeamInfo(BaseModel):
    team_id: str
    team_name: str
    role: str

# ----------------------------------------------------------------
#  --- HELPER FUNCTIONS ---
# ----------------------------------------------------------------
async def get_user_team(uid: str):
    """Get user's team information from Firestore"""
    user_doc = db.collection("users").document(uid).get()
    if user_doc.exists:
        data = user_doc.to_dict()
        return data.get("team_id"), data.get("role")
    return None, None

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

async def send_invite_email(to_email: str, invite_token: str, inviter_email: str, team_name: str):
    """Send invitation email"""
    # Get SMTP settings from environment
    smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USER")
    smtp_password = os.getenv("SMTP_PASSWORD")
    frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
    
    if not smtp_user or not smtp_password:
        print("⚠️ SMTP credentials not configured")
        return False
    
    invite_link = f"{frontend_url}/accept-invite?token={invite_token}"
    
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"You've been invited to join {team_name}"
    msg["From"] = smtp_user
    msg["To"] = to_email

    # prettier HTML version of the email
    html = f"""
    <!DOCTYPE html>
    <html>
      <head>
        <meta charset="UTF-8" />
        <title>You're Invited!</title>
        <style>
          body {{
            background-color: #f4f7f9;
            font-family: "Poppins", Arial, sans-serif;
            color: #333;
            margin: 0;
            padding: 0;
          }}
          .container {{
            max-width: 500px;
            margin: 40px auto;
            background: #ffffff;
            border-radius: 16px;
            padding: 30px;
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.05);
          }}
          .logo {{
            text-align: center;
            margin-bottom: 20px;
          }}
          .logo img {{
            width: 150px;
            border-radius: 12px;
          }}
          h1 {{
            text-align: center;
            font-size: 1.6rem;
            margin-bottom: 10px;
            color: #2c3e50;
          }}
          p {{
            font-size: 1rem;
            line-height: 1.6;
            color: #555;
            margin-bottom: 20px;
          }}
          .button {{
            display: block;
            width: 80%;
            margin: 25px auto 10px;
            text-align: center;
            background-color: #2e7d32;
            color: #fff !important;
            text-decoration: none;
            font-weight: 600;
            padding: 14px 0;
            border-radius: 10px;
            transition: all 0.3s ease;
          }}
          .button:hover {{
            background-color: #256427;
          }}
          .note {{
            text-align: center;
            font-size: 0.9rem;
            color: #888;
            margin-top: 5px;
            margin-bottom: 20px;
          }}
          .footer {{
            text-align: center;
            margin-top: 30px;
            font-size: 0.9rem;
            color: #aaa;
          }}
        </style>
      </head>

      <body>
        <div class="container">
          <div class="logo">
            <!-- Replace with your logo -->
            <img src="https://i.postimg.cc/QHQPV4Kh/Slack-Inspired-Logo.png" alt="Tree'd logo" />
          </div>

          <h1>You've Been Invited!</h1>

          <p>
            Hey there 👋 <br />
            <strong>{inviter_email}</strong> has invited you to join the team:
            <strong>{team_name}</strong>.
          </p>

          <p>Click the button below to accept the invitation and create your account.</p>

          <a href="{invite_link}" class="button">Accept Invitation</a>

          <p class="note">This invitation will expire in 7 days.</p>

          <div class="footer">
            <p>Tree'd — Your gate to the past.</p>
          </div>
        </div>
      </body>
    </html>
    """

    part = MIMEText(html, "html")
    msg.attach(part)
    
    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, to_email, msg.as_string())
        print(f"✅ Invite email sent to {to_email}")
        return True
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False

# ----------------------------------------------------------------
#  --- INVITE ENDPOINTS ---
# ----------------------------------------------------------------

@app.post("/invite/send")
async def send_invite(invite: InviteRequest, user=Depends(verify_firebase_token)):
    """
    Send an invitation to a new user
    Only admins with a team can send invites
    """
    uid = user["uid"]
    email = user.get("email", "Unknown")
    
    print(f"📨 [INVITE] Request from {email} (UID: {uid}) to invite {invite.email}")
    
    # Check if user is admin and has a team
    team_id, role = await get_user_team(uid)
    
    if not team_id:
        raise HTTPException(status_code=403, detail="You must be part of a team to send invites")
    
    if role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can send invites")
    
    # Get team info
    team_doc = db.collection("teams").document(team_id).get()
    if not team_doc.exists:
        raise HTTPException(status_code=404, detail="Team not found")
    
    team_data = team_doc.to_dict()
    team_name = team_data.get("name", "Unknown Team")
    
    # Check if email is already invited or part of a team
    existing_invite = db.collection("invites").where("email", "==", invite.email).where("status", "==", "pending").limit(1).get()
    if len(list(existing_invite)) > 0:
        raise HTTPException(status_code=400, detail="This email already has a pending invitation")
    
    # Check if user already exists
    try:
        existing_user = firebase_auth.get_user_by_email(invite.email)
        user_doc = db.collection("users").document(existing_user.uid).get()
        if user_doc.exists and user_doc.to_dict().get("team_id"):
            raise HTTPException(status_code=400, detail="This user is already part of a team")
    except firebase_auth.UserNotFoundError:
        pass  # User doesn't exist yet, which is fine
    
    # Generate invite token
    invite_token = secrets.token_urlsafe(32)
    
    # Create invite document
    invite_data = {
        "email": invite.email,
        "team_id": team_id,
        "team_name": team_name,
        "role": invite.role,
        "invited_by": uid,
        "invited_by_email": email,
        "token": invite_token,
        "status": "pending",
        "created_at": datetime.now(),
        "expires_at": datetime.now().replace(hour=23, minute=59, second=59) + timedelta(days=7)
    }
    
    db.collection("invites").add(invite_data)
    
    # Send email
    email_sent = await send_invite_email(invite.email, invite_token, email, team_name)
    
    print(f"✅ Invite created for {invite.email}")
    
    return {
        "message": "Invitation sent successfully",
        "email": invite.email,
        "email_sent": email_sent,
        "team_name": team_name
    }


@app.get("/invite/validate")
async def validate_invite(token: str):
    print(f"🔍 [VALIDATE] Checking token: {token[:10]}...")
    
    invites = (
        db.collection("invites")
        .where("token", "==", token)
        .where("status", "==", "pending")
        .limit(1)
        .stream()
    )
    invite_doc = next(invites, None)
    
    if not invite_doc:
        raise HTTPException(status_code=404, detail="Invalid or expired invitation")
    
    invite_data = invite_doc.to_dict()
    expires_at = invite_data.get("expires_at")

    # 👇 timezone-safe comparison
    if expires_at and datetime.now(timezone.utc) > expires_at:
        db.collection("invites").document(invite_doc.id).update({"status": "expired"})
        raise HTTPException(status_code=410, detail="This invitation has expired")
    
    print(f"✅ Valid invite for {invite_data.get('email')}")
    
    return {
        "valid": True,
        "email": invite_data.get("email"),
        "team_name": invite_data.get("team_name"),
        "role": invite_data.get("role")
    }


@app.post("/invite/accept/{token}")
async def accept_invite(token: str, user=Depends(verify_firebase_token)):
    """
    Accept an invitation and join the team
    User must be authenticated
    """
    uid = user["uid"]
    email = user.get("email")
    
    print(f"✅ [ACCEPT] User {email} accepting invite with token: {token[:10]}...")

    # Find invite by token
    invites = (
        db.collection("invites")
        .where("token", "==", token)
        .where("status", "==", "pending")
        .limit(1)
        .stream()
    )
    invite_doc = next(invites, None)

    if not invite_doc:
        raise HTTPException(status_code=404, detail="Invalid or expired invitation")

    invite_data = invite_doc.to_dict()

    # Verify email matches
    if invite_data.get("email") != email:
        raise HTTPException(status_code=403, detail="This invitation is for a different email address")

    # Check if expired
    expires_at = invite_data.get("expires_at")
    if expires_at and datetime.now(timezone.utc) > expires_at.replace(tzinfo=timezone.utc):
        db.collection("invites").document(invite_doc.id).update({"status": "expired"})
        raise HTTPException(status_code=410, detail="This invitation has expired")

    # Check if user already has a team
    user_doc = db.collection("users").document(uid).get()
    if user_doc.exists:
        user_data = user_doc.to_dict()
        if user_data.get("team_id"):
            raise HTTPException(status_code=400, detail="You are already part of a team")

    team_id = invite_data.get("team_id")
    role = invite_data.get("role", "normal")

    # Add user to team
    db.collection("users").document(uid).set(
        {
            "email": email,
            "team_id": team_id,
            "role": role,
            "joined_at": datetime.now(timezone.utc),
        },
        merge=True,
    )

    # Update team members count
    db.collection("teams").document(team_id).update(
        {"member_count": firestore.Increment(1)}
    )

    # Mark invite as accepted
    db.collection("invites").document(invite_doc.id).update(
        {
            "status": "accepted",
            "accepted_at": datetime.now(timezone.utc),
            "accepted_by_uid": uid,
        }
    )

    print(f"✅ User {email} joined team {team_id} as {role}")

    return {
        "message": "Successfully joined the team",
        "team_id": team_id,
        "team_name": invite_data.get("team_name"),
        "role": role,
    }



@app.get("/invite/list")
async def list_invites(user=Depends(verify_firebase_token)):
    """
    List all invites sent by the team (admin only)
    Includes status: pending, accepted, or expired
    """
    uid = user["uid"]
    team_id, role = await get_user_team(uid)

    if not team_id:
        raise HTTPException(status_code=403, detail="You must be part of a team")
    if role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can view invites")

    # Query all invites for that team
    invites = (
        db.collection("invites")
        .where("team_id", "==", team_id)
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .stream()
    )

    invite_list = []
    now = datetime.now(timezone.utc)

    for invite_doc in invites:
        data = invite_doc.to_dict()
        if not data:
            continue

        # Convert timestamps to ISO strings for frontend
        for field in ["created_at", "expires_at", "accepted_at"]:
            if field in data and data[field]:
                data[field] = data[field].astimezone(timezone.utc).isoformat()

        # determine the status dynamically
        expires_at = invite_doc.to_dict().get("expires_at")
        accepted_at = invite_doc.to_dict().get("accepted_at")
        status = invite_doc.to_dict().get("status", "pending")

        # make sure we handle the status properly
        if accepted_at:
            status = "accepted"
        elif expires_at and datetime.now(timezone.utc) > expires_at:
            status = "expired"
        else:
            status = "pending"

        invite_list.append({
            "id": invite_doc.id,
            "email": data.get("email"),
            "role": data.get("role", "normal"),
            "invited_by_email": data.get("invited_by_email"),
            "accepted_by_uid": data.get("accepted_by_uid"),
            "team_name": data.get("team_name"),
            "status": status,
            "created_at": data.get("created_at"),
            "expires_at": data.get("expires_at"),
            "accepted_at": data.get("accepted_at"),
        })

    print(f"📋 Retrieved {len(invite_list)} invites for team {team_id}")

    return {
        "invites": invite_list,
        "count": len(invite_list),
    }


@app.get("/user/profile")
async def get_user_profile(user=Depends(verify_firebase_token)):
    """
    Get current user's profile including team info
    """
    uid = user["uid"]
    email = user.get("email")
    
    user_doc = db.collection("users").document(uid).get()
    
    if not user_doc.exists:
        return {
            "uid": uid,
            "email": email,
            "team_id": None,
            "role": None,
            "has_team": False
        }
    
    data = user_doc.to_dict()
    team_id = data.get("team_id")
    
    team_info = None
    if team_id:
        team_doc = db.collection("teams").document(team_id).get()
        if team_doc.exists:
            team_data = team_doc.to_dict()
            team_info = {
                "id": team_id,
                "name": team_data.get("name"),
                "member_count": team_data.get("member_count", 0)
            }
    
    return {
        "uid": uid,
        "email": email,
        "team_id": team_id,
        "role": data.get("role"),
        "has_team": team_id is not None,
        "team": team_info,
        "joined_at": data.get("joined_at").isoformat() if data.get("joined_at") else None
    }


@app.post("/team/create")
async def create_team(team_name: str, user=Depends(verify_firebase_token)):
    """
    Create a new team (first user becomes admin)
    """
    uid = user["uid"]
    email = user.get("email")
    
    # Check if user already has a team
    user_doc = db.collection("users").document(uid).get()
    if user_doc.exists and user_doc.to_dict().get("team_id"):
        raise HTTPException(status_code=400, detail="You are already part of a team")
    
    # Create team
    team_ref = db.collection("teams").document()
    team_id = team_ref.id
    
    team_ref.set({
        "name": team_name,
        "created_by": uid,
        "created_at": datetime.now(),
        "member_count": 1
    })
    
    # Add user to team as admin
    db.collection("users").document(uid).set({
        "email": email,
        "team_id": team_id,
        "role": "admin",
        "joined_at": datetime.now()
    }, merge=True)
    
    print(f"✅ Team '{team_name}' created by {email}")
    
    return {
        "message": "Team created successfully",
        "team_id": team_id,
        "team_name": team_name,
        "role": "admin"
    }

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

# Reverse mapping for display names
SLOT_TO_STATUE = {v: k for k, v in STATUE_TO_SLOT.items()}

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

# Reverse mapping for display names
KEY_TO_LANG = {v: k for k, v in LANG_TO_KEY.items()}

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
    print(f"🗿 Statue: {statue_name} | 🗣️ Language: {language_name} | 📝 Event: {explicit_event}")

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

    current_time = datetime.now()
    
    # --- SAVE TO TIME-SERIES COLLECTION ---
    # Save every interaction with timestamp to interactions collection
    if event_type == "statue" and slot and lang_key and not is_turnoff:
        interaction_data = {
            "device_id": device_id,
            "artifact": slot,
            "artifact_name": statue_name,
            "language": lang_key,
            "language_name": language_name,
            "timestamp": current_time,
            "date": current_time.strftime("%Y-%m-%d"),
            "event_type": "artifact_scan"
        }
        
        # Add to interactions collection (auto-generated document ID)
        db.collection("interactions").add(interaction_data)
        print(f"📊 [TIMESERIES] Saved interaction: {slot}-{lang_key} at {current_time}")

    # --- COMPLETION TRACKING ---
    if event_type == "statue" and slot and lang_key and prev_data:
        prev_statue = prev_data.get("statue", "")
        prev_language = prev_data.get("language", "")
        prev_was_turnoff = prev_statue == "NULL" and prev_language == "NULL"

        if not prev_was_turnoff:
            prev_slot = STATUE_TO_SLOT.get(prev_statue)
            prev_lang = LANG_TO_KEY.get(prev_language)
            prev_time = prev_data.get("timestamp")
            print(f"🕐 Prev slot/lang: {prev_slot}/{prev_lang}, time={prev_time}")

            if prev_slot and prev_lang and prev_time:
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

    data["timestamp"] = current_time.isoformat()
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


@app.get("/analytics/interactions")
def get_interactions(
    start_date: str = None,
    end_date: str = None,
    user=Depends(verify_firebase_token)
):
    """
    Get time-series interaction data
    Query params:
    - start_date: YYYY-MM-DD format (optional)
    - end_date: YYYY-MM-DD format (optional)
    """
    print(f"📈 [INTERACTIONS] Requested by UID: {user['uid']}")
    print(f"📅 Date range: {start_date} to {end_date}")
    
    query = db.collection("interactions")
    
    # Apply date filters if provided
    if start_date:
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.where("timestamp", ">=", start_dt)
        except ValueError:
            print(f"⚠️ Invalid start_date format: {start_date}")
    
    if end_date:
        try:
            # Add one day to include the entire end date
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            end_dt = end_dt.replace(hour=23, minute=59, second=59)
            query = query.where("timestamp", "<=", end_dt)
        except ValueError:
            print(f"⚠️ Invalid end_date format: {end_date}")
    
    # Order by timestamp
    query = query.order_by("timestamp")
    
    docs = query.stream()
    interactions = []
    
    for doc in docs:
        data = doc.to_dict()
        # Convert timestamp to ISO string for JSON serialization
        if "timestamp" in data:
            data["timestamp"] = data["timestamp"].isoformat()
        interactions.append({
            "id": doc.id,
            **data
        })
    
    print(f"✅ Retrieved {len(interactions)} interactions")
    
    return {
        "interactions": interactions,
        "count": len(interactions),
        "user_uid": user["uid"]
    }


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
                    "artifact_name": SLOT_TO_STATUE.get(artifact, artifact),
                    "language": language,
                    "language_name": KEY_TO_LANG.get(language, language),
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
        print("🔭 No completion data found.")
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
