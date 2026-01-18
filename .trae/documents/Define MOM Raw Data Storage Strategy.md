I will update `design_spec_v1.md` to explicitly define the storage strategy for raw MOM data.

1.  **Add a new subsection in "5. MOM Data Interaction Specification"**:
    *   **Title**: `5.4 原始数据存储 (Raw Data Storage)`
    *   **Content**:
        *   Define a database table `sys_mom_log` (or `biz_mom_log` to match the `biz_` prefix convention, but the spec previously mentioned `sys_mom_log`. I will stick to `sys_mom_log` or change it to `biz_mom_req_log` for consistency if needed. Actually, `sys_mom_log` was mentioned in section 3.2. I will detail it here).
        *   **Table Schema**:
            *   `id`: Primary Key.
            *   `req_type`: Type of request (e.g., "TASK_PUSH", "PROCESS_SYNC").
            *   `req_payload`: **LongText/JSON** type to store the full raw JSON body.
            *   `req_time`: Timestamp of receipt.
            *   `process_status`: Status of async processing (RECEIVED, PROCESSED, FAILED).
            *   `err_msg`: Error message if processing failed.
        *   **Retention Policy**: Suggest a cleanup policy (e.g., keep for 30 days) to avoid database bloat.

2.  **Rationale**:
    *   Traceability: Essential for debugging integration issues with MOM.
    *   Replayability: Allows re-processing messages if the business logic updates or fails.

I will implement this update to the markdown file.