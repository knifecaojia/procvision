I have updated the plan to explicitly mock all network operations as the server is not ready.

## 1. Backend Service Layer (`src/services/algorithm_manager.py`)

Create `AlgorithmManager` to handle logic, mocking server interactions.

*   **Mock Data**: Define a hardcoded list of "Server Algorithms" (similar to the dummy data currently in `model_page.py`) to simulate the server response.
*   **Sync Logic**:
    *   `get_all_algorithms()`:
        *   1. Fetch Mock Server List.
        *   2. Scan `algorithms/zips` (Downloaded).
        *   3. Scan `Runner.registry` (Deployed).
        *   4. Merge based on Name/Version.
        *   5. Mark algorithms found in Zips/Registry but NOT in Server List as "Local".
*   **Mock Actions**:
    *   `download(algorithm_id)`: Simulate network delay (Timer), then copy a dummy "template" zip to `algorithms/zips/<name>-<version>.zip` to simulate a successful download.
    *   `deploy(zip_path)`: **Real execution** using `Runner.package_manager.install_package` (since this is local).
    *   `import_local(path)`: **Real execution** (Copy file).

## 2. Enhance Runner Manager (`src/runner/manager.py`)

*   Add `uninstall_package(name, version)`: Real deletion of deployed files/registry entry.
*   Add `delete_zip(name, version)`: Real deletion of zip file.

## 3. UI Components (`src/ui/components/model_card.py`)

*   **Style**: Strict adherence to existing `QFrame/Layout` styles.
*   **New Elements**:
    *   Add `QProgressBar` (default hidden).
    *   Add "Source" label (Server/Local).
*   **Buttons**: Dynamic visibility based on state:
    *   `Remote Only` -> [Download]
    *   `Downloaded` -> [Deploy] [Delete Zip]
    *   `Deployed` -> [Undeploy]

## 4. UI Page (`src/ui/pages/model_page.py`)

*   **Header**: Add "Import Local Package" button (Styled like existing buttons).
*   **Logic**:
    *   Replace hardcoded `models_data` with calls to `AlgorithmManager`.
    *   Implement `QThread` or `QTimer` workers for the Mock Download and Real Deploy operations to keep UI responsive and update progress bars.

## 5. Mock Resources
*   Create a simple valid `template_algo.zip` (with `manifest.json`) in `tests/assets` or similar to use for the Mock Download action, so "Download" actually results in a deployable file.

This plan ensures full UI functionality testing without a real backend.
