from fastapi import FastAPI, Request
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000",
                    "https://tree-d-dashboard.vercel.app/"
    ],  # or ["*"] for testing
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage
stored_data = []
stored_data2 = []

@app.get("/gettime")
def get_time():
    """Return the current server time and date."""
    now = datetime.now()
    return {
        "current_time": now.strftime("%H:%M:%S"),
        "current_date": now.strftime("%Y-%m-%d"),
        "timestamp": now.isoformat()
    }

@app.post("/postdata")
async def post_data(request: Request):
    """Receive JSON data and store/update by device ID."""
    data = await request.json()
    device_id = data.get("id")

    # check if device exists in stored_data
    for i, existing in enumerate(stored_data):
        if existing["id"] == device_id:
            # overwrite the old data with the new one
            stored_data[i] = data
            break
    else:
        # if device not found, add it
        stored_data.append(data)

    print("Current stored_data:", stored_data)
    return {"message": "Data stored successfully", "stored_data": stored_data}

@app.get("/getdata")
def get_data():
    """Return all stored data."""
    return {"stored_data": stored_data2}

@app.post("/poststoreddata")
async def post_stored_data(request: Request):
    """Same logic for stored_data2."""
    data = await request.json()
    device_id = data.get("id")

    for i, existing in enumerate(stored_data2):
        if existing["id"] == device_id:
            stored_data2[i] = data
            break
    else:
        stored_data2.append(data)

    print("Current stored_data2:", stored_data2)
    return {"message": "Data stored successfully", "stored_data2": stored_data2}

if __name__ == "__main__":
    import uvicorn
    import pathlib, os

    here = pathlib.Path(__file__).parent.resolve()
    os.chdir(here)

    module_name = pathlib.Path(__file__).stem
    uvicorn.run(
        f"{module_name}:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=[str(here)]
    )
