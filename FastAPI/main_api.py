from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, String, Integer, MetaData, Table ,select
from sqlalchemy.dialects.sqlite import insert 
from sqlalchemy.orm import sessionmaker

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
DATABASE_URL = "sqlite:///./main.db"
engine = create_engine(DATABASE_URL)
metadata = MetaData()


rooms = Table(
    "rooms",
    metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("name", String, unique=True, index=True),
    Column("room_number", Integer),
)


metadata.create_all(bind=engine)


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class RoomCreate(BaseModel):
    name: str
    room_number: int


@app.post("/add_room/")
async def add_room(room: RoomCreate):
    db = SessionLocal()
    try:
        
        upsert_statement = insert(rooms).values(
            name=room.name, room_number=room.room_number
        ).on_conflict_do_update(
            index_elements=['name'],
            set_={'room_number': room.room_number}
        )

        result = db.execute(upsert_statement)
        db.commit()

        
        inserted_data = {
            "id": result.inserted_primary_key[0],
            "name": room.name,
            "room_number": room.room_number,
        }

        return {"message": "Room added or updated successfully", "data": inserted_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.post("/create_room_table/")
async def create_room_table():
    try:
        # Create the 'room' table
        rooms.create(bind=engine)
        return {"message": "Table 'room' created successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



class RoomResponse(BaseModel):
    id: int
    name: str
    room_number: int


@app.get("/get_room/{name}", response_model=RoomResponse)
async def get_room(name: str):
    db = SessionLocal()
    try:
        
        query = select(rooms).where(rooms.c.name == name)
        result = db.execute(query).fetchone()

        if result is None:
            raise HTTPException(status_code=404, detail="Room not found")

        room_data = {
            "id": result.id,
            "name": result.name,
            "room_number": result.room_number,
        }

        return room_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()