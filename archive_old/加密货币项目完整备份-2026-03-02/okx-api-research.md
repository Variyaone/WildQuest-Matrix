# OKX API 交易脚本开发研究报告

## 一、API基础信息

### 1. REST API 基础URL

根据交易类型和账户类型的不同，OKX提供多个REST API端点：

**交易API：**
- 实盘交易：`https://www.okx.com`
- 模拟盘：`https://www.okx.com` (需在URL中添加模拟标识或使用配置)

**WebSocket实时数据URL：**
- 公共频道：`wss://ws.okx.com:8443/ws/v5/public`
- 私有频道：`wss://ws.okx.com:8443/ws/v5/private`

**API版本：** V5（当前稳定版本）

### 2. 认证方式

OKX使用三重认证机制：

**所需参数：**
1. **API Key** - 从OKX账户创建的公钥
2. **Secret Key** - 用于生成签名的私钥
3. **Passphrase** - 创建API Key时设置的密码短语

**JWT令牌方式（推荐用于个人交易）：**
- 通过JWT令牌进行认证，简化流程

## 二、API认证流程

### 标准认证流程（API Key + 签名）

```python
import hmac
import base64
import hashlib
import time
import uuid

def generate_signature(api_key, secret_key, passphrase, timestamp, method, request_path, body=""):
    """
    生成OKX API签名
    """
    # 拼接签名字符串
    sign_str = timestamp + method + request_path + body

    # 使用HMAC-SHA256生成签名
    mac = hmac.new(
        bytes(secret_key, encoding='utf-8'),
        bytes(sign_str, encoding='utf-8'),
        digestmod=hashlib.sha256
    )

    # Base64编码
    signature = base64.b64encode(mac.digest()).decode()

    # 构建请求头
    headers = {
        'OK-ACCESS-KEY': api_key,
        'OK-ACCESS-SIGN': signature,
        'OK-ACCESS-TIMESTAMP': timestamp,
        'OK-ACCESS-PASSPHRASE': passphrase,
        'Content-Type': 'application/json'
    }

    return headers
```

### JWT令牌认证流程

```python
def get_jwt_token(api_key, secret_key, passphrase, password):
    """
    使用JWT获取访问令牌
    """
    from okx import Okx

    # 创建客户端实例
    client = Okx(
        api_key=api_key,
        secret_key=secret_key,
        passphrase=passphrase,
        password=password,  # 账户登录密码
        simulation=False  # False为实盘，True为模拟盘
    )

    # JWT令牌会自动处理
    return client
```

## 三、关键端点清单

### 1. 账户相关

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v5/account/balance` | GET | 查询账户余额 |
| `/api/v5/account/positions` | GET | 查询持仓信息 |
| `/api/v5/account/account-position-risk` | GET | 查询账户持仓风险 |

### 2. 交易相关

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v5/trade/order` | POST | 下单 |
| `/api/v5/trade/batch-orders` | POST | 批量下单 |
| `/api/v5/trade/cancel-order` | POST | 撤单 |
| `/api/v5/trade/cancel-batch-orders` | POST | 批量撤单 |
| `/api/v5/trade/amend-order` | POST | 修改订单 |
| `/api/v5/trade/close-position` | POST | 市价全平仓 |
| `/api/v5/trade/orders-pending` | GET | 查询当前委托 |
| `/api/v5/trade/orders-history` | GET | 查询历史委托 |
| `/api/v5/trade/fills` | GET | 查询成交明细 |

### 3. 市场数据

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v5/market/ticker` | GET | 获取产品行情信息 |
| `/api/v5/market/tickers` | GET | 获取所有产品行情信息 |
| `/api/v5/market/candles` | GET | 获取K线数据 |
| `/api/v5/market/order-book` | GET | 获取产品深度 |
| `/api/v5/market/instruments` | GET | 获取交易产品基础信息 |

### 4. 公共数据

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v5/public/instruments` | GET | 获取交易产品基础信息 |
| `/api/v5/public/contract-oracles` | GET | 获取合约预言机 |
| `/api/v5/public/liquidation-orders` | GET | 获取强平订单 |
| `/api/v5/public/funding-rate` | GET | 获取资金费率 |

## 四、订单类型

### 1. 订单方向
- **buy** - 买入
- **sell** - 卖出

### 2. 订单类型（ordType）

| 类型 | 说明 |
|------|------|
| `market` | 市价单 |
| `limit` | 限价单 |
| `post_only` | 只做maker单 |
| `ioc` | 立即成交并取消剩余 |
| `fok` | 全成交或全取消 |
| `limit_mkt` | 市价限价单 |
| `optimal_limit_ioc` | 市价委托立即成交并取消剩余 |
| `optimal_limit_fok` | 市价委托全成交或全取消 |

### 3. 交易模式（tdMode）
- **cross** - 全仓模式
- **isolated** - 逐仓模式
- **cash** - 现金模式
- **spot** - 现货交易

## 五、交易对格式

OKX使用统一的交易对标识格式：

```
{币种1}-{币种2}
```

**常见交易对示例：**
- 现货：`BTC-USDT`、`ETH-USDT`、`SOL-USDT`
- 合约：`BTC-USDT-SWAP`（永续合约）、`ETH-USDT-240329`（交割合约）
- 期权：`BTC-USD-240628-60000-C`
- 杠杆：`BTC-USDT`

### 交易产品类型（instType）
- **SPOT** - 现货
- **MARGIN** - 杠杆
- **SWAP** - 永续合约
- **FUTURES** - 交割合约
- **OPTION** - 期权

## 六、订单创建示例（伪代码）

### 示例1：市价买单

```python
import requests
import json

# API配置
API_KEY = "your-api-key"
SECRET_KEY = "your-secret-key"
PASSPHRASE = "your-passphrase"
BASE_URL = "https://www.okx.com"

# 获取当前时间戳
timestamp = str(int(time.time()))

# 构建请求
method = "POST"
request_path = "/api/v5/trade/order"
body = json.dumps({
    "instId": "BTC-USDT",
    "tdMode": "cash",
    "side": "buy",
    "ordType": "market",
    "sz": "0.001"  # 数量
})

# 生成签名
headers = generate_signature(API_KEY, SECRET_KEY, PASSPHRASE, timestamp, method, request_path, body)

# 发送请求
response = requests.post(
    BASE_URL + request_path,
    headers=headers,
    data=body
)

result = response.json()
print(result)
```

### 示例2：限价单（带止损止盈）

```python
order_params = {
    "instId": "BTC-USDT-SWAP",  # 永续合约
    "tdMode": "cross",  # 全仓
    "side": "buy",
    "ordType": "limit",
    "sz": "100",  # 合约张数
    "px": "45000",  # 限价
    "tpTriggerPx": "46000",  # 止盈触发价
    "tpOrdPx": "-1",  # 止盈委托价，-1表示市价
    "slTriggerPx": "44000",  # 止损触发价
    "slOrdPx": "-1"  # 止损委托价
}

body = json.dumps(order_params)
headers = generate_signature(API_KEY, SECRET_KEY, PASSPHRASE, timestamp, method, request_path, body)
response = requests.post(BASE_URL + request_path, headers=headers, data=body)
```

### 示例3：条件单（止盈止损）

```python
# 策略订单
condition_order = {
    "instId": "ETH-USDT",
    "tdMode": "cash",
    "side": "sell",
    "ordType": "conditional",
    "sz": "1.0",
    "triggerPx": "2800",  # 触发价格
    "ordPx": "-1"  # 触发后委托价格，-1为市价
}
```

## 七、Python SDK推荐

### 1. 官方Python SDK（推荐）

**安装：**
```bash
pip install okx
```

**使用示例：**
```python
from okx import Okx
from okx import Market

# 创建客户端
api_key = "your-api-key"
secret_key = "your-secret-key"
passphrase = "your-passphrase"
password = "your-password"  # 账户密码

client = Okx(
    api_key=api_key,
    secret_key=secret_key,
    passphrase=passphrase,
    password=password,
    simulation=False  # False=实盘, True=模拟盘
)

# 创建市场数据客户端
market = Market(simulation=False)

# 获取K线数据
candles = market.get_candles(
    instId="BTC-USDT",
    bar="1H",  # 1小时K线
    limit="100"
)

# 获取账户余额
balance = client.account.get_balance()

# 下市价单
order = client.trade.place_order(
    instId="BTC-USDT",
    tdMode="cash",
    side="buy",
    ordType="market",
    sz="0.001"
)
```

### 2. ccxt库（多个交易所统一接口）

**安装：**
```bash
pip install ccxt
```

**使用示例：**
```python
import ccxt

exchange = ccxt.okx({
    'apiKey': 'your-api-key',
    'secret': 'your-secret-key',
    'password': 'your-passphrase',  # OKX特有
    'enableRateLimit': True,
})

# 获取余额
balance = exchange.fetch_balance()

# 获取K线
ohlcv = exchange.fetch_ohlcv('BTC/USDT', '1h')

# 下市价单
order = exchange.create_market_order('BTC/USDT', 'buy', 0.001)
```

### 3. SDK对比

| SDK | 优点 | 缺点 | 适用场景 |
|-----|------|------|----------|
| **okx官方SDK** | 功能完整，支持所有API，有详细文档 | 仅支持OKX | 专注OKX交易 |
| **ccxt** | 支持多个交易所，统一接口 | 部分高级功能不支持，更新可能滞后 | 多交易所套利 |
| **自定义请求** | 最大灵活性 | 需要自己处理签名、重试等 | 需要高度定制 |

## 八、开发建议

### 1. 错误处理
```python
def safe_request(func, *args, **kwargs):
    max_retries = 3
    for i in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if i == max_retries - 1:
                raise
            time.sleep(2 ** i)  # 指数退避
```

### 2. 风险管理
- 始终在模拟盘测试策略
- 设置合理的止损止盈
- 控制仓位大小（建议不超过资金的5-10%）
- 监控账户余额和保证金充足率

### 3. 重要提醒
- **切勿将API密钥硬编码在代码中**，使用环境变量
- **不要泄露API密钥和Passphrase**
- 在实盘交易前，务必在模拟盘充分测试
- 关注API调用的频率限制（Rate Limit），避免被封禁

### 4. 常见问题
- **签名错误**：检查时间戳格式和签名算法
- **IP白名单**：确保服务器IP已添加到API设置的白名单
- **权限不足**：检查API Key是否有读写权限
- **余额错误**：确认账户类型（现货、合约、杠杆）正确

## 九、WebSocket实时数据

连接实时市场数据的示例：

```python
import websockets
import asyncio
import json

async def subscribe_market_data():
    uri = "wss://ws.okx.com:8443/ws/v5/public"

    async with websockets.connect(uri) as websocket:
        # 订阅行情
        subscribe_msg = {
            "op": "subscribe",
            "args": [
                {
                    "channel": "tickers",
                    "instId": "BTC-USDT"
                }
            ]
        }

        await websocket.send(json.dumps(subscribe_msg))

        # 接收数据
        while True:
            message = await websocket.recv()
            data = json.loads(message)
            print(f"实时数据: {data}")

# 运行
asyncio.get_event_loop().run_until_complete(subscribe_market_data())
```

---

**报告完成时间：** 2026-02-25
**适用版本：** OKX API V5
