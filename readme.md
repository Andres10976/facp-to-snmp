# Fire Alarm Control Panel SNMP Monitor

This project implements a monitoring system for Fire Alarm Control Panel (FACP) model Edwards iO1000 using SNMP (Simple Network Management Protocol). It reads serial data from the FACP and sends SNMP notifications (either INFORM or TRAP) to a specified destination.

## Features

- Reads serial data from Fire Alarm Control Panels
- Parses and categorizes events based on severity
- Sends SNMP INFORM or TRAP notifications
- Supports both synchronous and asynchronous operation
- Configurable via YAML file
- Includes custom MIB (Management Information Base) definitions

## Project Structure

The project is organized into two main versions:

1. Inform Version
2. Trap Version

### Inform Version

- `facp_to_snmp_v1.py`: Synchronous implementation using SNMP INFORM
- `facp_to_snmp_v2.py`: Asynchronous implementation using SNMP INFORM
- `FIRE-ALARM-CONTROL-PANEL-MIB.mib`: Custom MIB for INFORM notifications
- `snmp_receiver_test.py`: Test script for receiving SNMP INFORM notifications

### Trap Version

- `facp_to_snmp.py`: Asynchronous implementation using SNMP TRAP
- `FIRE-ALARM-CONTROL-PANEL-TRAP-MIB.mib`: Custom MIB for TRAP notifications
- `trap_receiver.py`: Script for receiving SNMP TRAP notifications

## Configuration

Both versions use a `config.yml` file for configuration. This file includes:

- SNMP settings (community, destination IP, port)
- Serial port settings
- OID definitions
- Event severity mappings

## Requirements

The project requires the following Python packages:

- pyyaml
- pysnmp
- pyserial
- pyserial-asyncio

You can install these dependencies using the provided `requirements.txt` file:

```
pip install -r requirements.txt
```

## Usage

1. Configure the `config.yml` file with your specific settings.
2. Run the desired version of the script:

   For Inform version:
   ```
   python facp_to_snmp_v2.py
   ```

   For Trap version:
   ```
   python facp_to_snmp.py
   ```

3. To test the SNMP receiver, run the appropriate receiver script:

   For Inform version:
   ```
   python snmp_receiver_test.py
   ```

   For Trap version:
   ```
   python trap_receiver.py
   ```

## MIB Files

The project includes custom MIB files for both INFORM and TRAP versions. These MIB files define the structure of the SNMP notifications sent by the system. You may need to load these MIB files into your SNMP management software to properly interpret the received notifications.

## Contributing

Contributions to improve the project are welcome. Please follow these steps:

1. Fork the repository
2. Create a new branch for your feature
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request

## License

[Specify the license under which this project is released]

## Contact

For any questions or support, please contact [Your Contact Information].