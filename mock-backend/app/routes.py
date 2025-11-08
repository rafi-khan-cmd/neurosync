import random 
from fastapi import APIRouter

router = APIRouter(prefix="")

@router.get("/student/insights")
def student_insights():
    return {
        "focus": round(random.uniform(0.4, 0.95), 2),
        "stress" : round(random.uniform(0.2,0.9), 2),
        "engagement": round(random.uniform(0.5, 1.0), 2),
        "relaxation": round(random.uniform(0.3, 0.9), 2),
        "signal_quality": random.choice(["good","medium","poor"]),
    }

@router.get("/instructor/summary")
def instructor_summary():
    return {
        "module": random.choice(["module 1", "Module 2", "Module 3", "Module 4"]),
        "avg_focus": round(random.uniform(0.5,0.9), 2),
        "avg_stress": round(random.uniform(0.3,0.8), 2),
        "avg_engagement": round(random.uniform(0.5,0.95), 2),
        "students_high_stress": random.randint(5,25),
        "students_total": 30,
    }