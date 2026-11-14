# Phiếu duyệt nhãn của học viên

Toàn bộ nhãn trong `results/agent/*/labels/*.json` và `results/retrieval/test/context_labels.json` là **bản nháp do LLM chấm** (Claude Code, Opus 5.5). LLM đã đọc câu trả lời, toàn văn từng chunk được trích dẫn và evidence gold. Lý do của từng nhãn nằm trong `grading_spec_*.json`.

BENCHMARK.md yêu cầu người làm bài **tự đọc** ít nhất 5 câu test có đáp án và 2 câu thiếu evidence. Với mỗi dòng dưới đây, bạn mở trace (`results/agent/test/<config>.jsonl`, tìm theo `query_id`), đọc câu trả lời và chunk được trích, rồi điền cột "Học viên". Nếu bạn không đồng ý với nhãn, sửa `grading_spec_test.json` và chạy lại:

```bash
python src/make_labels.py . test results/agent/test/labels/grading_spec_test.json
python -m src.agent_report --split test --configs agent_dense_B agent_hrr_B_1shot agent_hrr_B_1shot_v2
```

| # | Câu | Cấu hình | Nhãn LLM | Lý do tóm tắt | Học viên (đồng ý / sửa thành) | Ghi chú |
|---|---|---|---|---|---|---|
| 1 | t01 | agent_hrr_B_1shot | 2, citation 2/2 | $3.25→$2.50, 250k→550k, p78 | | |
| 2 | t05 | agent_hrr_B_1shot | 2, citation 1/1 | $7, lý do "tăng lương cho mọi người", p344 | | |
| 3 | t07 | agent_dense_B | 2, citation 1/1 | FLSA 1938, bảng 14.4 p342; filter chương 14 | | |
| 4 | t09 | agent_dense_B | 0 (từ chối nhầm) | p342-001 tìm thấy ở hạng 5 nhưng bị budget loại | | |
| 5 | t10 | agent_hrr_B_1shot | 2, citation 2/2 | 57% (p355) + $2.8M/$1.2M (p362) | | |
| 6 | t02 | agent_hrr_B_1shot_v2 | 1 | Thiếu "more required education → lower supply" và các ví dụ | | |
| 7 | t11 | agent_hrr_B_1shot | 2, citation 1/1 | $700B − $510B = $190B | | |
| 8 | ut1 | agent_hrr_B_1shot | từ chối đúng | Không có % cho laptop | | |
| 9 | ut3 | agent_dense_B | từ chối đúng | UAW chỉ có số năm 1985/2015/2021 | | |
| 10 | dev q22 | agent_hrr_B | 1, citation p357-005 sai | Model tự viết tiếp chunk bị cắt | | |
| 11 | dev ud3 | agent_hrr_B_1shot | không tính là từ chối | Gọi `submit_answer` để nói "sách không ghi" | | |

Người duyệt: ____________ · Ngày: ____________ · Số nhãn đã sửa: ____
