import yaml
import logging
import asyncio
from pysnmp.hlapi.v3arch.asyncio import *
from typing import Dict, Any
from asyncio import PriorityQueue
import time
import os
import serial
import serial_asyncio

BASE_DELAY = 30  # seconds

class SNMPManager:
    def __init__(self, config: Dict[str, Any], queue: PriorityQueue):
        self.config = config
        self.queue = queue
        self.engine = SnmpEngine()
        self.community = CommunityData(
            self.config['snmp']['community'], 
            mpModel=1
        )
        self.target = None
        self.context = ContextData()
        
    async def initialize(self):
        """Initialize the UDP transport target asynchronously"""
        self.target = await UdpTransportTarget.create(
            (self.config['snmp']['inform_destination'], 
             self.config['snmp']['inform_port'])
        )

    async def run(self):
        await self.initialize()
        while True:
            priority, timestamp, message = await self.queue.get()
            await self.send_inform(**message)
            self.queue.task_done()

    async def send_inform(self, event: str, severity: int, timestamp: str, description: str):
        try:
            notification = NotificationType(
                ObjectIdentity(self.config['oids']['inform'])
            ).add_varbinds(
                (ObjectIdentity(self.config['oids']['event']), 
                 OctetString(event.encode('latin-1'))),
                (ObjectIdentity(self.config['oids']['severity']), 
                 Integer32(severity)),
                (ObjectIdentity(self.config['oids']['datetime']), 
                 OctetString(timestamp.encode('latin-1'))),
                (ObjectIdentity(self.config['oids']['description']), 
                 OctetString(description.encode('latin-1')))
            )

            error_indication, error_status, error_index, var_binds = await send_notification(
                self.engine,
                self.community,
                self.target,
                self.context,
                'inform',
                notification
            )

            if error_indication:
                raise Exception(f"SNMP Inform failed: {error_indication}")
            if error_status:
                raise Exception(
                    f"SNMP Inform failed: {error_status.prettyPrint()} at "
                    f"{error_index and var_binds[int(error_index) - 1][0] or '?'}"
                )
            
            logging.info(f"SNMP Inform sent: {event}")
            return

        except Exception as e:
            logging.error(f"Error sending SNMP Inform: {e}")
            logging.error(
                f"Failed to send SNMP Inform. Requeuing message at the front. "
                f"Waiting {BASE_DELAY} seconds before retrying."
            )
            await asyncio.sleep(BASE_DELAY)
            # Requeue the message at the front of the queue
            await self.queue.put((0, time.time(), {
                'event': event,
                'severity': severity,
                'timestamp': timestamp,
                'description': description
            }))

    async def cleanup(self):
        """Cleanup resources"""
        self.engine.close_dispatcher()

class SerialMonitor:
    def __init__(self, config: Dict[str, Any], queue: PriorityQueue):
        self.config = config
        self.queue = queue
        self.ser = None
        self.running = False
        self.reader = None
        self.writer = None

    async def open_serial_connection(self):
        serial_config = self.config['serial'].copy()
        port = serial_config.pop('port')
        self.reader, self.writer = await serial_asyncio.open_serial_connection(url=port, **serial_config)

    async def run(self):
        self.running = True
        while self.running:
            try:
                await self.open_serial_connection()
                await self.process_incoming_data()
            except (serial.SerialException, serial.SerialTimeoutException) as e:
                logging.error(f"Serial error: {e}")
                await asyncio.sleep(5)
            except (TypeError, UnicodeDecodeError) as e:
                logging.error(f"Error occurred, strange character found: {e}")
                await self.reset_connection()
            except Exception as e:
                logging.error(f"Unexpected error in serial connection: {e}")
                await asyncio.sleep(5)

    async def reset_connection(self):
        logging.info("Resetting serial connection")
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
        self.reader = None
        self.writer = None
        await asyncio.sleep(1)

    async def process_incoming_data(self):
        buffer = ""
        while self.running and self.reader:
            try:
                if self.reader.at_eof():
                    break
                incoming_line = await self.reader.readline()
                incoming_line = incoming_line.decode('latin-1').strip()
                logging.debug(f"Raw incoming data: {incoming_line}")
                if incoming_line:
                    buffer += incoming_line + "\n"
                else:
                    if buffer.strip():
                        logging.debug(f"Complete buffer to parse: {buffer}")
                        await self.parse_and_queue_event(buffer)
                    buffer = ""
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.error(f"Error processing incoming data: {e}")
                await asyncio.sleep(0.1)

    async def parse_and_queue_event(self, event: str):
        try:
            logging.debug(f"Parsing event: {event}")
            lines = list(filter(None, event.strip().split('\n')))
            if not lines:
                logging.warning("No lines to parse in the event")
                return

            primary_data = lines[0].split('|')

            event_type = primary_data[0].strip()
            time_date_metadata = primary_data[1].strip().split()
            FACP_date = f"{time_date_metadata[0]} {time_date_metadata[1]}"

            severity = self.config['event_severities'].get(event_type, 1)  

            description = " | ".join(time_date_metadata[2:])
            if len(lines) > 1:
                description += " | " + "\n".join(lines[1:])

            description = description.replace("\n", "")

            # Use current timestamp as priority (lower number = higher priority)
            priority = time.time()
            await self.queue.put((priority, priority, {
                'event': event_type,
                'severity': severity,
                'timestamp': FACP_date,
                'description': description
            }))
            logging.info(f"Event queued: {event_type}")
        except Exception as e:
            logging.exception(f"Error parsing event: {e}")

    def stop(self):
        self.running = False
        if self.writer:
            self.writer.close()

def load_config():
    print(f"Current working directory: {os.getcwd()}")
    config_path = os.path.join(os.getcwd(), 'config.yml')
    print(f"Attempting to load config from: {config_path}")
    with open('config.yml', 'r') as f:
        return yaml.safe_load(f)

def setup_logging():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def main():
    config = load_config()
    setup_logging()

    logging.info("Starting Fire Alarm Control Panel Monitor")

    event_queue = PriorityQueue()
    snmp_manager = SNMPManager(config, event_queue)
    serial_monitor = SerialMonitor(config, event_queue)

    try:
        await asyncio.gather(
            serial_monitor.run(),
            snmp_manager.run()
        )
    except asyncio.CancelledError:
        logging.info("Application cancelled. Shutting down...")
    except Exception as e:
        logging.exception(f"Unexpected error: {e}")
    finally:
        serial_monitor.stop()
        await snmp_manager.cleanup()
        await event_queue.join()
        logging.info("Application shut down complete.")

if __name__ == "__main__":
    asyncio.run(main())
