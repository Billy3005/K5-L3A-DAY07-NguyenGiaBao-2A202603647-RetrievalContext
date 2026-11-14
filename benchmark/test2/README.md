# test2 — holdout thứ hai (tạo sau khi test gốc đã được dùng)

**Vì sao có test2:** test gốc đã chạy đúng một lần (commit `9fbe014`). Phân tích lỗi trên test (t09, t02) dẫn tới giả thuyết mới về budget context. Theo RULES.md ("Nếu đã xem test để chỉnh, tạo test mới và ghi rõ"), mọi thay đổi làm **sau khi** xem test chỉ được đánh giá trên bộ câu mới này.

| | Có đáp án | Thiếu evidence |
|---|---:|---:|
| test2 | 10 (2 direct, 1 paraphrase, 2 conditional/bảng, 2 filter, 2 multi-hop, 1 direct có evidence thay thế) | 4 |

- **Nguồn:** chỉ lấy từ các trang **chưa từng** là trang evidence của dev hay test gốc (p60, 73, 81, 98, 101, 109, 337, 352, 354, 359). Ngoại lệ là a07, có thêm một câu thay thế ở p342 (một câu khác với câu dev/test đã dùng ở trang này). Script kiểm tra test2 không chung câu evidence nào với dev hay test: `python -m src.benchmark --test2`.
- **Schema, định nghĩa metric và cách chấm:** giống hệt bộ chính ([../README.md](../README.md)).
- **Filter** (a06, a08) là input người dùng, kèm distractor khác chương được ghi trước khi chạy:
  - a06: Social Security ở Ch4 (tiết kiệm), distractor là Social Security Act ở Ch14.
  - a08: người đánh máy ở Ch4 (công nghệ thay thế lao động), distractor là người đánh máy ở Ch14 (năng suất cao hơn).
- **Câu thiếu evidence:** đặt sát cạnh câu có đáp án, ví dụ giá xăng 2022 (sách chỉ có 2020/2021) hay tỷ lệ công đoàn ở Canada (sách chỉ có ngưỡng 60% chữ ký). Mọi trang có keyword liên quan đã được đọc tay.
- **Hạn chế:** câu do Claude Code soạn khi đã đọc trang gốc; 10 câu là mẫu nhỏ.

**Cấu hình được phép chạy và các so sánh đã khai báo trước:** xem `results/test2_preregistration.json`, commit trước khi chạy. Code chặn mọi cấu hình không có trong file đó. test2 **không dùng để chọn cấu hình**, chỉ để kiểm chứng giả thuyết.
