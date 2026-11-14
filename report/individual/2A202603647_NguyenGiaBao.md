# Báo cáo Day 7 — Agentic RAG

**Học viên:** Nguyễn Gia Bảo · **MSSV:** 2A202603647 · **Lớp:** K5-L3A · **Ngày:** 14/11/2026

> Mọi con số dưới đây được lấy từ file trong repo, có ghi đường dẫn. Lệnh tái lập nằm ở [README.md](../../README.md#bài-làm--nguyễn-gia-bảo--2a202603647--k5-l3a).

## Tóm tắt

- **Hệ thống:** agent `claude-haiku-5-5` gọi tool `search_textbook` trên index Day 6 (e5-base, pgvector). Agent trả lời có citation `[chunk-id]` hoặc gọi `abstain`.
- **Phương pháp retrieval:** 4 phương pháp (dense, BM25, hybrid RRF, hybrid + cross-encoder rerank) trên 2 index (B, B500), tổng cộng 7 cấu hình.
- **Quy trình:**
  - Benchmark 43 câu, định nghĩa metric, cấu hình retrieval và *câu chữ* của quy tắc chọn được khóa trước mọi lần chạy (commit `a6ab742`).
  - Các cấu hình agent, bản v2 và script `select_config.py` được viết trong lúc làm dev và commit cùng kết quả dev (`ab54365`), **trước** khi chạy test.
  - Test được chạy **một lần** (`9fbe014`). Sau đó tạo **test2 mới**, khóa riêng, để kiểm chứng các thay đổi làm sau khi đã xem test.
- **Retrieval:** trên dev, `hybrid_rerank_B` đạt Evidence Hit@3 **22/24** so với baseline dense **15/24**. Trên test kết quả đảo chiều: dense 11/11, rerank 10/11. Với N=11, chênh 1 câu tương đương 9 điểm %.
- **Agent:** trên test, cả baseline và cấu hình chọn đều đạt grounded **1.82/2**, từ chối đúng **4/4**, citation hợp lệ **15/15**. Mỗi cấu hình có 1 câu từ chối nhầm (t09).
- **Phát hiện chính:** câu t09 (multi-hop, FLSA cộng nguyên nhân công đoàn suy giảm) bị cả 3 agent từ chối nhầm, nhưng **nguyên nhân khác nhau theo cấu hình**:
  - Ở `agent_dense_B` và `agent_hrr_B_1shot_v2`, retriever **có tìm thấy** chunk FLSA (hạng 5) nhưng **budget context 4000 ký tự loại nó đi** trước khi model đọc. Đây là lỗi ở bước chọn context.
  - Ở **cấu hình được chọn** `agent_hrr_B_1shot`, một query gộp cả hai ý nên chunk FLSA **không vào top-5**. Đây là lỗi retrieval multi-hop của agent chỉ search một lượt.
  - Chẩn đoán hậu kiểm: với budget 8000 ký tự, Context Evidence của `hybrid_rerank_B` trên test tăng từ 9/11 lên 11/11. Cách sửa này được kiểm chứng trên **test2** mới (xem phần dưới).
- **Sau test** (mục riêng ở dưới):
  - Tách bản v2 thành 2 ablation: mỗi thay đổi riêng lẻ đều sửa được q22.
  - Chạy lại cấu hình chọn 3 lần: lỗi ud3 lặp lại ở cả 3/3 lần chạy.
  - Tạo **test2 mới** (10 câu có đáp án, 4 câu thiếu evidence), khóa trước khi chạy. Trên test2, retrieval chọn đạt Hit@1 **9/10** so với dense 5/10; cả 4 agent đạt **2.00/2** và từ chối đúng 4/4.
- **Chi phí:**
  - **Thực trả (Anthropic Console):** **$0.11** cho toàn bộ Day 7, gồm cả phần nâng cao. Số liệu lọc theo API key `Day7`, model Claude Haiku 5.5, dữ liệu cập nhật đến 14/11/2026 9:42 UTC.
  - **Ước tính từ trace:** số token ghi trong trace nhân với giá niêm yết ($0.10 / $0.50 cho 1 triệu token vào / ra). Phần cơ bản: 381 lượt chạy agent, khoảng $0.23. Cả Day 7: 663 lượt, 2,68 triệu token vào và 0,34 triệu token ra, khoảng $0.44.
  - Ước tính cao hơn số thực trả khoảng 4 lần và tôi chưa giải thích được chênh lệch này. Các con số chi phí khác trong báo cáo là ước tính dùng để **so sánh giữa các cấu hình**, không phải hóa đơn.
  - Truy xuất 0 USD (chạy local).
- **Thử thách nâng cao:** index toàn bộ cuốn sách 595 trang (text, bảng, hình qua vision), agent có tool xem vùng gốc trên PDF. Kết quả test (30 câu, chạy một lần) **30/30**. Chi tiết ở [mục cuối](#thử-thách-nâng-cao) và [advanced/REPORT.md](../../advanced/REPORT.md).

## Dữ liệu và benchmark

- **Nguồn, quyền sử dụng, số trang và số chunk:**
  - Corpus giống Day 6: OpenStax *Principles of Microeconomics 3e* (Rice University), CC BY-NC-SA 4.0. Chỉ dùng phi thương mại và có ghi nguồn.
  - Gồm Ch3, Ch4, Ch14, tổng **78 trang nội dung**; `page` là trang PDF vật lý.
  - Index **B** (theo đoạn, ≤1000 ký tự) có **326 chunk**, index **B500** (theo đoạn, ≤500 ký tự) có **628 chunk**. Cả hai được ingest ở Day 6; Day 7 chỉ đọc, không ghi vào index.
  - Chunk được export kèm `index_version_sha256` ([data/day6_export/manifest.json](../../data/day6_export/manifest.json)), nhờ đó BM25 và dense chạy trên **cùng một phiên bản index**.
- **Vector store, embedding model, phiên bản và số chiều:**
  - PostgreSQL 16.16 + pgvector 0.8.7 (Docker), metric cosine `<=>`, **exact search**.
  - Embedding `intfloat/multilingual-e5-base`, **768 chiều**, tiền tố `query: ` / `passage: `, vector chuẩn hóa L2, sentence-transformers 6.3.0, chạy trên CPU.
  - Code kiểm tra số chiều của bảng và tên `embedding_model` của từng dòng trước khi truy vấn ([src/store.py](../../src/store.py)).
  - **Kiểm chứng kết nối:** `dense_B` (Day 7) cho top-3 **giống hệt** cấu hình C của Day 6 trên **22/22** câu Day 6.
- **Agent model, cách chạy và phân chia dev/test:**
  - Model `claude-haiku-5-5` qua Anthropic SDK 2.8.0, dùng adaptive thinking mặc định, effort `medium`.
  - Không đặt temperature: model này không cho phép, gửi giá trị khác mặc định sẽ bị lỗi 400. Vì vậy kết quả không tất định (xem phần Giới hạn).
  - **Dev:** 22 câu Day 6, cộng 2 câu multi-hop mới, cộng 4 câu thiếu evidence, tổng 28 câu. Test Day 6 được đưa vào dev vì đã từng được phân tích hậu kiểm, nên không còn là holdout độc lập.
  - **Test:** 11 câu có đáp án và 4 câu thiếu evidence, **viết mới hoàn toàn**. Script kiểm tra dev và test không chung câu evidence nào ([benchmark/README.md](../../benchmark/README.md)).
- **Cách xác định câu có/thiếu evidence và tiêu chí chấm:**
  - **Câu có đáp án:** evidence là câu nguyên văn được máy kiểm tra trên đúng trang. Câu multi-hop dùng `evidence_groups` (mọi nhóm đều bắt buộc). Các evidence thay thế (t04, t08, t11) được tìm bằng cách quét con số đặc trưng của đáp án trên toàn corpus **trước khi chạy**.
  - **Câu thiếu evidence:** gần chủ đề, ví dụ ut3 hỏi UAW năm 1960 trong khi sách chỉ có số liệu 1985/2015/2021. Script quét keyword trên cả 78 trang, sau đó đọc tay.
  - Một câu ut4 bản nháp đã bị **loại khi soát tay**, vì p107 có câu "A typical credit card interest rate ranges from 12% to 18%".
  - **Chấm điểm:** grounded 0/1/2, citation phải có trong context **và** hỗ trợ đúng câu được gắn, abstention đúng. Từ chối một câu có đáp án chấm 0.

## Retrieval và thử nghiệm

Cùng corpus, cùng phiên bản index, cùng câu hỏi và nhãn. Query là **câu hỏi gốc**, không viết lại. Filter `chapter` là input người dùng cung cấp ở 7 câu (q05, q09, q13, q18, q19, t07, t08) và được áp dụng cho mọi phương pháp. Budget context 4000 ký tự, đóng gói theo rank, không cắt ngang chunk. Thời gian đo trên CPU laptop, mỗi cấu hình một lần, không tính thời gian nạp model. Nguồn: [results/retrieval/dev/metrics.csv](../../results/retrieval/dev/metrics.csv), [results/retrieval/test/metrics.csv](../../results/retrieval/test/metrics.csv).

| Cấu hình | Phương pháp, top-k, filter, rerank, context budget | Giả thuyết / thay đổi | Split | Hit@1 | Evidence Hit@3 | Context Evidence Rate | Thời gian / chi phí |
|---|---|---|---|---|---|---|---|
| Baseline `dense_B` | Dense e5 trên B, top-10, filter chapter, 4000 ký tự | = cấu hình C của Day 6 | dev | 13/24 (54%) | 15/24 (63%) | 19/24 | 97 ms trung vị / 0 USD |
| Phương pháp 2 `bm25_B` | BM25 (k1=1.5, b=0.75; stopword + stem nhẹ) trên cùng chunk B | Khớp từ khóa tốt hơn với thuật ngữ đặc thù | dev | 12/24 | 17/24 (71%) | 17/24 | 0.8 ms / 0 USD |
| Phương pháp 3 `hybrid_B` | RRF (k=60) của dense top-50 và BM25 top-50 | Kết hợp recall diễn đạt lại với độ chính xác từ khóa | dev | 12/24 | 20/24 (83%) | 21/24 | 127 ms / 0 USD |
| Cải thiện 1 `hybrid_rerank_B` | Hybrid → cross-encoder `ms-marco-MiniLM-L6-v2` xếp lại top-20 | Sửa lỗi "đúng trang, sai chunk" | dev | **16/24** | **22/24 (92%)** | **22/24** | 871 ms / 0 USD |
| Cải thiện 2 `dense_B500` | Dense trên index B500 (chunk ≤500 ký tự) | Chunk ngắn giảm pha loãng ngữ nghĩa (giả thuyết từ Day 6) | dev | 15/24 | 19/24 | 23/24 | 89 ms / 0 USD |
| (thêm) `hybrid_B500` | Hybrid trên B500 | Kết hợp cải thiện 2 với hybrid | dev | 14/24 | 18/24 | 20/24 | 91 ms / 0 USD |
| (thêm) `hybrid_rerank_B500` | Cải thiện 1 + 2 | Kết hợp | dev | 16/24 | 19/24 | 19/24 | 432 ms / 0 USD |
| **Cấu hình đã chọn** `hybrid_rerank_B` | như trên | Chốt trên dev | test | 8/11 | 10/11 (91%) | 9/11 | 889 ms / 0 USD |
| Baseline `dense_B` | như trên | | test | 7/11 | **11/11** (100%) | 10/11 | 103 ms / 0 USD |

- **Phương pháp mới đồng thời là cải thiện:** hybrid (phương pháp 3) và rerank (cải thiện 1) mỗi cái là một pipeline riêng, có giả thuyết và được đo riêng. B500 là cải thiện về index cho cùng phương pháp dense.
- **Full Evidence@3** (đủ mọi nhóm, khác Hit@3 ở câu multi-hop) và **MRR@10** được ghi trong `metrics.csv`. Ví dụ MRR@10 trên dev: dense 0.641, rerank 0.792.

**Lựa chọn giai đoạn 1** (script [src/select_config.py](../../src/select_config.py), quy tắc chốt trong commit `a6ab742`): Hit@3 cao nhất, chênh ≤1 câu coi là hòa. `hybrid_rerank_B` đạt 22 và đứng một mình (cấu hình kế tiếp đạt 20), nên được chọn.

**Hai lỗi ở tầng retrieval trên dev** (ma trận theo từng câu trong `results/retrieval/dev/*.jsonl`):
1. **"Đúng trang, sai chunk" ở dense** (q01, q04, q12, q14: hit đầu tiên ở hạng 4).
   - *Nguyên nhân:* chunk B dài 700–950 ký tự, câu evidence chỉ chiếm một phần nhỏ trong vector. Day 6 đã gọi hiện tượng này là pha loãng ngữ nghĩa.
   - *Thử:* cross-encoder đọc đồng thời câu hỏi và chunk. *Kết quả:* hạng 4 → 1 / 3 / 1 / 2. Hit@3 dev tăng từ 15 (dense) lên 20 (hybrid) rồi 22 (rerank).
   - *Đánh đổi:* thời gian trung vị tăng khoảng 9 lần (97 → 871 ms trên CPU).
2. **q03, câu hỏi điều kiện mà dense trượt hẳn** ("How should we analyze demand when price and income change at the same time?").
   - BM25 xếp đúng ở hạng 1 nhờ khớp các từ "change... same time... income". Hybrid xếp ở hạng 2, rerank ở hạng 1.
   - Đây là lý do phải kết hợp hai phương pháp thay vì thay hẳn dense.

**Kết quả không cải thiện (báo cáo đầy đủ):**
- **B500 không cộng dồn với hybrid hay rerank.** B500 giúp dense (Hit@3 15 → 19), nhưng làm hybrid giảm từ 20 xuống 18 và rerank giảm từ 22 xuống 19.
  - Ví dụ q20: ở B500, phần đặt vấn đề (luật usury, trần lãi suất "well above the market") nằm ở `p0112-pb500-000` (hạng 1, nhưng không chứa evidence). Câu kết luận "A price ceiling that is set at a relatively high level is nonbinding…" thành một chunk riêng (`pb500-001`), không còn từ "interest rate" hay "cap".
  - Hệ quả: dense xếp chunk này ở hạng 6, hybrid đẩy nó ra khỏi top-10. Đây là hiện tượng **chunk nhỏ mất ngữ cảnh**, ngược với pha loãng ngữ nghĩa ở chunk dài.
- **Context Evidence của B500 cao** (dense_B500 đạt 23/24) chủ yếu vì có nhiều chunk hơn vừa trong budget (trung bình 7.3 so với 4.4), không phải vì xếp hạng tốt hơn.
- **q09** trượt ở mọi cấu hình. Câu hỏi tổng quát ("price floor set above equilibrium"), và mọi chunk top-5 trong chương 4 đều là bằng chứng *tương đương* (lương tối thiểu p105, lãi suất p108), trong khi định nghĩa hit chặt chỉ chấp nhận câu living wage ở p104. Đây là giới hạn của nhãn. Agent vẫn trả lời đúng q09 (được 2 điểm).

**Đảo chiều trên test.** Dense đạt 11/11, rerank đạt 10/11. Câu khác biệt duy nhất là t02: rerank đẩy p102-001 (câu gold) xuống hạng 4 và đưa p102-002 (chính sách bằng cấp, cùng trang) lên hạng 1. Với 11 câu, chênh 1 câu chưa đủ để kết luận phương pháp nào tốt hơn. Dev (24 câu, chênh 7 câu) vẫn là bằng chứng mạnh hơn, nhưng dev là câu Day 6 do chính tôi viết khi đã biết trang gold.

**Chấm context bằng tay trên test** (11 câu có đáp án × 2 cấu hình, thang 0/1/2; [results/retrieval/test/context_labels.json](../../results/retrieval/test/context_labels.json)):

| Cấu hình | 0 | 1 | 2 | Câu mức 1 và lý do |
|---|---:|---:|---:|---|
| `dense_B` | 0 | 1 | 10 | t09: chỉ có nửa evidence về công đoàn; p342-000 liệt kê luật chung, không nêu tên FLSA |
| `hybrid_rerank_B` | 0 | 2 | 9 | t09 như trên; t02: p102-001 tìm thấy ở hạng 4 nhưng **bị budget loại**, chỉ còn p102-002 (một phần) |

**Chẩn đoán hậu kiểm về budget** (chạy offline, đóng gói lại top-10 đã lưu; ở mức 4000 khớp chính xác các con số đã ghi; **không dùng để chọn cấu hình**; [results/retrieval/budget_ablation_posthoc.csv](../../results/retrieval/budget_ablation_posthoc.csv)):

| Context Evidence | 2000 | **4000 (đã dùng)** | 6000 | 8000 |
|---|---|---|---|---|
| dev `dense_B` | 13/24 | 19/24 | 20/24 | 21/24 |
| dev `hybrid_rerank_B` | 17/24 | 22/24 | 22/24 | 22/24 |
| test `dense_B` | 8/11 | 10/11 | 10/11 | 10/11 |
| test `hybrid_rerank_B` | 8/11 | 9/11 | 10/11 | **11/11** |

Trên dev, budget 4000 đã bão hòa với rerank nên dev không thể cho thấy vấn đề này. Trên test, budget là nút thắt.

## Agent và đánh giá

- **Tool, số lượt gọi, điều kiện dừng, cách chọn context và xử lý lỗi** ([src/agent.py](../../src/agent.py)):
  - **Tool:** `search_textbook(query)` chạy retriever của cấu hình, trả về top-5 chunk đóng gói trong 4000 ký tự, mỗi chunk kèm id, nguồn, trang, chương, mục. Filter của phiên do code áp dụng; model không đổi được. Hai tool còn lại là `submit_answer(answer, citations)` và `abstain(reason)`. Mọi schema dùng `strict: true`.
  - **Điều kiện dừng:**
    - Model gọi `submit_answer` hoặc `abstain`.
    - Search vượt `max_searches` (4, hoặc 1 với bản 1shot) bị từ chối bằng một `tool_result` lỗi.
    - Có giới hạn cứng `max_searches + 3` lượt gọi model; quá giới hạn thì tự từ chối.
  - **Kiểm tra citation:**
    - Mỗi id phải nằm trong các chunk đã trả về cho model, và phải xuất hiện dạng `[id]` trong câu trả lời.
    - Sai lần đầu thì trả lỗi để model sửa (q03 dev: model viết `[id1, id2]` và đã tự sửa). Sai lần hai thì chuyển thành từ chối.
  - **Context cuối:** hợp của mọi chunk đã đưa cho model.
  - **Bản v2 có thêm:** nếu chunk kết thúc giữa câu, chèn chunk kế tiếp ngay sau nó; và hai luật trong prompt (xem phần dưới).
  - **Xử lý lỗi:** lỗi từ API hoặc vector store được ghi `status: "error"`, không thay bằng kết quả giả (có test mock). Kết quả: 0 lỗi trong 381 lượt chạy có lưu trace (dev, test, test2).
  - **An toàn:** system prompt ghi rõ nội dung passage là dữ liệu, không phải chỉ dẫn. Gold chỉ được gắn vào trace *sau khi* chạy xong.

**Các cấu hình agent trên dev** (cùng 28 câu; [results/agent/dev/agent_table.md](../../results/agent/dev/agent_table.md)):

| Cấu hình / split | Tool use | Số lượt gọi (search) | Grounded answer 0/1/2 và trung bình | Citation hợp lệ | Câu có citation | Abstention đúng | Từ chối nhầm |
|---|---|---|---|---|---|---|---|
| `agent_dense_B` (baseline) / dev | 28/28 | 1:19 · 2:8 · 3:1 | 0/0/24 → 2.00 | 42/42 | 24/24 | 4/4 | 0/24 |
| `agent_hrr_B` / dev | 28/28 | 1:18 · 2:8 · 3:2 | 0/1/23 → 1.96 | 42/43 | 24/24 | 4/4 | 0/24 |
| `agent_hrr_B_1shot` / dev | 28/28 | 1:28 | 0/0/24 → 2.00 | 42/42 | 25/25 | **3/4** | 0/24 |
| `agent_hrr_B_v2` / dev | 28/28 | 1:18 · 2:9 · 4:1 | 0/0/24 → 2.00 | 43/43 | 24/24 | 4/4 | 0/24 |
| `agent_hrr_B_1shot_v2` / dev | 28/28 | 1:28 | 0/0/24 → 2.00 | 43/43 | 24/24 | 4/4 | 0/24 |
| **`agent_hrr_B_1shot` (chọn) / test** | 15/15 | 1:15 | 1/0/10 → **1.82** | 15/15 | 10/10 | **4/4** | 1/11 |
| `agent_dense_B` (baseline) / test | 15/15 | 1:8 · 2:5 · 3:2 | 1/0/10 → **1.82** | 15/15 | 10/10 | 4/4 | 1/11 |
| `agent_hrr_B_1shot_v2` (phụ, khai báo trước) / test | 15/15 | 1:15 | 1/1/9 → 1.73 | 17/17 | 10/10 | 4/4 | 1/11 |

- Chi phí trên dev: $0.0180 / $0.0181 / $0.0140 / $0.0187 / $0.0144 (28 câu mỗi cấu hình).
- Chi phí trên test: chọn **$0.0075**, baseline $0.0107, phụ $0.0080. Thời gian trung vị 3.6–4.7 giây/câu.
- Context Evidence của agent: dev 21–22/24; test 10/11 (baseline và chọn), 9/11 (phụ).
- Tổng hợp bằng `aggregate()` của starter ([src/agent_report.py](../../src/agent_report.py)); file `*_summary.json` có thêm điểm theo loại câu.

**Hai lỗi agent trên dev và vòng sửa** (cải thiện 3 và 4, có giả thuyết, đo trước và sau):
1. **q22, `agent_hrr_B`, chấm 1.** Chunk p357-005 dừng ở "refuse to pay women and/or minorities a". Model **tự viết tiếp** "those firms can gain an advantage by hiring them", một ý không có trong context và sai chủ thể (người được lợi là đối thủ, không phải công ty phân biệt đối xử).
   - Đáng chú ý: `agent_dense_B` thấy cùng chunk nhưng chủ động ghi "the passage cuts off" và không viết tiếp.
   - *Giả thuyết:* model thấy câu bị cắt nên lấp chỗ trống bằng kiến thức có sẵn. *Thay đổi:* chèn chunk lân cận khi chunk kết thúc giữa câu, cộng luật prompt "never complete a cut-off sentence".
   - *Kết quả:* `_v2` lấy được p358-000 ("other profit-seeking employers can hire these workers") và trả lời đúng, được 2 điểm.
2. **ud3, `agent_hrr_B_1shot`.** Nội dung trả lời đúng ("The textbook does not state…"), nhưng model gọi `submit_answer` thay vì `abstain`, nên theo quy ước không được tính là từ chối (3/4).
   - *Thay đổi:* luật "never use submit_answer to say the information is not in the textbook".
   - *Kết quả:* `1shot_v2` đạt 4/4.

**Lựa chọn giai đoạn 2** (theo quy tắc đã chốt):
- Cả 5 cấu hình đủ điều kiện (từ chối ≥3/4) và **hòa** về grounded (≥1.90), cũng hòa về số câu từ chối nhầm (0). Tiêu chí cuối là chi phí, nên chọn `agent_hrr_B_1shot` ($0.000501/câu).
- **Tự phê bình:** quy tắc này bỏ qua tỷ lệ từ chối khi đã qua ngưỡng, nên đã chọn đúng bản v1 có lỗi ud3, dù v2 đã sửa lỗi đó với chi phí chỉ cao hơn 3%. Tôi **không đổi quy tắc sau khi thấy kết quả**. Thay vào đó, tôi khai báo trước khi chạy test rằng `1shot_v2` chỉ được báo cáo như cấu hình phụ, không thể thay thế lựa chọn ([results/selection.json](../../results/selection.json)).
- **Dev bị hiệu ứng trần:** 4/5 agent đạt 2.00/2, nên dev không phân biệt được chất lượng agent. Lý do là agent tìm lại nhiều lượt và LLM dùng được bằng chứng tương đương, nên khoảng cách retrieval (15 so với 22 trên Hit@3) không chuyển thành khoảng cách trong câu trả lời.

**Bảng câu tiêu biểu** (trace trong `results/agent/test/*.jsonl`; nhãn kèm lý do trong `labels/grading_spec_test.json`):

| Query ID | Loại câu | Tool call và kết quả | Câu trả lời và citation | Nhãn, lý do |
|---|---|---|---|---|
| t10 (`agent_dense_B`) | Multi-hop, **có bằng chứng** | 2 search: "share of bachelor's degrees earned by women 2018-19" → p355-004 hạng 1; "bachelor's degree holder lifetime earnings…" → p362-002 hạng 1 | "women earned 57% of bachelor's degrees [p0355-…-004]… $2.8 million… $1.2 million more [p0362-…-002]" | **2**, 2/2 citation đúng: mỗi bước tìm một ý |
| ut3 (`agent_hrr_B_1shot`) | **Thiếu evidence** | 1 search "United Auto Workers membership 1960" → p351-000, p346-003… | Từ chối: "give UAW membership for 1985 (975,000), 2015 (about 390,000) and 2021 (408,000), but do not state the membership in 1960" | **Từ chối đúng**: nêu đúng dữ liệu có trong sách, không bịa số năm 1960 |
| t09 (`agent_dense_B`) | Multi-hop, **lỗi** | 3 search; p342-001 (bảng FLSA) xuất hiện ở hạng 5 trong 2 lượt nhưng **bị budget loại cả hai lần** (`context_ids` không chứa nó) | Từ chối: "never mention the Fair Labor Standards Act by name…" | **0** (từ chối nhầm). Lỗi ở bước chọn context; model trung thực với những gì nó được thấy |
| t02 (`agent_hrr_B_1shot_v2`) | Paraphrase, lỗi một phần | 1 search; p102-001 ở hạng 5 bị loại, chunk lân cận chiếm thêm budget | Nói về "tougher qualifications" và ví dụ trợ cấp y tá [p0102-…-002], tự ghi chú còn thiếu | **1**: thiếu ý "more required education → lower supply" và các ví dụ của sách |
| t07 (`agent_dense_B`) | Filter chương 14 | 1 search, filter `{chapter: 14}` → p342-001 hạng 1 | "The Fair Labor Standards Act of 1938 established the minimum wage and… overtime pay [p0342-…-001]" | **2**: filter loại được các đoạn lương tối thiểu ở Ch4 vốn không nêu tên luật |
| dev q22 (`agent_hrr_B`) | Direct, lỗi | 2 search; p357-005 bị cắt giữa câu | "...those firms can gain an advantage by hiring them [p0357-…-005]" | **1**, citation p357-005 không hợp lệ (đã sửa ở v2) |

- **Đường dẫn trace, nhãn, lệnh chạy, thời gian và chi phí:**
  - Trace: `results/agent/{dev,test}/<config>.jsonl`. Mỗi câu có câu hỏi, filter, từng event (`search`: query, top-k, kết quả với id/trang/score, `context_ids`, số ký tự, ms), câu trả lời, citation, `usage` token, chi phí, thời gian, lỗi; gold chỉ được gắn vào sau.
  - Nhãn: `results/agent/*/labels/`. Bảng: `results/agent/*/agent_table.md`. Lệnh chạy: README.
  - Tổng (gồm cả phần sau test): 381 lượt chạy agent, 1,643,722 token input, 130,082 token output, **$0.23** (giá Haiku 5.5: $0.10 / $0.50 cho mỗi triệu token). Riêng giai đoạn trước test và test: 185 lượt, $0.11. Retrieval chạy local, 0 USD.
- **Kết quả trước/sau, ví dụ lỗi, đánh đổi và giới hạn:**
  - **Chất lượng so với chi phí:** trên test, agent một lượt search (chọn) bằng điểm baseline đa lượt (1.82 so với 1.82) mà **rẻ hơn 30%** ($0.0075 so với $0.0107).
  - **Chất lượng so với thời gian:** rerank chậm hơn khoảng 9 lần trên CPU. Với agent, thời gian bị chi phối bởi lượt gọi model (khoảng 4 giây).
  - **Multi-hop:** một query gộp hai ý có thể trượt một bước (t09 ở 1shot), còn agent đa lượt tách thành 2–3 search (t10, m01, m02). Trên test, nhóm multi-hop đạt 2/4 điểm ở mọi cấu hình.
  - **Cấu hình v2** sửa được hai lỗi dev nhưng trên test thấp hơn một chút (1.73 so với 1.82). Chunk lân cận chiếm budget và đẩy rank-5 ra ngoài (t02). Một cải tiến có thể gây tác dụng phụ ở chỗ khác.
  - **Hướng sửa có bằng chứng** (chưa kiểm chứng độc lập): budget theo số chunk thay vì số ký tự, hoặc budget 6000–8000 ký tự, cộng chunk lân cận *trong* budget riêng. Cần một test mới để xác nhận.

## Sau test: ablation, dao động và test2

Mọi thứ trong mục này được làm **sau** lần chạy test duy nhất, nên không được dùng như bằng chứng test độc lập. Các thay đổi chỉ được đo trên dev và trên **test2**, một holdout mới được khóa trước khi chạy:
- Câu hỏi test2 được khóa ở commit `5c0102d`, cùng bản khai báo cấu hình và giả thuyết [results/test2_preregistration.json](../../results/test2_preregistration.json).
- Câu hỏi chỉ lấy từ các trang chưa từng là trang evidence; script kiểm tra test2 không chung câu evidence nào với dev hay test ([benchmark/test2/README.md](../../benchmark/test2/README.md)).

**1. Tách hai thay đổi của v2 trên dev** (mỗi cấu hình chỉ đổi một yếu tố so với `agent_hrr_B`; [results/agent/dev/agent_table.md](../../results/agent/dev/agent_table.md)):

| Cấu hình (dev) | Thay đổi | q22 (chunk bị cắt) | ud3 (giao thức từ chối) | Grounded TB | Từ chối đúng | Chi phí |
|---|---|---|---|---|---|---|
| `agent_hrr_B` | không | 1 (viết tiếp câu bị cắt) | từ chối đúng | 1.96 | 4/4 | $0.0181 |
| `agent_hrr_B_nbr` | chỉ chunk lân cận | **2** (p358-000 nối đủ câu) | từ chối đúng | 2.00 | 4/4 | $0.0178 |
| `agent_hrr_B_rule` | chỉ luật prompt | **2** (không viết tiếp, dùng ví dụ đầy đủ trong p357-005) | từ chối đúng | 1.96 (q13 = 1, xem dưới) | 4/4 | $0.0176 |
| `agent_hrr_B_v2` | cả hai | 2 | từ chối đúng | 2.00 | 4/4 | $0.0187 |

- Kết luận: **mỗi thay đổi riêng lẻ đều sửa được q22**. Lỗi ud3 không xuất hiện ở các agent tìm nhiều lượt, kể cả khi dùng prompt v1. Như vậy luật prompt chỉ thật sự cần cho agent một lượt (xem mục 2).
- Câu q13 ở `_rule` bị chấm 1: câu trả lời gọi MPL×P là "marginal revenue product", sai thuật ngữ so với sách. Đây là lỗi riêng lẻ, không do luật prompt gây ra.

**2. Dao động giữa các lần chạy** (Haiku 5.5 không cho đặt temperature; chạy lại `agent_hrr_B_1shot` trên dev 3 lần):

| Lần | Grounded TB | Từ chối đúng | Từ chối nhầm | Chi phí |
|---|---|---|---|---|
| 1 | 2.00 | 3/4 (ud3) | 0/24 | $0.0140 |
| 2 | 2.00 | 3/4 (ud3) | 0/24 | $0.0142 |
| 3 | 1.92 | 3/4 (ud3) | **1/24** (m02) | $0.0142 |

- **ud3 hỏng ở 3/3 lần chạy:** lỗi giao thức này có hệ thống, không phải ngẫu nhiên. Khi hết lượt search, agent một lượt chọn `submit_answer` để nói "sách không ghi". `agent_hrr_B_1shot_v2` (có luật prompt) sửa được lỗi này (4/4).
- **m02 ở lần 3:** query gộp hai ý bỏ sót chunk chứa con số 20%. Lỗi multi-hop này **giống hệt t09 trên test**, nên điểm yếu của agent một lượt được xác nhận lặp lại.
- Mức dao động của điểm trung bình khoảng 0.08/2, tương đương 1 câu.

**3. test2: chạy một lần cho 4 cấu hình đã khai báo trước**

| test2 | Hit@1 | Evidence Hit@3 | Context Evidence (4000 ký tự) | MRR@10 | Thời gian trung vị |
|---|---|---|---|---|---|
| `dense_B` | 5/10 | 9/10 | 10/10 | 0.725 | 80 ms |
| `hybrid_rerank_B` | **9/10** | **10/10** | 10/10 | **0.950** | 1019 ms |

| Agent / test2 | Số lượt search | Grounded 0/1/2 → TB | Citation hợp lệ | Từ chối đúng | Từ chối nhầm | Context Evidence | Chi phí |
|---|---|---|---|---|---|---|---|
| `agent_dense_B` (baseline) | 1:2 · 2:12 | 0/0/10 → 2.00 | 19/19 | 4/4 | 0/10 | 9/10 | $0.0099 |
| `agent_hrr_B_1shot` (chọn) | 1:14 | 0/0/10 → 2.00 | 17/17 | 4/4 | 0/10 | 10/10 | **$0.0070** |
| `agent_hrr_B` | 1:5 · 2:8 · 3:1 | 0/0/10 → 2.00 | 14/14 | 4/4 | 0/10 | 10/10 | $0.0095 |
| `agent_hrr_B_ctx8k` | 1:2 · 2:12 | 0/0/10 → 2.00 | 18/18 | 4/4 | 0/10 | 10/10 | $0.0107 |

**Kết luận các giả thuyết đã khai báo trước:**
- **H1 (budget): không kết luận được.** Trên test2, evidence của mọi câu đều đã vừa budget 4000 ký tự (chẩn đoán offline: 10/10 ở mọi mức từ 4000 trở lên). Test2 không tạo ra tình huống mà budget 8000 có thể giúp. Bằng chứng duy nhất cho việc budget gây lỗi vẫn là t09 và t02 trên test.
- **H2 (đa lượt so với một lượt ở multi-hop): không kết luận được.** Ở a09 và a10, một query gộp tình cờ lấy được cả hai bước. Trên dev (m02 lần 3) và test (t09), cùng kiểu câu đó lại thất bại. Kết luận thận trọng: trong 10 lần agent một lượt gặp câu multi-hop (m01×3, m02×3, t09, t10, a09, a10), nó trượt **2 lần** do query gộp bỏ sót một bước. Agent đa lượt có trượt 1 lần (t09 ở `agent_dense_B`), nhưng nguyên nhân là budget, không phải retrieval.
- **H3 (cấu hình chọn so với baseline): hòa** (2.00 và 2.00), giống kết quả test (1.82 và 1.82). Cấu hình chọn rẻ hơn **29%** ($0.0070 so với $0.0099).
- **Retrieval:** test2 xác nhận kết luận của dev (rerank tốt hơn rõ ở Hit@1 và MRR), không xác nhận sự đảo chiều của test. Sự đảo chiều trên test (11/11 so với 10/11, chỉ 1 câu) phù hợp với nhiễu do mẫu nhỏ.

**Khuyến nghị nếu triển khai** (rút ra sau tất cả bằng chứng; không thay thế lựa chọn đã khóa): dùng `hybrid_rerank_B`, agent đa lượt, bật luật prompt v2 và chunk lân cận, budget theo số chunk thay vì số ký tự. Chi phí tăng khoảng 30–50% so với agent một lượt, nhưng tránh được cả ba kiểu lỗi đã quan sát: multi-hop một lượt, giao thức từ chối, và viết tiếp câu bị cắt.

## Giới hạn

- **Mẫu nhỏ:** test có 11 câu có đáp án (1 câu tương đương 9 điểm %) và 4 câu thiếu evidence; dev có 24 câu. Không chênh lệch nào ở đây có ý nghĩa thống kê.
- **Không tất định:** Haiku 5.5 không cho đặt temperature. Mức dao động mới được đo cho cấu hình chọn trên dev (3 lần: điểm trung bình dao động trong khoảng 1.92–2.00; ud3 hỏng ở 3/3 lần). Các cấu hình khác chỉ chạy 1 lần. Query do model tự viết thay đổi giữa các lần chạy.
- **Benchmark do người biết gold viết:** cách diễn đạt có thể vô tình thuận lợi cho truy xuất, và dev là câu Day 6 nên có trần cao. Định nghĩa hit chặt đánh giá thấp bằng chứng tương đương (q03, q09, m02). Nhãn chấm tay có ghi nhận các trường hợp này.
- **Nhãn:** do LLM chấm nháp (Claude Code, Opus 5.5), đã đọc toàn văn mọi chunk được trích.
  - Học viên đã duyệt 11 mục: 9 câu test (7 câu có đáp án, 2 câu thiếu evidence) và 2 lỗi dev. Học viên đồng ý với giá trị nhãn ở cả **11/11** mục, và làm rõ phạm vi citation của q22 ([results/agent/REVIEW.md](../../results/agent/REVIEW.md)).
  - **Chấm mù lần hai:** học viên tự đọc trace và chấm 15 câu test của cấu hình được chọn khi chưa xem nhãn LLM ([results/agent/BLIND_REVIEW.md](../../results/agent/BLIND_REVIEW.md), [blind_review.csv](../../results/agent/blind_review.csv)).
  - **Kết quả** ([results/agent/blind_agreement.json](../../results/agent/blind_agreement.json), tính bằng `python -m src.blind_review score`):
    - Trên **10 câu thật sự mù**, đồng thuận **10/10** và Cohen's kappa **1.00**. Tính cả 5 câu đã xem nhãn trong REVIEW.md thì đồng thuận 15/15.
    - Citation: học viên xác nhận 15/15 citation hỗ trợ đúng câu được gắn, khớp với nhãn LLM.
    - Học viên chấm t09 = 0 với cùng lý do: thiếu bước FLSA nên từ chối một câu có đáp án.
  - **Cách đọc kết quả:** con số cao một phần vì các câu này dễ phân loại (10/11 câu có đáp án đạt 2, 4/4 câu từ chối rõ ràng). Kappa trên 10 câu, với số mức nhãn ít, nên khoảng tin cậy rộng. Kết quả này cho thấy nhãn LLM **không lệch so với người** trên mẫu này; nó chưa chứng minh nhãn LLM đúng trên các câu khó, chẳng hạn kiểu lỗi q22 ở dev.
  - Mỗi nhãn có lý do cụ thể: hoặc viết tay cho các ngoại lệ, hoặc sinh từ trace (chunk nào chứa câu gold, con số nào khớp, lý do từ chối nguyên văn). Trường `reason_kind` cho biết nhãn thuộc loại nào.
  - **Phạm vi người duyệt:** tổng cộng 21 mục khác nhau được người đọc lại. Gồm 11 mục ở REVIEW.md, nơi người duyệt đã xem nhãn LLM nên có rủi ro thiên lệch tự động hóa, và 10 mục chấm mù. Khoảng 360 nhãn còn lại (dev, các cấu hình khác, test2) chỉ do LLM chấm. Chúng có lý do kiểm chứng được, nhưng chưa được người đọc lại.
- **Bỏ qua hình (phần cơ bản):** index Day 6 không trích hình và đồ thị, nên câu hỏi về hình nằm ngoài phạm vi phần cơ bản. Phần nâng cao xử lý chúng (xem mục dưới).
- **Phân tích hậu kiểm:** chẩn đoán budget được thêm sau khi xem test. test2 được tạo để kiểm chứng nó, nhưng không tạo ra tình huống gây lỗi, nên **giả thuyết về budget vẫn chưa được xác nhận** trên dữ liệu độc lập.

## Thử thách nâng cao

Đã thực hiện. Báo cáo đầy đủ nằm ở [advanced/REPORT.md](../../advanced/REPORT.md); code, benchmark, trace và nhãn nằm trong [advanced/](../../advanced/). Tóm tắt:

- **Tài liệu:** toàn bộ cuốn OpenStax *Principles of Microeconomics 3e* (595 trang, CC BY-NC-SA 4.0). Index trang 21–576 thành 2.194 unit: 1.829 đoạn text, 167 bảng, 198 hình. Hình được mô tả bằng Haiku vision với chi phí $0.10; mỗi unit giữ trang gốc và bbox.
- **Agent:** `claude-haiku-5-5` với `search_document(query, content_type)` và **`view_region`**. Tool này render vùng gốc trên trang PDF để đọc lại con số trong bảng hoặc hình, thay vì tin mô tả AI hay text trích. Trên dev, nó là khác biệt duy nhất giữa các cấu hình: 18/18 so với 17/18 và 17/18.
- **Benchmark:** dev 18 câu, test 30 câu (6 bảng, 5 sơ đồ, 5 biểu đồ, 4 multi-hop, 4 text, 6 thiếu evidence). Benchmark và quy tắc chọn được khóa trước khi chạy (`c200359`, `36f5d53`). Cấu hình được chọn trên dev (`bd6f3de`), và test chạy đúng một lần (`3690d62`).
- **Test:** **30/30 (100%)**, ngưỡng là 27/30. Theo nhóm: bảng 6/6, sơ đồ 5/5, biểu đồ 5/5, multi-hop 4/4, text 4/4, thiếu evidence 6/6. Chi phí $0.046 cho 30 câu; 0 lỗi hệ thống.
- **Nhãn test:** LLM chấm nháp; học viên đối chiếu cả 30 câu với crop trang gốc, đồng ý 30/30, không sửa nhãn nào ([advanced/results/review/STUDENT_REVIEW.md](../../advanced/results/review/STUDENT_REVIEW.md)). Lần duyệt này không mù vì phiếu hiển thị nhãn nháp.
- **Lỗi và giới hạn chính:**
  - Trên dev, mô tả AI của hình không đủ tin cậy để trả lời con số (d07); đây là lý do thêm `view_region`.
  - 3/30 câu test có thẻ thừa ở cuối câu trả lời (lỗi định dạng).
  - Mỗi cấu hình chỉ chạy một lần, và người dựng hệ thống cũng là người soạn benchmark.
  - Chi phí phần nâng cao ước tính theo token khoảng $0.21. Số thực trả theo Anthropic Console là $0.11 cho **cả** Day 7.

## Sử dụng AI

Dùng Claude Code (Claude Opus 5.5) để đọc đề, viết code, soạn câu hỏi benchmark và chấm nháp nhãn. Agent của bài chạy bằng `claude-haiku-5-5`.
- **Cách kiểm tra:**
  - Evidence được máy kiểm tra trên trang gốc. Top-3 dense được đối chiếu với trace Day 6 (22/22).
  - Có 24 unit test, gồm test mock cho vòng lặp agent: citation sai, giới hạn search, lỗi vector store.
  - Chẩn đoán budget được kiểm tra lại để khớp chính xác các con số đã ghi.
  - Mọi nhãn kèm lý do và tham chiếu đến chunk cụ thể.
- **Rà soát độc lập:** một giám khảo AI thứ hai (Claude Sonnet 5.5, không thấy điểm của lượt chấm đầu) đã chấm lại bài theo RUBRIC.
  - Kết quả kiểm tra: 13 con số và 8 nhãn khớp hoàn toàn.
  - Lỗi phát hiện: báo cáo khái quát quá mức nguyên nhân t09 và nói quá về những gì đã được khóa trong `a6ab742`. Cả hai đã được sửa trong báo cáo này.
- **Các chỗ AI đã sai và được sửa trong quá trình làm:**
  - Lần đầu ghi nhãn citation q22 sai vị trí (danh sách citation đã bỏ trùng).
  - Một test dùng dữ liệu thiếu dấu nháy.
  - Script chẩn đoán budget ban đầu tái tạo sai header của chunk.
  - Bản nháp báo cáo giải thích sai lỗi q20 trên B500 là "evidence bị tách". Đọc lại trace cho thấy evidence nằm trọn trong một chunk nhưng mất ngữ cảnh, và báo cáo đã được sửa.
