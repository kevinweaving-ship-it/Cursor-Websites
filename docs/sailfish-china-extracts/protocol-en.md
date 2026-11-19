# Communication Protocol | 旗鱼体育

On this page
# Communication Protocol 1.0 ​

## 👉 Receive Message Protocol ​

```
`$$|ACK|VERSION|MESSAGE TYPE|DEVICE ID|MESSAGES NUMBER|MESSAGE 1|MESSAGE 2|...|MESSAGE N|**`
```
 |  | Field | Description
 | ACK | Incremental sequence number
 | VERSION | Protocol version
 | MESSAGE TYPE | Message type code (see message types below)
 | DEVICE ID | Device identifier
 | MESSAGES NUMBER | Number of messages included in this transmission
 | MESSAGE[s] | One or more specific message contents

### Message Type Codes (MESSAGE TYPE) ​

 |  | Code | Message Type
 | 0 | Server Message
 | 1 | Heartbeat Message
 | 2 | Position Message
 | 3 | Wind Message

## 0. Server Message (Server) ​

Used to receive server messages

Message Type Code: `0`

### Syntax ​

```
`TYPE|CONTENT`
```

### Field Description ​

 |  | Field | Type | Description
 | TYPE | string | Type（CMD）
 | CONTENT | string | Return content

### Example ​

```
`$$|1|1|0|700000001|1|CMD|CONNECTED|**`
```
Parsed result:

 |  | Field | Value
 | TYPE | CMD
 | CONTENT | CONNECTED

## 1. Heartbeat Message (Heartbeat) ​

Used to receive device heartbeat information.

TIP

After the device is remotely powered off, the server still sends heartbeat messages, but the battery level and charging status are empty

Message Type Code: `1`

### Syntax ​

```
`LEVEL|STATUS`
```

### Field Description ​

 |  | Field | Type | Description
 | BATTERY | int | Battery level, 0-100
 | STATUS | int | Charging status (same as STATUS in position message)

### Example ​

```
`$$|1|1|2|700000001|1|100|2|**`
```
Parsed result:

 |  | Field | Value
 | BATTERY | 100
 | STATUS | 2 (CHARGING)

## 2. Position Message (Position) ​

Used to send device position information to server.

Message Type Code: `2`

### Syntax ​

```
`SAMPLE TIME|LONGITUDE|LATITUDE|ALTITUDE|SPEED|HEADING|BATTERY|STATUS|SOS`
```

### Field Description ​

 |  | Field | Type | Description
 | SAMPLE TIME | long | Position time, timestamp
 | LONGITUDE | double | Longitude, in decimal degrees
 | LATITUDE | double | Latitude, in decimal degrees
 | ALTITUDE | double | Altitude, unit: meters
 | SPEED | double | Speed, unit: m/s
 | HEADING | double | Heading angle, 0-360°, 0 indicates north, clockwise direction
 | BATTERY | int | Battery level, 0-100
 | SOS | int | Whether SOS is triggered, 1 means triggered, 0 means not triggered
 | STATUS | int | Device status, 2 means charging

### Example ​

```
`$$|1|1|1|2463|1|1772009017000|120.371522|36.1087272|41.0|0.01|339.0|100||2|**`
```
Parsed result:

 |  | Field | Value
 | ACK | 1
 | VERSION | 1
 | MESSAGE TYPE | 2
 | DEVICE ID | 2463
 | MESSAGES NUMBER | 1
 | SAMPLE TIME | 1772009017000
 | LONGITUDE | 120.371522
 | LATITUDE | 36.1087272
 | ALTITUDE | 41.0
 | SPEED | 0.01
 | HEADING | 339.0
 | BATTERY | 100
 | SOS | NULL (NOT SOS)
 | STATUS | 2 (CHARGING)

## 3. Wind Message (Wind) ​

Used to send device position information to server.

Message Type Code: `3`

### Syntax ​

```
`SAMPLE TIME|LONGITUDE|LATITUDE|ALTITUDE|SPEED|HEADING|BATTERY|STATUS|SOS`
```

### Field Description ​

 |  | Field | Type | Description
 | SAMPLE TIME | long | Position time, timestamp
 | LONGITUDE | double | Longitude, in decimal degrees
 | LATITUDE | double | Latitude, in decimal degrees
 | ALTITUDE | double | Altitude, unit: meters
 | SPEED | double | Speed, unit: m/s
 | HEADING | double | Heading angle, 0-360°, 0 indicates north, clockwise direction
 | VOLTAGE | double | Voltage, unit: volts
 | TWD | double | True wind direction, unit: degrees
 | TWS | double | True wind speed, unit: m/s

### Example ​

```
`$$|1|1|1|2463|1|1772009017000|120.371522|36.1087272|41.0|0.01|339.0|12.1|270.0|2.5|**`
```
Parsed result:

 |  | Field | Value
 | ACK | 1
 | VERSION | 1
 | MESSAGE TYPE | 3
 | DEVICE ID | 2463
 | MESSAGES NUMBER | 1
 | SAMPLE TIME | 1772009017000
 | LONGITUDE | 120.371522
 | LATITUDE | 36.1087272
 | ALTITUDE | 41.0
 | SPEED | 0.01
 | HEADING | 339.0
 | VOLTAGE | 12.1
 | TWD | 270.0
 | TWS | 2.5

## 👉 Send Message Protocol ​

```
`$$|COMMAND|DEVICE ID|##`
```

### Field Description ​

 |  | Field | Type | Description
 | COMMAND | string | Command
 | DEVICE ID | string | Device ID, multiple separated by commas

### Command Description ​

 |  | Command | Description
 | 33 | Restart
 | 35 | Remote Power Off
 | 36 | Remote Power On (this command is unavailable after manual power off)
 | 90 | Disarm SOS

### Example ​

```
`$$|36|2248,2249|##`
```
Parsed result:

 |  | Field | Value
 | COMMAND | 36 (Power on)
 | DEVICE ID | 2248,2249
PagerPrevious pageWebsocket
