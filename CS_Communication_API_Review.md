# CS 通信代码 vs 接口文档评审报告

更新时间：2026-01-18  
范围：`f:\Ai-LLM\southwest\05ui-poc`（桌面端 C/S 通信：登录、任务列表、算法列表、保活、MinIO 上传、步骤过程上报、任务状态变更、引导图下载）

## 结论摘要

- **已对齐且落地**：登录、保活、任务列表、任务状态变更、MinIO 上传 URL 获取、步骤过程上报（上传 objectName 后再上报过程）。
- **存在偏差/风险点**：
  - 算法列表接口文档注明“不用分页”，当前客户端仍会携带 `pageNum/pageSize`（一般不会致命，但属于偏差）。
  - `DataService.get_work_orders_online()` 在服务端返回空列表时会“回退生成 mock 数据”，这与接口契约不一致，可能导致线上误判/误操作。
  - `step_infos.guide_url` 文档同时出现“objectName 形式”和“预签名 URL 形式”；客户端目前**只可靠支持预签名 URL**（含反引号包裹的脏数据清洗）。若服务端返回 objectName，客户端缺少“objectName→可下载 URL”的接口对接（文档未提供该下载接口）。
  - `/client/getRecordList`（过程记录获取）在文档存在，但客户端未实现调用。
- **总体建议**：将“mock 回退”和“接口 fallback 行为”严格限定在开发/离线模式；补齐 guide_url 为 objectName 时的下载链路；把算法列表请求参数对齐为“无分页”；补齐 `/client/getRecordList` 页面/服务能力。

## 评审方法与依据

- 依据：你提供的“九洲项目-服务端与C端接口定义”（核心端点：`/client/task/list`、`/client/algorithm/list`、`/client/auth/login`、`/client/auth/health`、`/client/getUrl`、`/client/task/status/{taskNo}/{statusCode}`、`/client/process`、`/client/getRecordList`）。
- 方法：全仓库扫描 `src/` 下所有 HTTP 调用点，逐一对照接口文档的路径/方法/参数/返回结构与异常处理。

## 代码侧通信架构概览

### 统一网络层

- [network_service.py](file:///f:/Ai-LLM/southwest/05ui-poc/src/services/network_service.py)
  - 维护 `requests.Session()`，登录成功后写入 `Authorization: Bearer <token>`。
  - 负责 `/client/auth/login`、`/client/task/list`、`/client/algorithm/list`、`/client/auth/health`。

### 数据服务层（含 mock 回退）

- [data_service.py](file:///f:/Ai-LLM/southwest/05ui-poc/src/services/data_service.py)
  - `get_work_orders_online()`：通过 `NetworkService.get_work_orders()` 拉取任务列表；异常/空列表时会 fallback 到 mock（需重点关注）。
  - `get_algorithms()`：通过 `NetworkService.get_algorithms()` 拉取算法列表；异常时 fallback 到本地 `data/algorithms.json`。

### 结果上报独立服务（队列、异步、不阻塞 UI）

- [result_report_service.py](file:///f:/Ai-LLM/southwest/05ui-poc/src/services/result_report_service.py)
  - 后台线程消费队列：取 `/client/getUrl` → PUT 预签名 URL 上传 JPEG → POST `/client/process` 上报步骤过程 → GET `/client/task/status/{...}` 变更任务状态。

### UI 调用入口

- 任务列表页：[assembly_tasks_page.py](file:///f:/Ai-LLM/southwest/05ui-poc/src/ui/pages/assembly_tasks_page.py)
  - `load_data()` 拉取任务列表并渲染
  - 执行窗口关闭后自动刷新列表（已实现）
- 执行窗口：[process_execution_window.py](file:///f:/Ai-LLM/southwest/05ui-poc/src/ui/windows/process_execution_window.py)
  - 每步检测后入队上报步骤过程
  - 进入检测时入队把任务置为“进行中(2)”，最后一步完成后入队置为“已完成(3)”
  - 引导图下载：支持预签名 URL 且会清洗反引号/引号包裹

## 逐接口对照（文档 vs 代码）

### 1) 获取装配任务信息

- 文档：`GET /client/task/list`，参数 `pageNum/pageSize`，返回 `{total, rows, code, msg}`，每行含 `task_no/craft_no/.../status/algorithm_id/step_infos/...`。
- 代码：
  - 请求：`NetworkService.get_work_orders()` → `GET /client/task/list`，带 `pageNum/pageSize/status?`  
    代码：[get_work_orders](file:///f:/Ai-LLM/southwest/05ui-poc/src/services/network_service.py#L113-L139)
  - 使用：`DataService.get_work_orders_online()` 解析 `rows/total`，再由 `AssemblyTasksPage.load_data()` 归一化展示  
    代码：[get_work_orders_online](file:///f:/Ai-LLM/southwest/05ui-poc/src/services/data_service.py#L213-L294)、[load_data](file:///f:/Ai-LLM/southwest/05ui-poc/src/ui/pages/assembly_tasks_page.py#L151-L180)
- 符合项：
  - 路径/方法/分页参数符合。
  - 支持 status 过滤（文档也在状态字段定义中给出）。
- 偏差/风险：
  - `get_work_orders_online()` 当服务端返回 `rows=[]` 时会 fallback 到 mock（属于“伪造数据”），会掩盖真实的“暂无任务/查询条件无数据”场景。  
    风险：线上会出现“服务端无任务但客户端显示有任务”的错觉。

### 2) 获取算法信息（不用分页）

- 文档：`GET /client/algorithm/list`，返回 `{code,msg,data:[{id,name,version,url,desc}]}`，注明“不用分页”。
- 代码：
  - `NetworkService.get_algorithms(page_num, page_size)` 仍会带 `pageNum/pageSize`  
    代码：[get_algorithms](file:///f:/Ai-LLM/southwest/05ui-poc/src/services/network_service.py#L141-L165)
  - `DataService.get_algorithms()` 兼容 `data=list` 形态（符合文档），但同样以“分页参数”调用网络接口  
    代码：[get_algorithms](file:///f:/Ai-LLM/southwest/05ui-poc/src/services/data_service.py#L92-L123)
- 偏差：
  - “不用分页”但仍发送分页参数（一般服务端会忽略，但属于契约不一致）。
- 建议：
  - 客户端取消 query 参数，或仅在服务端明确支持分页时才发送。

### 3) 登录

- 文档：`POST /client/auth/login`，入参 `username/password`，返回 `data.token/expire_time`。
- 代码：
  - 主路径：`POST JSON`；异常时 fallback：`POST form`，再 fallback：`GET query`  
    代码：[login](file:///f:/Ai-LLM/southwest/05ui-poc/src/services/network_service.py#L67-L90)
  - token 处理：`Authorization: Bearer <token>` 写入 session header  
    代码：[set_token](file:///f:/Ai-LLM/southwest/05ui-poc/src/services/network_service.py#L61-L66)
- 符合项：
  - 主路径与返回解析符合（`code==200` 且提取 `data.token`）。
- 偏差/风险：
  - login 的 GET fallback 不符合“登录必须 POST”的常规安全约束；若服务端开启审计/网关限制，可能触发安全策略告警。

### 4) 保活接口

- 文档：`GET /client/auth/health`，返回 `{msg, code}`。
- 代码：`NetworkService.health_check()` → `GET /client/auth/health`，并由 [session.py](file:///f:/Ai-LLM/southwest/05ui-poc/src/core/session.py) 的后台线程周期调用。  
  代码：[health_check](file:///f:/Ai-LLM/southwest/05ui-poc/src/services/network_service.py#L166-L189)、[start_health_monitor](file:///f:/Ai-LLM/southwest/05ui-poc/src/core/session.py#L77-L123)
- 符合项：路径/方法符合。
- 注意：
  - 健康检查日志会打印整个返回结构，若未来返回中包含敏感信息需考虑脱敏（当前接口仅 `{msg,code}` 风险较低）。

### 5) 获取 MinIO 上传 URL

- 文档：`GET /client/getUrl`，返回 `data.objectName` 与 `data.url`（预签名 PUT URL，示例存在反引号包裹）。
- 代码：`ResultReportService._upload_step_image()`  
  - 先 `GET /client/getUrl`（走带 token 的 session）  
  - 再 `PUT <data.url>` 上传图片（**不带 Authorization**，并会清洗反引号/引号/空格包裹）  
  代码：[result_report_service.py](file:///f:/Ai-LLM/southwest/05ui-poc/src/services/result_report_service.py)
- 符合项：路径/方法/字段 `objectName/url` 对齐，且对“反引号包裹”做了容错。

### 6) 任务状态变更接口

- 文档：`GET /client/task/status/{taskNo}/{statusCode}`。
- 代码：
  - 实现：`ResultReportService._process_task_status()`  
    代码：[result_report_service.py](file:///f:/Ai-LLM/southwest/05ui-poc/src/services/result_report_service.py)
  - 调用时机：
    - 进入检测：上报 `statusCode=2`（仅一次）  
      代码：`ProcessExecutionWindow._mark_task_running_once()`（同文件内）
    - 全部步骤完成：上报 `statusCode=3`  
      代码：[advance_to_next_step](file:///f:/Ai-LLM/southwest/05ui-poc/src/ui/windows/process_execution_window.py#L2309-L2329)
    - 手工通过：上报 `statusCode=4`  
      代码：[assembly_tasks_page.py](file:///f:/Ai-LLM/southwest/05ui-poc/src/ui/pages/assembly_tasks_page.py)
- 符合项：路径/方法符合，调用时机符合状态机定义。

### 7) 检测过程上传接口

- 文档：`POST /client/process`，入参：`task_no/step_code/step_status/object_name` 必填，`algo_result` 可选字符串。
- 代码：`ResultReportService._process_step_result()` 固定上报：
  - `step_status=2`（当前实现：检测结束后才上报“已完成”）
  - `algo_result`：将算法返回结构化对象 `json.dumps` 成字符串
  - 图片：先走 `/client/getUrl` 上传 JPEG，再把 `object_name` 作为必填字段上报  
  代码：[result_report_service.py](file:///f:/Ai-LLM/southwest/05ui-poc/src/services/result_report_service.py)
- 符合项：路径/方法/字段名对齐；符合“先传图片拿 objectName，再上报步骤过程”的流程。
- 可改进项（按文档语义更严格）：
  - `step_status=1（未完成）` 目前未在“步骤开始”上报；如果服务端需要完整过程链路，建议在开始检测时补一条 `step_status=1` 的上报（不带图片也可，取决于服务端约束）。

### 8) 获取过程记录接口

- 文档：`GET /client/getRecordList`（分页 + status 过滤）。
- 代码：未实现调用点（缺失功能）。

## 引导图 guide_url / guide_info 对齐情况

- 文档：`step_infos[].guide_url` 示例同时出现：
  - 纯 objectName（如 `2026-01-...uuid...`）
  - 带 `X-Amz-*` 的预签名 URL（且外层常被反引号包裹）
- 代码现状：
  - 已支持预签名 URL：会清洗反引号并对预签名 URL 用 `requests.get`（避免带 Authorization 导致 400），且日志脱敏 query。  
    代码：`GuideImageDownloadWorker`（[process_execution_window.py](file:///f:/Ai-LLM/southwest/05ui-poc/src/ui/windows/process_execution_window.py)）
  - `guide_info`：若为 JSON 字符串会 `json.loads` 后传给算法，否则原样传递。  
    代码：`_get_step_guide_info()`（同文件）
- 主要缺口：
  - 若服务端返回 `guide_url=objectName`，客户端目前没有从 objectName 生成下载 URL 的对接（文档未给出“下载接口/换取预签名下载 URL”的端点），会导致引导图无法加载。

## 建议整改清单（按优先级）

### P0（建议尽快）

- 禁止线上“空列表回退 mock”：将 [get_work_orders_online](file:///f:/Ai-LLM/southwest/05ui-poc/src/services/data_service.py) 的 mock 逻辑用配置开关控制（仅 dev/offline 模式启用）。
- 明确 `guide_url` 形态：推动服务端统一返回“可直接下载的预签名 URL”；或补充一个 “objectName→下载 URL/预签名下载 URL” 接口并在客户端对接。

### P1

- 算法列表请求不带分页参数：按文档“无需分页”修改 `NetworkService.get_algorithms()` 的请求参数与 `DataService.get_algorithms()` 的调用方式。
- 补齐 `/client/getRecordList`：如产品需要“过程记录查看/历史追溯”，建议新增页面与服务封装。

### P2

- 登录请求的 GET fallback 建议删除或仅在开发模式启用，避免安全策略风险。

