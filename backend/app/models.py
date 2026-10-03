from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def uuid() -> str:
    return str(uuid4())


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String, default="Development User")
    auth_provider: Mapped[str] = mapped_column(String, default="dev")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    ideas: Mapped[list["Idea"]] = relationship(back_populates="user")


class Idea(Base):
    __tablename__ = "ideas"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String, index=True)
    problem: Mapped[str] = mapped_column(Text)
    mechanism: Mapped[str] = mapped_column(Text)
    data_flow: Mapped[str] = mapped_column(Text)
    algorithm: Mapped[str] = mapped_column(Text)
    technical_novelty: Mapped[str] = mapped_column(Text)
    implementation_notes: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String, default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user: Mapped[User] = relationship(back_populates="ideas")
    prior_art_results: Mapped[list["PriorArtResult"]] = relationship(back_populates="idea")
    analysis_reports: Mapped[list["AnalysisReport"]] = relationship(back_populates="idea")


class PriorArtResult(Base):
    __tablename__ = "prior_art_results"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid)
    idea_id: Mapped[str] = mapped_column(ForeignKey("ideas.id"), index=True)
    source: Mapped[str] = mapped_column(String, index=True)
    external_id: Mapped[str] = mapped_column(String, index=True)
    title: Mapped[str] = mapped_column(String)
    abstract: Mapped[str] = mapped_column(Text, default="")
    publication_date: Mapped[str] = mapped_column(String, default="")
    assignee: Mapped[str] = mapped_column(String, default="")
    link: Mapped[str] = mapped_column(String, default="")
    similarity_score: Mapped[float] = mapped_column(Float, default=0.0)
    raw_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    idea: Mapped[Idea] = relationship(back_populates="prior_art_results")


class AnalysisReport(Base):
    __tablename__ = "analysis_reports"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uuid)
    idea_id: Mapped[str] = mapped_column(ForeignKey("ideas.id"), index=True)
    novelty_score: Mapped[int] = mapped_column(Integer)
    obviousness_risk: Mapped[int] = mapped_column(Integer)
    eligibility_risk: Mapped[int] = mapped_column(Integer)
    summary: Mapped[str] = mapped_column(Text)
    overlaps: Mapped[list] = mapped_column(JSON, default=list)
    section_101_flags: Mapped[list] = mapped_column(JSON, default=list)
    suggested_tweaks: Mapped[list] = mapped_column(JSON, default=list)
    generated_by: Mapped[str] = mapped_column(String, default="heuristic")
    disclaimer: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    idea: Mapped[Idea] = relationship(back_populates="analysis_reports")
