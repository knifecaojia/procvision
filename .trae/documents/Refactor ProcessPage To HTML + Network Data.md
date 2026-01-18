## 为什么 QTextBrowser 更合适
- 现有 `records_page.py` 已经用 `QTextBrowser` 做 HTML 渲染（不依赖 WebEngine），并用 `anchorClicked` 做交互回调。
- 相比 WebEngine：更轻量、启动更快、对登录窗口链式 import 更不敏感，也更少出现“程序在后台跑但窗口不弹”的问题。

## 代码现状（与本次改动直接相关）
- `src/ui/pages/records_page.py`：QTextBrowser + `setHtml(...)` + `anchorClicked` 已跑通交互范式。
- `src/services/network_service.py`：已有 `get_work_orders()` 调用 `/client/workorder/list`（需要 token）。
- `src/services/data_service.py`：`get_work_orders()` 目前“网络优先，失败回退 mock”。
- `src/ui/main_window.py`：模块顶层 import `ProcessPage`/`RecordsPage`。
- 你说明：`process_page` 的修改已被 git 忽略，所以不能依赖直接改 `process_page.py` 来落地需求。

## 修改目标（按 spec20260116.md）
- 装配任务页显示改为与 records 一样：HTML 预览（QTextBrowser），不再依赖自定义控件卡片。
- 装配任务数据完全来自网络接口（不使用 mock 回退）。

## 实施计划（最小侵入、可回滚）
### 1) 新增“装配任务 HTML 页”（不改被 ignore 的 process_page.py）
- 新增 `src/ui/pages/assembly_tasks_page.py`：
  - UI 结构沿用 records：Header + Filter（状态）+ QTextBrowser + Pagination。
  - `QTextBrowser.setOpenExternalLinks(False)` + `anchorClicked` 实现“启动工艺/查看详情”等动作。
  - HTML 采用表格布局（对齐 records 的可控样式），列：工单号、工艺名称、版本、操作员、算法、状态、部署状态、操作（启动）。

### 2) 主窗口切换引用到新页面
- 修改 `src/ui/main_window.py`：将“装配引导与检测”页面从 `ProcessPage` 切换为 `AssemblyTasksPage`（新增文件）。
  - 保留旧 `ProcessPage` 文件不动，避免 git ignore 带来的不可控。

### 3) ProcessPage 数据网络化（network-only）实现方式
- 在 `DataService` 增加网络专用方法（不影响其他页面）：
  - `get_work_orders_online(page, page_size, status)`：仅调用 `NetworkService.get_work_orders`，失败返回空列表并附带错误信息（不读 mock）。
- `AssemblyTasksPage.load_data()` 固定调用该 online 方法。
- token 缺失时（未登录/登录失败）：页面渲染空态 HTML（提示“未登录或无权限”），不走 mock。

### 4) 服务端字段映射（集中处理）
- 在 `assembly_tasks_page.py` 内实现 `map_work_order(row)`：
  - 将服务端 `rows` 映射到 UI 统一字段（work_order_code/process_name/craft_version/worker_name/status/algorithm_code/algorithm_name/algorithm_version/step_infos）。
  - 允许字段缺失时 fallback 默认值，保证 HTML 不崩。
  - 后续如果飞书文档字段与现有接口不一致，只需改这个映射函数。

### 5) 部署状态与按钮启用
- 继续复用 `AlgorithmManager.check_deployment_status(algo_name, algo_version, algorithm_code)`。
- HTML 中：未部署则“启动”显示为灰色不可点击（不渲染 href）；已部署渲染为可点击链接（href 采用自定义 scheme）。

### 6) 启动工单执行
- `anchorClicked(QUrl)` 解析形如 `app://start?work_order=...` 的链接。
- Qt 侧根据 work_order_code 从缓存的 `items_by_code` 取出工单原始数据，组装 `ProcessExecutionWindow` 需要的 normalized dict 并打开窗口。

## 验证清单（实现后）
- 登录后进入“装配引导与检测”：能从网络加载工单并显示 HTML 表格。
- 状态筛选、分页可用。
- 未登录/断网：显示空态提示，不读取 mock。
- 点击“启动”：能打开 `ProcessExecutionWindow`。

## 影响文件（预计）
- 新增：`src/ui/pages/assembly_tasks_page.py`
- 修改：`src/ui/main_window.py`
- 修改：`src/services/data_service.py`（新增 get_work_orders_online 或 allow_fallback 参数）

确认后我再开始落地实现。