"""
Utility functions for workout plan generation.

Provides ID generation, timestamp handling, and other helper functions.
"""

import secrets
import string
from datetime import datetime, timezone
from typing import Optional


def _generate_random_suffix(length: int = 8) -> str:
    """
    Generate a random alphanumeric suffix.
    
    Args:
        length: Length of the random string (default: 8)
        
    Returns:
        Random alphanumeric string
    """
    alphabet = string.ascii_lowercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def generate_id(prefix: str, suffix: Optional[str] = None) -> str:
    """
    Generate a unique ID with the given prefix.
    
    Format: prefix_random or prefix_suffix_random
    
    Args:
        prefix: The prefix for the ID (e.g., 'wrk', 'phase', 'day')
        suffix: Optional additional suffix before random string
        
    Returns:
        Unique ID string
        
    Example:
        >>> generate_id("wrk")
        'wrk_a1b2c3d4'
        >>> generate_id("ex", "bench")
        'ex_bench_a1b2c3d4'
    """
    random_part = _generate_random_suffix()
    if suffix:
        return f"{prefix}_{suffix}_{random_part}"
    return f"{prefix}_{random_part}"


def generate_workout_id() -> str:
    """
    Generate a unique workout plan ID.
    
    Returns:
        Workout ID in format 'wrk_xxxxxxxx'
    """
    return generate_id("wrk")


def generate_phase_id(phase_number: Optional[int] = None) -> str:
    """
    Generate a unique phase ID.
    
    Args:
        phase_number: Optional phase number to include
        
    Returns:
        Phase ID in format 'phase_n_xxxxxxxx' or 'phase_xxxxxxxx'
    """
    if phase_number is not None:
        return generate_id("phase", str(phase_number))
    return generate_id("phase")


def generate_week_id(week_number: int) -> str:
    """
    Generate a unique week ID.
    
    Args:
        week_number: The week number in the program
        
    Returns:
        Week ID in format 'w{n}_xxxxxxxx'
    """
    return generate_id(f"w{week_number}")


def generate_day_id(week_number: int, day_number: int, day_name: Optional[str] = None) -> str:
    """
    Generate a unique workout day ID.
    
    Args:
        week_number: The week number in the program
        day_number: The day number in the week (1-7)
        day_name: Optional descriptive name (e.g., 'push', 'pull', 'legs')
        
    Returns:
        Day ID in format 'w{week}_d{day}_name_xxxxxxxx' or 'w{week}_d{day}_xxxxxxxx'
        
    Example:
        >>> generate_day_id(1, 1, "push")
        'w1_d1_push_a1b2c3d4'
    """
    prefix = f"w{week_number}_d{day_number}"
    if day_name:
        # Clean the day name for use in ID
        clean_name = day_name.lower().replace(" ", "_")[:10]
        return generate_id(prefix, clean_name)
    return generate_id(prefix)


def generate_block_id(block_number: Optional[int] = None) -> str:
    """
    Generate a unique exercise block ID.
    
    Args:
        block_number: Optional block number to include
        
    Returns:
        Block ID in format 'block_n_xxxxxxxx' or 'block_xxxxxxxx'
    """
    if block_number is not None:
        return generate_id("block", str(block_number))
    return generate_id("block")


def generate_exercise_id(exercise_name: Optional[str] = None) -> str:
    """
    Generate a unique exercise ID.
    
    Args:
        exercise_name: Optional exercise name to include (will be shortened)
        
    Returns:
        Exercise ID in format 'ex_name_xxxxxxxx' or 'ex_xxxxxxxx'
        
    Example:
        >>> generate_exercise_id("Barbell Bench Press")
        'ex_bench_a1b2c3d4'
    """
    if exercise_name:
        # Create a short version of the exercise name
        words = exercise_name.lower().split()
        # Take first 2-3 significant words, skip common words
        skip_words = {"the", "a", "an", "with", "and", "or", "to"}
        significant = [w for w in words if w not in skip_words][:2]
        short_name = "_".join(significant)[:15]
        return generate_id("ex", short_name)
    return generate_id("ex")


def generate_feedback_id() -> str:
    """
    Generate a unique feedback entry ID.
    
    Returns:
        Feedback ID in format 'fb_xxxxxxxx'
    """
    return generate_id("fb")


def get_current_timestamp() -> str:
    """
    Get the current UTC timestamp in ISO 8601 format.
    
    Returns:
        ISO 8601 formatted timestamp string with Z suffix
        
    Example:
        >>> get_current_timestamp()
        '2024-01-15T10:30:00Z'
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get_timestamp_for_date(
    year: int,
    month: int,
    day: int,
    hour: int = 0,
    minute: int = 0,
    second: int = 0
) -> str:
    """
    Generate an ISO 8601 timestamp for a specific date and time.
    
    Args:
        year: Year (e.g., 2024)
        month: Month (1-12)
        day: Day (1-31)
        hour: Hour (0-23), default 0
        minute: Minute (0-59), default 0
        second: Second (0-59), default 0
        
    Returns:
        ISO 8601 formatted timestamp string with Z suffix
    """
    dt = datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def format_timestamp(dt: datetime) -> str:
    """
    Format a datetime object to ISO 8601 string.
    
    Args:
        dt: Datetime object (will be treated as UTC if no timezone)
        
    Returns:
        ISO 8601 formatted timestamp string with Z suffix
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_timestamp(timestamp_str: str) -> datetime:
    """
    Parse an ISO 8601 timestamp string to a datetime object.
    
    Args:
        timestamp_str: ISO 8601 formatted string (e.g., '2024-01-15T10:30:00Z')
        
    Returns:
        Datetime object with UTC timezone
        
    Raises:
        ValueError: If the timestamp string is invalid
    """
    # Handle both 'Z' suffix and '+00:00' format
    if timestamp_str.endswith("Z"):
        timestamp_str = timestamp_str[:-1] + "+00:00"
    
    return datetime.fromisoformat(timestamp_str)


# ============================================================================
# Convenience functions for common ID generation patterns
# ============================================================================


def generate_all_workout_ids(
    num_phases: int = 1,
    weeks_per_phase: int = 4,
    days_per_week: int = 7,
    blocks_per_day: int = 3,
    exercises_per_block: int = 4
) -> dict:
    """
    Pre-generate all IDs needed for a workout plan.
    
    This is useful when you need to know all IDs upfront for cross-referencing.
    
    Args:
        num_phases: Number of training phases
        weeks_per_phase: Number of weeks per phase
        days_per_week: Number of days per week (including rest days)
        blocks_per_day: Average number of exercise blocks per day
        exercises_per_block: Average number of exercises per block
        
    Returns:
        Dictionary containing all generated IDs organized by structure
        
    Example:
        >>> ids = generate_all_workout_ids(num_phases=1, weeks_per_phase=2, days_per_week=3)
        >>> print(ids['workout_id'])
        'wrk_a1b2c3d4'
    """
    ids = {
        "workout_id": generate_workout_id(),
        "generated_at": get_current_timestamp(),
        "phases": []
    }
    
    week_counter = 1
    
    for phase_num in range(1, num_phases + 1):
        phase_data = {
            "id": generate_phase_id(phase_num),
            "weeks": []
        }
        
        for week_offset in range(weeks_per_phase):
            week_num = week_counter
            week_data = {
                "id": generate_week_id(week_num),
                "week_number": week_num,
                "days": []
            }
            
            for day_num in range(1, days_per_week + 1):
                day_data = {
                    "id": generate_day_id(week_num, day_num),
                    "day_number": day_num,
                    "blocks": []
                }
                
                for block_num in range(1, blocks_per_day + 1):
                    block_data = {
                        "id": generate_block_id(block_num),
                        "exercises": [
                            {"id": generate_exercise_id()}
                            for _ in range(exercises_per_block)
                        ]
                    }
                    day_data["blocks"].append(block_data)
                
                week_data["days"].append(day_data)
            
            phase_data["weeks"].append(week_data)
            week_counter += 1
        
        ids["phases"].append(phase_data)
    
    return ids

