# Day 7 — Agentic RAG

**Bài cá nhân · Python 3.11+ · tiếp nối Day 6**

Dùng embedding và vector store từ Day 6 để xây một agent biết tìm bằng chứng, trả lời có nguồn và nhận biết khi không đủ thông tin. Bạn tự chọn kiến trúc, số tool và cách tổ chức retrieval.

> **Tùy chọn:** [Gợi ý dùng AI để lập trình](AGENT_SETUP.md) giúp bạn làm lab; phần này không bắt buộc và không tính điểm.

## Bài cần làm

![Agent tìm tài liệu trong kho Day 6 và trả lời có nguồn](assets/retrieval-pipeline.svg)

1. Kết nối dữ liệu, embedding và vector store Day 6.
2. Xây agent dùng model thật và ít nhất một khả năng truy xuất dữ liệu. Agent có thể dùng nhiều tool và nhiều lượt gọi.
3. Thử **ít nhất 3 phương pháp retrieval khác nhau**, trong đó có dense retrieval dùng vector store Day 6. Tự chọn các phương pháp còn lại; xem [gợi ý](GUIDE.md#2-thử-các-phương-pháp-retrieval).
4. Thử nhiều cấu hình, benchmark, phân tích lỗi và chọn cấu hình tốt trên **dev**; sau đó đánh giá trên **test**.

Benchmark tối thiểu có **24 câu**: dev gồm 15 câu có đáp án và 2 câu thiếu bằng chứng; test gồm 5 câu có đáp án và 2 câu thiếu bằng chứng. Xem [benchmark](BENCHMARK.md) và [rubric](RUBRIC.md).

## Thử thách nâng cao · +15 điểm

Index một tài liệu thực tế từ **100 trang** có bảng, ảnh và biểu đồ; xây agent truy xuất và trả lời các câu hỏi về nội dung đó. Hoàn thành [thử thách nâng cao](ADVANCED.md) và đạt **ít nhất 90% benchmark test** để nhận 15 điểm bonus. Phần cơ bản tối đa 85 điểm; toàn bài tối đa 100 điểm.

## Bắt đầu

1. Đọc [hướng dẫn](GUIDE.md), [rubric](RUBRIC.md) và [quy tắc](RULES.md).
2. Tạo repo cá nhân theo [cách nộp bài](SUBMISSION.md), chuẩn bị đầu ra Day 6 và model hỗ trợ tool calling.
3. Dùng hoặc thay thế [starter](starter/README.md); bạn cần kết nối model và vector store thật.
4. Chạy `python -m unittest discover -s tests -v`. Test mock chỉ kiểm tra code, không phải benchmark agent thật.

![Các bước thử nghiệm trên dev và đánh giá trên test](assets/experiment-loop.svg)

Nộp code, cách chạy, cấu hình, benchmark, trace và [báo cáo](report/individual/MSSV_HoTen.md). Thời gian ở [checkpoints](CHECKPOINTS.md) là gợi ý, có thể điều chỉnh theo lớp và phạm vi thử nghiệm.

---

## Bài làm — Nguyễn Gia Bảo · 2A202603647 · K5-L3A

**Báo cáo:** [report/individual/2A202603647_NguyenGiaBao.md](report/individual/2A202603647_NguyenGiaBao.md) · **Benchmark:** [benchmark/README.md](benchmark/README.md) · **Dữ liệu:** [data/README.md](data/README.md)

Agentic RAG trên index Day 6 (OpenStax *Principles of Microeconomics 3e*, Ch3/4/14; e5-base 768 chiều; PostgreSQL + pgvector).
- **Agent:** `claude-haiku-5-5`, dùng vòng lặp tool thủ công với 3 tool: `search_textbook`, `submit_answer`, `abstain`.
- **Retrieval:** 4 phương pháp, gồm dense, BM25, hybrid RRF và hybrid + cross-encoder rerank, chạy trên 2 index B và B500.
- **Quy trình:** benchmark và tiêu chí chọn được khóa trước khi chạy (commit `a6ab742`). Cấu hình được chọn trên dev (commit `ab54365`), sau đó test được chạy đúng một lần.

### Cài đặt

Cần Python 3.11+ (đã thử trên 3.13.5, Windows, CPU), Docker, và repo Day 6 nằm cạnh repo này (hoặc đặt `DAY6_DIR`).

```bash
python -m venv .venv && .venv/Scripts/activate        # macOS/Linux: source .venv/bin/activate
python -m pip install torch==2.15.0 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.txt               # bản pin đầy đủ: requirements-lock.txt
# .env (không commit): ANTHROPIC_API_KEY=...  DATABASE_URL=postgresql://day6:day6_local_only@127.0.0.1:55433/day6_lab
# Trong <Day6>/starter: docker compose -p day6_student_starter up -d --wait   (index A/B/B500 đã ingest ở Day 6)
```

Trên Windows nên đặt `PYTHONUTF8=1`. Nếu thiếu, test `test_cli_uses_requested_split_only` của starter sẽ đọc file bằng cp1252 và báo lỗi.

### Lệnh chạy (theo đúng thứ tự đã làm)

| Bước | Lệnh | Output |
|---|---|---|
| 0. Test code (offline) | `python -m unittest discover -s tests -v` | 29 test (15 starter + 9 Day 7 + 5 phần nâng cao) |
| 1. Dựng và kiểm chứng benchmark | `python -m src.benchmark` | `benchmark/questions.json` |
| 2. Export index Day 6 | `python -m src.cli export` | `data/day6_export/` (+ `manifest.json` có hash phiên bản index) |
| 3. Retrieval trên dev | `python -m src.eval_retrieval --split dev` | `results/retrieval/dev/*.jsonl`, `metrics.csv` |
| 4. Agent trên dev | `python -m src.eval_agent --split dev` | `results/agent/dev/*.jsonl` (trace đầy đủ) |
| 5. Chấm nhãn và tổng hợp | `python src/make_labels.py . dev results/agent/dev/labels/grading_spec_dev.json` rồi `python -m src.agent_report --split dev --configs ...` | `labels/*.json`, `*_summary.json` |
| 6. Chọn cấu hình theo quy tắc đã chốt | `python -m src.select_config` | `results/selection.json` (mở khóa test) |
| 7. Test (một lần) | `python -m src.eval_retrieval --split test --configs dense_B hybrid_rerank_B` và `python -m src.eval_agent --split test --configs agent_dense_B agent_hrr_B_1shot agent_hrr_B_1shot_v2` | `results/*/test/` |
| 8. Chẩn đoán hậu kiểm (không dùng để chọn) | `python -m src.budget_ablation` | `results/retrieval/budget_ablation_posthoc.csv` |
| 9. Kiểm chứng kết nối Day 6 | `python -m src.check_day6_parity` | `results/day6_parity.json` (22/22) |
| 10. Sau test, chỉ trên dev: ablation và lặp lại | `python -m src.eval_agent --split dev --configs agent_hrr_B_nbr agent_hrr_B_rule agent_hrr_B_ctx8k`; `... --configs agent_hrr_B_1shot --tag _run2` (và `_run3`) | `results/agent/dev/` |
| 11. test2 (holdout mới, khóa ở `5c0102d`) | `python -m src.benchmark --test2`; `python -m src.eval_retrieval --split test2 --configs dense_B hybrid_rerank_B`; `python -m src.eval_agent --split test2 --configs agent_dense_B agent_hrr_B_1shot agent_hrr_B agent_hrr_B_ctx8k` | `results/*/test2/` |
| 12. Chấm mù của học viên | `python -m src.blind_review make` → điền `results/agent/blind_review.csv` → `python -m src.blind_review score` | `results/agent/blind_agreement.json` |
| Thử một query | `python -m src.cli search "What is the first rule of labor markets?" --config hybrid_rerank_B` | |

Code chặn chạy `--split test` khi chưa có `results/selection.json`, và chặn mọi cấu hình không được khai báo trong file đó.

### Kết quả chính

| | Dev (24 + 4) | Test (11 + 4) | test2 (10 + 4, sau test) |
|---|---|---|---|
| Retrieval baseline `dense_B`: Hit@1 / Evidence Hit@3 / Context Evidence | 13/24 · 15/24 · 19/24 | 7/11 · 11/11 · 10/11 | 5/10 · 9/10 · 10/10 |
| Retrieval chọn `hybrid_rerank_B` | 16/24 · **22/24** · 22/24 | 8/11 · 10/11 · 9/11 | **9/10** · 10/10 · 10/10 |
| Agent baseline `agent_dense_B`: grounded TB · từ chối đúng · từ chối nhầm | 2.00/2 · 4/4 · 0/24 | 1.82/2 · 4/4 · 1/11 | 2.00/2 · 4/4 · 0/10 |
| Agent chọn `agent_hrr_B_1shot` | 2.00/2 · 3/4 · 0/24 (3 lần chạy: 1.92–2.00) | 1.82/2 · 4/4 · 1/11 | 2.00/2 · 4/4 · 0/10 |
| Chi phí agent (Haiku 5.5) | khoảng $0.0005–0.0007/câu | | tổng cả bài $0.23 (381 lượt chạy) |

Phân tích, lỗi và giới hạn nằm trong [báo cáo](report/individual/2A202603647_NguyenGiaBao.md). Nhãn do LLM chấm nháp; phiếu duyệt của học viên nằm ở [results/agent/REVIEW.md](results/agent/REVIEW.md).

### Thử thách nâng cao

Toàn bộ nằm trong [advanced/](advanced/); báo cáo ở [advanced/REPORT.md](advanced/REPORT.md).
- **Phạm vi:** cả cuốn sách 595 trang (text, 167 bảng, 198 hình mô tả bằng vision), agent có tool `view_region` để đọc lại vùng gốc trên PDF.
- **Benchmark:** dev 18 câu, test 30 câu.
- **Kết quả test (chạy một lần):** __ADV_TEST__
- **Lệnh chạy:** xem [advanced/REPORT.md §11](advanced/REPORT.md#11-tái-lập).

### Cấu trúc code

| File | Vai trò |
|---|---|
| `src/config.py` | Đường dẫn, model, giá, toàn bộ cấu hình retrieval và agent (kèm giả thuyết) |
| `src/store.py` | Đọc pgvector Day 6 (read-only, exact cosine, filter qua whitelist), export chunk |
| `src/bm25.py`, `src/retrievers.py` | BM25; dense, hybrid RRF, rerank; filter `chapter` áp dụng cho mọi phương pháp |
| `src/metrics.py` | Hit theo chuẩn hóa Day 6, multi-hop `evidence_groups`, đóng gói context theo budget |
| `src/agent.py` | Vòng lặp agent: điều kiện dừng, kiểm tra citation, ghi lỗi, mở rộng chunk lân cận (v2) |
| `src/eval_retrieval.py`, `src/eval_agent.py` | Chạy benchmark và ghi trace |
| `src/make_labels.py`, `src/agent_report.py` | Nhãn từ spec có lý do; tổng hợp bằng `aggregate()` của starter |
| `src/select_config.py`, `src/budget_ablation.py` | Áp quy tắc chọn đã chốt; chẩn đoán budget hậu kiểm |
| `src/check_day6_parity.py`, `src/blind_review.py` | Kiểm chứng kết quả top-3 khớp Day 6; phiếu chấm mù và Cohen's kappa |
| `benchmark/test2/` | Holdout thứ hai, khóa trước khi chạy (README riêng) |
