#!/usr/bin/env python3
# SNMP INFORM Notification Receiver (SNMPv2c specific)

from pysnmp.entity import engine, config
from pysnmp.carrier.asyncio.dgram import udp
from pysnmp.entity.rfc3413 import ntfrcv
import asyncio

# Callback function for received notifications
def handle_notification(snmp_engine, state_reference, context_engine_id,
                       context_name, var_binds, cb_ctx):
    print('----------------------------------------------------------')
    print('Received SNMPv2c Notification:')
    print('----------------------------------------------------------')
    
    # Check if this is an INFORM (rather than a TRAP)
    if state_reference is not None:
        print('* This is an INFORM notification (acknowledgment will be sent automatically)')
    else:
        print('* This is a TRAP notification (no acknowledgment needed)')
    
    # Print context information
    print(f'* From: {context_engine_id.prettyPrint()} / {context_name.prettyPrint()}')
    
    # Print all variable bindings
    print('* Notification contents:')
    for name, val in var_binds:
        # The first two varbinds are always:
        # 1) sysUpTime.0
        # 2) snmpTrapOID.0
        if name.prettyPrint() == '1.3.6.1.2.1.1.3.0':
            print(f'  System Uptime: {val.prettyPrint()}')
        elif name.prettyPrint() == '1.3.6.1.6.3.1.1.4.1.0':
            print(f'  Trap OID: {val.prettyPrint()}')
        else:
            print(f'  {name.prettyPrint()} = {val.prettyPrint()}')
    
    print('----------------------------------------------------------')

async def run_receiver():
    # Create SNMP engine
    snmp_engine = engine.SnmpEngine()
    
    # Transport configuration - listen on all interfaces on port 162
    config.add_transport(
        snmp_engine,
        udp.DOMAIN_NAME + (1,),
        udp.UdpTransport().open_server_mode(('0.0.0.0', 162))
    )
    
    # SNMPv2c setup - this configures the engine to accept SNMPv2c messages
    # with community string 'public'
    config.add_v1_system(
        snmp_engine, 
        'my-area',           # securityName
        'public',            # communityName
        contextName=''       # default context
    )
    
    # Register the notification receiver callback
    ntfrcv.NotificationReceiver(snmp_engine, handle_notification)
    
    print('SNMPv2c Notification Receiver started')
    print('Listening for SNMPv2c INFORM notifications on UDP port 162')
    print('Community string: public')
    print('Press Ctrl+C to stop')
    
    try:
        # Run forever
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print('Shutting down...')
    finally:
        # Properly close the transport dispatcher
        snmp_engine.transport_dispatcher.close_dispatcher()
        print('SNMP Notification Receiver stopped')

if __name__ == '__main__':
    asyncio.run(run_receiver())