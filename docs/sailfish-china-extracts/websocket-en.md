# WebSocket Data Push Service | 旗鱼体育

On this page
# WebSocket Data Push Service ​

## Overview ​

The WebSocket service is used to push real-time positioning and status data from SF-Tracer devices. After connecting via WebSocket, clients can receive device-reported messages such as position and heartbeat in real-time.

## Connection Configuration ​

### Connection Parameters ​

 |  | Parameter | Type | Required | Description
 | token | string | Yes | Authentication token, Contact us to get

### Connection Example URL ​

```
`ws://domain?token=your_token_here`
```

## Data Format ​

The data format pushed via WebSocket is consistent with the Device Interface Protocol.

## Keep Long Connection ​

To ensure data real-time performance, it is recommended that clients maintain long connection status after connecting.

Send PING every 10 seconds to keep connection alive.

JavaScript
```
`const socket = new WebSocket('ws://domain?token=your_token_here');

socket.onopen = () => {
  console.log('WebSocket connection successful');
};

socket.onmessage = (event) => {
  console.log('Received message:', event.data);
};

socket.onerror = (error) => {
  console.error('WebSocket error:', error);
};

socket.onclose = () => {
  console.log('WebSocket connection closed');
};

// Send PING every 10 seconds
setInterval(() => {
  socket.send('\x0A');
}, 10000);`
```
PagerPrevious pageOverviewNext pageCommunication Protocol
