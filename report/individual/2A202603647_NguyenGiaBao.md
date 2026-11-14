# Báo cáo Day 7 — Agentic RAG

**Học viên:** Nguyễn Gia Bảo · **MSSV:** 2A202603647 · **Lớp:** K5-L3A · **Ngày:** 14/11/2026

> Mọi con số dưới đây được lấy từ file trong repo, có ghi đường dẫn. Lệnh tái lập nằm ở [README.md](../../README.md#bài-làm--nguyễn-gia-bảo--2a202603647--k5-l3a).

## Tóm tắt

- **Hệ thống:** agent `claude-haiku-5-5` gọi tool `search_textbook` trên index Day 6 (e5-base, pgvector). Agent trả lời có citation `[chunk-id]` hoặc gọi `abstain`.
- **Phương pháp retrieval:** 4 phương pháp (dense, BM25, hybrid RRF, hybrid + cross-encoder rerank) trên 2 index (B, B500), tổng cộng 7 cấu hình.
- **Quy trình:** benchmark 43 câu và tiêu chí chọn được **khóa trước mọi lần chạy** (commit `a6ab742`). Cấu hình được chọn trên dev bằng script (commit `ab54365`). Test được chạy **một lần**.
- **Retrieval:** trên dev, `hybrid_rerank_B` đạt Evidence Hit@3 **22/24** so với baseline dense **15/24**. Trên test kết quả đảo chiều: dense 11/11, rerank 10/11. Với N=11, chênh 1 câu tương đương 9 điểm %.
- **Agent:** trên test, cả baseline và cấu hình chọn đều đạt grounded **1.82/2**, từ chối đúng **4/4**, citation hợp lệ **15/15**. Mỗi cấu hình có 1 câu từ chối nhầm (t09).
- **Phát hiện chính:** ở t09, retriever **có tìm thấy** chunk evidence (hạng 5, hai lần), nhưng **budget context 4000 ký tự loại nó đi** trước khi model kịp đọc. Lỗi nằm ở bước chọn context, không phải ở retrieval. Chẩn đoán hậu kiểm: với budget 8000 ký tự, Context Evidence của `hybrid_rerank_B` trên test tăng từ 9/11 lên 11/11.
- **Chi phí:** 185 lượt chạy agent, khoảng **$0.11** tổng cộng; truy xuất 0 USD (chạy local).

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
  - **Xử lý lỗi:** lỗi từ API hoặc vector store được ghi `status: "error"`, không thay bằng kết quả giả (có test mock). Kết quả: 0 lỗi trong 185 lượt chạy có lưu trace.
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
  - Tổng: 185 lượt chạy agent, 778,726 token input, 63,188 token output, **$0.11** (giá Haiku 5.5: $0.10 / $0.50 cho mỗi triệu token). Retrieval chạy local, 0 USD.
- **Kết quả trước/sau, ví dụ lỗi, đánh đổi và giới hạn:**
  - **Chất lượng so với chi phí:** trên test, agent một lượt search (chọn) bằng điểm baseline đa lượt (1.82 so với 1.82) mà **rẻ hơn 30%** ($0.0075 so với $0.0107).
  - **Chất lượng so với thời gian:** rerank chậm hơn khoảng 9 lần trên CPU. Với agent, thời gian bị chi phối bởi lượt gọi model (khoảng 4 giây).
  - **Multi-hop:** một query gộp hai ý có thể trượt một bước (t09 ở 1shot), còn agent đa lượt tách thành 2–3 search (t10, m01, m02). Trên test, nhóm multi-hop đạt 2/4 điểm ở mọi cấu hình.
  - **Cấu hình v2** sửa được hai lỗi dev nhưng trên test thấp hơn một chút (1.73 so với 1.82). Chunk lân cận chiếm budget và đẩy rank-5 ra ngoài (t02). Một cải tiến có thể gây tác dụng phụ ở chỗ khác.
  - **Hướng sửa có bằng chứng** (chưa kiểm chứng độc lập): budget theo số chunk thay vì số ký tự, hoặc budget 6000–8000 ký tự, cộng chunk lân cận *trong* budget riêng. Cần một test mới để xác nhận.

## Giới hạn

- **Mẫu nhỏ:** test có 11 câu có đáp án (1 câu tương đương 9 điểm %) và 4 câu thiếu evidence; dev có 24 câu. Không chênh lệch nào ở đây có ý nghĩa thống kê.
- **Không tất định:** Haiku 5.5 không cho đặt temperature, và mỗi cấu hình chỉ chạy một lần. Query do model tự viết thay đổi giữa các lần chạy (t02 cho hai query khác nhau ở 1shot và 1shot_v2). Mức dao động chưa được đo.
- **Benchmark do người biết gold viết:** cách diễn đạt có thể vô tình thuận lợi cho truy xuất, và dev là câu Day 6 nên có trần cao. Định nghĩa hit chặt đánh giá thấp bằng chứng tương đương (q03, q09, m02). Nhãn chấm tay có ghi nhận các trường hợp này.
- **Nhãn:** do LLM chấm nháp (Claude Code, Opus 5.5), đã đọc toàn văn mọi chunk được trích. Phần duyệt của học viên nằm ở [results/agent/REVIEW.md](../../results/agent/REVIEW.md). Đây không phải chú thích của hai người chấm độc lập.
- **Bỏ qua hình:** hình và đồ thị không được trích ở Day 6, nên câu hỏi về hình nằm ngoài phạm vi.
- **Phân tích hậu kiểm:** chẩn đoán budget được thêm sau khi xem test và chỉ mang tính chẩn đoán. Kết luận về budget cần một test mới.

## Thử thách nâng cao

Không thực hiện. Thử thách yêu cầu tài liệu từ 100 trang có bảng, ảnh và biểu đồ, test ≥30 câu và đạt ≥90%, không cộng điểm một phần. Tôi ưu tiên làm phần cơ bản cho chặt chẽ: chốt benchmark trước, chấm từng trace, phân tích lỗi. Ứng viên tự nhiên nếu làm tiếp là toàn bộ cuốn sách OpenStax (595 trang, nhiều bảng và đồ thị có nhãn số), dùng PyMuPDF `find_tables()` và mô tả hình bằng model vision.

## Sử dụng AI

Dùng Claude Code (Claude Opus 5.5) để đọc đề, viết code, soạn câu hỏi benchmark và chấm nháp nhãn. Agent của bài chạy bằng `claude-haiku-5-5`.
- **Cách kiểm tra:**
  - Evidence được máy kiểm tra trên trang gốc. Top-3 dense được đối chiếu với trace Day 6 (22/22).
  - Có 24 unit test, gồm test mock cho vòng lặp agent: citation sai, giới hạn search, lỗi vector store.
  - Chẩn đoán budget được kiểm tra lại để khớp chính xác các con số đã ghi.
  - Mọi nhãn kèm lý do và tham chiếu đến chunk cụ thể.
- **Các chỗ AI đã sai và được sửa trong quá trình làm:**
  - Lần đầu ghi nhãn citation q22 sai vị trí (danh sách citation đã bỏ trùng).
  - Một test dùng dữ liệu thiếu dấu nháy.
  - Script chẩn đoán budget ban đầu tái tạo sai header của chunk.
  - Bản nháp báo cáo giải thích sai lỗi q20 trên B500 là "evidence bị tách". Đọc lại trace cho thấy evidence nằm trọn trong một chunk nhưng mất ngữ cảnh, và báo cáo đã được sửa.
