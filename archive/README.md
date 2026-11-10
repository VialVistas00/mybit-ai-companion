# archive 索引

这里放的是开发过程中的一次性脚本。**不需要运行**，留作记录，方便回看当时是怎么排查的。

按问题分类：

## srun认证/（35 个）

校园网 Portal（SRun / 深澜）认证的排查过程。

| 文件 | 用途 |
|---|---|
| `srun_client.py` | **核心实现**：SRun 协议完整实现（已移到 `pc/`，这里留副本） |
| `test_hmac_login.py` | 验证 hmd5 = HMAC-MD5(key=token, msg=pwd) |
| `understand_errors.py` | 厘清 `auth_info_error` / `sign_error` 的含义 |
| `board_*.py` | 让板子自己发起认证的各种版本 |
| `query_online.py` | 查账号在线设备 |
| `force_logout.py` | 各种注销方式测试 |

**结论**：算法 100% 正确（hmd5 / info / chksum 都与浏览器逐字节一致），但服务端对脚本客户端有不同的策略，`BAS respond timeout` 说明卡在接入服务器层。详见 [../docs/开发历程.md](../docs/开发历程.md)。

## portal分析/（55 个）

反向分析 Portal 前端 JS 的工具。

| 文件 | 用途 |
|---|---|
| `core_compare.py` | **关键**：验证我的 xxtea 与浏览器 0 差异 |
| `hook_*.py` | 各种 hook（base64 / JSON.stringify / XHR / btoa） |
| `capture_*.py` | 抓真实登录请求 |
| `find_*.py` | 在压缩 JS 里找加密函数 |
| `dump_*.py` | 导出函数源码 |
| `probe_*.py` | 探测各种接口 |

**关键发现**：
- `CREATER.cryptography = false`，所以密码不走 base64
- `chksum` 用 SHA1（不是 MD5）
- `md5(pwd, token)` 实际是 `HMAC-MD5(key=token, msg=pwd)`
- 空值参数（`nas_ip=`、`ap_id=`、`mac=`）也必须在场

## 音频调试/（17 个）

麦克风和录音接口的排查。

| 文件 | 用途 |
|---|---|
| `test_xunfei_fw.py` | 测试固件内置讯飞接口（存在但不可用） |
| `test_record.py` | 验证 `audio.record()` 能生成 WAV |
| `test_acoustic.py` | 真实声学测试（播放语音同时录音） |
| `scan_audio*.py` | 找固件里所有音频相关模块 |
| `verify_mic*.py` | 验证模块检测逻辑 |

**结论**：
- `microphone` 模块不存在，真正的接口是 `audio.record(file, seconds)`
- 生成 8kHz/16bit/单声道 WAV，3 秒 = 49196 字节
- **有 -8567 直流偏置和启动尖峰**，必须处理才能识别
- `sound.read()` 恒为 0 是正常的（麦克风走 I2S 不走 ADC）

## 网络探测/（18 个）

板子联网能力的各种测试。

**结论**：
- 板子连校园网能拿 IP，但存在 Portal 认证，只放行 80/443
- 同网段被 AP 隔离，板子访问不到电脑
- 电脑开热点不行（网卡不支持 STA+AP 同时）
- 最终方案：USB 串口

## AI链路/（13 个）

AI 问答链路的各个版本。

| 文件 | 说明 |
|---|---|
| `ai_gateway.py` | HTTP 网关（走网络时用） |
| `test_full_chain.py` | 全链路测试 |
| `test_voice_agent.py` | 5 条指令的识别测试 |
| `test_codegen.py` | LLM 生成代码能力测试 |

## 烧录工具/（17 个）

板子烧录和测试的辅助脚本。

| 文件 | 说明 |
|---|---|
| `test_snake.py` | 贪吃蛇逻辑单元测试 |
| `test_protocol_e2e.py` | 串口协议双向验证 |
| `verify_hmac.py` | HMAC 实现验证 |
| `flash_*.py` | 各个程序的烧录脚本 |

## 其他/（12 个）

未归类的杂项脚本。
