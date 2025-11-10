from brainflow.board_shim import BoardShim, BrainFlowInputParams, BrainFlowPresets
from datetime import datetime
import numpy as np
import time
import signal
import threading
from collections import deque


# Global flag for graceful shutdown
running = True

def signal_handler(*_args):
    """Handle Ctrl+C gracefully"""
    global running
    print("\n\nStopping stream...")
    running = False

signal.signal(signal.SIGINT, signal_handler)


def prepare_board(board_id, params):
    """Prepare board and enable p50 for 5th EEG + PPG"""
    board = BoardShim(board_id, params)
    board.prepare_session()

    # Enable 5th EEG channel and PPG
    try:
        board.config_board("p50")
        print("✓ p50 enabled (5th EEG + PPG)")
    except Exception as e:
        print(f"⚠️  p50 config failed: {e}")

    return board


# Configuration
BOARD_ID = 38
params = BrainFlowInputParams()
params.serial_port = '/dev/tty.usbmodem11'

# Hardcoded channel configuration for Muse 2
# Based on board descriptions: DEFAULT (EEG), AUXILIARY (Gyro/Accel), ANCILLARY (PPG)
CHANNELS = [
    # EEG channels (DEFAULT_PRESET) - channels [1,2,3,4] = TP9, AF7, AF8, TP10
    ('EEG 0 (TP9)', BrainFlowPresets.DEFAULT_PRESET, 1, '#2E86AB'),
    ('EEG 1 (AF7)', BrainFlowPresets.DEFAULT_PRESET, 2, '#2E86AB'),
    ('EEG 2 (AF8)', BrainFlowPresets.DEFAULT_PRESET, 3, '#2E86AB'),
    ('EEG 3 (TP10)', BrainFlowPresets.DEFAULT_PRESET, 4, '#2E86AB'),
    # PPG channels (ANCILLARY_PRESET) - channels [1,2,3]
    ('PPG 0', BrainFlowPresets.ANCILLARY_PRESET, 1, '#A23B72'),
    ('PPG 1', BrainFlowPresets.ANCILLARY_PRESET, 2, '#A23B72'),
    ('PPG 2', BrainFlowPresets.ANCILLARY_PRESET, 3, '#A23B72'),
    # Gyro channels (AUXILIARY_PRESET) - channels [4,5,6] = X,Y,Z
    ('Gyro X', BrainFlowPresets.AUXILIARY_PRESET, 4, '#F77F00'),
    ('Gyro Y', BrainFlowPresets.AUXILIARY_PRESET, 5, '#F77F00'),
    ('Gyro Z', BrainFlowPresets.AUXILIARY_PRESET, 6, '#F77F00'),
    # Accel channels (AUXILIARY_PRESET) - channels [1,2,3] = X,Y,Z
    ('Accel X', BrainFlowPresets.AUXILIARY_PRESET, 1, '#E63946'),
    ('Accel Y', BrainFlowPresets.AUXILIARY_PRESET, 2, '#E63946'),
    ('Accel Z', BrainFlowPresets.AUXILIARY_PRESET, 3, '#E63946'),
]

# Timestamp channel from DEFAULT_PRESET
TIMESTAMP_CHANNEL = 6

# Sampling rates for each preset (from board descriptions)
SAMPLING_RATES = {
    BrainFlowPresets.DEFAULT_PRESET: 256,    # EEG
    BrainFlowPresets.AUXILIARY_PRESET: 52,   # Gyro/Accel
    BrainFlowPresets.ANCILLARY_PRESET: 64,   # PPG
}

# Pre-grouped channels by preset for efficient data population
# Format: (channel_index_in_CHANNELS, data_channel_index)
CHANNELS_BY_PRESET = {
    BrainFlowPresets.DEFAULT_PRESET: [(0, 1), (1, 2), (2, 3), (3, 4)],  # EEG channels
    BrainFlowPresets.ANCILLARY_PRESET: [(4, 1), (5, 2), (6, 3)],  # PPG channels
    BrainFlowPresets.AUXILIARY_PRESET: [(7, 4), (8, 5), (9, 6), (10, 1), (11, 2), (12, 3)],  # Gyro + Accel
}

# Shared data storage for API access
class MuseDataBuffer:
    """Thread-safe buffer for storing Muse 2 sensor data"""
    def __init__(self, max_window_seconds=5):
        self.max_window_seconds = max_window_seconds
        # Store EEG data as deque of (timestamp, data_array) tuples
        # data_array shape: (4, n_samples) for 4 EEG channels
        self.eeg_buffer = deque(maxlen=1280)  # 5 seconds at 256 Hz
        self.ppg_buffer = deque(maxlen=320)   # 5 seconds at 64 Hz
        self.gyro_buffer = deque(maxlen=260)  # 5 seconds at 52 Hz
        self.accel_buffer = deque(maxlen=260) # 5 seconds at 52 Hz
        self.lock = threading.Lock()
        self.last_update_time = None

    def add_eeg_data(self, data):
        """Add EEG data. data shape: (4, n_samples) for TP9, AF7, AF8, TP10"""
        with self.lock:
            for i in range(data.shape[1]):
                self.eeg_buffer.append(data[:, i])
            self.last_update_time = time.time()

    def add_ppg_data(self, data):
        """Add PPG data. data shape: (3, n_samples)"""
        with self.lock:
            for i in range(data.shape[1]):
                self.ppg_buffer.append(data[:, i])

    def add_gyro_data(self, data):
        """Add Gyro data. data shape: (3, n_samples) for X, Y, Z"""
        with self.lock:
            for i in range(data.shape[1]):
                self.gyro_buffer.append(data[:, i])

    def add_accel_data(self, data):
        """Add Accelerometer data. data shape: (3, n_samples) for X, Y, Z"""
        with self.lock:
            for i in range(data.shape[1]):
                self.accel_buffer.append(data[:, i])

    def get_eeg_window(self, window_seconds=5):
        """Get recent EEG data window. Returns shape: (4, n_samples)"""
        with self.lock:
            if len(self.eeg_buffer) == 0:
                return np.array([]).reshape(4, 0)
            # Convert deque to numpy array
            data_list = list(self.eeg_buffer)
            return np.column_stack(data_list) if data_list else np.array([]).reshape(4, 0)

    def get_all_data(self):
        """Get all buffered data"""
        with self.lock:
            return {
                'eeg': list(self.eeg_buffer),
                'ppg': list(self.ppg_buffer),
                'gyro': list(self.gyro_buffer),
                'accel': list(self.accel_buffer),
                'last_update': self.last_update_time
            }

# Global shared buffer
muse_buffer = MuseDataBuffer()
board = None
streaming_thread = None
streaming_ready = False  # Flag to indicate streaming is active and receiving data


def streaming_loop():
    """Background thread for continuous data collection"""
    global board, running, streaming_ready

    try:
        # Connect
        print("Connecting to Muse 2...")
        board = prepare_board(BOARD_ID, params)
        print("✓ Connected")

        # Start streaming
        board.start_stream()
        print("Streaming started...")
        print("Waiting for data...\n")

        sample_count = 0
        start_time = time.time()
        TARGET_LOOP_TIME = 0.01  # Target 10ms loop time (100 Hz)

        print("Press Ctrl+C to stop\n")

        while running:
            loop_start = time.time()

            # Fetch data from each preset
            data_default = board.get_current_board_data(64, BrainFlowPresets.DEFAULT_PRESET)
            data_auxiliary = board.get_current_board_data(16, BrainFlowPresets.AUXILIARY_PRESET)
            data_ancillary = board.get_current_board_data(16, BrainFlowPresets.ANCILLARY_PRESET)

            # Process and store EEG data (channels 1-4 from DEFAULT_PRESET)
            if data_default.shape[1] > 0:
                eeg_data = data_default[[1, 2, 3, 4], :]  # TP9, AF7, AF8, TP10
                muse_buffer.add_eeg_data(eeg_data)
                sample_count += data_default.shape[1]

                # Mark streaming as ready once we start receiving data
                if not streaming_ready:
                    streaming_ready = True
                    print("✓ Receiving data from Muse 2\n")

            # Process and store PPG data (channels 1-3 from ANCILLARY_PRESET)
            if data_ancillary.shape[1] > 0:
                ppg_data = data_ancillary[[1, 2, 3], :]
                muse_buffer.add_ppg_data(ppg_data)

            # Process and store Gyro/Accel data (from AUXILIARY_PRESET)
            if data_auxiliary.shape[1] > 0:
                gyro_data = data_auxiliary[[4, 5, 6], :]  # Gyro X, Y, Z
                accel_data = data_auxiliary[[1, 2, 3], :]  # Accel X, Y, Z
                muse_buffer.add_gyro_data(gyro_data)
                muse_buffer.add_accel_data(accel_data)

            # Print stats
            elapsed = time.time() - start_time
            if sample_count % 256 == 0 and sample_count > 0:
                rate = sample_count / elapsed if elapsed > 0 else 0
                print(f"Time: {elapsed:.1f}s | Samples: {sample_count} | Rate: {rate:.1f} Hz", end='\r')

            # Adaptive sleep timing
            loop_time = time.time() - loop_start
            sleep_time = max(0, TARGET_LOOP_TIME - loop_time)
            if sleep_time > 0:
                time.sleep(sleep_time)

    except KeyboardInterrupt:
        print("\n\nStopped by user")
    except Exception as e:
        print(f"\n\nError in streaming loop: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        if board is not None:
            try:
                if board.is_prepared():
                    print("\nCleaning up...")
                    board.stop_stream()
                    board.release_session()
                    print("✓ Done")
            except Exception as e:
                print(f"Cleanup error: {e}")


def start_streaming():
    """Start the data streaming service in a background thread"""
    global streaming_thread, running, streaming_ready
    running = True
    streaming_ready = False
    streaming_thread = threading.Thread(target=streaming_loop, daemon=True)
    streaming_thread.start()
    return streaming_thread


def stop_streaming():
    """Stop the data streaming service"""
    global running, streaming_ready
    running = False
    streaming_ready = False
    if streaming_thread:
        streaming_thread.join(timeout=5)


def get_latest_eeg_data(window_seconds=5):
    """
    Get the latest EEG data window for processing by decode algorithms.

    Args:
        window_seconds: Number of seconds of data to retrieve (default: 5)

    Returns:
        numpy.ndarray: EEG data with shape (4, n_samples) where 4 channels are:
                       [TP9, AF7, AF8, TP10]
    """
    return muse_buffer.get_eeg_window(window_seconds)


def get_streaming_status():
    """
    Get the current status of the streaming service.

    Returns:
        dict: Status information including:
            - is_running: Whether the streaming thread is running
            - is_ready: Whether data is being received
            - buffer_size: Number of EEG samples in buffer
            - last_update: Timestamp of last data update
    """
    return {
        'is_running': streaming_thread is not None and streaming_thread.is_alive(),
        'is_ready': streaming_ready,
        'buffer_size': len(muse_buffer.eeg_buffer),
        'last_update': muse_buffer.last_update_time
    }


def save_data(duration_seconds=10, delay_seconds=10, filename=None):
    """
    Save Muse 2 data to file after a delay period.

    This function waits for a specified delay, then collects data for the specified
    duration and saves it to a numpy file (.npz format).

    Args:
        duration_seconds: Number of seconds of data to collect (default: 10)
        delay_seconds: Number of seconds to wait before starting collection (default: 10)
        filename: Output filename (default: auto-generated with timestamp)

    Returns:
        str: Path to the saved file
    """
    import os
    from datetime import datetime

    # Generate filename if not provided
    if filename is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"muse_data_{timestamp}.npz"

    # Check if streaming thread is running
    if streaming_thread is None or not streaming_thread.is_alive():
        raise RuntimeError("Streaming service not started. Please call start_streaming() first.")

    print(f"\n{'='*60}")
    print(f"Data Collection Started")
    print(f"{'='*60}")
    print(f"Delay before collection: {delay_seconds} seconds")
    print(f"Collection duration: {duration_seconds} seconds")
    print(f"Output file: {filename}")
    print(f"{'='*60}\n")

    # Wait for streaming to be ready (receiving data)
    if not streaming_ready:
        print("Waiting for Muse 2 connection and data stream...")
        wait_timeout = 30  # Maximum 30 seconds to wait
        wait_start = time.time()

        while not streaming_ready and time.time() - wait_start < wait_timeout:
            print("  Connecting to Muse 2...", end='\r')
            time.sleep(0.5)

        if not streaming_ready:
            raise RuntimeError(
                "Timeout waiting for Muse 2 data stream. "
                "Please check device connection and try again."
            )

        print("  ✓ Connected and receiving data!{' '*20}\n")
        # Give it a moment to fill the buffer
        time.sleep(2)

    # Wait for the specified delay
    print(f"Waiting {delay_seconds} seconds before collecting data...")
    for i in range(delay_seconds, 0, -1):
        print(f"  Starting in {i} seconds...", end='\r')
        time.sleep(1)
    print(f"  Starting NOW!{' '*20}")

    # Clear current buffers and start fresh collection
    print(f"\nCollecting {duration_seconds} seconds of data...")

    # Calculate expected number of samples
    expected_eeg_samples = SAMPLING_RATES[BrainFlowPresets.DEFAULT_PRESET] * duration_seconds
    expected_ppg_samples = SAMPLING_RATES[BrainFlowPresets.ANCILLARY_PRESET] * duration_seconds
    expected_gyro_samples = SAMPLING_RATES[BrainFlowPresets.AUXILIARY_PRESET] * duration_seconds

    # Create temporary storage for the collection period
    eeg_collection = []
    ppg_collection = []
    gyro_collection = []
    accel_collection = []
    timestamps = []

    # Record the initial buffer state
    initial_buffer_len = len(muse_buffer.eeg_buffer)

    # Collect data for the specified duration
    start_time = time.time()
    last_print_time = start_time

    while time.time() - start_time < duration_seconds:
        # Copy current buffer data
        with muse_buffer.lock:
            current_eeg = list(muse_buffer.eeg_buffer)
            current_ppg = list(muse_buffer.ppg_buffer)
            current_gyro = list(muse_buffer.gyro_buffer)
            current_accel = list(muse_buffer.accel_buffer)

        # Progress update every second
        elapsed = time.time() - start_time
        if time.time() - last_print_time >= 1.0:
            remaining = duration_seconds - elapsed
            print(f"  Progress: {elapsed:.1f}s / {duration_seconds}s (EEG samples: {len(current_eeg)})", end='\r')
            last_print_time = time.time()

        time.sleep(0.1)  # Small sleep to avoid busy-waiting

    # Get final data
    with muse_buffer.lock:
        final_eeg = list(muse_buffer.eeg_buffer)
        final_ppg = list(muse_buffer.ppg_buffer)
        final_gyro = list(muse_buffer.gyro_buffer)
        final_accel = list(muse_buffer.accel_buffer)

    print(f"\n  Collection complete!{' '*40}\n")

    # Convert to numpy arrays
    if len(final_eeg) > 0:
        eeg_array = np.column_stack(final_eeg)  # Shape: (4, n_samples)
    else:
        eeg_array = np.array([]).reshape(4, 0)

    if len(final_ppg) > 0:
        ppg_array = np.column_stack(final_ppg)  # Shape: (3, n_samples)
    else:
        ppg_array = np.array([]).reshape(3, 0)

    if len(final_gyro) > 0:
        gyro_array = np.column_stack(final_gyro)  # Shape: (3, n_samples)
    else:
        gyro_array = np.array([]).reshape(3, 0)

    if len(final_accel) > 0:
        accel_array = np.column_stack(final_accel)  # Shape: (3, n_samples)
    else:
        accel_array = np.array([]).reshape(3, 0)

    # Save to compressed numpy format
    np.savez_compressed(
        filename,
        eeg=eeg_array,
        ppg=ppg_array,
        gyro=gyro_array,
        accel=accel_array,
        sampling_rates={
            'eeg': SAMPLING_RATES[BrainFlowPresets.DEFAULT_PRESET],
            'ppg': SAMPLING_RATES[BrainFlowPresets.ANCILLARY_PRESET],
            'gyro': SAMPLING_RATES[BrainFlowPresets.AUXILIARY_PRESET],
            'accel': SAMPLING_RATES[BrainFlowPresets.AUXILIARY_PRESET],
        },
        channel_names={
            'eeg': ['TP9', 'AF7', 'AF8', 'TP10'],
            'ppg': ['PPG0', 'PPG1', 'PPG2'],
            'gyro': ['Gyro_X', 'Gyro_Y', 'Gyro_Z'],
            'accel': ['Accel_X', 'Accel_Y', 'Accel_Z'],
        },
        duration_seconds=duration_seconds,
        delay_seconds=delay_seconds,
        timestamp=datetime.now().isoformat()
    )

    # Print summary
    file_size = os.path.getsize(filename) / 1024  # KB
    print(f"{'='*60}")
    print(f"Data saved successfully!")
    print(f"{'='*60}")
    print(f"File: {filename}")
    print(f"Size: {file_size:.2f} KB")
    print(f"\nData Summary:")
    print(f"  EEG:    {eeg_array.shape[1]:5d} samples ({eeg_array.shape[0]} channels) @ {SAMPLING_RATES[BrainFlowPresets.DEFAULT_PRESET]} Hz")
    print(f"  PPG:    {ppg_array.shape[1]:5d} samples ({ppg_array.shape[0]} channels) @ {SAMPLING_RATES[BrainFlowPresets.ANCILLARY_PRESET]} Hz")
    print(f"  Gyro:   {gyro_array.shape[1]:5d} samples ({gyro_array.shape[0]} channels) @ {SAMPLING_RATES[BrainFlowPresets.AUXILIARY_PRESET]} Hz")
    print(f"  Accel:  {accel_array.shape[1]:5d} samples ({accel_array.shape[0]} channels) @ {SAMPLING_RATES[BrainFlowPresets.AUXILIARY_PRESET]} Hz")
    print(f"{'='*60}\n")

    # Instructions for loading the data
    print("To load this data:")
    print(f"  data = np.load('{filename}', allow_pickle=True)")
    print(f"  eeg = data['eeg']  # Shape: (4, {eeg_array.shape[1]})")
    print(f"  ppg = data['ppg']  # Shape: (3, {ppg_array.shape[1]})")
    print()

    return filename


# Main execution (for standalone testing)
if __name__ == "__main__":
    try:
        start_streaming()
        # Keep main thread alive
        while running:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nStopping...")
        stop_streaming()
