from pysnmp.entity import engine, config
from pysnmp.carrier.asyncore.dgram import udp
from pysnmp.entity.rfc3413 import ntfrcv
from pysnmp.smi import rfc1902
import sys

# Create SNMP engine
snmpEngine = engine.SnmpEngine()

# IP configuration
ip = '192.168.0.72'  # Replace with your IP address

# Configure transport
config.addTransport(
    snmpEngine,
    udp.domainName + (1,),
    udp.UdpTransport().openServerMode((ip, 162))
)

# Configure community
config.addV1System(snmpEngine, 'my-area', 'public')

# Callback function for receiving notifications
def cbFun(snmpEngine, stateReference, contextEngineId, contextName,
          varBinds, cbCtx):
    print("Received new SNMP trap:")
    for name, val in varBinds:
        print(f'{name.prettyPrint()} = {val.prettyPrint()}')

# Register SNMP Application
ntfrcv.NotificationReceiver(snmpEngine, cbFun)

print(f'SNMP trap receiver is running. Listening on {ip}:162')
snmpEngine.transportDispatcher.jobStarted(1)

try:
    snmpEngine.transportDispatcher.runDispatcher()
except:
    snmpEngine.transportDispatcher.closeDispatcher()
    raise