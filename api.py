from fastapi import FastAPI, APIRouter, HTTPException
from pydantic import BaseModel
import numpy as np
import random
from typing import Literal

# Import data access from fetch_data module
from fetch_data import get_latest_eeg_data, start_streaming, muse_buffer


# Pydantic models for API responses
class StudentInsightsResponse(BaseModel):
    """Response model for student insights endpoint"""
    focus: float
    stress: float
    engagement: float
    relaxation: float
    signal_quality: Literal["good", "medium", "poor"]
    message: str = ""


# Initialize FastAPI app
app = FastAPI(
    title="Muse 2 BCI API",
    description="Backend API for Muse 2 EEG headset data processing and insights",
    version="1.0.0"
)

# Create router
router = APIRouter()


# Decode Algorithm (Dummy Implementation)
def decode_eeg_data(eeg_data: np.ndarray) -> dict:
    """
    Decode EEG data to extract cognitive metrics.

    This is a DUMMY implementation that uses simple heuristics on EEG signal statistics.
    In production, this should be replaced with proper signal processing:
    - Band-pass filtering (e.g., alpha: 8-13 Hz, beta: 13-30 Hz, theta: 4-8 Hz)
    - Power spectral density analysis
    - Machine learning model inference

    Args:
        eeg_data: numpy array with shape (4, n_samples) for [TP9, AF7, AF8, TP10]

    Returns:
        dict with keys: focus, stress, engagement, relaxation, signal_quality
    """

    # Check if we have data
    if eeg_data.shape[1] == 0:
        # No data available, return random values with poor signal quality
        return {
            "focus": round(random.uniform(0.3, 0.6), 2),
            "stress": round(random.uniform(0.3, 0.7), 2),
            "engagement": round(random.uniform(0.3, 0.6), 2),
            "relaxation": round(random.uniform(0.3, 0.6), 2),
            "signal_quality": "poor"
        }

    # Dummy algorithm using simple statistics
    # In a real implementation, you would:
    # 1. Apply bandpass filters for different frequency bands
    # 2. Compute power spectral density (PSD)
    # 3. Extract band power ratios (e.g., beta/alpha for focus)
    # 4. Feed features into ML model

    # Calculate basic statistics across all channels
    mean_amplitude = np.mean(np.abs(eeg_data))
    std_amplitude = np.std(eeg_data)
    signal_variance = np.var(eeg_data, axis=1).mean()

    # Simple heuristics (PLACEHOLDER - not scientifically accurate!)
    # Focus: higher beta activity (simulated by higher variance)
    focus = min(0.95, max(0.4, 0.5 + (signal_variance / 10000)))

    # Stress: based on amplitude variability (high std = high stress)
    stress = min(0.9, max(0.2, std_amplitude / 500))

    # Engagement: combination of focus and amplitude
    engagement = min(1.0, max(0.5, (focus + mean_amplitude / 1000) / 2))

    # Relaxation: inverse relationship with stress
    relaxation = min(0.9, max(0.3, 0.9 - stress * 0.5))

    # Signal quality: based on data availability and variance
    n_samples = eeg_data.shape[1]
    if n_samples > 1000 and signal_variance > 10:
        signal_quality = "good"
    elif n_samples > 500:
        signal_quality = "medium"
    else:
        signal_quality = "poor"

    return {
        "focus": round(focus, 2),
        "stress": round(stress, 2),
        "engagement": round(engagement, 2),
        "relaxation": round(relaxation, 2),
        "signal_quality": signal_quality
    }


# API Endpoints
@router.get("/student/insights", response_model=StudentInsightsResponse)
def student_insights():
    """
    Get current student cognitive insights based on live EEG data.

    This endpoint:
    1. Retrieves the latest EEG data window from the streaming buffer
    2. Processes it through the decode algorithm
    3. Returns cognitive metrics (focus, stress, engagement, relaxation)

    Returns:
        StudentInsightsResponse: Current cognitive state metrics
    """
    try:
        # Get latest EEG data (5 second window)
        eeg_data = get_latest_eeg_data(window_seconds=5)

        # Check if streaming is active
        last_update = muse_buffer.last_update_time
        if last_update is None:
            raise HTTPException(
                status_code=503,
                detail="Muse 2 streaming service not started. Please start fetch_data.py first."
            )

        # Decode the EEG data
        insights = decode_eeg_data(eeg_data)

        # Add informational message
        n_samples = eeg_data.shape[1]
        insights["message"] = f"Analyzed {n_samples} EEG samples from {eeg_data.shape[0]} channels"

        return StudentInsightsResponse(**insights)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing EEG data: {str(e)}")


@router.get("/health")
def health_check():
    """Health check endpoint to verify API and streaming status"""
    last_update = muse_buffer.last_update_time
    import time

    if last_update is None:
        streaming_status = "not_started"
        time_since_update = None
    else:
        time_since_update = time.time() - last_update
        if time_since_update < 5:
            streaming_status = "active"
        else:
            streaming_status = "stale"

    return {
        "status": "ok",
        "streaming_status": streaming_status,
        "time_since_last_update": round(time_since_update, 2) if time_since_update else None,
        "buffer_size": len(muse_buffer.eeg_buffer)
    }


# Include router in app
app.include_router(router)


# Startup event to begin streaming
@app.on_event("startup")
async def startup_event():
    """Start the Muse 2 data streaming service when API starts"""
    print("\n" + "="*50)
    print("Starting Muse 2 BCI API Server")
    print("="*50)
    print("\nInitializing Muse 2 streaming service...")
    try:
        start_streaming()
        print("✓ Streaming service started successfully")
        print("\nAPI is ready to accept requests!")
        print("="*50 + "\n")
    except Exception as e:
        print(f"⚠️  Warning: Could not start streaming service: {e}")
        print("API will still run, but /student/insights will return errors until streaming is started manually.")
        print("="*50 + "\n")


# Main execution
if __name__ == "__main__":
    import uvicorn

    print("\n🚀 Starting Muse 2 BCI API Server...")
    print("📡 The streaming service will start automatically\n")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
