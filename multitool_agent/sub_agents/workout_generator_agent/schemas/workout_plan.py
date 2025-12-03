"""
Workout Plan Pydantic Schema

Use this schema to generate AI workout plans in a consistent format.

The structure follows: Program > Phase > Week > Day > ExerciseBlock > Exercise > Set

IMPORTANT FOR AI GENERATION:
- Always generate valid JSON matching these models
- All IDs should be unique strings (use format: "type_timestamp_random" e.g., "phase_1", "day_1", "ex_bench_1")
- Dates should be ISO 8601 format (e.g., "2024-01-15T10:30:00Z")
- RPE values are 1-10 scale (Rate of Perceived Exertion)
- Tempo format is "eccentric-pauseBottom-concentric-pauseTop" (e.g., "3-1-2-0")
- Rest times are in seconds
- Duration is in minutes
- Weight can be number (kg) or string ("bodyweight", "RPE 8")
- Reps can be number or string ("8-12", "AMRAP")
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional, Union

from pydantic import BaseModel, Field


# ============================================================================
# Enums as Literal Types
# ============================================================================

PlanType = Literal["single", "weekly", "program"]
Difficulty = Literal["beginner", "intermediate", "advanced"]
BlockType = Literal["superset", "circuit", "straight", "emom", "amrap"]
SetType = Literal["warmup", "working", "dropset", "failure", "backoff"]
FeedbackType = Literal["too_easy", "too_hard", "injury", "missed", "completed"]


# ============================================================================
# Set & Exercise Models
# ============================================================================


class ActualPerformance(BaseModel):
    """Logged performance data for a completed set."""

    reps: int = Field(..., description="Actual reps performed")
    weight: float = Field(..., description="Actual weight used in kg")
    rpe: int = Field(..., ge=1, le=10, description="Rate of Perceived Exertion 1-10")
    completed_at: str = Field(..., alias="completedAt", description="ISO 8601 timestamp")
    notes: Optional[str] = None

    class Config:
        populate_by_name = True


class ExerciseSet(BaseModel):
    """A single set within an exercise."""

    set_number: int = Field(..., alias="setNumber", ge=1, description="Set number starting from 1")
    type: SetType = Field(..., description="Type of set: warmup, working, dropset, failure, backoff")
    target_reps: Union[int, str] = Field(
        ..., alias="targetReps", description="Target reps (number) or range ('8-12') or 'AMRAP'"
    )
    target_weight: Optional[Union[int, float, str]] = Field(
        None, alias="targetWeight", description="Target weight in kg, or 'bodyweight', or 'RPE 8'"
    )
    target_rpe: Optional[int] = Field(None, alias="targetRpe", ge=1, le=10, description="Target RPE 1-10")
    actual: Optional[ActualPerformance] = Field(None, description="Logged performance (null until completed)")

    class Config:
        populate_by_name = True


class MuscleGroups(BaseModel):
    """Primary and secondary muscle groups targeted."""

    primary: list[str] = Field(..., description="Primary muscles: chest, back, legs, shoulders, arms, abs, etc.")
    secondary: list[str] = Field(default_factory=list, description="Secondary/stabilizer muscles")


class Exercise(BaseModel):
    """A single exercise with sets and coaching info."""

    id: str = Field(..., description="Unique ID, e.g., 'ex_bench_1'")
    name: str = Field(..., description="Exercise name, e.g., 'Barbell Bench Press'")
    equipment: list[str] = Field(
        default_factory=list, description="Required equipment: barbell, dumbbells, cable, bodyweight, etc."
    )
    muscle_groups: MuscleGroups = Field(..., alias="muscleGroups")
    sets: list[ExerciseSet] = Field(..., min_length=1, description="List of sets for this exercise")
    rest_between_sets: int = Field(..., alias="restBetweenSets", ge=0, description="Rest time in seconds between sets")
    tempo: Optional[str] = Field(None, description="Tempo notation: 'eccentric-pause-concentric-pause', e.g., '3-1-2-0'")
    notes: Optional[str] = Field(None, description="Exercise-specific notes or modifications")
    video_url: Optional[str] = Field(None, alias="videoUrl", description="URL to exercise demonstration video")
    alternatives: list[str] = Field(default_factory=list, description="Alternative exercise names if equipment unavailable")
    cues: list[str] = Field(default_factory=list, description="Form cues for proper execution")
    common_mistakes: list[str] = Field(
        default_factory=list, alias="commonMistakes", description="Common mistakes to avoid"
    )

    class Config:
        populate_by_name = True


class ExerciseBlock(BaseModel):
    """A block of exercises (can be superset, circuit, or straight sets)."""

    id: str = Field(..., description="Unique ID, e.g., 'block_1'")
    type: BlockType = Field(..., description="Block type: straight, superset, circuit, emom, amrap")
    exercises: list[Exercise] = Field(..., min_length=1, description="Exercises in this block")
    rest_between_rounds: Optional[int] = Field(
        None, alias="restBetweenRounds", description="Rest between rounds/circuits in seconds"
    )
    rounds: Optional[int] = Field(None, ge=1, description="Number of rounds for circuits")

    class Config:
        populate_by_name = True


# ============================================================================
# Day & Week Models
# ============================================================================


class WorkoutDay(BaseModel):
    """A single workout day."""

    id: str = Field(..., description="Unique ID, e.g., 'day_1_push'")
    day_number: int = Field(..., alias="dayNumber", ge=1, le=7, description="Day number 1-7")
    name: str = Field(..., description="Day name, e.g., 'Push Day A', 'Upper Body', 'Full Body'")
    target_duration: int = Field(..., alias="targetDuration", ge=0, description="Target duration in minutes")
    muscle_groups: list[str] = Field(..., alias="muscleGroups", description="Main muscle groups trained this day")
    warmup: Optional[ExerciseBlock] = Field(None, description="Optional warmup block")
    blocks: list[ExerciseBlock] = Field(default_factory=list, description="Main workout blocks")
    cooldown: Optional[ExerciseBlock] = Field(None, description="Optional cooldown block")
    rest_day: bool = Field(False, alias="restDay", description="True if this is a rest/recovery day")
    notes: Optional[str] = Field(None, description="Day-specific notes or focus points")

    class Config:
        populate_by_name = True


class Week(BaseModel):
    """A week of training."""

    week_number: int = Field(..., alias="weekNumber", ge=1, description="Week number in the program")
    focus: str = Field(..., description="Week focus: 'Volume', 'Intensity', 'Strength', 'Deload', etc.")
    is_deload: bool = Field(False, alias="isDeload", description="True if this is a deload/recovery week")
    days: list[WorkoutDay] = Field(..., min_length=1, max_length=7, description="Workout days for this week")

    class Config:
        populate_by_name = True


# ============================================================================
# Phase & Program Models
# ============================================================================


class Phase(BaseModel):
    """A training phase (mesocycle)."""

    id: str = Field(..., description="Unique ID, e.g., 'phase_foundation'")
    name: str = Field(..., description="Phase name: 'Foundation', 'Hypertrophy', 'Strength', 'Peak', 'Deload'")
    objective: str = Field(..., description="Phase objective/goal description")
    week_start: int = Field(..., alias="weekStart", ge=1, description="Starting week number")
    week_end: int = Field(..., alias="weekEnd", ge=1, description="Ending week number")
    weeks: list[Week] = Field(..., min_length=1, description="Weeks in this phase")

    class Config:
        populate_by_name = True


# ============================================================================
# AI Context & Tracking Models
# ============================================================================


class AIContext(BaseModel):
    """Context for AI generation and adaptation."""

    user_profile_snapshot: dict = Field(
        default_factory=dict, alias="userProfileSnapshot", description="User profile at generation time"
    )
    generation_prompt: str = Field(default="", alias="generationPrompt", description="The prompt used to generate this plan")
    model_version: str = Field(default="1.0", alias="modelVersion", description="AI model version used")

    class Config:
        populate_by_name = True


class PreviousRecord(BaseModel):
    """Previous personal record data."""

    weight: float
    reps: int
    achieved_at: str = Field(..., alias="achievedAt")

    class Config:
        populate_by_name = True


class PersonalRecord(BaseModel):
    """Personal record for an exercise."""

    exercise_name: str = Field(..., alias="exerciseName")
    weight: float = Field(..., description="Weight in kg")
    reps: int = Field(..., ge=1)
    achieved_at: str = Field(..., alias="achievedAt", description="ISO 8601 timestamp")
    previous_record: Optional[PreviousRecord] = Field(None, alias="previousRecord")

    class Config:
        populate_by_name = True


class FeedbackEntry(BaseModel):
    """User feedback entry for AI adaptation."""

    id: str
    date: str = Field(..., description="ISO 8601 timestamp")
    type: FeedbackType
    workout_day_id: str = Field(..., alias="workoutDayId")
    notes: Optional[str] = None
    ai_suggestion: Optional[str] = Field(None, alias="aiSuggestion", description="AI response to feedback")

    class Config:
        populate_by_name = True


class ProgressTracker(BaseModel):
    """Tracks user progress through the program."""

    started_at: Optional[str] = Field(default=None, alias="startedAt", description="ISO 8601 timestamp when started")
    current_week: int = Field(default=1, alias="currentWeek", ge=1)
    current_day: int = Field(default=1, alias="currentDay", ge=1)
    completed_workouts: list[str] = Field(
        default_factory=list, alias="completedWorkouts", description="List of completed workout day IDs"
    )
    personal_records: dict[str, PersonalRecord] = Field(default_factory=dict, alias="personalRecords")
    feedback: list[FeedbackEntry] = Field(default_factory=list)

    class Config:
        populate_by_name = True


# ============================================================================
# Main Workout Plan Model
# ============================================================================


class WorkoutPlan(BaseModel):
    """
    Complete workout plan schema.

    AI GENERATION INSTRUCTIONS:
    1. Generate a complete plan with all required fields
    2. Use realistic exercise progressions
    3. Include proper warm-up and cooldown for each day
    4. Vary rep ranges based on goals:
       - Strength: 1-5 reps, high weight
       - Hypertrophy: 8-12 reps, moderate weight
       - Endurance: 15-20+ reps, lower weight
    5. Include rest days (typically 1-2 per week)
    6. Deload weeks every 4-6 weeks (reduce volume/intensity by 40-50%)
    7. Progress difficulty across phases
    8. Match exercises to available equipment
    9. Respect user injuries and exercise dislikes
    """

    # Metadata
    id: str = Field(..., description="Unique plan ID, e.g., 'wrk_abc123'")
    version: int = Field(1, ge=1, description="Schema version for migrations")
    generated_at: str = Field(..., alias="generatedAt", description="ISO 8601 timestamp")
    plan_type: PlanType = Field(..., alias="planType", description="single, weekly, or program")

    # Program Info
    name: str = Field(..., description="Plan name, e.g., '12-Week Strength Builder'")
    description: str = Field(..., description="Plan description and overview")
    duration_weeks: int = Field(..., alias="durationWeeks", ge=1, le=52, description="Total program duration in weeks")
    difficulty: Difficulty = Field(..., description="beginner, intermediate, or advanced")
    goal: str = Field(
        ..., description="Primary goal: build_muscle, lose_weight, strength, endurance, general_fitness"
    )

    # AI Context
    ai_context: AIContext = Field(default=AIContext(), alias="aiContext")

    # Program Structure
    phases: list[Phase] = Field(..., min_length=1, description="Training phases/mesocycles")

    # Tracking (initialize with defaults for new plans)
    progress: ProgressTracker = Field(default=ProgressTracker())

    class Config:
        populate_by_name = True


# ============================================================================
# AI Generation Prompt Context
# ============================================================================

AI_WORKOUT_GENERATION_CONTEXT = """
You are generating a workout plan. Output ONLY valid, raw JSON matching the WorkoutPlan schema.

⚠️ CRITICAL JSON FORMAT RULES:
- Output RAW JSON only - no escaped quotes, no string encoding
- NEVER output JSON like this: { \\"key\\": \\"value\\" } or { \"key\": \"value\" }
- ALWAYS output clean JSON like this: { "key": "value" }
- NO explanatory text before, during, or after the JSON
- NO markdown code blocks around the JSON
- NO messages like "Here is your workout plan:" or "The plan is ready"
- Just output the pure JSON object starting with { and ending with }

SCHEMA OVERVIEW:
- WorkoutPlan contains phases (mesocycles)
- Each Phase contains weeks
- Each Week contains days (WorkoutDay)
- Each WorkoutDay contains exercise blocks
- Each ExerciseBlock contains exercises
- Each Exercise contains sets

REQUIRED FIELDS FOR EACH LEVEL:
1. WorkoutPlan: id, generatedAt, planType, name, description, durationWeeks, difficulty, goal, phases
2. Phase: id, name, objective, weekStart, weekEnd, weeks
3. Week: weekNumber, focus, isDeload, days
4. WorkoutDay: id, dayNumber, name, targetDuration, muscleGroups, blocks, restDay
5. ExerciseBlock: id, type, exercises
6. Exercise: id, name, muscleGroups, sets, restBetweenSets, equipment, alternatives, cues, commonMistakes
7. ExerciseSet: setNumber, type, targetReps (ALWAYS REQUIRED)

⚠️ CRITICAL - targetReps IS ALWAYS REQUIRED:
- Every set MUST have "targetReps" - this field is NEVER optional
- For rep-based exercises: use the number of reps (e.g., "targetReps": 10)
- For time-based/isometric exercises (planks, wall sits, holds): use "targetReps": 1
  * For these exercises, add duration info in the "notes" field of the exercise
  * Example: A 60-second plank hold should have "targetReps": 1 and notes: "Hold for 60 seconds"
- For AMRAP exercises: use "targetReps": "AMRAP"
- For rep ranges: use string format like "targetReps": "8-12"
- DO NOT invent fields like "targetDurationSeconds" - this field does not exist in the schema!

EXERCISE BLOCK TYPES:
- "straight": Complete all sets of one exercise before moving to next
- "superset": Alternate between 2 exercises with minimal rest
- "circuit": Perform all exercises back-to-back, then rest
- "emom": Every Minute On the Minute
- "amrap": As Many Rounds As Possible

SET TYPES:
- "warmup": Light weight, higher reps to prepare
- "working": Main working sets at target intensity
- "dropset": Reduce weight immediately and continue
- "failure": Push to muscular failure
- "backoff": Reduced intensity after heavy sets

MUSCLE GROUPS:
Primary: chest, back, shoulders, biceps, triceps, quads, hamstrings, glutes, calves, abs, core
Secondary: forearms, traps, rear_delts, hip_flexors, obliques

EXAMPLE - TIME-BASED EXERCISE (PLANK):
{
  "id": "ex_plank_1",
  "name": "Plank",
  "equipment": [],
  "muscleGroups": { "primary": ["core", "abs"], "secondary": ["shoulders"] },
  "sets": [
    {"setNumber": 1, "type": "working", "targetReps": 1}
  ],
  "restBetweenSets": 60,
  "notes": "Hold for 60 seconds",
  "alternatives": ["Side Plank", "Dead Bug"],
  "cues": ["Keep body in straight line", "Brace core"],
  "commonMistakes": ["Hips too high", "Hips sagging"]
}

EXAMPLE STRUCTURE:
{
  "id": "wrk_strength_12wk",
  "version": 1,
  "generatedAt": "2024-01-15T10:00:00Z",
  "planType": "program",
  "name": "12-Week Strength Foundation",
  "description": "Build foundational strength with progressive overload",
  "durationWeeks": 12,
  "difficulty": "intermediate",
  "goal": "strength",
  "aiContext": {
    "userProfileSnapshot": {},
    "generationPrompt": "...",
    "modelVersion": "1.0"
  },
  "phases": [
    {
      "id": "phase_1",
      "name": "Foundation",
      "objective": "Build movement patterns and base strength",
      "weekStart": 1,
      "weekEnd": 4,
      "weeks": [
        {
          "weekNumber": 1,
          "focus": "Volume",
          "isDeload": false,
          "days": [
            {
              "id": "w1_d1",
              "dayNumber": 1,
              "name": "Push Day",
              "targetDuration": 60,
              "muscleGroups": ["chest", "shoulders", "triceps"],
              "restDay": false,
              "blocks": [
                {
                  "id": "block_1",
                  "type": "straight",
                  "exercises": [
                    {
                      "id": "ex_bench_1",
                      "name": "Barbell Bench Press",
                      "equipment": ["barbell", "bench"],
                      "muscleGroups": {
                        "primary": ["chest"],
                        "secondary": ["triceps", "shoulders"]
                      },
                      "sets": [
                        {"setNumber": 1, "type": "warmup", "targetReps": 12, "targetWeight": 40},
                        {"setNumber": 2, "type": "working", "targetReps": 8, "targetWeight": 60, "targetRpe": 7},
                        {"setNumber": 3, "type": "working", "targetReps": 8, "targetWeight": 60, "targetRpe": 8},
                        {"setNumber": 4, "type": "working", "targetReps": 8, "targetWeight": 60, "targetRpe": 9}
                      ],
                      "restBetweenSets": 120,
                      "tempo": "2-1-1-0",
                      "alternatives": ["Dumbbell Bench Press", "Machine Chest Press"],
                      "cues": ["Retract shoulder blades", "Arch upper back slightly", "Drive feet into floor"],
                      "commonMistakes": ["Bouncing bar off chest", "Flaring elbows too wide", "Lifting hips off bench"]
                    }
                  ]
                }
              ]
            }
          ]
        }
      ]
    }
  ]
}

GENERATION RULES:
1. Match exercises to user's available equipment
2. Respect injuries - avoid exercises that stress injured areas
3. Exclude disliked exercises, use alternatives
4. Scale difficulty to experience level
5. Include 4-6 exercises per workout day
6. 3-5 sets per exercise typically
7. Rest days every 2-3 training days
8. Deload every 4-6 weeks
9. Progressive overload across weeks (increase weight or reps)
10. Balance push/pull movements
11. Include compound movements before isolation
12. Warmup sets before heavy working sets
13. ALWAYS include targetReps for EVERY set - no exceptions!

OUTPUT ONLY THE RAW JSON OBJECT. NO TEXT. NO EXPLANATIONS. NO MARKDOWN.
"""


def get_example_workout_plan() -> dict:
    """Returns an example workout plan as a dictionary for reference."""
    return {
        "id": "wrk_example_001",
        "version": 1,
        "generatedAt": datetime.now().isoformat(),
        "planType": "program",
        "name": "4-Week Beginner Full Body",
        "description": "A beginner-friendly program focusing on fundamental movements and building exercise habits.",
        "durationWeeks": 4,
        "difficulty": "beginner",
        "goal": "general_fitness",
        "aiContext": {"userProfileSnapshot": {}, "generationPrompt": "", "modelVersion": "1.0"},
        "phases": [
            {
                "id": "phase_1",
                "name": "Foundation",
                "objective": "Learn proper form and build training consistency",
                "weekStart": 1,
                "weekEnd": 4,
                "weeks": [
                    {
                        "weekNumber": 1,
                        "focus": "Technique",
                        "isDeload": False,
                        "days": [
                            {
                                "id": "w1_d1",
                                "dayNumber": 1,
                                "name": "Full Body A",
                                "targetDuration": 45,
                                "muscleGroups": ["chest", "back", "legs", "core"],
                                "restDay": False,
                                "blocks": [
                                    {
                                        "id": "block_main",
                                        "type": "straight",
                                        "exercises": [
                                            {
                                                "id": "ex_squat",
                                                "name": "Goblet Squat",
                                                "equipment": ["dumbbell"],
                                                "muscleGroups": {
                                                    "primary": ["quads", "glutes"],
                                                    "secondary": ["core", "hamstrings"],
                                                },
                                                "sets": [
                                                    {
                                                        "setNumber": 1,
                                                        "type": "warmup",
                                                        "targetReps": 10,
                                                        "targetWeight": "bodyweight",
                                                    },
                                                    {
                                                        "setNumber": 2,
                                                        "type": "working",
                                                        "targetReps": 12,
                                                        "targetWeight": 10,
                                                        "targetRpe": 6,
                                                    },
                                                    {
                                                        "setNumber": 3,
                                                        "type": "working",
                                                        "targetReps": 12,
                                                        "targetWeight": 10,
                                                        "targetRpe": 7,
                                                    },
                                                ],
                                                "restBetweenSets": 90,
                                                "alternatives": ["Bodyweight Squat", "Leg Press"],
                                                "cues": [
                                                    "Keep chest up",
                                                    "Push knees out over toes",
                                                    "Sit back into heels",
                                                ],
                                                "commonMistakes": [
                                                    "Knees caving in",
                                                    "Rounding lower back",
                                                    "Rising on toes",
                                                ],
                                            }
                                        ],
                                    }
                                ],
                            },
                            {
                                "id": "w1_d2",
                                "dayNumber": 2,
                                "name": "Rest Day",
                                "targetDuration": 0,
                                "muscleGroups": [],
                                "restDay": True,
                                "blocks": [],
                            },
                        ],
                    }
                ],
            }
        ],
        "progress": {
            "currentWeek": 1,
            "currentDay": 1,
            "completedWorkouts": [],
            "personalRecords": {},
            "feedback": [],
        },
    }

