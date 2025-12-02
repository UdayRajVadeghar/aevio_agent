"""
Workout Generator Agent - Generates personalized workout plans based on user data from Supabase.
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator
from google.adk.agents import Agent
from supabase import create_client, Client

from ...config import (
    SUPABASE_URL,
    SUPABASE_KEY,
)

# Initialize logger
logger = logging.getLogger(__name__)


# Pydantic Models
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
    exerciseFamiliarity: Optional[Dict[str, Any]] = None  # { squat: true, deadlift: false, pullup: true, pushup: true }

    # Equipment Availability
    equipmentAvailable: Optional[Dict[str, Any]] = None  # { gym: true, dumbbells: { available: true, weightRange: "5-50" }, ... }

    # Workout Schedule & Preferences
    workoutDays: Optional[int] = None  # number of days per week (1-7)
    workoutDuration: Optional[int] = None  # preferred duration in minutes (20, 30, 45, 60, 90)

    # Training Style & Preferences
    trainingStyle: List[str] = Field(default_factory=list)  # ["hiit", "strength", "calisthenics", "yoga", "functional", "crossfit", "pilates"]
    targetBodyParts: List[str] = Field(default_factory=list)  # ["chest", "shoulders", "arms", "abs", "legs", "back"]
    exerciseDislikes: List[str] = Field(default_factory=list)  # ["running", "burpees", "jumping jacks"]

    # Lifestyle Factors
    stepCount: Optional[int] = None  # daily step count target
    sleepHours: Optional[float] = None  # hours per day
    stressLevel: Optional[int] = None  # 1-5 scale
    workType: Optional[str] = None  # "desk_job", "on_feet", "heavy_labor"

    # Restrictions & Safety
    injuries: Optional[List[Dict[str, Any]]] = None  # [{ area: "knee", severity: "mild", notes: "avoid deep squats" }]

    # Accountability & Motivation
    motivationStyle: Optional[str] = None  # "strict", "chill", "encouraging"

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

    @field_validator('gender')
    @classmethod
    def validate_gender(cls, v):
        if v and v not in ['male', 'female', 'other', 'prefer_not_to_say']:
            logger.warning(f"Unexpected gender value: {v}")
        return v

    @field_validator('activityLevel')
    @classmethod
    def validate_activity_level(cls, v):
        valid_levels = ['sedentary', 'light', 'moderate', 'active', 'athlete']
        if v and v not in valid_levels:
            logger.warning(f"Unexpected activityLevel: {v}")
        return v

    @field_validator('dietaryPreference')
    @classmethod
    def validate_dietary_preference(cls, v):
        valid_prefs = ['veg', 'non_veg', 'vegan', 'keto']
        if v and v not in valid_prefs:
            logger.warning(f"Unexpected dietaryPreference: {v}")
        return v

    @field_validator('trainingExperience')
    @classmethod
    def validate_training_experience(cls, v):
        valid_levels = ['beginner', 'intermediate', 'advanced']
        if v and v not in valid_levels:
            logger.warning(f"Unexpected trainingExperience: {v}")
        return v

    @field_validator('workoutDays')
    @classmethod
    def validate_workout_days(cls, v):
        if v and (v < 1 or v > 7):
            logger.warning(f"workoutDays should be between 1-7, got: {v}")
        return v

    @field_validator('stressLevel')
    @classmethod
    def validate_stress_level(cls, v):
        if v and (v < 1 or v > 5):
            logger.warning(f"stressLevel should be between 1-5, got: {v}")
        return v

    @field_validator('workType')
    @classmethod
    def validate_work_type(cls, v):
        valid_types = ['desk_job', 'on_feet', 'heavy_labor']
        if v and v not in valid_types:
            logger.warning(f"Unexpected workType: {v}")
        return v

    @field_validator('motivationStyle')
    @classmethod
    def validate_motivation_style(cls, v):
        valid_styles = ['strict', 'chill', 'encouraging']
        if v and v not in valid_styles:
            logger.warning(f"Unexpected motivationStyle: {v}")
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
            return 'Not specified'
        available = []
        for equip, value in self.equipmentAvailable.items():
            if isinstance(value, bool) and value:
                available.append(equip)
            elif isinstance(value, dict) and value.get('available'):
                weight_range = value.get('weightRange', '')
                available.append(f"{equip} ({weight_range})" if weight_range else equip)
        return ', '.join(available) if available else 'None'

    def _format_exercise_familiarity(self) -> str:
        """Format exercise familiarity for display."""
        if not self.exerciseFamiliarity:
            return 'Not specified'
        familiar = [ex for ex, knows in self.exerciseFamiliarity.items() if knows]
        unfamiliar = [ex for ex, knows in self.exerciseFamiliarity.items() if not knows]
        result = []
        if familiar:
            result.append(f"Familiar with: {', '.join(familiar)}")
        if unfamiliar:
            result.append(f"Needs guidance: {', '.join(unfamiliar)}")
        return ' | '.join(result) if result else 'Not specified'

    def _format_injuries(self) -> str:
        """Format injuries for display."""
        if not self.injuries:
            return 'None reported'
        injury_strs = []
        for injury in self.injuries:
            area = injury.get('area', 'Unknown')
            severity = injury.get('severity', 'unknown')
            notes = injury.get('notes', '')
            injury_str = f"{area} ({severity})"
            if notes:
                injury_str += f" - {notes}"
            injury_strs.append(injury_str)
        return '; '.join(injury_strs)

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


# this function fetches user information from the Supabase database and returns a string containing the user information
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
        
        response = supabase.table('UserProfile').select('*').eq('userId', user_id).execute()

     
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




workout_planner_agent = Agent(
    name="workout_planner_agent",
    model="gemini-2.5-flash",
    description="This agent is responsible for generating a workout plan based on the user's goals and preferences fetched from Supabase.",
    instruction=(
        "You are a workout planner agent. You are responsible for generating a workout plan based on the user's goals and preferences. "
        "Use the fetch_user_info tool to fetch user information from Supabase postgres db."
        "When creating workout plans, be specific about exercises, sets, reps, and rest periods. "
        "Always consider the user's fitness level, available equipment, and any health conditions mentioned."
        "ask questions to the user to get more information about their goals and preferences."
        "if the user does not provide enough information, ask follow-up questions to get more information."
    ),
    tools=[fetch_user_info ],
)
