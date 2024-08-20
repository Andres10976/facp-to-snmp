from pysnmp.entity import engine, config
from pysnmp.carrier.asyncore.dgram import udp
from pysnmp.entity.rfc3413 import ntfrcv
from pysnmp.smi import rfc1902
import sys

# Create SNMP engine
snmpEngine = engine.SnmpEngine()

# IP configuration
ip = '192.168.0.87'

# Configure transport
config.addTransport(
    snmpEngine,
    udp.domainName + (1,),
    udp.UdpTransport().openServerMode((ip, 162))
)

# Configure community
config.addV1System(snmpEngine, 'my-area', 'public')

# Add support for SNMPv2c
config.addV1System(snmpEngine, 'inform_community', 'public')
config.addVacmUser(snmpEngine, 2, 'inform_community', 'noAuthNoPriv')

# Callback function for receiving notifications
def cbFun(snmpEngine, stateReference, contextEngineId, contextName,
          varBinds, cbCtx):
    print("Received new SNMP inform:")
    for name, val in varBinds:
        print(f'{name.prettyPrint()} = {val.prettyPrint()}')

# Register SNMP Application
ntfrcv.NotificationReceiver(snmpEngine, cbFun)

print(f'SNMP inform receiver is running. Listening on {ip}:162')
snmpEngine.transportDispatcher.jobStarted(1)

try:
    snmpEngine.transportDispatcher.runDispatcher()
except:
    snmpEngine.transportDispatcher.closeDispatcher()
    raise