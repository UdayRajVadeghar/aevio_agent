"""
Workout Generator Agent Schemas

This module contains all Pydantic models for the workout generator agent.
"""

from .workout_plan import (
    # Enums/Literals
    PlanType,
    Difficulty,
    BlockType,
    SetType,
    FeedbackType,
    # Set & Exercise Models
    ActualPerformance,
    ExerciseSet,
    MuscleGroups,
    Exercise,
    ExerciseBlock,
    # Day & Week Models
    WorkoutDay,
    Week,
    # Phase & Program Models
    Phase,
    # AI Context & Tracking Models
    AIContext,
    PreviousRecord,
    PersonalRecord,
    FeedbackEntry,
    ProgressTracker,
    # Main Model
    WorkoutPlan,
    # Constants
    AI_WORKOUT_GENERATION_CONTEXT,
    # Helper Functions
    get_example_workout_plan,
)

__all__ = [
    # Enums/Literals
    "PlanType",
    "Difficulty",
    "BlockType",
    "SetType",
    "FeedbackType",
    # Set & Exercise Models
    "ActualPerformance",
    "ExerciseSet",
    "MuscleGroups",
    "Exercise",
    "ExerciseBlock",
    # Day & Week Models
    "WorkoutDay",
    "Week",
    # Phase & Program Models
    "Phase",
    # AI Context & Tracking Models
    "AIContext",
    "PreviousRecord",
    "PersonalRecord",
    "FeedbackEntry",
    "ProgressTracker",
    # Main Model
    "WorkoutPlan",
    # Constants
    "AI_WORKOUT_GENERATION_CONTEXT",
    # Helper Functions
    "get_example_workout_plan",
]

