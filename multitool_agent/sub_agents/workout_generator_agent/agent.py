"""
Workout Generator Agent - Generates personalized workout plans based on user data from Supabase.
"""

import logging
from typing import Optional, Dict, Any
from google.adk.tools.tool_context import ToolContext
from google.adk.agents import Agent
from supabase import create_client, Client

from ...config import (
    SUPABASE_URL,
    SUPABASE_KEY,
)

# Initialize logger
logger = logging.getLogger(__name__)


def fetch_user_info(user_id: str, context: ToolContext) -> str:
    """
    Fetch user information from Supabase database.

    Args:
        user_id: The unique identifier for the user
        context: Tool context for logging and execution

    Returns:
        String containing user information including fitness goals, preferences, etc.
    """
    try:
        # Initialize Supabase client
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

        # Basic query: Fetch user data from the users table
        # Select specific fields that are relevant for workout planning
        response = supabase.table('users').select(
            'id, name, age, gender, fitness_level, goals, preferred_workout_type, '
            'available_equipment, workout_duration_preference, workout_frequency, '
            'health_conditions, created_at'
        ).eq('id', user_id).execute()

        if not response.data or len(response.data) == 0:
            logger.warning(f"No user found with id: {user_id}")
            return f"Error: User not found with id: {user_id}"

        user_data = response.data[0]
        logger.info(f"Successfully fetched user info for user_id: {user_id}")

        # Format the user data as a readable string
        user_info = f"""
User Information:
- User ID: {user_data.get('id', 'N/A')}
- Name: {user_data.get('name', 'N/A')}
- Age: {user_data.get('age', 'N/A')}
- Gender: {user_data.get('gender', 'N/A')}
- Fitness Level: {user_data.get('fitness_level', 'N/A')}
- Goals: {user_data.get('goals', 'N/A')}
- Preferred Workout Type: {user_data.get('preferred_workout_type', 'N/A')}
- Available Equipment: {user_data.get('available_equipment', 'N/A')}
- Workout Duration Preference: {user_data.get('workout_duration_preference', 'N/A')}
- Workout Frequency: {user_data.get('workout_frequency', 'N/A')}
- Health Conditions: {user_data.get('health_conditions', 'None reported')}
"""
        return user_info.strip()

    except Exception as e:
        logger.error(f"Error fetching user info for user_id {user_id}: {str(e)}")
        return f"Error: Failed to fetch user info - {str(e)}"


def generate_workout_plan(user_id: str, context: ToolContext) -> str:
    """
    Generate a personalized workout plan based on user information from Supabase.

    Args:
        user_id: The unique identifier for the user
        context: Tool context for logging and execution

    Returns:
        String containing a personalized workout plan
    """
    # Fetch user information first
    user_info = fetch_user_info(user_id, context)

    if user_info.startswith("Error:"):
        return user_info

    return f"""
{user_info}

Based on the above information, I will now generate a personalized workout plan.
Please use this information to create a workout plan that:
1. Matches the user's fitness level and goals
2. Considers their available equipment
3. Fits their preferred workout duration and frequency
4. Takes into account any health conditions
5. Aligns with their preferred workout type
"""


workout_planner_agent = Agent(
    name="workout_planner_agent",
    model="gemini-2.5-flash",
    description="This agent is responsible for generating a workout plan based on the user's goals and preferences fetched from Supabase.",
    instruction=(
        "You are a workout planner agent. You are responsible for generating a workout plan based on the user's goals and preferences. "
        "Use the generate_workout_plan tool to fetch user information from Supabase and create a personalized workout plan. "
        "Keep the tone warm and conversational — like a regular Indian conversational style. "
        "Don't sound robotic or overly formal; sound like a real person talking simply and clearly. "
        "Please dont use ** or * for bold. "
        "When creating workout plans, be specific about exercises, sets, reps, and rest periods. "
        "Always consider the user's fitness level, available equipment, and any health conditions mentioned."
    ),
    tools=[fetch_user_info, generate_workout_plan],
)   