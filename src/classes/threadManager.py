import threading
import logging
from src.snmp.snmp_manager import SNMPManager
from src.gpio.gpio_monitor import GPIOMonitor
from src.serial.serial_monitor import SerialMonitor
from src.classes.schema import Config
from typing import List


class ThreadManager:
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.snmp_manager = SNMPManager(config.snmp, config.oids)
        self.gpio_monitor = GPIOMonitor(config.gpio, self.snmp_manager)
        self.serial_monitor = SerialMonitor(config, self.snmp_manager)
        self.threads: List[threading.Thread] = []

    def start(self):
        self.threads.append(threading.Thread(target=self.snmp_manager.run))
        self.threads.append(threading.Thread(target=self.gpio_monitor.run))
        self.threads.append(threading.Thread(target=self.serial_monitor.run))

        for thread in self.threads:
            thread.start()

        self.logger.info("All threads started")

    def stop(self):
        self.snmp_manager.stop()
        self.gpio_monitor.stop()
        self.serial_monitor.stop()

        for thread in self.threads:
            thread.join()

        self.logger.info("All threads stopped")