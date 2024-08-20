import yaml
import logging
from pysnmp.hlapi import *
import serial
import time

MAX_RETRIES = 3
BASE_DELAY = 1  # second

class SNMPManager:
    def __init__(self, config):
        self.config = config
        self.engine = SnmpEngine()
        self.community = CommunityData(self.config['snmp']['community'])
        self.target = UdpTransportTarget((self.config['snmp']['trap_destination'], self.config['snmp']['trap_port']))
        self.context = ContextData()

    def send_inform(self, event, severity, timestamp, description):
        retries = 0
        while retries < MAX_RETRIES:
            try:
                error_indication, error_status, error_index, var_binds = next(
                    sendNotification(
                        self.engine,
                        self.community,
                        self.target,
                        self.context,
                        'inform',
                        NotificationType(
                            ObjectIdentity(self.config['oids']['trap'])
                        ).addVarBinds(
                            (self.config['oids']['event'], OctetString(event.encode('latin-1'))),
                            (self.config['oids']['severity'], Integer(severity)),
                            (self.config['oids']['timestamp'], OctetString(timestamp.encode('latin-1'))),
                            (self.config['oids']['description'], OctetString(description.encode('latin-1')))
                        )
                    )
                )

                if error_indication:
                    raise Exception(f"SNMP Inform failed: {error_indication}")
                if error_status:
                    raise Exception(f"SNMP Inform failed: {error_status.prettyPrint()} at {error_index and var_binds[int(error_index) - 1][0] or '?'}")
                
                logging.info(f"SNMP Inform sent: {event}")
                return  # Success, exit the function
            except Exception as e:
                logging.error(f"Error sending SNMP Inform (attempt {retries + 1}): {e}")
                retries += 1
                if retries < MAX_RETRIES:
                    time.sleep(BASE_DELAY * (2 ** retries))  # Exponential backoff
        
        logging.error(f"Failed to send SNMP Inform after {MAX_RETRIES} attempts")

class SerialMonitor:
    def __init__(self, config, snmp_manager: SNMPManager):
        self.config = config
        self.snmp_manager = snmp_manager
        self.ser: serial.Serial | None = None
        self.running = False

    def run(self):
        self.running = True
        while self.running:
            try:
                self.ser = serial.Serial(**self.config['serial'])
                self.process_incoming_data()
            except (serial.SerialException, serial.SerialTimeoutException) as e:
                logging.error(f"Serial error: {e}")
                time.sleep(5)
            except (TypeError, UnicodeDecodeError) as e:
                self.logger.error(f"Error occurred, strange character found. Resetting the serial: {e}")
                if self.ser:
                    self.ser.reset_input_buffer()

    def process_incoming_data(self):
        buffer = ""
        while self.running:
            if self.ser.in_waiting > 0:
                incoming_line = self.ser.readline().decode('latin-1').strip()
                logging.debug(f"Raw incoming data: {incoming_line}")
                if incoming_line:
                    buffer += incoming_line + "\n"
                else:
                    if buffer.strip():
                        logging.debug(f"Complete buffer to parse: {buffer}")
                        self.parse_and_send_event(buffer)
                    buffer = ""
            else:
                time.sleep(0.1)

    def parse_and_send_event(self, event: str):
        try:
            logging.debug(f"Parsing event: {event}")
            lines = list(filter(None, event.strip().split('\n')))
            if not lines:
                logging.warning("No lines to parse in the event")
                return

            primary_data = lines[0].split('|')

            event = primary_data[0].strip()
            time_date_metadata = primary_data[1].strip().split()
            FACP_date = f"{time_date_metadata[0]} {time_date_metadata[1]}"

            severity = self.config['event_severities'].get(event, 1)  

            description = " | ".join(time_date_metadata[2:])
            if len(lines) > 1:
                description += " | " + "\n".join(lines[1:])

            description = description.replace("\n", "")

            self.snmp_manager.send_inform(event, severity, FACP_date, description)
        except Exception as e:
            logging.exception(f"Error parsing event: {e}")

    def stop(self):
        self.running = False
        if self.ser:
            self.ser.close()

def load_config():
    with open('config.yml', 'r') as f:
        return yaml.safe_load(f)

def setup_logging():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    config = load_config()
    setup_logging()

    logging.info("Starting Fire Alarm Control Panel Monitor")

    snmp_manager = SNMPManager(config)
    serial_monitor = SerialMonitor(config, snmp_manager)

    try:
        serial_monitor.run()
    except KeyboardInterrupt:
        logging.info("Keyboard interrupt received. Shutting down...")
    finally:
        serial_monitor.stop()
        logging.info("Application shut down complete.")

if __name__ == "__main__":
    main()