from typing import Dict, Any
from pysnmp.hlapi import *
from pysnmp.carrier.asyncore.dispatch import AsyncoreDispatcher
from pysnmp.carrier.asyncore.dgram import udp
from pysnmp.entity import engine, config
from pysnmp.entity.rfc3413 import cmdrsp
from pysnmp.proto.api import v2c
import logging
from contextlib import contextmanager
from src.classes.schema import SNMPConfig, OIDConfig

class SNMPManager:
    def __init__(self, snmp_config: SNMPConfig, oid_config: OIDConfig):
        self.snmp_config = snmp_config
        self.oid_config = oid_config
        self.logger = logging.getLogger(__name__)
        self.snmp_engine = engine.SnmpEngine()
        self.running = False
        self.values: Dict[str, int] = {
            self.oid_config.alarm: 0,
            self.oid_config.supervision: 0,
            self.oid_config.trouble: 0
        }
        self.dispatcher = None

    @contextmanager
    def run_context(self):
        try:
            self.run()
            yield
        finally:
            self.stop()

    def run(self):
        try:
            self.running = True
            self._setup_snmp_agent()
            self.logger.info("SNMP Agent started")
            self.dispatcher = AsyncoreDispatcher()
            self.dispatcher.run()
        except Exception as e:
            self.logger.error(f"Error starting SNMP Agent: {e}")
            self.stop()

    def stop(self):
        self.running = False
        if self.dispatcher:
                self.dispatcher.close()
        self.snmp_engine.transportDispatcher.closeDispatcher()
        self.logger.info("SNMP Agent stopped")

    def _setup_snmp_agent(self):
        config.addV1System(self.snmp_engine, 'my-area', self.snmp_config.community)
        config.addVacmUser(self.snmp_engine, 2, 'my-area', 'noAuthNoPriv', readSubTree=(1, 3, 6, 1, 4, 1))

        config.addSocketTransport(
            self.snmp_engine,
            udp.domainName,
            udp.UdpSocketTransport().openServerMode(('0.0.0.0', self.snmp_config.port))
        )

        cmdrsp.GetCommandResponder(self.snmp_engine, self._get_handler)

    def _get_handler(self, snmpEngine: Any, stateReference: Any, contextName: Any, PDU: Any, acInfo: Any):
        for oid, val in v2c.apiPDU.getVarBinds(PDU):
            if oid.prettyPrint() in self.values:
                v2c.apiPDU.setVarBinds(PDU, [(oid, v2c.Integer(self.values[oid.prettyPrint()]))])
            else:
                v2c.apiPDU.setVarBinds(PDU, [(oid, v2c.NoSuchObject())])

    def update_value(self, oid: str, value: int):
        self.values[oid] = value
        self.send_trap(oid, value)

    def send_trap(self, oid: str, value: int):
        try:
            errorIndication, errorStatus, errorIndex, varBinds = next(
                sendNotification(
                    SnmpEngine(),
                    CommunityData(self.snmp_config.community),
                    UdpTransportTarget((self.snmp_config.trap_destination, self.snmp_config.trap_port)),
                    ContextData(),
                    'trap',
                    NotificationType(
                        ObjectIdentity(oid)
                    ).addVarBinds(
                        (oid, v2c.Integer(value))
                    )
                )
            )

            if errorIndication:
                raise Exception(f"SNMP Trap failed: {errorIndication}")
            self.logger.info(f"SNMP Trap sent: {oid} = {value}")
        except Exception as e:
            self.logger.error(f"Error sending SNMP Trap: {e}")