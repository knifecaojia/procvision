根据最新的 `runner_spec.md` 和 SDK 代码分析，我将对算法运行引擎进行重构。

### 重构目标
将现有的 "双阶段 (Pre-Execute/Execute)" 引擎改造为符合新规范的 **"单次 Execute 调用"** 模型，并支持双图像输入（当前图像 + 引导图像）及新的数据结构。

### 详细变更计划

**1. 重构数据类型 (`src/runner/types.py`)**
*   **`CallRequest`**:
    *   移除 `phase`, `session`, `user_params`, `pid` 等过时字段。
    *   新增 `request_id` 和 `data` 容器。
    *   `data` 结构将包含：`step_index`, `step_desc`, `guide_info`, 以及两组图像信息 (`cur_image_shm_id/meta`, `guide_image_shm_id/meta`)。
*   **`CallResult`**:
    *   适配新的返回结构，包含 `request_id`, `status` (协议级), `data` (业务级结果)。
    *   `CallResultData` 将精简为 `result_status` (OK/NG), `defect_rects`, `ng_reason` 等。

**2. 重写运行引擎 (`src/runner/engine.py`)**
*   **移除旧生命周期方法**：删除 `setup_algorithm`, `teardown_algorithm`, `reset_algorithm`, `on_step_start/finish`，因为新协议不再支持这些显式调用。
*   **重构 `execute_flow`**：
    *   **签名变更**：更新为接受双图输入 `(cur_image, guide_image)` 及步骤信息 `(step_index, step_desc, guide_info)`。
    *   **共享内存处理**：为 `cur_image` 和 `guide_image` 分别生成唯一的 SHM ID 并写入数据。
    *   **调用逻辑**：构建单次 `execute` 请求，不再进行 `pre` 阶段调用。
    *   **清理逻辑**：确保两份图像的共享内存都在调用结束后清理。

**3. 更新进程通信 (`src/runner/process.py`)**
*   **`call` 方法增强**：
    *   自动生成并注入 `request_id` (UUID)。
    *   发送请求后，在接收循环中严格匹配返回消息的 `request_id`，确保请求响应一一对应。

### 兼容性说明
此次重构是破坏性变更，不再兼容旧版 SDK 的双阶段调用协议。请确保所有使用的算法包均已升级到适配新规范的 SDK 版本。