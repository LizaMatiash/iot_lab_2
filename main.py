import json
from typing import Set, Dict, List, Any
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Body
from sqlalchemy import ( create_engine, MetaData, Table, Column, Integer, String, Float, DateTime)
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import select, update, delete

from models.processed_agent_data_in_db import ProcessedAgentDataInDB
from models.processed_agent_data import ProcessedAgentData

from config import (
    POSTGRES_HOST,
    POSTGRES_PORT,
    POSTGRES_DB,
    POSTGRES_USER,
    POSTGRES_PASSWORD,
)

# FastAPI app setup
app = FastAPI()
# SQLAlchemy setup
DATABASE_URL = f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
engine = create_engine(DATABASE_URL)
metadata = MetaData()
# Define the ProcessedAgentData table
processed_agent_data = Table(
    "processed_agent_data",
    metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("road_state", String),
    Column("user_id", Integer),
    Column("x", Float),
    Column("y", Float),
    Column("z", Float),
    Column("latitude", Float),
    Column("longitude", Float),
    Column("timestamp", DateTime),
)
SessionLocal = sessionmaker(bind=engine)

# WebSocket subscriptions
subscriptions: Dict[int, Set[WebSocket]] = {}


# FastAPI WebSocket endpoint
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    await websocket.accept()
    if user_id not in subscriptions:
        subscriptions[user_id] = set()
    subscriptions[user_id].add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        subscriptions[user_id].remove(websocket)


# Function to send data to subscribed users
async def send_data_to_subscribers(user_id: int, data):
    if user_id in subscriptions:
        for websocket in subscriptions[user_id]:
            await websocket.send_json(json.dumps(data))


# FastAPI CRUD endpoints
@app.post("/processed_agent_data/")
async def create_processed_agent_data(data: List[ProcessedAgentData]):
    with SessionLocal() as db:
        for item in data:
            try:
                dat = processed_agent_data.insert().values(
                      road_state=item.road_state,
                      user_id=item.agent_data.user_id,
                      x=item.agent_data.accelerometer.x,
                      y=item.agent_data.accelerometer.y,
                      z=item.agent_data.accelerometer.z,
                      latitude=item.agent_data.gps.latitude,
                      longitude=item.agent_data.gps.longitude,
                      timestamp=item.agent_data.timestamp
                )
                # Insert data to database
                result = db.execute(dat)
                db.commit()
                # Send data to subscribers
                await send_data_to_subscribers(item.agent_data.user_id, result)
            except Exception as e:
                db.rollback()
                raise e


@app.get(
    "/processed_agent_data/{processed_agent_data_id}",
    response_model=ProcessedAgentDataInDB,
)
def read_processed_agent_data(processed_agent_data_id: int):
    with SessionLocal() as db:
        # Get data by id
        dat = select(processed_agent_data).where(processed_agent_data.c.id == processed_agent_data_id)
        result = db.execute(dat).fetchone()

        if result is None:
            raise HTTPException(status_code=404, detail="ProcessedAgentData not found")

        return ProcessedAgentDataInDB(**result._asdict())


@app.get("/processed_agent_data/", response_model=list[ProcessedAgentDataInDB])
def list_processed_agent_data():
    with SessionLocal() as db:
        # Get list of data
        dat = select(processed_agent_data)
        results = db.execute(dat).fetchall()

        return [ProcessedAgentDataInDB(**row._asdict()) for row in results]


@app.put(
    "/processed_agent_data/{processed_agent_data_id}",
    response_model=ProcessedAgentDataInDB,
)
def update_processed_agent_data(processed_agent_data_id: int, data: ProcessedAgentData):
    with SessionLocal() as db:
        # Update data
        dat = update(processed_agent_data).where(processed_agent_data.c.id == processed_agent_data_id).values(
            road_state=data.road_state,
            user_id=data.agent_data.user_id,
            x=data.agent_data.accelerometer.x,
            y=data.agent_data.accelerometer.y,
            z=data.agent_data.accelerometer.z,
            latitude=data.agent_data.gps.latitude,
            longitude=data.agent_data.gps.longitude,
            timestamp=data.agent_data.timestamp
        )

        result = db.execute(dat)
        db.commit()

        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="ProcessedAgentData not found")

        updated_dat = select(processed_agent_data).where(processed_agent_data.c.id == processed_agent_data_id)
        updated_result = db.execute(updated_dat).fetchone()

        if updated_result is None:
            raise HTTPException(status_code=404, detail="Failed to fetch updated ProcessedAgentData")

        return ProcessedAgentDataInDB(**updated_result._asdict())


@app.delete(
    "/processed_agent_data/{processed_agent_data_id}",
    response_model=ProcessedAgentDataInDB,
)
def delete_processed_agent_data(processed_agent_data_id: int):
    with SessionLocal() as db:
        dat = select(processed_agent_data).where(processed_agent_data.c.id == processed_agent_data_id)
        result = db.execute(dat).fetchone()

        if result is None:
            raise HTTPException(status_code=404, detail="ProcessedAgentData not found")

        # Delete by id
        dat = delete(processed_agent_data).where(processed_agent_data.c.id == processed_agent_data_id)

        db.execute(dat)
        db.commit()

        return ProcessedAgentDataInDB(**result._asdict())


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)