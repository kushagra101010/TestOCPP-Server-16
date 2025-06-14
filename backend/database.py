from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, JSON, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import json

# Create SQLite database engine
engine = create_engine('sqlite:///./ocpp_chargers.db', echo=False)
Base = declarative_base()

class Charger(Base):
    __tablename__ = 'chargers'
    
    id = Column(Integer, primary_key=True)
    charge_point_id = Column(String, unique=True, nullable=False)
    status = Column(String, default='disconnected')
    last_heartbeat = Column(DateTime, default=datetime.utcnow)
    meter_value = Column(Float, default=0.0)
    current_transaction = Column(Integer, nullable=True)
    data_transfer_packets = Column(JSON, default=list)  # For received packets from charger
    logs = Column(JSON, default=list)
    connector_status = Column(JSON, default=dict)  # Separate field for connector status
    logs_cleared_at = Column(DateTime, nullable=True)  # Timestamp when logs were last cleared
    
    def to_dict(self):
        return {
            'id': self.id,
            'charge_point_id': self.charge_point_id,
            'status': self.status,
            'last_heartbeat': self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            'meter_value': self.meter_value,
            'current_transaction': self.current_transaction,
            'data_transfer_packets': self.data_transfer_packets,
            'logs': self.logs,
            'connector_status': self.connector_status,
            'logs_cleared_at': self.logs_cleared_at.isoformat() if self.logs_cleared_at else None
        }

class IdTag(Base):
    __tablename__ = 'id_tags'
    
    id = Column(Integer, primary_key=True)
    id_tag = Column(String, unique=True, nullable=False)
    status = Column(String, default='accepted')
    expiry_date = Column(DateTime, nullable=True)
    parent_id_tag = Column(String, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'id_tag': self.id_tag,
            'status': self.status,
            'expiry_date': self.expiry_date.isoformat() if self.expiry_date else None,
            'parent_id_tag': self.parent_id_tag
        }

class DataTransferPacketTemplate(Base):
    __tablename__ = 'data_transfer_packet_templates'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    vendor_id = Column(String, nullable=False)
    message_id = Column(String, nullable=True)
    data = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'vendor_id': self.vendor_id,
            'message_id': self.message_id,
            'data': self.data,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

# Create all tables
Base.metadata.create_all(engine)

# Add migration for logs column if it doesn't exist
try:
    import sqlite3
    conn = sqlite3.connect('ocpp_chargers.db')
    cursor = conn.cursor()
    
    # Check if logs column exists
    cursor.execute("PRAGMA table_info(chargers)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'logs' not in columns:
        cursor.execute("ALTER TABLE chargers ADD COLUMN logs TEXT DEFAULT '[]'")
        conn.commit()
        print("Added logs column to chargers table")
    
    # Check if connector_status column exists
    if 'connector_status' not in columns:
        cursor.execute("ALTER TABLE chargers ADD COLUMN connector_status TEXT DEFAULT '{}'")
        conn.commit()
        print("Added connector_status column to chargers table")
    
    # Check if logs_cleared_at column exists
    if 'logs_cleared_at' not in columns:
        cursor.execute("ALTER TABLE chargers ADD COLUMN logs_cleared_at DATETIME")
        conn.commit()
        print("Added logs_cleared_at column to chargers table")
        
    conn.close()
except Exception as e:
    print(f"Migration note: {e}")

# Create session factory
SessionLocal = sessionmaker(bind=engine)

class Database:
    def __init__(self):
        self.session = SessionLocal()

    def save_id_tag(self, id_tag: str, status: str = "Accepted", expiry_date=None) -> None:
        """Save or update an ID tag in the database."""
        existing_tag = self.session.query(IdTag).filter_by(id_tag=id_tag).first()
        if existing_tag:
            existing_tag.status = status
            if expiry_date is not None:
                existing_tag.expiry_date = expiry_date
        else:
            new_tag = IdTag(id_tag=id_tag, status=status, expiry_date=expiry_date)
            self.session.add(new_tag)
        self.session.commit()

    def get_id_tags(self) -> dict:
        """Get all ID tags from the database."""
        tags = self.session.query(IdTag).all()
        return {tag.id_tag: tag.to_dict() for tag in tags}

    def get_id_tag(self, id_tag: str) -> dict:
        """Get a specific ID tag from the database."""
        tag = self.session.query(IdTag).filter_by(id_tag=id_tag).first()
        return tag.to_dict() if tag else None

    def delete_id_tag(self, id_tag: str) -> bool:
        """Delete an ID tag from the database."""
        tag = self.session.query(IdTag).filter_by(id_tag=id_tag).first()
        if tag:
            self.session.delete(tag)
            self.session.commit()
            return True
        return False

    def save_data_transfer_packet(self, name: str, vendor_id: str, message_id: str = None, data: str = None) -> int:
        """Save a data transfer packet template."""
        packet = DataTransferPacketTemplate(
            name=name,
            vendor_id=vendor_id,
            message_id=message_id,
            data=data
        )
        self.session.add(packet)
        self.session.commit()
        return packet.id
    
    def get_data_transfer_packets(self) -> list:
        """Get all data transfer packet templates."""
        packets = self.session.query(DataTransferPacketTemplate).all()
        return [packet.to_dict() for packet in packets]
    
    def delete_data_transfer_packet(self, packet_id: int) -> bool:
        """Delete a data transfer packet by ID."""
        packet = self.session.query(DataTransferPacketTemplate).filter_by(id=packet_id).first()
        if packet:
            self.session.delete(packet)
            self.session.commit()
            return True
        return False

# Initialize database
db = Database() 