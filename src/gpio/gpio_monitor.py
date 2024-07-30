import RPi.GPIO as GPIO
import time
import logging
from src.classes.schema import GPIOConfig
from src.snmp.snmp_manager import SNMPManager

class GPIOMonitor:
    def __init__(self, gpio_config: GPIOConfig, snmp_manager: SNMPManager):
        self.gpio_config = gpio_config
        self.snmp_manager = snmp_manager
        self.logger = logging.getLogger(__name__)
        self.running = False

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.gpio_config.alarm_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(self.gpio_config.supervision_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(self.gpio_config.trouble_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

    def run(self):
        self.running = True
        self.logger.info("GPIO Monitor started")

        while self.running:
            self._check_pin(self.gpio_config.alarm_pin, self.snmp_manager.oid_config.alarm)
            self._check_pin(self.gpio_config.supervision_pin, self.snmp_manager.oid_config.supervision)
            self._check_pin(self.gpio_config.trouble_pin, self.snmp_manager.oid_config.trouble)
            time.sleep(0.1)  # Small delay to prevent excessive CPU usage

    def stop(self):
        self.running = False
        GPIO.cleanup()

    def _check_pin(self, pin, oid):
        current_state = GPIO.input(pin)
        if current_state != self.snmp_manager.values[oid]:
            # Implement debounce
            time.sleep(self.gpio_config.debounce_time)
            if GPIO.input(pin) == current_state:
                self.snmp_manager.update_value(oid, current_state)
                self.logger.info(f"Pin {pin} changed state to {current_state}")