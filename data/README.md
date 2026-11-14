# Định dạng dữ liệu

Các file `example_*.json` chỉ minh họa định dạng, không đủ để nộp bài. Dữ liệu thật là JSON array UTF-8; nếu dùng định dạng khác, ghi cách chuyển trong README.

- **Chunk:** `id`, `text`, `source_id`, `source`, `page`, `metadata`. ID phải duy nhất; giữ phiên bản hoặc ngày nếu có.
- **Câu có đáp án:** `id`, `split` (`dev` hoặc `test`), `question`, `expected_answer`, `gold`: danh sách `{source_id, page, evidence}`. Với schema mẫu, mỗi evidence phải nằm trọn trong một chunk đúng nguồn và trang; các phần tử `gold` là evidence thay thế. Với câu multi-hop cần nhiều đoạn, bạn có thể mở rộng schema, ghi rõ nhóm evidence bắt buộc và cách chấm. Có thể thêm `filter` do người dùng cung cấp trước.
- **Câu thiếu evidence:** `id`, `split`, `question`, `answerable: false`, `expected_behavior: "search_and_abstain"`, `absence_reason`. Xem `agent_cases_example.json`.

Không đưa `gold` hoặc nhãn đáp án vào model và retrieval tool. Ghi nguồn dữ liệu và quyền sử dụng. Cách chuyển một số định dạng Day 6: [starter/README.md](../starter/README.md).

## Dữ liệu thật của bài này

- **`day6_export/chunks_B.jsonl`, `chunks_B500.jsonl`:** chunk của index `B` (326) và `B500` (628), export từ bảng `chunks` của pgvector Day 6 bằng `python -m src.cli export`.
  - Định dạng **JSONL** (mỗi dòng một chunk theo đúng schema ở trên), không phải JSON array.
  - `metadata` gồm `chapter`, `chapter_title`, `section`, `start_char`, `end_char`, `index` và `content_hash`.
  - Không chứa vector; vector chỉ nằm trong pgvector.
- **`day6_export/manifest.json`:** số chunk, model embedding và `index_version_sha256`, là sha256 của danh sách `chunk_id:content_hash`. Dùng để xác nhận BM25 và dense chạy trên **cùng một phiên bản index**.
- **Nguồn:** OpenStax *Principles of Microeconomics 3e* (Rice University), CC BY-NC-SA 4.0. Chỉ dùng phi thương mại và có ghi nguồn. Chi tiết lấy PDF và manifest trang nằm ở repo Day 6.
- **Benchmark:** [../benchmark/questions.json](../benchmark/questions.json). Schema mở rộng `evidence_groups` cho câu multi-hop, xem [../benchmark/README.md](../benchmark/README.md).
