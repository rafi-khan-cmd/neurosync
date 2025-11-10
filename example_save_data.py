#!/usr/bin/env python3
"""
Example script demonstrating how to use the save_data function
to collect and save 10 seconds of Muse 2 data with a 10-second delay.
"""

from fetch_data import start_streaming, save_data, stop_streaming

def main():
    """Main function to demonstrate data collection"""
    print("\n" + "="*60)
    print("Muse 2 Data Collection Example")
    print("="*60)
    print("\nThis script will:")
    print("1. Start streaming from Muse 2")
    print("2. Wait 10 seconds (delay)")
    print("3. Collect 10 seconds of data")
    print("4. Save to compressed numpy file (.npz)")
    print("="*60 + "\n")

    try:
        # Start the streaming service
        print("Starting Muse 2 streaming service...")
        start_streaming()
        print("✓ Streaming thread started\n")

        # Call save_data with default parameters:
        # Note: save_data will automatically wait for the device to connect
        # - duration_seconds=10 (collect 10 seconds)
        # - delay_seconds=10 (wait 10 seconds before starting)
        # - filename=None (auto-generate timestamp-based filename)
        saved_file = save_data(
            duration_seconds=10,
            delay_seconds=10,
            filename=None  # Will create muse_data_YYYYMMDD_HHMMSS.npz
        )

        print(f"✓ Data collection complete!")
        print(f"✓ Saved to: {saved_file}\n")

        # Example: Load and verify the saved data
        print("Verifying saved data...")
        import numpy as np
        data = np.load(saved_file, allow_pickle=True)

        print(f"\nLoaded data arrays:")
        print(f"  EEG shape:   {data['eeg'].shape}")
        print(f"  PPG shape:   {data['ppg'].shape}")
        print(f"  Gyro shape:  {data['gyro'].shape}")
        print(f"  Accel shape: {data['accel'].shape}")

        print(f"\nMetadata:")
        print(f"  Duration: {data['duration_seconds']} seconds")
        print(f"  Delay: {data['delay_seconds']} seconds")
        print(f"  Timestamp: {data['timestamp']}")

        print("\n✓ Data verified successfully!")

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Stop streaming
        print("\nStopping streaming service...")
        stop_streaming()
        print("✓ Done\n")


if __name__ == "__main__":
    main()
