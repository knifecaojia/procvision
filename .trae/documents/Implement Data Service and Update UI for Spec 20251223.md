I have refined the plan to include a background thread for processing the upload queue, ensuring the UI remains responsive.

### 1. Create Data Service Layer
- **Create `src/services/data_service.py`**:
    - Implement `DataService` class.
    - **Background Processing**:
        - Initialize a thread-safe **FIFO Queue**.
        - Start a **Background Daemon Thread** to continuously consume and process items from the queue.
        - Ensure all upload operations (logs and images) are non-blocking for the UI.
    - **Methods**:
        - `get_algorithms()`: Read from `data/mock/algorithms.json`.
        - `get_work_orders(page, page_size)`: Read from `data/mock/work_orders.json` with pagination.
        - `upload_step_log(step_data)`: Push step log to the unified queue.
        - `upload_result_log(result_data)`: Push result log to the unified queue.
        - `upload_image(file_path)`: Push image upload task to the unified queue (or handle as part of the log task if dependent).

### 2. Refactor Algorithm Manager
- **Modify `src/services/algorithm_manager.py`**:
    - Remove hardcoded `mock_server_data`.
    - Integrate `DataService` to fetch algorithm list.
    - Map `algorithms.json` fields to the internal format expected by the UI.

### 3. Update Process Page (Work Orders)
- **Modify `src/ui/pages/process_page.py`**:
    - Replace simulated data with `DataService.get_work_orders`.
    - **Add Pagination**:
        - Add "Previous" and "Next" buttons and a page indicator.
        - Implement logic to handle page navigation.

### 4. Update Process Card
- **Modify `src/ui/components/process_card.py`**:
    - Update UI to display fields from `work_orders.json`:
        - **Header**: Process Name, Work Order Code.
        - **Info Grid**: Worker Name, Algorithm Name/Version, Status.
        - **Steps**: Display step count and content from `step_infos`.
    - Map status codes to human-readable labels.

### 5. Verify & Test
- Verify `ModelPage` loads algorithms from JSON.
- Verify `ProcessPage` loads work orders with pagination.
- Verify `ProcessCard` displays correct details.
