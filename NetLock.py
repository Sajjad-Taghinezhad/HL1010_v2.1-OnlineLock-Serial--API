import serial
import configparser
import os
import logging
from flask import Flask, jsonify

# Initialize the Flask app
app = Flask(__name__)

# Set up logging
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
log_file = 'app.logs'

# Create a file handler to write logs to a file
file_handler = logging.FileHandler(log_file)
file_handler.setFormatter(log_formatter)
file_handler.setLevel(logging.INFO)  # You can adjust the log level as needed

# Create a stream handler to suppress logs on the terminal
stream_handler = logging.StreamHandler()
stream_handler.setLevel(logging.CRITICAL + 1)  # This will suppress all logs in the terminal

# Add handlers to the root logger
logging.getLogger().addHandler(file_handler)
logging.getLogger().addHandler(stream_handler)
logging.getLogger().setLevel(logging.INFO)  # Set global log level

# Define the command codes and packet builder
class RS485Commands:
    """Container for RS485 command codes."""
    OPEN = '0111'


class RS485PacketBuilder:
    """Utility class for building RS485 packets."""

    @staticmethod
    def calculate_lrc(data):
        """
        Calculate LRC (Longitudinal Redundancy Check) by XOR-ing all bytes.
        :param data: Byte array for which LRC is calculated.
        :return: LRC as an integer.
        """
        lrc = 0
        for byte in data:
            lrc ^= byte
        return lrc

    @staticmethod
    def build_packet(address, command_code, door_number):
        """
        Build the RS485 packet.
        :param address: Device address as a hex string (e.g., '01').
        :param command_code: Command code as a hex string (e.g., '0111').
        :param door_number: Door number as an integer.
        :return: Fully formed packet as a hex string.
        """
        return_code = '0000'
        data_content = f'{door_number:02x}'  # Convert door number to 2-digit hex
        packet_length = '0007'

        # Combine the components
        packet = packet_length + command_code + address + return_code + data_content

        # Calculate LRC
        lrc = RS485PacketBuilder.calculate_lrc(bytes.fromhex(packet))

        # Final packet with LRC
        return f"f3{packet}{lrc:02x}"


class RS485Communicator:
    """Class to handle RS485 communication."""

    def __init__(self, port, baudrate):
        """
        Initialize the RS485 communicator.
        :param port: Serial port to use (e.g., '/dev/ttyUSB0').
        :param baudrate: Communication baudrate (e.g., 9600).
        """
        self.port = port
        self.baudrate = baudrate
        self.ser = None

    def open_connection(self):
        """Open the serial connection once at the start."""
        if self.ser is None or not self.ser.is_open:
            try:
                self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
                logging.info(f"Successfully opened port {self.port}.")
            except serial.SerialException as e:
                logging.error(f"Error opening serial port {self.port}: {e}")
                self.ser = None

    def send_packet(self, packet):
        """
        Send a packet to the device via the open serial connection.
        :param packet: Packet as a hex string.
        """
        if self.ser and self.ser.is_open:
            try:
                # Convert the raw packet (hex string) to bytes
                packet_bytes = bytes.fromhex(packet)

                # Send the packet over the serial port
                self.ser.write(packet_bytes)
                logging.info(f"Sent packet: {packet}")
            except serial.SerialException as e:
                logging.error(f"Serial error while sending packet: {e}")
        else:
            logging.warning("Serial port not open, attempting to reopen...")
            self.open_connection()


def load_config(config_file='app.conf'):
    """
    Load configuration settings from a single config file.
    :param config_file: Path to the configuration file.
    :return: A dictionary with the configuration settings for serial and server.
    """
    if not os.path.exists(config_file):
        raise FileNotFoundError(f"Configuration file '{config_file}' not found.")
    
    config = configparser.ConfigParser()
    config.read(config_file)
    
    # Fetch serial settings
    usb_port = config.get('serial', 'USB_PORT', fallback=None)
    baudrate = config.getint('serial', 'BAUDRATE', fallback=None)

    # Fetch server settings
    host = config.get('server', 'HOST', fallback='0.0.0.0')
    port = config.getint('server', 'PORT', fallback=5000)

    if not usb_port or baudrate is None:
        raise ValueError(f"Missing required configuration settings in '{config_file}' under 'serial' section.")
    
    return usb_port, baudrate, host, port


def open_door(communicator, address, door_number):
    """
    Open the door with the specified address and door number.
    :param communicator: Instance of RS485Communicator.
    :param address: Address of the device as a hex string (e.g., '01').
    :param door_number: Door number as an integer.
    """
    command_code = RS485Commands.OPEN
    packet = RS485PacketBuilder.build_packet(address, command_code, door_number)
    communicator.send_packet(packet)


# Load configuration settings from app.conf
USB_PORT, BAUDRATE, HOST, PORT = load_config('app.conf')

# Initialize the RS485 communicator
communicator = RS485Communicator(USB_PORT, BAUDRATE)


@app.route('/open/<address>/<int:door_number>', methods=['GET'])
def open_door_api(address, door_number):
    """
    API endpoint to open a door.
    :param address: Device address (e.g., '01').
    :param door_number: Door number (e.g., 1, 2, 3, etc.).
    :return: JSON response indicating success or failure.
    """
    try:
        open_door(communicator, address, door_number)
        return jsonify({"status": "success", "message": f"Door {door_number} on device {address} opened."}), 200
    except Exception as e:
        logging.error(f"Failed to open door {door_number} on device {address}: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 400


if __name__ == "__main__":
    # Open the serial connection before starting the Flask app
    communicator.open_connection()
    print("Online Lock serial to API by https://sajX.net/")

    # Run the Flask application with host and port from app.conf
    logging.info(f"Starting Flask app on {HOST}:{PORT}")
    print("The app is started successfully.")
    app.run(host=HOST, port=PORT)
