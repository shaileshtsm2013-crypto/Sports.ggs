import datetime
from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship
from backend.app.database.database import Base


class Match(Base):
    __tablename__ = "matches"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    sport_type = Column(String(50), nullable=False, default="volleyball")  # volleyball, kabaddi, kho_kho
    title = Column(String(255), nullable=False, default="New Match Session")
    started_at = Column(DateTime, default=datetime.datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    duration_sec = Column(Float, default=0.0)
    video_source = Column(String(255), default="webcam_0")
    status = Column(String(50), default="active")  # active, completed, paused
    total_players = Column(Integer, default=0)
    fps = Column(Float, default=0.0)
    notes = Column(Text, nullable=True)

    players = relationship("Player", back_populates="match", cascade="all, delete-orphan")
    events = relationship("SportsEvent", back_populates="match", cascade="all, delete-orphan")
    tracking_points = relationship("TrackingDataPoint", back_populates="match", cascade="all, delete-orphan")


class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    match_id = Column(Integer, ForeignKey("matches.id", ondelete="CASCADE"), nullable=False)
    tracker_id = Column(Integer, nullable=False, index=True)
    jersey_number = Column(String(10), nullable=True)
    team = Column(String(50), default="Team A")
    first_detected_at = Column(DateTime, default=datetime.datetime.utcnow)
    last_detected_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    # Aggregated performance metrics
    total_distance_m = Column(Float, default=0.0)
    max_speed_mps = Column(Float, default=0.0)
    avg_speed_mps = Column(Float, default=0.0)
    max_accel_mps2 = Column(Float, default=0.0)
    jump_count = Column(Integer, default=0)
    max_jump_height_cm = Column(Float, default=0.0)
    avg_jump_height_cm = Column(Float, default=0.0)
    court_coverage_pct = Column(Float, default=0.0)

    match = relationship("Match", back_populates="players")
    tracking_points = relationship("TrackingDataPoint", back_populates="player", cascade="all, delete-orphan")


class TrackingDataPoint(Base):
    __tablename__ = "tracking_data_points"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    match_id = Column(Integer, ForeignKey("matches.id", ondelete="CASCADE"), nullable=False, index=True)
    player_id = Column(Integer, ForeignKey("players.id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(Float, nullable=False)  # match elapsed seconds
    frame_idx = Column(Integer, nullable=False)
    
    # Bounding Box (pixel or normalized)
    bbox_x = Column(Float, nullable=False)
    bbox_y = Column(Float, nullable=False)
    bbox_w = Column(Float, nullable=False)
    bbox_h = Column(Float, nullable=False)
    confidence = Column(Float, default=0.0)
    
    # Kinematics
    court_x = Column(Float, nullable=True)
    court_y = Column(Float, nullable=True)
    instant_speed_mps = Column(Float, default=0.0)
    acceleration_mps2 = Column(Float, default=0.0)

    match = relationship("Match", back_populates="tracking_points")
    player = relationship("Player", back_populates="tracking_points")


class SportsEvent(Base):
    __tablename__ = "sports_events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    match_id = Column(Integer, ForeignKey("matches.id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(Float, nullable=False)  # match elapsed seconds
    frame_idx = Column(Integer, nullable=False)
    event_type = Column(String(100), nullable=False)  # e.g. "spike", "jump", "raid_entry", "tackle", "chase_switch"
    player_id = Column(Integer, nullable=True)
    confidence = Column(Float, default=0.0)
    metadata_json = Column(JSON, nullable=True)

    match = relationship("Match", back_populates="events")


class RuleItem(Base):
    __tablename__ = "rule_items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    sport = Column(String(50), nullable=False, index=True)  # volleyball, kabaddi, kho_kho
    category = Column(String(100), nullable=False)  # scoring, fouls, general, terminology
    title = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    federations = Column(String(255), default="FIVB / IKF / KKFI")
    tags = Column(String(255), nullable=True)
