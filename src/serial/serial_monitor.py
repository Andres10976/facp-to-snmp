import serial
from typing import Dict, Any
import time
import json
import logging
from datetime import datetime
from src.classes.schema import Config
from src.snmp.snmp_manager import SNMPManager

class SerialMonitor:
    def __init__(self, config: Config, snmp_manager: SNMPManager):
        self.config = config
        self.snmp_manager = snmp_manager
        self.logger = logging.getLogger(__name__)
        self.ser: serial.Serial | None = None
        self.running = False
        self.parity_dic = {
            'none': serial.PARITY_NONE, 
            'even': serial.PARITY_EVEN,
            'odd': serial.PARITY_ODD
        }
        self.attempt = 0
        self.max_reconnect_delay = 60  # Maximum delay between reconnection attempts (in seconds)
        self.base_delay = 1

    def init_serial_port(self) -> None:
        self.ser = serial.Serial(
            port=self.config.serial.port,
            baudrate=self.config.serial.baudrate,
            bytesize=self.config.serial.bytesize,
            parity=self.parity_dic[self.config.serial.parity],
            stopbits=self.config.serial.stopbits,
            timeout=self.config.serial.timeout
        )

    def open_serial_port(self) -> None:
        try:
            if self.ser is None:
                self.init_serial_port()
            if not self.ser.is_open:
                self.ser.open()
            self.logger.info("Serial port opened successfully")
        except serial.SerialException as e:
            raise serial.SerialException(f"An error occurred while opening the specified port: {e}")

    def close_serial_port(self) -> None:
        if self.ser and self.ser.is_open:
            self.ser.close()
        self.logger.info("Serial port closed")

    def process_incoming_data(self) -> None:
        buffer = ""
        if self.ser is None:
            raise ValueError("Serial port is not initialized")

        try:
            while self.running:
                if self.ser.in_waiting > 0:
                    raw_data = self.ser.readline()
                    incoming_line = raw_data.decode('latin-1').strip()
                    if incoming_line:
                        buffer += incoming_line + "\n"
                    else:
                        if buffer.strip():
                            self.parse_and_send_event(buffer)
                        buffer = ""
                else:
                    time.sleep(0.1)
        except (serial.SerialException, serial.SerialTimeoutException) as e:
            raise serial.SerialException(str(e))
        except (TypeError, UnicodeDecodeError) as e:
            if buffer:
                self.parse_and_send_event(buffer)
            raise TypeError(str(e))
        except Exception as e:
            raise Exception(f"Unexpected failure occurred: {str(e)}")

    def parse_and_send_event(self, event: str) -> None:
        try:
            lines = list(filter(None, event.strip().split('\n')))
            if not lines:
                self.logger.error(f"Invalid event received: {event}")
                return

            primary_data = lines[0].split('|')
            if len(primary_data) < 2:
                self.logger.error(f"Invalid event received: {event}")
                return

            event_id = primary_data[0].strip()
            metadata = " | ".join(primary_data[1:])

            if len(lines) > 1:
                metadata += "\n" + "\n".join(lines[1:])

            event_data = {
                "Event": event_id,
                "Metadata": metadata,
                "Timestamp": datetime.now().isoformat()
            }

            self.snmp_manager.send_trap(self.config.oids.event, json.dumps(event_data))
            self.logger.info(f"Event sent: {event_id}")

        except Exception as e:
            self.logger.exception(f"An error occurred while parsing the event: {event}")

    def run(self) -> None:
        self.running = True
        while self.running:
            try:
                self.open_serial_port()
                self.process_incoming_data()
            except (serial.SerialException, serial.SerialTimeoutException) as e:
                self.logger.error(f"Lost serial connection: {e}")
                self.attempt_reconnection()
            except (TypeError, UnicodeDecodeError) as e:
                self.logger.error(f"Error occurred, strange character found. Resetting the serial: {e}")
                if self.ser:
                    self.ser.reset_input_buffer()
            except Exception as e:
                self.close_serial_port()
                self.logger.error(f"An unexpected error has occurred: {str(e)}")
                time.sleep(1)

    def stop(self) -> None:
        self.running = False
        self.close_serial_port()

    def attempt_reconnection(self) -> None:
        while self.running:
            try:
                self.open_serial_port()
                if self.ser and self.ser.is_open:
                    self.attempt = 1
                    break
            except Exception as e:
                delay = min(self.base_delay * (2 ** self.attempt), self.max_reconnect_delay)
                self.logger.error(f"Error found trying to open serial: {e}. Retrying in {delay} seconds.")
                time.sleep(delay)
                self.attempt += 1