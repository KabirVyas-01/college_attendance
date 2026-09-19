import math
from typing import Dict, Any

def calculate_subject_metrics(attended: int, conducted: int, total_planned: int) -> Dict[str, Any]:
    """
    Computes attendance metrics and 75% threshold advisor figures for a subject.
    
    Parameters:
        attended (int): Number of lectures attended so far.
        conducted (int): Total number of lectures conducted so far.
        total_planned (int): Approx. total planned lectures in the semester.
        
    Returns:
        dict: Detailed metrics including percentages and approx recommendations.
    """
    if conducted < 0 or attended < 0:
        raise ValueError("Attendance counts cannot be negative.")
    if attended > conducted:
        raise ValueError("Attended lectures cannot exceed conducted lectures.")

    if conducted == 0:
        current_pct = 100.0  # Default 100% when no classes conducted yet
    else:
        current_pct = round((attended / conducted) * 100.0, 2)

    absent = conducted - attended
    remaining_planned = max(0, total_planned - conducted) if total_planned else 0

    metrics: Dict[str, Any] = {
        "conducted": conducted,
        "attended": attended,
        "absent": absent,
        "current_pct": current_pct,
        "total_planned": total_planned,
        "approx_total_planned": total_planned,
        "remaining_planned": remaining_planned,
        "is_on_track": current_pct >= 75.0 or conducted == 0,
        "approx_safe_leaves": 0,
        "approx_needed_consecutive": 0,
        "advice_message": ""
    }

    if metrics["is_on_track"]:
        # Student has >= 75% attendance
        if total_planned and total_planned >= conducted:
            # Formula: floor(Attended - (0.75 * Total Planned)) + (Total Planned - Conducted)
            raw_safe = math.floor(attended - (0.75 * total_planned)) + (total_planned - conducted)
            safe_leaves = max(0, raw_safe)
        elif total_planned and total_planned < conducted:
            # Conducted exceeded planned
            safe_leaves = max(0, math.floor((4 * attended) / 3) - conducted)
        else:
            # Total planned not configured yet: calculate based on current conducted
            safe_leaves = max(0, math.floor((4 * attended) / 3) - conducted)

        metrics["approx_safe_leaves"] = safe_leaves
        metrics["approx_needed_consecutive"] = 0
        metrics["advice_message"] = (
            f"You are on track! Approx. safe leaves allowed in remaining semester: "
            f"{safe_leaves} lecture(s)."
        )
    else:
        # Student has < 75% attendance
        # Formula: ceil(3 * Conducted - 4 * Attended)
        needed = max(0, math.ceil(3 * conducted - 4 * attended))
        metrics["approx_safe_leaves"] = 0
        metrics["approx_needed_consecutive"] = needed
        metrics["advice_message"] = (
            f"Attendance below 75%! Approx. consecutive lectures needed to attend: "
            f"{needed} lecture(s)."
        )

    return metrics

def calculate_overall_metrics(subjects_metrics: list) -> Dict[str, Any]:
    """
    Aggregates metrics across all enrolled subjects for a student.
    """
    total_conducted = sum(m.get("conducted", 0) for m in subjects_metrics)
    total_attended = sum(m.get("attended", 0) for m in subjects_metrics)
    total_planned = sum(m.get("total_planned", m.get("approx_total_planned", 0)) for m in subjects_metrics)

    if total_conducted == 0:
        overall_pct = 100.0
    else:
        overall_pct = round((total_attended / total_conducted) * 100.0, 2)

    return {
        "total_conducted": total_conducted,
        "total_attended": total_attended,
        "total_absent": total_conducted - total_attended,
        "total_planned": total_planned,
        "overall_pct": overall_pct,
        "is_on_track": overall_pct >= 75.0 or total_conducted == 0
    }
