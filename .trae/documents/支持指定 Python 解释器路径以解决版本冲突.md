根据您的指示，我将更新算法包的部署逻辑，以支持使用包内自带的 Python 解释器。这将彻底解决环境兼容性问题，实现真正的“一次打包，到处运行”。

### 核心变更计划

**1. 更新 `src/runner/manager.py`**

*   **修改 `validate_package` 方法**：
    *   增加扫描逻辑：在 ZIP 包中查找 Python 解释器。
    *   **判定规则**：查找包含 `python.exe` (Windows) 或 `bin/python` (Linux) 的目录。
    *   **记录**：将发现的解释器路径（ZIP 内相对路径）记录到 `manifest` 的 `_internal_python_path` 字段中。

*   **修改 `install_package` 方法**：
    *   **优先级调整**：
        1.  **自带解释器（最高优先级）**：如果 `manifest` 中包含 `_internal_python_path`：
            *   解压该解释器目录到安装目录（例如 `deployed/<name>/<version>/python_runtime`）。
            *   验证解释器可用性（执行 `--version`）。
            *   **关键步骤**：调用该解释器创建虚拟环境：
                `deployed/.../python_runtime/python.exe -m venv deployed/.../venv`
        2.  **Conda 环境（次优先级）**：如果未发现自带解释器，但检测到版本不匹配且系统安装了 Conda，尝试创建 Conda 环境。
        3.  **系统解释器（低优先级）**：使用当前运行 Runner 的系统 Python 创建 venv。

*   **依赖安装**：
    *   无论使用哪种方式创建的 `venv`，后续的 `pip install` 步骤都将使用该 `venv` 中的 `pip`，确保依赖安装到正确的环境中。

### 预期效果
*   **自带环境**：如果算法包内含 Python 3.12 解释器，部署时将直接使用它创建环境，无需系统预装 Python 3.12 或 Conda。
*   **完全隔离**：算法运行环境完全自包含，不依赖宿主机的 Python 版本。
*   **向下兼容**：不含解释器的旧版算法包将继续使用现有的自动检测/Conda 回退逻辑。

请确认是否执行此计划。