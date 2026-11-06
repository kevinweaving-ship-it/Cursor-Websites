# 通讯协议 | 旗鱼体育

本页目录
# 通讯协议 1.0 ​

## 👉 接收消息协议 ​

```
`$$|ACK|VERSION|MESSAGE TYPE|DEVICE ID|MESSAGES NUMBER|MESSAGE 1|MESSAGE 2|...|MESSAGE N|**`
```
 |  | 字段 | 说明
 | ACK | 递增的序列号
 | VERSION | 协议版本
 | MESSAGE TYPE | 消息类型编码（见下方消息类型编码）
 | DEVICE ID | 设备标识符
 | MESSAGES NUMBER | 本次发送包含的消息条数
 | MESSAGE[s] | 一条或多条具体消息内容

### 消息类型编码（MESSAGE TYPE） ​

 |  | 编码 | 消息类型
 | 0 | 服务器消息 (Server)
 | 1 | 心跳消息 (Heartbeat)
 | 2 | 位置消息 (Position)
 | 3 | 风力消息 (Wind)

## 0. 服务器消息 (Server) ​

用于接收服务器消息

消息类型编码： `0`

### 语法 ​

```
`TYPE|CONTENT`
```

### 字段说明 ​

 |  | 字段 | 类型 | 说明
 | TYPE | string | 类型(CMD)
 | CONTENT | string | 返回内容

### 示例 ​

```
`$$|1|1|0|700000001|1|CMD|CONNECTED|**`
```
解析结果：

 |  | 字段 | 值
 | TYPE | CMD
 | CONTENT | CONNECTED

## 1. 心跳消息 (Heartbeat) ​

用于接收设备心跳信息。

TIP

设备远程关机后，服务器仍然发送心跳消息，但是电量和充电状态为空

消息类型编码： `1`

### 语法 ​

```
`LEVEL|STATUS`
```

### 字段说明 ​

 |  | 字段 | 类型 | 说明
 | BATTERY | int | 电池电量，0-100
 | STATUS | int | 充电状态（同位置消息的 STATUS）

### 示例 ​

```
`$$|1|1|2|700000001|1|100|2|**`
```
解析结果：

 |  | 字段 | 值
 | BATTERY | 100
 | STATUS | 2 (CHARGING)

## 2. 位置消息 (Position) ​

用于向服务器发送设备位置信息。

消息类型编码： `1`

### 语法 ​

```
`SAMPLE TIME|LONGITUDE|LATITUDE|ALTITUDE|SPEED|HEADING|BATTERY|STATUS|SOS`
```

### 字段说明 ​

 |  | 字段 | 类型 | 说明
 | SAMPLE TIME | long | 位置时间，时间戳
 | LONGITUDE | double | 经度，十进制度数
 | LATITUDE | double | 纬度，十进制度数
 | ALTITUDE | double | 海拔高度，单位：米
 | SPEED | double | 速度，单位：m/s
 | HEADING | double | 航向角，0-360°，0 表示正北，顺时针方向
 | BATTERY | int | 电池电量，0-100
 | SOS | int | 是否触发SOS，1表示触发，0表示未触发
 | STATUS | int | 设备状态，2表示充电中

### 示例 ​

```
`$$|1|1|1|2463|1|1772009017000|120.371522|36.1087272|41.0|0.01|339.0|100||2|**`
```
解析结果：

 |  | 字段 | 值
 | ACK | 1
 | VERSION | 1
 | MESSAGE TYPE | 1
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

## 3. 风力消息 (Wind) ​

用于向服务器发送设备位置信息。

消息类型编码： `1`

### 语法 ​

```
`SAMPLE TIME|LONGITUDE|LATITUDE|ALTITUDE|SPEED|HEADING|BATTERY|STATUS|SOS`
```

### 字段说明 ​

 |  | 字段 | 类型 | 说明
 | SAMPLE TIME | long | 位置时间，时间戳
 | LONGITUDE | double | 经度，十进制度数
 | LATITUDE | double | 纬度，十进制度数
 | ALTITUDE | double | 海拔高度，单位：米
 | SPEED | double | 速度，单位：m/s
 | HEADING | double | 航向角，0-360°，0 表示正北，顺时针方向
 | VOLTAGE | double | 电压，单位：伏特
 | TWD | double | 真风向，单位：度
 | TWS | double | 真风速，单位：m/s

### 示例 ​

```
`$$|1|1|1|2463|1|1772009017000|120.371522|36.1087272|41.0|0.01|339.0|12.1|270.0|2.5|**`
```
解析结果：

 |  | 字段 | 值
 | ACK | 1
 | VERSION | 1
 | MESSAGE TYPE | 1
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

## 👉 发送消息协议 ​

```
`$$|COMMAND|DEVICE ID|##`
```

### 字段说明 ​

 |  | 字段 | 类型 | 说明
 | COMMAND | string | 命令
 | DEVICE ID | string | 设备ID，多个用逗号分隔

### 命令说明 ​

 |  | 命令 | 说明
 | 33 | 重启
 | 35 | 远程关机
 | 36 | 远程开机（手动关机后该命令不可用）
 | 90 | 解除SOS

### 示例 ​

```
`$$|36|2248,2249|##`
```
解析结果：

 |  | 字段 | 值
 | COMMAND | 36(开机)
 | DEVICE ID | 2248,2249
PagerPrevious page连接方式
