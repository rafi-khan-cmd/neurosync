#!/usr/bin/env python3
"""
Utility script to load and analyze saved Muse 2 data files.

Usage:
    python load_saved_data.py muse_data_20250108_123456.npz
"""

import numpy as np
import sys


def load_and_analyze(filename):
    """Load and display information about saved Muse 2 data"""

    print("\n" + "="*60)
    print(f"Loading: {filename}")
    print("="*60)

    # Load the data
    data = np.load(filename, allow_pickle=True)

    # Display available keys
    print(f"\nAvailable data arrays:")
    for key in data.files:
        print(f"  - {key}")

    # Get the sensor data
    eeg = data['eeg']
    ppg = data['ppg']
    gyro = data['gyro']
    accel = data['accel']

    # Display shapes
    print(f"\n{'='*60}")
    print("Data Shapes:")
    print(f"{'='*60}")
    print(f"  EEG:    {eeg.shape} (channels x samples)")
    print(f"  PPG:    {ppg.shape} (channels x samples)")
    print(f"  Gyro:   {gyro.shape} (channels x samples)")
    print(f"  Accel:  {accel.shape} (channels x samples)")

    # Display metadata
    print(f"\n{'='*60}")
    print("Metadata:")
    print(f"{'='*60}")
    if 'sampling_rates' in data:
        sampling_rates = data['sampling_rates'].item()
        print(f"  Sampling Rates:")
        for key, rate in sampling_rates.items():
            print(f"    {key}: {rate} Hz")

    if 'channel_names' in data:
        channel_names = data['channel_names'].item()
        print(f"\n  Channel Names:")
        for sensor, names in channel_names.items():
            print(f"    {sensor}: {names}")

    if 'duration_seconds' in data:
        print(f"\n  Duration: {data['duration_seconds']} seconds")

    if 'delay_seconds' in data:
        print(f"  Delay: {data['delay_seconds']} seconds")

    if 'timestamp' in data:
        print(f"  Timestamp: {data['timestamp']}")

    # Display basic statistics for EEG
    if eeg.shape[1] > 0:
        print(f"\n{'='*60}")
        print("EEG Statistics:")
        print(f"{'='*60}")
        channel_names = ['TP9', 'AF7', 'AF8', 'TP10']
        print(f"{'Channel':<8} {'Mean':>10} {'Std':>10} {'Min':>10} {'Max':>10}")
        print("-" * 60)
        for i, name in enumerate(channel_names):
            if i < eeg.shape[0]:
                channel_data = eeg[i, :]
                print(f"{name:<8} {channel_data.mean():>10.2f} {channel_data.std():>10.2f} "
                      f"{channel_data.min():>10.2f} {channel_data.max():>10.2f}")

    print(f"\n{'='*60}")
    print("✓ Analysis complete!")
    print(f"{'='*60}\n")

    # Example usage code
    print("Example code to access the data:")
    print(f"  import numpy as np")
    print(f"  data = np.load('{filename}', allow_pickle=True)")
    print(f"  eeg = data['eeg']  # Shape: {eeg.shape}")
    print(f"  # Access channel 0 (TP9): eeg[0, :]")
    print(f"  # Access all channels at sample 0: eeg[:, 0]")
    print()


def main():
    filename = "./muse_data.npz"

    try:
        load_and_analyze(filename)
        breakpoint()
    except FileNotFoundError:
        print(f"\nError: File not found: {filename}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\nError loading file: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
