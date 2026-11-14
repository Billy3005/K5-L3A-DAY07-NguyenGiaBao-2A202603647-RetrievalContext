# Phiếu duyệt nhãn của học viên

Toàn bộ nhãn trong `results/agent/*/labels/*.json` và `results/retrieval/test/context_labels.json` là **bản nháp do LLM chấm** (Claude Code, Opus 5.5). Học viên đã đối chiếu các trace, câu trả lời, chunk được trích dẫn và evidence gold cho 11 mục dưới đây.

| # | Câu | Cấu hình | Nhãn LLM | Lý do tóm tắt | Học viên (đồng ý / sửa thành) | Ghi chú |
|---|---|---|---|---|---|---|
| 1 | t01 | agent_hrr_B_1shot | 2, citation 2/2 | $3.25→$2.50, 250k→550k, p78 | Đồng ý: 2, citation 2/2 | Hai chunk p78-001 và p78-000 lần lượt hỗ trợ kết quả cung tăng và đầy đủ số liệu giá, lượng cân bằng trước/sau. |
| 2 | t05 | agent_hrr_B_1shot | 2, citation 1/1 | $7, lý do "tăng lương cho mọi người", p344 | Đồng ý: 2, citation 1/1 | Bảng 14.5 cho MC = $7 (tổng chi phí $16 − $9); phần văn bản ngay dưới bảng giải thích phải trả mức lương cao hơn cho cả lao động đã tuyển trước đó. |
| 3 | t07 | agent_dense_B | 2, citation 1/1 | FLSA 1938, bảng 14.4 p342; filter chương 14 | Đồng ý: 2, citation 1/1 | p342-001 nêu trực tiếp Fair Labor Standards Act of 1938 và quy định lương tối thiểu, làm thêm giờ khi vượt 40 giờ/tuần. Đáp án trả lời đúng câu hỏi xác định tên luật. |
| 4 | t09 | agent_dense_B | 0 (từ chối nhầm) | p342-001 tìm thấy ở hạng 5 nhưng bị budget loại | Đồng ý: 0 (từ chối nhầm) | Đây là câu trả lời được trong sách. Trace cho thấy chunk FLSA được lấy ở hạng 5 nhưng không vào context do giới hạn 4.000 ký tự; phần union có trong context nhưng thiếu hop FLSA. Agent từ chối vì thiếu context, nên điểm câu trả lời là 0. |
| 5 | t10 | agent_hrr_B_1shot | 2, citation 2/2 | 57% (p355) + $2.8M/$1.2M (p362) | Đồng ý: 2, citation 2/2 | p355-004 hỗ trợ tỷ lệ 57%; p362-002 hỗ trợ mức thu nhập $2,8 triệu và chênh lệch $1,2 triệu. Cả hai hop đều có bằng chứng và citation phù hợp. |
| 6 | t02 | agent_hrr_B_1shot_v2 | 1 | Thiếu "more required education → lower supply" và các ví dụ | Đồng ý: 1 | p102-002 chỉ hỗ trợ ý rằng tiêu chuẩn/đào tạo khắt khe làm giảm số lao động đủ điều kiện. Đáp án thiếu quan hệ cụ thể giữa số năm học yêu cầu và nguồn cung, đồng thời không nêu các ví dụ PhD mathematicians, cardiologists, physicians trong gold. |
| 7 | t11 | agent_hrr_B_1shot | 2, citation 1/1 | $700B − $510B = $190B | Đồng ý: 2, citation 1/1 | p108-003 nêu lượng vốn người vay muốn vay $700B và lượng doanh nghiệp thẻ tín dụng sẵn sàng cung cấp $510B; phép trừ $190B chính xác và chunk còn giải thích tình trạng thiếu hụt. |
| 8 | ut1 | agent_hrr_B_1shot | từ chối đúng | Không có % cho laptop | Đồng ý: từ chối đúng | p69 chỉ nói nhu cầu laptop giảm/đường cầu dịch trái khi giá tablet giảm, không cung cấp phần trăm hay lượng giảm. Từ chối là phù hợp. |
| 9 | ut3 | agent_dense_B | từ chối đúng | UAW chỉ có số năm 1985/2015/2021 | Đồng ý: từ chối đúng | Các chunk liên quan chỉ nêu UAW có 975.000 thành viên năm 1985, khoảng 390.000 năm 2015 và 408.000 năm 2021; không có số liệu năm 1960. |
| 10 | dev q22 | agent_hrr_B | 1, citation p357-005 sai | Model tự viết tiếp chunk bị cắt | Đồng ý: 1, citation 1/2 (làm rõ: citation p357-005 không hỗ trợ câu ví dụ) | Câu đầu về động cơ không phân biệt đối xử của doanh nghiệp tìm kiếm lợi nhuận được p357-005 hỗ trợ. Nhưng chunk này bị cắt ở giữa câu; đáp án tự hoàn thành ý "bigoted firms ... gain an advantage by hiring them", nội dung đó không có trong context và còn đảo chủ thể hưởng lợi. p358-002 hỗ trợ ý về khách hàng có định kiến và việc chính sách không phân biệt đối xử có thể làm giảm lợi nhuận. Vì vậy giữ grade 1, đánh dấu citation p357-005 không hỗ trợ câu ví dụ. |
| 11 | dev ud3 | agent_hrr_B_1shot | không tính là từ chối | Gọi submit_answer để nói "sách không ghi" | Đồng ý: không tính là từ chối | Nội dung không bịa số H1B và nêu đúng rằng sách không cung cấp số visa mỗi năm; hai citation hỗ trợ các phát biểu. Tuy nhiên agent gọi submit_answer, khiến status là answered, không gọi abstain; đây là lỗi tuân thủ giao thức từ chối, không phải hallucination. |

Người duyệt: Nguyễn Gia Bảo · Ngày: 14/11/2026 · Số nhãn đã sửa: 0 (1 nhãn được làm rõ phạm vi citation)

## Kết luận duyệt

- 11/11 mục đồng ý với giá trị nhãn LLM (bao gồm các mục có ghi chú về nguyên nhân lỗi retrieval/context hoặc giao thức).
- 1/11 mục (q22, agent_hrr_B): giữ grade 1 và citation 1/2, chỉ làm rõ rằng p357-005 không hỗ trợ câu ví dụ do model tự suy diễn từ chunk bị cắt; p358-002 vẫn hỗ trợ.
- Không sửa các nhãn test còn lại. Riêng t09 giữ grade 0 vì đây là câu answerable nhưng agent đã từ chối do evidence bị loại khỏi context budget.
