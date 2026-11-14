# Thử thách nâng cao — Agentic RAG đa phương thức trên toàn bộ một cuốn sách 595 trang

**Học viên:** Nguyễn Gia Bảo · 2A202603647 · K5-L3A · 14/11/2026

> Mọi con số đều lấy từ file trong `advanced/`, có ghi đường dẫn. Lệnh tái lập ở cuối file.

## Kết quả chính

| | |
|---|---|
| **Test (30 câu, chạy 1 lần, cấu hình `adv_hrr_view`)** | **30/30 = 100%** (ngưỡng 27/30) · từ chối đúng 6/6 · lỗi hệ thống 0 |
| Theo nhóm (test) | bảng 6/6 · sơ đồ 5/5 · biểu đồ 5/5 · multi-hop 4/4 · text 4/4 · thiếu evidence 6/6 |
| Dev (18 câu), 3 cấu hình agent | `adv_dense` 17/18 · `adv_hrr` 17/18 · `adv_hrr_view` **18/18** |
| Chi phí | **Thực trả theo Anthropic Console: $0.11 cho toàn bộ Day 7** (phần cơ bản và nâng cao, API key `Day7`, dữ liệu đến 14/11 9:42 UTC). Ước tính theo token × giá niêm yết cho riêng phần nâng cao: ≈ $0.21 (vision $0.101, dev $0.064, test $0.046, chạy thử $0.002), xem §9 |
| Thời gian test | trung vị 26,1 s/câu, tối đa 43,3 s (4 luồng song song, rerank trên CPU) |
| Nhãn test | LLM chấm nháp từ trace và crop trang gốc; học viên đối chiếu cả 30 câu với crop trang gốc, đồng ý 30/30, sửa 0 nhãn (không mù, xem §7) |

Kết quả test và nhãn: [results/agent/test/adv_hrr_view.jsonl](results/agent/test/adv_hrr_view.jsonl) (trace đầy đủ). Mỗi câu ghi các lần search (query, `content_type`, top-k với id, loại, trang, score, ms, `context_ids`, số ký tự context), các lần `view_region` (unit, trang, bbox), câu trả lời, citation kèm trang/bbox, token, chi phí, thời gian và lỗi. Văn bản context mà model đọc được tái tạo chính xác từ `context_ids` và file [data/index/units.jsonl](data/index/units.jsonl) đã commit, qua hàm `format_unit` trong [agent.py](agent.py).
Các file khác: [results/agent/test/adv_hrr_view_score.json](results/agent/test/adv_hrr_view_score.json) (nhãn cuối cùng và lý do), [results/review/test_adv_hrr_view.md](results/review/test_adv_hrr_view.md) (phiếu duyệt có ảnh gốc), [results/review/test_adv_hrr_view_labels.csv](results/review/test_adv_hrr_view_labels.csv) (nhãn của học viên).

## 1. Tài liệu

- **Nguồn:** OpenStax, *Principles of Microeconomics 3e*, bản PDF web, ©2026 Rice University, giấy phép **CC BY-NC-SA 4.0** (trang 4 của PDF). Tải miễn phí tại https://openstax.org/details/books/principles-microeconomics-3e. Đây là cùng file đã dùng ở Day 6 (`<Day6>/starter/data/raw/principles-microeconomics-3e_-_WEB.pdf`). PDF **không** được commit vào repo này; đường dẫn đặt bằng biến `ADV_PDF`.
- **Quy mô:** 595 trang. Có 160 hình có chú thích, 38 ảnh không chú thích (icon và ảnh minh họa trong khung) và 167 khối bảng.
- **Phạm vi index:** trang PDF 21–576, gồm cả 20 chương, phụ lục A–C và đáp án. Số trang in = số trang PDF − 12.
- **Không index:**
  - Trang 1–20: bìa, bản quyền, mục lục, lời nói đầu. Không có nội dung môn học.
  - Trang 577–595: tài liệu tham khảo và chỉ mục chữ cái. Chỉ có thông tin thư mục và điều hướng.
  - 12 trang trắng cuối chương (58, 198, 226, …). Danh sách đầy đủ ở [data/ingest_report.json](data/ingest_report.json).
  - **Ảnh hưởng:** câu hỏi kiểu "sách trích nguồn nào cho số liệu X" sẽ không trả lời được. Benchmark không có câu nào như vậy.

## 2. Pipeline và index

| Bước | File | Cách làm |
|---|---|---|
| Phân tích trang | [ingest.py](ingest.py) | PyMuPDF đọc text block theo tọa độ. Bỏ header/footer; header chạy cho biết chương và mục. Mỗi đơn vị (unit) giữ trang gốc và **bbox** (điểm PDF), đủ để cắt lại đúng vùng. |
| Bảng | [ingest.py](ingest.py) | Dò chú thích `TABLE x.y`, rồi gom vùng các block nằm sát ngay phía trên (cho phép các cột chồng nhau theo chiều dọc). Mỗi block là một hàng, mỗi dòng là một ô (nối bằng ` \| `). Thử `find_tables()` của PyMuPDF trước nhưng nó đọc sai `$1.00` thành `$100<br>.` và làm mất hàng tiêu đề, nên không dùng. |
| Hình | [ingest.py](ingest.py), [describe_figures.py](describe_figures.py) | Mỗi ảnh raster được ghép với chú thích `FIGURE x.y` gần nhất. Vùng hình được render 150 dpi rồi gửi `claude-haiku-5-5` (vision) mô tả: loại hình, toàn bộ chữ, trục, đơn vị, chú giải, nhãn số, và chuỗi dữ liệu (giá trị ước lượng có dấu `~`). Kết quả: 198 mô tả, 172k token vào, 167k token ra, **$0.101**. Mô tả được lưu riêng ([data/figure_descriptions.jsonl](data/figure_descriptions.jsonl)) và gắn nhãn "AI-generated … verify against the original" trong index. |
| Text | [ingest.py](ingest.py) | Gom block còn lại thành đoạn khoảng 1.100 ký tự, không vượt qua ranh giới trang, nên mỗi citation chỉ thuộc một trang. |
| Index | [index.py](index.py) | **2.194 unit:** 1.829 text (trung vị 841 ký tự), 167 bảng (269), 198 hình (1.715). Embedding bằng `intfloat/multilingual-e5-base` (model của Day 6), prefix `passage:`/`query:`, cosine chính xác trên ma trận NumPy. Cùng một index dùng cho cả BM25. SHA256 của file unit ghi trong [data/index/manifest.json](data/index/manifest.json). |

**Kiểm tra nội dung trích so với bản gốc.** Text OCR hay mô tả do model sinh ra không tự bảo đảm đúng, nên tôi kiểm tra thủ công như sau:

- **Bảng:** con số lấy từ lớp text số của PDF (không qua OCR). Đáp án chuẩn của câu bảng được soạn từ lớp text này. Sau khi chạy test, tôi đối chiếu lại **9 bảng dùng trong test** (14.6, 15.1, 16.2, 17.2, 20.2, 13.3, 19.1, 19.4, 14.8) trên ảnh trang gốc: tất cả khớp. Các bảng dev chưa được đối chiếu bằng ảnh, trừ Bảng 3.2 (bản gốc chỉ có 5 hàng, đúng như bản trích). Trường `gold_source` trong benchmark ghi rằng mọi đáp án đều đọc từ ảnh; câu đó nói quá và đã được đính chính trong `gold_source_correction`. Lỗi trích còn lại nằm ở **tiêu đề nhiều dòng** (Bảng 16.2, 9.2): thứ tự cột bị đảo trong text, nên agent có `view_region` để đọc ảnh bảng. Hai bảng không gom được hàng (5.4 dạng công thức, 8.5 vắt qua 2 trang) được ghi trong `ingest_report.json`; nội dung của chúng vẫn nằm trong unit text.
- **Mô tả hình:** tôi so với ảnh gốc 7 hình: 4 biểu đồ trong benchmark (15.2, 14.11, 14.15, 17.7) và 3 sơ đồ chọn ngẫu nhiên với seed 7 (3.4, 19.5, 2.4). Mọi nhãn số in trên hình đều đúng. Giá trị ước lượng từ trục (`~`) lệch trong khoảng ±2% thang đo (ví dụ Hình 17.7: 2007 ≈ $313k). Hai sai sót nhỏ:
  - Hình 19.5: model tự sửa lỗi in của sách (vạch trục ghi "50" thay vì "5").
  - Hình 2.4: vị trí điểm B so với đường H₂ được mô tả hơi lệch.
- **Mâu thuẫn ngay trong sách** (phát hiện khi chấm, đã kiểm tra trên trang gốc):
  - Hình 15.5: chú thích ghi CTC 2016 "over $25 billion", nhưng đường vẽ ở khoảng $51 tỷ.
  - Hình 17.7: chú thích nói về giá *trung vị* 1990–2015 ($248k năm 2007), nhưng đường vẽ là giá *trung bình* đến 2021 (khoảng $313k năm 2007).
  - Text trang 273 nói Hình 11.2(b) là năm 2015, nhưng nhãn hình ghi 2012.
  - Benchmark tránh hỏi phần mâu thuẫn trên test. Riêng d08 trên dev được nới gold, xem §4.

## 3. Phương pháp retrieval (cùng index, query = câu hỏi gốc, không filter, top-10)

| | dev (15 câu có đáp án) | | | | test (24 câu có đáp án) | | | |
|---|---|---|---|---|---|---|---|---|
| Phương pháp | Hit@1 | Hit@3 | Full@5 | MRR@10 | Hit@1 | Hit@3 | Full@5 | MRR@10 |
| dense (e5) | 8 | 12 | 13 | 0.717 | 20 | 22 | 22 | 0.881 |
| BM25 | 9 | 11 | 11 | 0.703 | 17 | **23** | 21 | 0.833 |
| hybrid RRF (k=60, 50+50) | 8 | 12 | 13 | 0.702 | 19 | 22 | 21 | 0.865 |
| **hybrid + rerank** (MiniLM-L6, top-30) | **11** | **15** | 13 | **0.856** | **22** | 22 | **22** | **0.917** |

Nguồn: [results/retrieval/dev/metrics.csv](results/retrieval/dev/metrics.csv), [results/retrieval/test/metrics.csv](results/retrieval/test/metrics.csv). Độ trễ trung vị: dense 88 ms, BM25 10 ms, rerank 4,2 s (cross-encoder chạy CPU trên các unit hình dài).

- Trên dev, các câu dense bỏ sót ở top-3 đều là multi-hop (d10, d11, d12): query gộp hai ý và trả về đoạn text giải thích thay vì bảng. Rerank đưa bảng lên top-3 ở cả 3 câu.
- Trên test, rerank chỉ trượt top-3 ở hai câu:
  - **t17:** multi-hop, Bảng 19.1 và 19.4. Các đoạn text giải thích cùng trang xếp trên.
  - **t24:** danh sách gold của tôi thiếu. Unit hạng 1 (`p0212-t0`) nêu đúng quy tắc shutdown nhưng không có trong danh sách. Tôi **không sửa gold test sau khi chạy**, nên con số retrieval ở câu này thấp hơn thực tế.
- Ở cấp agent, cả hai câu đều đạt: agent search tách từng ý (t17), và trích được unit tương đương (t24).

## 4. Benchmark

[benchmark/questions.json](benchmark/questions.json), khóa ở commit `c200359` trước mọi lần chạy benchmark. Mỗi câu có: ID, nhóm chính, câu hỏi, đáp án mong đợi, các thành phần bắt buộc, dung sai (với biểu đồ không có nhãn số), các nhóm evidence (unit + trang + vị trí: hàng/cột bảng hoặc phần hình), và lý do. Với câu thiếu evidence còn ghi cách kiểm tra sự vắng mặt (đối chiếu trang gốc và regex trên toàn bộ unit lẫn mô tả hình).

| Nhóm | Bảng | Ảnh/sơ đồ | Biểu đồ | Multi-hop | Text | Thiếu evidence | Tổng |
|---|---|---|---|---|---|---|---|
| Test (yêu cầu tối thiểu) | 6 (6) | 5 (5) | 5 (5) | 4 (4) | 4 (4) | 6 (6) | **30** |
| Dev (yêu cầu ≥15 + 3) | 3 | 3 | 3 | 3 | 3 | 3 | **18** |

- **Chia dev/test theo hình và bảng:** không hình hay bảng nào xuất hiện ở cả hai tập. Lúc đầu Hình 15.2 bị dùng ở cả hai; script kiểm tra phát hiện và tôi đã thay câu dev **trước khi khóa**.
- **Gold:** đáp án hình và biểu đồ đọc từ ảnh crop; đáp án bảng đọc từ lớp text PDF, và với test đã đối chiếu lại trên ảnh (xem §2). Không đáp án nào lấy từ mô tả AI.
- **Câu hỏi về hình:** ảnh và sơ đồ đều là hình mang thông tin (sơ đồ dòng chảy, đồ thị cung cầu có số, chu trình bầu chọn). Không dùng ảnh trang trí. Một số câu cố ý cần chi tiết **chỉ có trong hình**, chẳng hạn t08 ($1,500 ở 40 pound), t09 ("profits or losses"), t07 (chiều mũi tên B, C).
- **Câu thiếu evidence:** sát chủ đề nhưng nằm ngoài phạm vi dữ liệu. Có loại năm ngoài trục (2016, 2021, 2022) và loại đối tượng không có trong bảng (Japan, CWA). Đây là kiểu khó nhất với RAG vì agent thấy dữ liệu "gần đúng" và dễ thay thế bằng nó.
- **Thay đổi sau khi khóa (chỉ dev):** đáp án d08 được nới để chấp nhận cả số trên đường vẽ (CTC ≈ $51B) lẫn số in trong chú thích ("over $25 billion"). Lý do là sách tự mâu thuẫn; thay đổi được ghi trong trường `change_log`. Gold test không đổi.

## 5. Agent

[agent.py](agent.py): vòng lặp tool thủ công với `claude-haiku-5-5`, effort `medium`, schema strict.

- `search_document(query, content_type)`: model tự chọn `any`, `text`, `table` hoặc `figure`. Mỗi lượt trả top-6, gói tối đa 7.000 ký tự; một unit dài không chiếm quá 60% budget. Kết quả ghi rõ loại unit, nhãn (Table/Figure x.y), trang PDF, trang in, chương và mục.
- `view_region(unit_id)` (chỉ ở cấu hình `adv_hrr_view`): render **vùng gốc trên trang PDF** của một unit đã được search trả về, rồi gửi cho model dưới dạng ảnh. Đây là cách agent kiểm chứng mô tả AI và bảng có tiêu đề rối. Prompt yêu cầu xem ảnh trước khi dùng bất kỳ con số nào từ bảng hay hình.
- `submit_answer(answer, citations)`: mỗi câu kết thúc bằng `[unit-id]`, và citation phải là id search đã trả về. Trace lưu thêm `citation_details` (trang PDF, trang in, loại, nhãn, bbox), nên mỗi citation chỉ được tới **trang và vùng** evidence.
- `abstain(reason)`.
- **Giới hạn:** 5 search, 4 view, 12 lượt gọi model. Citation sai được cho sửa một lần; lần sai thứ hai tính là abstain. Lỗi model hoặc retriever được ghi vào trace, không bị che.
- **Gold không bao giờ vào pipeline:** `agent.py` không đọc benchmark. `run.py` chỉ truyền câu hỏi.

## 6. Thử nghiệm trên dev và chọn cấu hình

Quy tắc chọn được commit **trước** khi có kết quả dev (commit `36f5d53`, [benchmark/SELECTION_RULE.md](benchmark/SELECTION_RULE.md)): chọn pass rate dev cao nhất; nếu bằng nhau, chọn cấu hình ít lỗi ở câu thiếu evidence hơn; nếu vẫn bằng, chọn chi phí thấp hơn.

| Cấu hình | Retrieval | view | Dev | Chi phí/câu | Trung vị s/câu |
|---|---|---|---|---|---|
| `adv_dense` | dense | không | 17/18 | $0.00099 | 6,1 |
| `adv_hrr` | hybrid + rerank | không | 17/18 | $0.00091 | 20,9 |
| **`adv_hrr_view`** | hybrid + rerank | **có** | **18/18** | $0.00167 | 23,9 |

- **Lỗi dev duy nhất (d07, biểu đồ giá nhà):** biểu đồ không có nhãn số và chú thích mâu thuẫn với đường vẽ.
  - Hai cấu hình không có `view_region` đều **từ chối**: model chỉ có mô tả AI (≈ $460k năm 2021) và chú thích ($248k, giá trung vị). Nó không tin mô tả, nên không dám trả lời.
  - `adv_hrr_view` mở ảnh gốc, đọc được ≈ $460k năm 2021 và đỉnh năm 2007 ≈ $310–315k, đồng thời nêu rõ mâu thuẫn với chú thích.
  - Đây đúng là giả thuyết khi thêm tool: **mô tả AI đủ để tìm (retrieval), nhưng không đủ để trả lời con số; cần đọc lại bản gốc.**
- **Lựa chọn:** `adv_hrr_view`, theo quy tắc 1 ([results/selection.json](results/selection.json)). `run.py` từ chối chạy test với cấu hình khác.
- Nhãn dev: [results/labels/](results/labels/), có lý do cho từng câu. Nhãn dev do LLM chấm, học viên chưa duyệt.

## 7. Kết quả test (chạy một lần, commit `3690d62`)

| Nhóm | Đạt | Ghi chú |
|---|---|---|
| Bảng | 6/6 | gồm xếp hạng theo giá trị (t01), chọn đúng cột nữ/nam (t03), các phép trừ (t02, t03, t05) |
| Ảnh, sơ đồ | 5/5 | các chi tiết chỉ có trong hình: chiều mũi tên (t07), điểm $1,500 (t08), "profits or losses" (t09) |
| Biểu đồ | 5/5 | 2 biểu đồ có nhãn số và 3 biểu đồ đọc theo trục, đều trong dung sai |
| Multi-hop | 4/4 | 2 bảng (t17), biểu đồ + bảng (t18), bảng + đoạn text (t19, t20) |
| Text | 4/4 | |
| Thiếu evidence | 6/6 | từ chối, không đưa số cho năm hoặc đối tượng ngoài phạm vi |
| **Tổng** | **30/30 (100%)** | lỗi hệ thống 0, trung vị 26,1 s/câu, $0.0456 |

Nguồn: [results/agent/test/adv_hrr_view_score.json](results/agent/test/adv_hrr_view_score.json).

- Agent trả lời 24/24 câu có đáp án và từ chối 6/6 câu thiếu evidence.
- Có 44 lượt search và 23 lượt `view_region`; agent mở ảnh gốc ở mọi câu bảng, sơ đồ và biểu đồ.
- 0 lỗi hệ thống, $0.0456 cho 30 câu.
- **Nhãn:** Claude Code chấm nháp bằng cách đọc từng trace và mở từng unit được trích cùng vùng gold trên trang gốc. Phiếu duyệt có ảnh crop: [results/review/test_adv_hrr_view.md](results/review/test_adv_hrr_view.md).
- **Học viên duyệt** ([results/review/STUDENT_REVIEW.md](results/review/STUDENT_REVIEW.md)):
  - Học viên đối chiếu cả 30 câu với crop trang gốc và điền `student_label` cho đủ 30 dòng. Kết quả: 30 pass, 0 fail, không sửa nhãn nháp nào.
  - Ghi chú ở t14: cột thập niên 1930 khoảng 0,7 triệu, agent nói khoảng 1 triệu, nhưng câu hỏi chỉ hỏi thập niên nào.
  - Thẻ thừa ở t17, t20, t21 được coi là lỗi định dạng.
  - **Giới hạn:** lần duyệt này **không mù**, vì phiếu hiển thị nhãn và lý do nháp cạnh mỗi câu, nên mức đồng thuận có thể bị nâng lên do thiên lệch tự động hóa. Phần đóng góp của nó là việc người đọc kiểm tra từng câu trên ảnh gốc.
  - Điểm cuối tính bằng `python -m advanced.review score`; nhãn học viên ghi đè nhãn nháp.

## 8. Phân tích lỗi và điểm yếu (kể cả các câu vẫn đạt)

1. **Mô tả AI không đáng tin với con số đọc từ trục** (d07, dev). Đã xử lý bằng `view_region`. Không có tool này, agent chọn từ chối thay vì bịa số; đó là hướng an toàn.
2. **Lỗi định dạng:** model chèn thẻ thừa `</answer><parameter name="citations">…` vào cuối chuỗi trả lời. Gặp ở 3/30 câu test (t17, t20, t21); trên dev là 2/18 với `adv_dense`, 0/18 với `adv_hrr` và 1/18 với `adv_hrr_view`. Lỗi này không thêm khẳng định nào, nên vẫn chấm đạt, nhưng người dùng sẽ thấy rác. Tôi không sửa sau khi chọn cấu hình, để giữ test "đúng cấu hình đã khóa". Cách sửa đơn giản: cắt chuỗi từ `</answer>` trở đi.
3. **Ước lượng thô ở phần không được hỏi** (t14): agent nói thập niên 1930 có "roughly 1 million", trong khi cột thực tế khoảng 0,7 triệu. Câu hỏi chỉ hỏi *thập niên nào* nên vẫn đạt, nhưng đây là dấu hiệu model làm tròn lỏng khi không có nhãn số.
4. **Retrieval multi-hop bằng một query** (t17, d10–d12 với dense): đoạn text giải thích lấn át bảng. Agent bù lại bằng search lần hai với `content_type="table"`.
5. **Gold evidence chưa đầy đủ** (t19, t24): agent trích đoạn văn tương đương (`p0370-t1` cho 11,4%; `p0212-t0` cho quy tắc shutdown), không phải unit tôi ghi. Người chấm đã đọc các đoạn này: chúng nêu đúng thông tin. Tôi ghi chú trong nhãn, không sửa gold.

## 9. Chi phí

**Số thực trả:** Anthropic Console báo **$0.11** cho toàn bộ Day 7, gồm cả phần cơ bản và phần nâng cao. Số liệu lọc theo API key `Day7`, toàn bộ là Claude Haiku 5.5, dữ liệu cập nhật đến 14/11/2026 9:42 UTC. Kết quả test được commit lúc 16:38 giờ Việt Nam (9:38 UTC), nên mọi lượt gọi API của phần nâng cao đều diễn ra trước mốc này.

Bảng dưới là **ước tính**: số token ghi trong trace nhân với giá niêm yết ($0.10 / $0.50 cho 1 triệu token vào / ra). Ước tính này tái lập được từ trace và dùng để so sánh giữa các cấu hình. Cộng cả Day 7, ước tính là khoảng $0.44, tức cao hơn số thực trả khoảng 4 lần. Tôi chưa xác định được nguyên nhân chênh lệch, nên không dùng ước tính này làm số tiền thực tế.

| Hạng mục | Lượt | Ước tính |
|---|---|---|
| Mô tả 198 hình (vision) | 198 | $0.1006 |
| Agent dev (3 cấu hình × 18 câu) | 54 | $0.0643 |
| Agent test (1 cấu hình × 30 câu) | 30 | $0.0456 |
| Chạy thử (1 hình, 1 câu agent) | 2 | $0.0022 |
| **Tổng** | 284 lượt chạy | **≈ $0.21** |

Embedding, BM25 và rerank chạy local trên CPU: dựng index mất 738 s, chi phí 0.

## 10. Giới hạn

- **Mẫu nhỏ và chạy một lần:** test 30 câu, 1 câu tương đương 3,3 điểm %. Haiku 5.5 không cho đặt temperature, và cấu hình được chọn chưa được chạy lặp lại để đo dao động.
- **Người viết benchmark cũng là người dựng hệ thống:** Claude Code soạn câu hỏi sau khi đã xem danh sách hình và bảng, nên cách diễn đạt có thể vô tình thuận lợi cho retrieval. Câu thiếu evidence chủ yếu thuộc dạng "ngoài phạm vi năm hoặc đối tượng"; chưa có dạng "câu hỏi có tiền đề sai".
- **Nhãn:** LLM chấm nháp, học viên duyệt tập test (xem §7). Nhãn dev chưa được người duyệt.
- **Thời gian đo** gồm cả tranh chấp giữa 4 luồng chạy song song và khóa dùng chung cho model rerank, nên cao hơn khi chạy tuần tự (dense, 1 luồng: khoảng 6 s/câu).
- **Không commit:** PDF gốc, ảnh crop và `embeddings.npy`. Tất cả tạo lại được bằng các lệnh dưới (mô tả hình được cache, nên không cần gọi API lại).

## 11. Tái lập

```bash
# .env: ANTHROPIC_API_KEY=...   ;  ADV_PDF=<đường dẫn PDF> nếu repo Day 6 không nằm cạnh repo này
python -m advanced.ingest                      # units.jsonl + ingest_report.json
python -m advanced.describe_figures            # crop hình; chỉ gọi vision cho hình chưa có trong cache (hiện đã đủ 198)
python -m advanced.index                       # embeddings + manifest (khoảng 12 phút trên CPU)
python -m advanced.run retrieval --split dev   # results/retrieval/dev
python -m advanced.run agent --split dev       # 3 cấu hình -> results/agent/dev
python -m advanced.review score --split dev --config adv_hrr_view
python -m advanced.run agent --split test --configs adv_hrr_view    # cần results/selection.json
python -m advanced.run retrieval --split test
python -m advanced.review sheet --split test --config adv_hrr_view  # phiếu duyệt có ảnh gốc
python -m advanced.review score --split test --config adv_hrr_view  # điểm cuối (nhãn học viên ghi đè nhãn nháp)
```

Lịch sử commit thể hiện thứ tự các bước: `c200359` (index và benchmark khóa) → `36f5d53` (quy tắc chọn) → `bd6f3de` (dev và lựa chọn) → `3690d62` (test một lần, nhãn nháp) → commit nhãn của học viên.
