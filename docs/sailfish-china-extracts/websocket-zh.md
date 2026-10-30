# WebSocket 数据推送服务 | 旗鱼体育

本页目录
# WebSocket 数据推送服务 ​

## 概述 ​

WebSocket 服务用于实时推送设备的定位和状态数据。客户端通过 WebSocket 连接后，可以实时接收设备上报的位置、心跳等消息。

## 连接配置 ​

### 连接参数 ​

 |  | 参数名 | 类型 | 必填 | 说明
 | token | string | 是 | 认证令牌，联系我们获取

### 连接示例 URL 联系我们获取 ​

```
`ws://domain?token=your_token_here`
```

## 数据格式 ​

WebSocket 推送的数据格式与 设备接口协议 保持一致。

## 保持长连接 ​

为了确保数据的实时性，建议客户端在连接后保持长连接状态。

每10秒发送一次PING，保持连接状态。

JavaScript
```
`const socket = new WebSocket('ws://domain?token=your_token_here');

socket.onopen = () => {
  console.log('WebSocket 连接成功');
};

socket.onmessage = (event) => {
  console.log('收到消息:', event.data);
};

socket.onerror = (error) => {
  console.error('WebSocket 错误:', error);
};

socket.onclose = () => {
  console.log('WebSocket 连接关闭');
};

// 每10秒发送一次PING
setInterval(() => {
  socket.send('\x0A');
}, 10000);`
```
PagerPrevious page概述Next page通讯协议
