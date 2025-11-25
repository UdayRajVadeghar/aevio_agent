"""
Workout Generator Agent - Generates personalized workout plans based on user data from Supabase.
"""

import logging
from datetime import datetime
from typing import Optional, List
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
""".strip()


def fetch_user_info(user_id: str) -> str:
    """
    Fetch user information from Supabase database with Pydantic validation.

    Args:
        user_id: The unique identifier for the user (can be userId or id)

    Returns:
        String containing validated user information including fitness goals, preferences, etc.
    """
    try:
        # Initialize Supabase client
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

        # Fetch all relevant fields from UserProfile table
        # First try to find by userId, then by id
        response = supabase.table('UserProfile').select('*').eq('userId', user_id).execute()

        # If not found by userId, try by id
        if not response.data or len(response.data) == 0:
            response = supabase.table('UserProfile').select('*').eq('id', user_id).execute()

        if not response.data or len(response.data) == 0:
            logger.warning(f"No user profile found with userId or id: {user_id}")
            return f"Error: User profile not found with identifier: {user_id}"

        user_data = response.data[0]
        logger.info(f"Successfully fetched user profile for: {user_id}")

        # Validate and parse data using Pydantic
        try:
            # Parse full schema for validation
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
                thirtyDayGoal=full_profile.thirtyDayGoal
            )

            return workout_info.to_formatted_string()

        except Exception as validation_error:
            logger.error(f"Pydantic validation error: {str(validation_error)}")
            # Fallback: return raw data if validation fails
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
        "Use the generate_workout_plan tool to fetch user information from Supabase and create a personalized workout plan. "
        "When creating workout plans, be specific about exercises, sets, reps, and rest periods. "
        "Always consider the user's fitness level, available equipment, and any health conditions mentioned."
        "ask questions to the user to get more information about their goals and preferences."
        "if the user does not provide enough information, ask follow-up questions to get more information."
    ),
    tools=[fetch_user_info],
)
