# Benchmark Day 7 — Principles of Microeconomics 3e (Ch3, Ch4, Ch14)

Khóa ở commit này **trước mọi lần chạy retrieval hoặc agent**. Dựng lại và kiểm chứng: `python -m src.benchmark`.

## Nguồn câu hỏi và chia split

| Split | Có đáp án | Thiếu evidence | Tổng | Nguồn |
|---|---:|---:|---:|---|
| dev | 24 | 4 | 28 | 22 câu Day 6 (`q01`–`q22`, kể cả 6 câu test Day 6) + `m01`, `m02` (multi-hop) + `ud1`–`ud4` |
| test | 11 | 4 | 15 | Câu mới hoàn toàn: `t01`–`t11`, `ut1`–`ut4` |

- **Vì sao đưa test Day 6 vào dev:** test Day 6 đã được chạy và phân tích hậu kiểm (thí nghiệm B500 được đề xuất *sau khi* xem kết quả test). Vì vậy nó không còn là holdout độc lập, và theo RULES phải dùng một test mới.
- **Test mới:** được viết từ những đoạn mà không câu dev nào dùng làm evidence. Script kiểm tra dev và test không chung câu evidence nào. Các câu test có thể cùng *mục* với câu dev (corpus chỉ có 78 trang, các mục đều đã có câu dev), nhưng khác trang, đoạn và đáp án.
- **Loại câu ở test:** 2 direct, 3 paraphrase, 2 conditional/bảng, 2 filter, 2 multi-hop, và 4 câu thiếu evidence.
- **Hạn chế đã biết:** người viết câu hỏi biết trang gold, nên cách diễn đạt có thể vô tình thuận lợi cho truy xuất. Câu hỏi được viết bằng **tiếng Anh**, cùng ngôn ngữ với corpus, giống Day 6. Các câu mới do Claude Code soạn từ việc đọc trang gốc và được máy kiểm chứng evidence.
  - *Đính chính ngày 14/11/2026, sau khi khóa; chỉ sửa câu chữ, không đổi câu hỏi hay nhãn:* bản trước ghi "học viên duyệt từng câu", nhưng thực tế học viên chưa duyệt độc lập từng câu benchmark.
  - Phần duyệt của học viên nằm ở [results/agent/REVIEW.md](../results/agent/REVIEW.md) và [results/agent/BLIND_REVIEW.md](../results/agent/BLIND_REVIEW.md).

## Schema

- `evidence_groups`: danh sách **nhóm bắt buộc**. Mỗi nhóm gồm các **evidence thay thế** `{source_id, page, evidence}`. Câu thường có 1 nhóm; câu multi-hop có 2 nhóm.
- `gold` là nhóm đầu tiên, giữ lại để tương thích với starter. Lưu ý: hàm `hit()` của starter so chuỗi thô, không chuẩn hóa.
- `alt_gold` của Day 6 được chuyển thành evidence thay thế trong cùng nhóm.
- **Bổ sung evidence thay thế cho câu mới:** t04 (chú thích hình p88), t08 (ví dụ xăng p64), t11 (p107 lặp lại số liệu của p108). Các trang này được tìm ra bằng cách quét con số đặc trưng của đáp án trên toàn corpus *trước khi chạy*.
- **Câu thiếu evidence:** có `absence_reason` và `absence_check.keywords`. Script quét keyword trên toàn bộ 78 trang `pages.jsonl`, rồi học viên đọc từng trang có keyword để xác nhận không có đáp án. Việc từ chối **không** được suy ra từ chỗ top-k không tìm thấy.
  - Ví dụ ut4 bản đầu (lãi suất thẻ tín dụng 2022) bị loại khi soát tay, vì p107 có câu "A typical credit card interest rate ranges from 12% to 18%".
- **Filter** `{"chapter": N}` chỉ có ở `q05, q09, q13, q18, q19` (dev) và `t07, t08` (test). Đây là input giả định "người học đang học chương N", được cung cấp trước khi truy xuất, giống Day 6. Filter **không** suy ra từ gold. Agent nhận filter như một tham số của phiên, không thấy gold.

## Định nghĩa metric (chốt trước)

**Chunk hit:** chunk có `document_id` và `page` khớp một evidence thay thế, **và** `match_key(evidence)` là chuỗi con của `match_key(chunk.text)`. `match_key` là hàm chuẩn hóa của Day 6: NFKC, nháy và gạch ngang ASCII, gộp khoảng trắng, chữ thường. Evidence bị cắt qua hai chunk thì không tính là hit.

| Metric | Định nghĩa | Mẫu số |
|---|---|---|
| Hit@1 | Chunk top-1 là hit của bất kỳ nhóm nào | câu có đáp án |
| Evidence Hit@3 | Có ít nhất một hit trong top-3 | câu có đáp án |
| Full Evidence@3 | **Mọi** nhóm đều có hit trong top-3 (khác Hit@3 chỉ ở câu multi-hop) | câu có đáp án |
| MRR@10 | 1/rank của hit đầu tiên trong top-10 | câu có đáp án |
| Context Evidence Rate | **Mọi** nhóm có hit nằm trong *context cuối gửi cho model* | câu có đáp án |

- Câu thiếu evidence **không** nằm trong mẫu số của các metric retrieval.
- Retrieval được đánh giá trên **query gốc**. Query do agent viết lại được báo riêng trong trace agent.
- **Context của pipeline retrieval:** các kết quả xếp theo rank, bỏ trùng, lần lượt thêm vào nếu còn vừa budget **4000 ký tự** (gồm cả header nguồn). Chunk không vừa thì bị bỏ qua, không cắt ngang. Token ≈ ký tự/4 (ước lượng).
- **Context của agent:** hợp của mọi chunk mà tool trả về cho model trong cả phiên. Kích thước đo bằng ký tự, và token lấy từ `usage` thật của API.

**Đánh giá agent** (theo BENCHMARK.md của đề): tool use; grounded answer 0/1/2 (từ chối câu có đáp án → 0); citation hợp lệ (có trong context **và** hỗ trợ câu trả lời); abstention đúng; từ chối nhầm. Nhãn do người chấm đọc trace và đối chiếu evidence.

## Tiêu chí chọn cấu hình (chốt trước, chỉ dùng dev)

**Giai đoạn 1: chọn retriever cho agent** (so 7 cấu hình trong `src/config.py`, cùng index version, cùng câu hỏi):
1. Evidence Hit@3 dev cao nhất. Chênh ≤1 câu (≤1/24) coi là hòa.
2. Nếu hòa: Context Evidence Rate dev cao hơn.
3. Nếu vẫn hòa: Hit@1 dev cao hơn.
4. Nếu vẫn hòa: thời gian truy vấn trung vị thấp hơn (ít thành phần hơn).

**Giai đoạn 2: chọn cấu hình agent** (agent + `dense_B` là baseline, so với agent + retriever chọn ở giai đoạn 1 và các biến thể agent):
1. Điều kiện bắt buộc: abstention dev ≥ 3/4 và không lỗi hệ thống.
2. Grounded answer trung bình dev cao nhất. Chênh ≤0,1/2 coi là hòa.
3. Nếu hòa: từ chối nhầm ít hơn.
4. Nếu vẫn hòa: chi phí trung bình mỗi câu thấp hơn.

**Test:** chạy **một lần** cho baseline và cấu hình đã chọn, sau khi `results/selection.json` đã được commit. Code từ chối chạy test khi chưa có file này.
