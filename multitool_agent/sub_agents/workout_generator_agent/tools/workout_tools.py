"""
Workout Generator Agent Tools

Tools for generating and managing workout plans.
These tools are designed to be used with the Google ADK Agent framework.
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import ValidationError
from supabase import Client, create_client

from ....config import SUPABASE_KEY, SUPABASE_URL
from ..schemas import (
    AI_WORKOUT_GENERATION_CONTEXT,
    WorkoutPlan,
    get_example_workout_plan,
)
from .utils import (
    generate_block_id,
    generate_day_id,
    generate_exercise_id,
    generate_feedback_id,
    generate_phase_id,
    generate_week_id,
    generate_workout_id,
    get_current_timestamp,
)

# Initialize logger
logger = logging.getLogger(__name__)


# ============================================================================
# User Profile Pydantic Models (moved from agent.py for reuse)
# ============================================================================

from pydantic import BaseModel, Field, field_validator


class UserProfileSchema(BaseModel):
    """
    Pydantic model matching the Prisma UserProfile schema.
    Validates and structures data fetched from Supabase.
    """

    id: str
    userId: str

    # Basic Profile
    dateOfBirth: Optional[datetime] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    timezone: Optional[str] = None

    # Health & Wellness
    height: Optional[float] = None  # cm
    weight: Optional[float] = None  # kg
    activityLevel: Optional[str] = None
    primaryGoal: Optional[str] = None
    dietaryPreference: Optional[str] = None

    # Body Composition (optional but powerful for scientific plans)
    bodyFatPercentage: Optional[float] = None  # percentage
    waistCircumference: Optional[float] = None  # cm
    hipCircumference: Optional[float] = None  # cm
    restingHeartRate: Optional[int] = None  # bpm

    # Experience & Skill Level
    trainingExperience: Optional[str] = None  # "beginner", "intermediate", "advanced"
    exerciseFamiliarity: Optional[Dict[str, Any]] = None

    # Equipment Availability
    equipmentAvailable: Optional[Dict[str, Any]] = None

    # Workout Schedule & Preferences
    workoutDays: Optional[int] = None  # number of days per week (1-7)
    workoutDuration: Optional[int] = None  # preferred duration in minutes

    # Training Style & Preferences
    trainingStyle: List[str] = Field(default_factory=list)
    targetBodyParts: List[str] = Field(default_factory=list)
    exerciseDislikes: List[str] = Field(default_factory=list)

    # Lifestyle Factors
    stepCount: Optional[int] = None
    sleepHours: Optional[float] = None
    stressLevel: Optional[int] = None  # 1-5 scale
    workType: Optional[str] = None

    # Restrictions & Safety
    injuries: Optional[List[Dict[str, Any]]] = None

    # Accountability & Motivation
    motivationStyle: Optional[str] = None

    # Journaling
    journalingStyle: Optional[str] = None
    journalingTimeOfDay: Optional[str] = None
    moodTrackingEnabled: bool = False

    # Health Conditions
    healthConditions: List[str] = Field(default_factory=list)

    # Consent & Goals
    dataUsageConsent: bool = False
    thirtyDayGoal: Optional[str] = None

    # Onboarding Status
    onboardingCompleted: bool = False
    onboardingStep: int = 0

    createdAt: Optional[datetime] = None
    updatedAt: Optional[datetime] = None

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, v):
        if v and v not in ["male", "female", "other", "prefer_not_to_say"]:
            logger.warning(f"Unexpected gender value: {v}")
        return v

    @field_validator("activityLevel")
    @classmethod
    def validate_activity_level(cls, v):
        valid_levels = ["sedentary", "light", "moderate", "active", "athlete"]
        if v and v not in valid_levels:
            logger.warning(f"Unexpected activityLevel: {v}")
        return v

    @field_validator("trainingExperience")
    @classmethod
    def validate_training_experience(cls, v):
        valid_levels = ["beginner", "intermediate", "advanced"]
        if v and v not in valid_levels:
            logger.warning(f"Unexpected trainingExperience: {v}")
        return v


class WorkoutUserInfo(BaseModel):
    """
    Simplified model containing only fields relevant for workout planning.
    """

    id: str
    age: Optional[int] = None
    gender: Optional[str] = None
    height: Optional[float] = None
    weight: Optional[float] = None
    activityLevel: Optional[str] = None
    primaryGoal: Optional[str] = None
    dietaryPreference: Optional[str] = None
    healthConditions: List[str] = Field(default_factory=list)
    thirtyDayGoal: Optional[str] = None

    # Body Composition
    bodyFatPercentage: Optional[float] = None
    waistCircumference: Optional[float] = None
    hipCircumference: Optional[float] = None
    restingHeartRate: Optional[int] = None

    # Experience & Skill Level
    trainingExperience: Optional[str] = None
    exerciseFamiliarity: Optional[Dict[str, Any]] = None

    # Equipment Availability
    equipmentAvailable: Optional[Dict[str, Any]] = None

    # Workout Schedule & Preferences
    workoutDays: Optional[int] = None
    workoutDuration: Optional[int] = None

    # Training Style & Preferences
    trainingStyle: List[str] = Field(default_factory=list)
    targetBodyParts: List[str] = Field(default_factory=list)
    exerciseDislikes: List[str] = Field(default_factory=list)

    # Lifestyle Factors
    stepCount: Optional[int] = None
    sleepHours: Optional[float] = None
    stressLevel: Optional[int] = None
    workType: Optional[str] = None

    # Restrictions & Safety
    injuries: Optional[List[Dict[str, Any]]] = None

    # Accountability & Motivation
    motivationStyle: Optional[str] = None

    def _format_equipment(self) -> str:
        """Format equipment availability for display."""
        if not self.equipmentAvailable:
            return "Not specified"
        available = []
        for equip, value in self.equipmentAvailable.items():
            if isinstance(value, bool) and value:
                available.append(equip)
            elif isinstance(value, dict) and value.get("available"):
                weight_range = value.get("weightRange", "")
                available.append(f"{equip} ({weight_range})" if weight_range else equip)
        return ", ".join(available) if available else "None"

    def _format_exercise_familiarity(self) -> str:
        """Format exercise familiarity for display."""
        if not self.exerciseFamiliarity:
            return "Not specified"
        familiar = [ex for ex, knows in self.exerciseFamiliarity.items() if knows]
        unfamiliar = [ex for ex, knows in self.exerciseFamiliarity.items() if not knows]
        result = []
        if familiar:
            result.append(f"Familiar with: {', '.join(familiar)}")
        if unfamiliar:
            result.append(f"Needs guidance: {', '.join(unfamiliar)}")
        return " | ".join(result) if result else "Not specified"

    def _format_injuries(self) -> str:
        """Format injuries for display."""
        if not self.injuries:
            return "None reported"
        injury_strs = []
        for injury in self.injuries:
            area = injury.get("area", "Unknown")
            severity = injury.get("severity", "unknown")
            notes = injury.get("notes", "")
            injury_str = f"{area} ({severity})"
            if notes:
                injury_str += f" - {notes}"
            injury_strs.append(injury_str)
        return "; ".join(injury_strs)

    def to_formatted_string(self) -> str:
        """Convert user info to a readable string format for the agent."""
        return f"""
User Information:
- User ID: {self.id}
- Age: {self.age if self.age else 'N/A'}
- Gender: {self.gender if self.gender else 'N/A'}
- Height: {self.height if self.height else 'N/A'} cm
- Weight: {self.weight if self.weight else 'N/A'} kg
- Activity Level: {self.activityLevel if self.activityLevel else 'N/A'}
- Primary Goal: {self.primaryGoal if self.primaryGoal else 'N/A'}
- Dietary Preference: {self.dietaryPreference if self.dietaryPreference else 'N/A'}
- Health Conditions: {', '.join(self.healthConditions) if self.healthConditions else 'None reported'}
- 30-Day Goal: {self.thirtyDayGoal if self.thirtyDayGoal else 'N/A'}

Body Composition:
- Body Fat Percentage: {f'{self.bodyFatPercentage}%' if self.bodyFatPercentage else 'N/A'}
- Waist Circumference: {f'{self.waistCircumference} cm' if self.waistCircumference else 'N/A'}
- Hip Circumference: {f'{self.hipCircumference} cm' if self.hipCircumference else 'N/A'}
- Resting Heart Rate: {f'{self.restingHeartRate} bpm' if self.restingHeartRate else 'N/A'}

Experience & Skills:
- Training Experience: {self.trainingExperience if self.trainingExperience else 'N/A'}
- Exercise Familiarity: {self._format_exercise_familiarity()}

Equipment Available:
- {self._format_equipment()}

Workout Preferences:
- Workout Days per Week: {self.workoutDays if self.workoutDays else 'N/A'}
- Preferred Duration: {f'{self.workoutDuration} minutes' if self.workoutDuration else 'N/A'}
- Training Styles: {', '.join(self.trainingStyle) if self.trainingStyle else 'Not specified'}
- Target Body Parts: {', '.join(self.targetBodyParts) if self.targetBodyParts else 'Full body'}
- Exercise Dislikes: {', '.join(self.exerciseDislikes) if self.exerciseDislikes else 'None'}

Lifestyle Factors:
- Daily Step Count Target: {self.stepCount if self.stepCount else 'N/A'}
- Sleep Hours: {f'{self.sleepHours} hours' if self.sleepHours else 'N/A'}
- Stress Level: {f'{self.stressLevel}/5' if self.stressLevel else 'N/A'}
- Work Type: {self.workType if self.workType else 'N/A'}

Safety & Restrictions:
- Injuries: {self._format_injuries()}

Motivation:
- Motivation Style: {self.motivationStyle if self.motivationStyle else 'N/A'}
        """.strip()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for AI context snapshot."""
        return self.model_dump(exclude_none=True)


# ============================================================================
# Agent Tools
# ============================================================================


def fetch_user_info(user_id: str) -> str:
    """
    Fetch user information from Supabase database with Pydantic validation.

    Args:
        user_id: The unique identifier for the user (can be userId or id)

    Returns:
        String containing validated user information including fitness goals, preferences, etc.
    """
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

        response = supabase.table("UserProfile").select("*").eq("userId", user_id).execute()

        if not response.data or len(response.data) == 0:
            logger.warning(f"No user profile found with userId or id: {user_id}")
            return f"Error: User profile not found with identifier: {user_id}"

        user_data = response.data[0]
        logger.info(f"Successfully fetched user profile for: {user_id}")

        # Validate and parse data using Pydantic
        try:
            full_profile = UserProfileSchema.model_validate(user_data)

            # Extract workout-relevant fields
            workout_info = WorkoutUserInfo(
                id=full_profile.id,
                age=full_profile.age,
                gender=full_profile.gender,
                height=full_profile.height,
                weight=full_profile.weight,
                activityLevel=full_profile.activityLevel,
                primaryGoal=full_profile.primaryGoal,
                dietaryPreference=full_profile.dietaryPreference,
                healthConditions=full_profile.healthConditions,
                thirtyDayGoal=full_profile.thirtyDayGoal,
                # Body Composition
                bodyFatPercentage=full_profile.bodyFatPercentage,
                waistCircumference=full_profile.waistCircumference,
                hipCircumference=full_profile.hipCircumference,
                restingHeartRate=full_profile.restingHeartRate,
                # Experience & Skill Level
                trainingExperience=full_profile.trainingExperience,
                exerciseFamiliarity=full_profile.exerciseFamiliarity,
                # Equipment Availability
                equipmentAvailable=full_profile.equipmentAvailable,
                # Workout Schedule & Preferences
                workoutDays=full_profile.workoutDays,
                workoutDuration=full_profile.workoutDuration,
                # Training Style & Preferences
                trainingStyle=full_profile.trainingStyle,
                targetBodyParts=full_profile.targetBodyParts,
                exerciseDislikes=full_profile.exerciseDislikes,
                # Lifestyle Factors
                stepCount=full_profile.stepCount,
                sleepHours=full_profile.sleepHours,
                stressLevel=full_profile.stressLevel,
                workType=full_profile.workType,
                # Restrictions & Safety
                injuries=full_profile.injuries,
                # Accountability & Motivation
                motivationStyle=full_profile.motivationStyle,
            )

            return workout_info.to_formatted_string()

        except Exception as validation_error:
            logger.error(f"Pydantic validation error: {str(validation_error)}")
            return f"Warning: Data validation failed. Raw data: {user_data}"

    except Exception as e:
        logger.error(f"Error fetching user info for user_id {user_id}: {str(e)}")
        return f"Error: Failed to fetch user info - {str(e)}"


def generate_workout_plan_ids(
    num_phases: int = 1,
    weeks_per_phase: int = 4,
    days_per_week: int = 5,
    blocks_per_day: int = 3,
    exercises_per_block: int = 3,
) -> str:
    """
    Generate all unique IDs needed for a workout plan structure.
    
    Use this tool when creating a new workout plan to get pre-generated unique IDs.
    This ensures all IDs are unique and properly formatted.
    
    Args:
        num_phases: Number of training phases (default: 1)
        weeks_per_phase: Number of weeks per phase (default: 4)
        days_per_week: Number of workout days per week, not counting rest days (default: 5)
        blocks_per_day: Number of exercise blocks per workout day (default: 3)
        exercises_per_block: Number of exercises per block (default: 3)
    
    Returns:
        JSON string containing all generated IDs organized by structure
    """
    ids = {
        "workout_id": generate_workout_id(),
        "generated_at": get_current_timestamp(),
        "phases": [],
    }

    week_counter = 1

    for phase_num in range(1, num_phases + 1):
        phase_data = {"phase_id": generate_phase_id(phase_num), "phase_number": phase_num, "weeks": []}

        for _ in range(weeks_per_phase):
            week_num = week_counter
            week_data = {"week_id": generate_week_id(week_num), "week_number": week_num, "days": []}

            for day_num in range(1, days_per_week + 1):
                day_data = {
                    "day_id": generate_day_id(week_num, day_num),
                    "day_number": day_num,
                    "blocks": [],
                }

                for block_num in range(1, blocks_per_day + 1):
                    block_data = {
                        "block_id": generate_block_id(block_num),
                        "block_number": block_num,
                        "exercise_ids": [generate_exercise_id() for _ in range(exercises_per_block)],
                    }
                    day_data["blocks"].append(block_data)

                week_data["days"].append(day_data)

            phase_data["weeks"].append(week_data)
            week_counter += 1

        ids["phases"].append(phase_data)

    return json.dumps(ids, indent=2)


def get_workout_schema_info() -> str:
    """
    Get information about the workout plan schema and generation guidelines.
    
    Use this tool to understand the expected structure and rules for generating workout plans.
    
    Returns:
        String containing the schema documentation and an example workout plan structure
    """
    example = get_example_workout_plan()
    
    return f"""
{AI_WORKOUT_GENERATION_CONTEXT}

EXAMPLE WORKOUT PLAN STRUCTURE:
{json.dumps(example, indent=2, default=str)}

AVAILABLE ID GENERATION FUNCTIONS:
- Workout Plan ID: Use format 'wrk_xxxxxxxx'
- Phase ID: Use format 'phase_N_xxxxxxxx' where N is the phase number
- Week ID: Use format 'wN_xxxxxxxx' where N is the week number
- Day ID: Use format 'wN_dM_name_xxxxxxxx' where N is week, M is day number
- Block ID: Use format 'block_N_xxxxxxxx' where N is the block number
- Exercise ID: Use format 'ex_name_xxxxxxxx' where name is a short version of exercise name

TIMESTAMP FORMAT:
- Use ISO 8601 format: 'YYYY-MM-DDTHH:MM:SSZ'
- Example: '2024-01-15T10:30:00Z'

⚠️ REMINDERS:
1. Output CLEAN, RAW JSON only - no escaped quotes, no string encoding
2. Every set MUST have "targetReps" - use 1 for time-based exercises like planks
3. Do NOT invent fields like "targetDurationSeconds" - it doesn't exist
4. Do NOT add commentary before/after the JSON

Use the generate_workout_plan_ids tool to get pre-generated unique IDs for your workout plan.
"""


def validate_workout_plan(workout_plan_json: str) -> str:
    """
    Validate a workout plan JSON against the schema.
    
    Use this tool to check if a generated workout plan is valid before saving.
    
    Args:
        workout_plan_json: JSON string of the workout plan to validate
    
    Returns:
        String indicating validation success or detailed error messages
    """
    try:
        # Parse the JSON
        plan_data = json.loads(workout_plan_json)
        
        # Validate against Pydantic model
        validated_plan = WorkoutPlan.model_validate(plan_data)
        
        # Generate summary statistics
        total_phases = len(validated_plan.phases)
        total_weeks = sum(len(phase.weeks) for phase in validated_plan.phases)
        total_days = sum(
            len(week.days) 
            for phase in validated_plan.phases 
            for week in phase.weeks
        )
        total_exercises = sum(
            len(block.exercises)
            for phase in validated_plan.phases
            for week in phase.weeks
            for day in week.days
            for block in day.blocks
        )
        
        return f"""
✅ Workout plan is VALID!

Plan Summary:
- ID: {validated_plan.id}
- Name: {validated_plan.name}
- Duration: {validated_plan.duration_weeks} weeks
- Difficulty: {validated_plan.difficulty}
- Goal: {validated_plan.goal}

Structure:
- Phases: {total_phases}
- Total Weeks: {total_weeks}
- Total Workout Days: {total_days}
- Total Exercises: {total_exercises}

The plan is ready to be saved to the database.
"""
    
    except json.JSONDecodeError as e:
        return f"❌ Invalid JSON format: {str(e)}"
    
    except ValidationError as e:
        error_messages = []
        for error in e.errors():
            location = " -> ".join(str(loc) for loc in error["loc"])
            error_messages.append(f"  - {location}: {error['msg']}")
        
        return f"""
❌ Workout plan validation FAILED!

Errors found:
{chr(10).join(error_messages)}

Please fix these issues and try again.
"""
    
    except Exception as e:
        return f"❌ Unexpected error during validation: {str(e)}"


def get_current_datetime() -> str:
    """
    Get the current date and time in ISO 8601 format.
    
    Use this tool when you need the current timestamp for generated_at or other date fields.
    
    Returns:
        Current UTC timestamp in ISO 8601 format (e.g., '2024-01-15T10:30:00Z')
    """
    return get_current_timestamp()


def save_workout_plan(user_id: str, workout_plan_json: str) -> str:
    """
    Save a validated workout plan to the Supabase database.
    
    Args:
        user_id: The user ID to associate the workout plan with
        workout_plan_json: JSON string of the validated workout plan
    
    Returns:
        String indicating success or error message
    """
    try:
        # First validate the plan
        plan_data = json.loads(workout_plan_json)
        validated_plan = WorkoutPlan.model_validate(plan_data)
        
        # Connect to Supabase
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        # Prepare the data for insertion
        workout_record = {
            "userId": user_id,
            "rawWorkout": plan_data,  # Store the raw JSON
        }
        
        # Insert into Workout table
        response = supabase.table("Workout").insert(workout_record).execute()
        
        if response.data:
            first_record = response.data[0]
            workout_id = first_record["id"] if isinstance(first_record, dict) else "unknown"
            logger.info(f"Successfully saved workout plan {validated_plan.id} for user {user_id}")
            return f"""
✅ Workout plan saved successfully!

Database Record:
- Record ID: {workout_id}
- User ID: {user_id}
- Plan Name: {validated_plan.name}
- Duration: {validated_plan.duration_weeks} weeks

The workout plan is now available in the user's account.
"""
        else:
            return "❌ Failed to save workout plan: No data returned from database"
            
    except json.JSONDecodeError as e:
        return f"❌ Invalid JSON format: {str(e)}"
    
    except ValidationError as e:
        return f"❌ Workout plan validation failed. Please validate the plan first using validate_workout_plan tool."
    
    except Exception as e:
        logger.error(f"Error saving workout plan: {str(e)}")
        return f"❌ Failed to save workout plan: {str(e)}"


# ============================================================================
# Workout Plan Formatting for User Review
# ============================================================================


def format_workout_plan_for_review(workout_plan_json: str) -> str:
    """
    Format a workout plan JSON into a human-readable summary for user review.
    
    Use this tool after generating a workout plan to present it to the user
    in a clear, readable format before they confirm saving.
    
    Args:
        workout_plan_json: JSON string of the workout plan
    
    Returns:
        Human-readable formatted string of the workout plan
    """
    try:
        plan_data = json.loads(workout_plan_json)
        validated_plan = WorkoutPlan.model_validate(plan_data)
        
        output = []
        output.append("=" * 60)
        output.append(f"📋 {validated_plan.name}")
        output.append("=" * 60)
        output.append(f"\n📝 Description: {validated_plan.description}")
        output.append(f"⏱️  Duration: {validated_plan.duration_weeks} weeks")
        output.append(f"💪 Difficulty: {validated_plan.difficulty.upper()}")
        output.append(f"🎯 Goal: {validated_plan.goal.replace('_', ' ').title()}")
        
        for phase in validated_plan.phases:
            output.append(f"\n{'─' * 50}")
            output.append(f"📌 PHASE: {phase.name} (Weeks {phase.week_start}-{phase.week_end})")
            output.append(f"   Objective: {phase.objective}")
            
            for week in phase.weeks:
                output.append(f"\n   📅 Week {week.week_number} - Focus: {week.focus}" + 
                            (" (DELOAD)" if week.is_deload else ""))
                
                for day in week.days:
                    if day.rest_day:
                        output.append(f"      Day {day.day_number}: 🛋️  REST DAY")
                    else:
                        output.append(f"\n      Day {day.day_number}: {day.name} ({day.target_duration} min)")
                        output.append(f"      Targets: {', '.join(day.muscle_groups)}")
                        
                        for block in day.blocks:
                            block_type_emoji = {
                                "straight": "➡️",
                                "superset": "🔄",
                                "circuit": "🔁",
                                "emom": "⏰",
                                "amrap": "💥"
                            }
                            output.append(f"\n         {block_type_emoji.get(block.type, '•')} {block.type.upper()} Block:")
                            
                            for ex in block.exercises:
                                sets_info = []
                                for s in ex.sets:
                                    weight_str = ""
                                    if s.target_weight:
                                        weight_str = f" @ {s.target_weight}"
                                        if isinstance(s.target_weight, (int, float)):
                                            weight_str += "kg"
                                    rpe_str = f" RPE {s.target_rpe}" if s.target_rpe else ""
                                    sets_info.append(f"{s.type}: {s.target_reps} reps{weight_str}{rpe_str}")
                                
                                output.append(f"            • {ex.name}")
                                output.append(f"              Equipment: {', '.join(ex.equipment) if ex.equipment else 'Bodyweight'}")
                                output.append(f"              Sets: {len(ex.sets)} | Rest: {ex.rest_between_sets}s")
                                if ex.alternatives:
                                    output.append(f"              Alternatives: {', '.join(ex.alternatives[:2])}")
        
        output.append("\n" + "=" * 60)
        output.append("💬 Would you like to make any changes to this plan?")
        output.append("   You can ask to:")
        output.append("   • Swap exercises (e.g., 'replace squats with leg press')")
        output.append("   • Adjust sets/reps (e.g., 'make it 4 sets instead of 3')")
        output.append("   • Add/remove exercises")
        output.append("   • Change workout days or duration")
        output.append("   • Or say 'save it' when you're happy with the plan!")
        output.append("=" * 60)
        
        return "\n".join(output)
        
    except json.JSONDecodeError as e:
        return f"❌ Error parsing workout plan JSON: {str(e)}"
    except ValidationError as e:
        return f"❌ Invalid workout plan structure: {str(e)}"
    except Exception as e:
        return f"❌ Error formatting workout plan: {str(e)}"


def summarize_workout_changes(original_json: str, updated_json: str) -> str:
    """
    Compare two workout plans and summarize what changed.
    
    Use this after modifying a workout plan to show the user what was updated.
    
    Args:
        original_json: The original workout plan JSON
        updated_json: The updated workout plan JSON
    
    Returns:
        Summary of changes made to the workout plan
    """
    try:
        original = json.loads(original_json)
        updated = json.loads(updated_json)
        
        changes = []
        
        # Check top-level changes
        if original.get("name") != updated.get("name"):
            changes.append(f"📝 Plan name: '{original.get('name')}' → '{updated.get('name')}'")
        
        if original.get("durationWeeks") != updated.get("durationWeeks"):
            changes.append(f"⏱️  Duration: {original.get('durationWeeks')} weeks → {updated.get('durationWeeks')} weeks")
        
        if original.get("difficulty") != updated.get("difficulty"):
            changes.append(f"💪 Difficulty: {original.get('difficulty')} → {updated.get('difficulty')}")
        
        # Count exercises in each plan
        def count_exercises(plan):
            count = 0
            for phase in plan.get("phases", []):
                for week in phase.get("weeks", []):
                    for day in week.get("days", []):
                        for block in day.get("blocks", []):
                            count += len(block.get("exercises", []))
            return count
        
        orig_ex_count = count_exercises(original)
        upd_ex_count = count_exercises(updated)
        
        if orig_ex_count != upd_ex_count:
            diff = upd_ex_count - orig_ex_count
            if diff > 0:
                changes.append(f"➕ Added {diff} exercise(s)")
            else:
                changes.append(f"➖ Removed {abs(diff)} exercise(s)")
        
        # Count workout days
        def count_workout_days(plan):
            count = 0
            for phase in plan.get("phases", []):
                for week in phase.get("weeks", []):
                    for day in week.get("days", []):
                        if not day.get("restDay", False):
                            count += 1
            return count
        
        orig_days = count_workout_days(original)
        upd_days = count_workout_days(updated)
        
        if orig_days != upd_days:
            changes.append(f"📅 Workout days: {orig_days} → {upd_days}")
        
        if not changes:
            return "✅ No significant structural changes detected. Minor adjustments may have been made to sets, reps, or weights."
        
        return "🔄 Changes made:\n" + "\n".join(changes)
        
    except Exception as e:
        return f"Could not compare plans: {str(e)}"


# ============================================================================
# Export all tools for the agent
# ============================================================================

WORKOUT_AGENT_TOOLS = [
    fetch_user_info,
    generate_workout_plan_ids,
    get_workout_schema_info,
    validate_workout_plan,
    get_current_datetime,
    save_workout_plan,
    format_workout_plan_for_review,
    summarize_workout_changes,
]

