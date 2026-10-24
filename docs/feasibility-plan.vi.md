# Nghiên cứu khả thi và kế hoạch triển khai

> Cập nhật sau bản kế hoạch ban đầu: đã hoàn thành audit dữ liệu thí điểm ngày 24/10/2026. Xem [kết quả đo thực tế](../reports/pilot_audit.vi.md). Các câu “chưa tải/chưa audit” bên dưới mô tả trạng thái ở thời điểm lập kế hoạch; chưa có huấn luyện mô hình.

**Dự án:** Dự đoán xác suất kết quả Premier League 2024–2025.

**Ngày nghiên cứu:** 24/10/2026, múi giờ Asia/Saigon. **Ngân sách:** chỉ dữ liệu miễn phí, theo xác nhận của người dùng.

**Phạm vi lần này:** kiểm chứng nguồn, thiết kế nghiên cứu và dữ liệu. Chưa huấn luyện mô hình, chưa có Accuracy hay kết luận đặc trưng cầu thủ có hiệu quả.

## 1. Kết luận và phạm vi nên chốt

Model A khả thi cao cho bài tập lớn. Model B/C khả thi có điều kiện: điểm khó nhất là dữ liệu đội hình và cầu thủ có thể biết tại thời điểm dự đoán, không phải lựa chọn thuật toán.

Đề xuất làm MVP độc lập với market value, xG/xA và lịch sử chấn thương. Sau khi MVP đạt kiểm tra thời gian, mở rộng theo từng khối để đo giá trị gia tăng. Không đặt việc hoàn thành bài tập phụ thuộc vào việc tìm đủ mọi trường dữ liệu.

Tên đề tài an toàn trước khi audit hoàn tất:

> Dự đoán xác suất kết quả Premier League mùa 2024–2025 bằng Machine Learning: đánh giá dữ liệu cấp đội và giá trị bổ sung của thông tin cầu thủ.

Chỉ đưa “đội hình xuất phát chính thức tại T−60” vào kết luận chính khi dữ liệu thực sự hỗ trợ. Đây là retrospective temporal backtest: mùa 2024–2025 đã kết thúc trước thời điểm nghiên cứu, không phải một dự báo tương lai được công bố năm 2024.

| Cấu phần | Khả thi | Quyết định |
|---|---|---|
| Kết quả, rolling form, Elo, điểm tích lũy | Cao | Lõi MVP |
| Phút, bàn thắng, kiến tạo từng cầu thủ trong quá khứ | Có ứng viên miễn phí | Audit ID, mùa, độ phủ, điều kiện dùng |
| XI lịch sử ghi nhận sau trận | Có bằng chứng tồn tại | Chưa đồng nghĩa XI đã công bố tại cutoff |
| Tuổi và continuity của XI | Có điều kiện | Cần XI đúng phiên bản và ngày sinh |
| Giá trị thị trường lịch sử | Có chuỗi định giá | Không phải giá từng ngày; thiếu bằng chứng công bố/phiên bản |
| xG/xA xuyên suốt 10 mùa | Chưa chứng minh | Không bắt buộc |
| Chấn thương/treo giò biết trước trận | Khó xác minh đồng nhất | Loại khỏi MVP |

Nếu mỗi mùa đủ 380 trận, train 8 mùa có 3.040 trận, validation và test mỗi tập 380 trận, tổng 3.800. Đây là **số kỳ vọng theo thiết kế**, chưa phải số bản ghi đã đếm. Các dòng cầu thủ không biến bài toán thành hàng chục nghìn nhãn độc lập: đơn vị dự đoán vẫn là trận đấu.

## 2. Mức bằng chứng và giới hạn kiểm chứng

Phân biệt ba mức:

1. **Đã đọc tài liệu/schema hoặc trang nguồn:** xác nhận nguồn mô tả trường, mùa, endpoint hoặc điều kiện cụ thể.
2. **Đã thấy ví dụ lịch sử:** xác nhận một vài bản ghi tồn tại; không suy thành độ phủ đầy đủ.
3. **Đã audit toàn bộ dữ liệu:** phải tải, đếm, kiểm tra missing/duplicate/ID theo mùa. Lần này chưa đạt mức này với nguồn nào.

Đã đọc trang tài liệu chính thức, repository tác giả, thư mục mùa và mã biến đổi dữ liệu. Một số trang trả 403/429; nội dung điều khoản/thông báo tương ứng chỉ đọc được qua chỉ mục tìm kiếm từ nguồn chính thức. Thử đọc header CSV FPL bằng Python không thành công do DNS trong môi trường; công cụ web cũng không đọc được các CSV lớn/kiểu nội dung đó. Không dùng các lỗi này làm bằng chứng dữ liệu không tồn tại. Không có bảng độ phủ đo được để công bố.

## 3. Đánh giá nguồn

### 3.1 Football-Data.co.uk — nguồn chính cho A

CSV theo mùa có ngày, đội, bàn thắng, H/D/A và thống kê trận; phạm vi archive bao trùm giai đoạn dự kiến. Rolling, Elo, điểm và H2H phải tự tính. Không có XI hay hồ sơ cầu thủ. Ghép bằng mùa, ngày và cặp đội đã chuẩn hóa. Cần audit giờ thi đấu và missing theo mùa. [Trang dữ liệu](https://www.football-data.co.uk/data.php), [từ điển trường](https://www.football-data.co.uk/notes.txt).

Nguồn miễn phí cho nghiên cứu cá nhân/học thuật; chính sách yêu cầu tải thủ công hoặc tự động nhẹ, tối đa hai lần/tuần. Chọn tải một lần, lưu cache; không xây scraper chạy lặp. Không mặc định quyền tái phân phối toàn bộ raw data. [Fair data usage](https://football-data.co.uk/contact.php).

### 3.2 FBref — không làm dependency huấn luyện mặc định

Có trang lịch sử cơ bản và xuất bảng, nhưng chưa kiểm chứng đủ mọi trận/cầu thủ 2015–2025. Sports Reference thông báo ngày 20/01/2026 đã gỡ advanced soccer data; không lập kế hoạch dựa vào xG/xA FBref hiện tại. [Thông báo chính thức](https://www.sports-reference.com/blog/2026/01/fbref-stathead-data-update/).

Điều khoản hiện tại đề cập hạn chế dùng nội dung cho ML dự đoán/phân loại. Khả năng xem hoặc xuất CSV không đủ để chọn làm nguồn training. [Terms of Use](https://www.sports-reference.com/termsofuse.html). Không có nhu cầu phụ thuộc nguồn này cho MVP.

### 3.3 Transfermarkt — dữ liệu tồn tại, tính point-in-time chưa được chứng minh

Đã xác minh ví dụ XI và sơ đồ ở [Arsenal–West Ham, 09/08/2015](https://www.transfermarkt.co.uk/arsenal-fc_west-ham-united/index/spielbericht/2577862) và [Ipswich–Liverpool, 17/08/2024](https://www.transfermarkt.com/ipswich-town_fc-liverpool/index/spielbericht/4361262). Không suy ra đủ 380 trận/mùa hoặc đúng phiên bản công bố tại T−60.

Market value là ước lượng của nguồn, khác phí chuyển nhượng; được cập nhật từng đợt, không phải quan sát hàng ngày. [Phương pháp định giá](https://www.transfermarkt.us/navigation/mwdefinition). Chưa xác minh API chính thức miễn phí đáp ứng nhu cầu. Điều kiện sao chép/tái sử dụng cần xét riêng. [Legal notice](https://www.transfermarkt.com/intern/).

### 3.4 Kaggle và dcaribou/transfermarkt-datasets — ứng viên cụ thể cho B/C

Kaggle là nơi phân phối, không phải một nguồn thống nhất về chất lượng hay giấy phép. Ứng viên là [Football Data from Transfermarkt](https://www.kaggle.com/datasets/davidcariboo/player-scores), đối chiếu với [repository của tác giả](https://github.com/dcaribou/transfermarkt-datasets). Có games, lineups, appearances, valuations; CSV/DuckDB và ID hỗ trợ ghép. Repo ghi CC0; chưa xác minh quyền tái cấp phép dữ liệu upstream.

[Config](https://github.com/dcaribou/transfermarkt-datasets/blob/master/config.yml) khai báo GB1 và mùa 2012–2025, chưa phải chứng cứ độ phủ. [Thông báo tác giả](https://github.com/dcaribou/transfermarkt-datasets/discussions/383) cho biết dữ liệu đã đóng băng trong năm 2026; không mô tả nguồn là đang cập nhật tuần.

Kiểm chứng trực tiếp schema:

- [game_lineups.sql](https://raw.githubusercontent.com/dcaribou/transfermarkt-datasets/master/dbt/models/curated/game_lineups.sql): có player/game/club/type; ngày lấy từ games, thiếu timestamp công bố XI.
- [player_valuations.sql](https://raw.githubusercontent.com/dcaribou/transfermarkt-datasets/master/dbt/models/curated/player_valuations.sql): có ngày và giá trị, thiếu timestamp công bố. Có fallback CLB hiện tại khi khôi phục CLB; không dùng để suy lịch sử roster.
- [appearances.sql](https://raw.githubusercontent.com/dcaribou/transfermarkt-datasets/master/dbt/models/curated/appearances.sql): có phút, bàn thắng, kiến tạo, thẻ; không có xG/xA hoặc bộ chỉ số phòng ngự chi tiết. Phân biệt CLB lúc ra sân với CLB hiện tại.

### 3.5 football-data.org — khác Football-Data.co.uk

Free có lịch/kết quả/bảng xếp hạng, 10 calls/phút; EPL thuộc coverage miễn phí. Lineups nằm ở gói Deep Data trả phí; 10 mùa lịch sử nằm ở ML Pack trả phí. Chưa xác minh free lấy đủ 2015–2025. Dùng làm ứng viên kiểm tra chéo fixtures qua API có token; không coi là nguồn XI miễn phí. [Pricing](https://www.football-data.org/pricing), [Coverage](https://www.football-data.org/coverage). Điều kiện sử dụng API cần lưu cùng manifest; đây không phải giấy phép dữ liệu mở. [Điều kiện đăng ký](https://www.football-data.org/client/register).

### 3.6 FPL Historical Dataset — ứng viên thực tế cho hiệu suất/proxy cầu thủ

[Thư mục tác giả](https://github.com/vaastav/Fantasy-Premier-League/tree/master/data) có mùa 2016–2017 đến 2024–2025. CSV gameweek hỗ trợ dữ liệu cầu thủ; cấu trúc và trường được mô tả trong [data dictionary](https://github.com/vaastav/Fantasy-Premier-League/blob/master/DATA_DICTIONARY.md). Cần audit thực tế từng mùa; không mặc định xG/xA hay ngày sinh có trong mọi phiên bản. Ghép fixture, team và player ID có season scope, không ghép tên đơn thuần.

[README](https://github.com/vaastav/Fantasy-Premier-League) cảnh báo xP có thể chứa thông tin sau trận; loại khỏi bộ chính. [LICENSE](https://github.com/vaastav/Fantasy-Premier-League/blob/master/LICENSE) ghi MIT cho phần mềm nhưng dữ liệu thuộc FPL/Understat; không diễn giải MIT là quyền vô điều kiện với dữ liệu.

FPL price không phải market value. Phút >0 không chứng minh đá chính; minutes/starts của chính trận dự đoán chỉ biết sau trận. Assists cần ghi rõ định nghĩa FPL, không trộn với kiến tạo của nguồn khác. Dữ liệu tuần cần sắp theo giờ trận thực tế, xử lý double/blank gameweek và chuyển CLB.

### 3.7 Nguồn khác

- **StatsBomb Open Data:** JSON có matches, events, lineups; có điều kiện sử dụng cho nghiên cứu và attribution. Danh sách hiện tại có EPL 2003/04 và 2015/16, không có EPL 2024/25. Hữu ích thử kỹ thuật dữ liệu cầu thủ, không đủ làm nguồn chính cho test đã chọn. [Repo](https://github.com/hudl/open-data), [competition manifest](https://raw.githubusercontent.com/statsbomb/open-data/master/data/competitions.json).
- **API-Football:** free 100 requests/ngày nhưng giới hạn mùa; chưa xác minh miễn phí đủ EPL lịch sử. Docs nói đội hình thường có khoảng 20–40 phút trước trận, nên không bảo đảm T−60. [Pricing](https://www.api-football.com/pricing), [docs](https://www.api-football.com/documentation-v3).
- **Sportmonks:** free không bao gồm EPL; loại khỏi đường triển khai miễn phí. [FAQ](https://www.sportmonks.com/faq/).
- **Trang Premier League/CLB chính thức:** có thể dùng kiểm tra thủ công một mẫu đội hình công bố; chưa có bằng chứng về một bulk archive miễn phí bao phủ toàn giai đoạn. Không giả định có API public chỉ vì website hiển thị dữ liệu.

Không ưu tiên thêm một scraper Understat hoặc nguồn mirror mới trước khi nguồn hiện có vượt qua audit. Mở rộng nguồn chỉ có ích nếu giải quyết được một thiếu hụt cụ thể.

## 4. Thời điểm dự đoán và nguyên tắc chống leakage

Cutoff mục tiêu: `scheduled_kickoff_as_known_at_prediction_utc - 60 minutes`. Dùng lịch đã biết lúc ra dự đoán; không dịch cutoff theo actual kickoff hoặc lịch được sửa sau đó. Nếu archive chỉ có giờ lịch cuối cùng, đánh dấu reconstructed_assumption. PL thông báo từ mùa 2024/25 đội hình có thể xem từ T−75. Tuy nhiên, điều đó không chứng minh file lịch sử hôm nay là snapshot đúng cutoff. [Premier League](https://www.premierleague.com/en/news/4081650).

Phải phân biệt:

- **Announced XI:** đội hình đã công bố trước cutoff.
- **Actual starters:** cầu thủ thực sự đá chính, có thể thay đổi lúc khởi động.
- **Expected lineup:** đội hình dự kiến từ dữ liệu quá khứ.

Không tự đặt `published_at = kickoff - 60min` cho bản ghi chỉ có ngày trận. Sơ đồ trong match report cũng có thể được diễn giải sau trận. Nếu thiếu chứng cứ, B/C chỉ là thí nghiệm có điều kiện theo đội hình hồi cứu; không đạt yêu cầu T−60 nghiêm ngặt của nghiên cứu chính.

Các quy tắc bắt buộc:

1. Với thống kê trận, trận đó phải kết thúc và thông tin phải có trước cutoff. Chỉ kiểm tra kickoff trước cutoff là chưa đủ.
2. Tạo feature trước, cập nhật kết quả sau. Các trận cùng thời điểm dùng chung trạng thái trước loạt trận.
3. Nếu chỉ có ngày, giữ giờ là unknown, không giả 15:00. Bản MVP dùng quy tắc bảo thủ loại kết quả cùng ngày khỏi trạng thái liên đội. Đây là bản tái dựng theo ngày, cần ghi hạn chế so với T−60 chính xác.
4. Rolling theo đội/cầu thủ đã sắp thời gian; loại trận hiện tại trước khi tính. `shift(1)` không tự giải quyết sai ID, sort, double gameweek, hoặc thời gian công bố.
5. Fit imputer/scaler/encoder và chọn feature trong train fold. Không fit toàn bộ dữ liệu trước split. [scikit-learn: leakage](https://scikit-learn.org/stable/common_pitfalls.html).
6. Không dùng bảng đội/cầu thủ cuối mùa làm trạng thái đầu mùa. Chuyển CLB phải có khoảng hiệu lực.
7. Không dùng kết quả/thống kê/odds sát giờ hoặc sau cutoff của trận đang dự đoán. Closing odds bị loại khỏi input MVP; benchmark odds chỉ mở sau khi có timestamp phù hợp.
8. Ghi riêng thời điểm tải hiện nay và thời điểm có thể biết trong lịch sử. Dữ liệu được hiệu chỉnh về sau không tự trở thành snapshot lịch sử.

### Market value đúng thời điểm

Chọn bản định giá có thời điểm công bố gần nhất nhưng không sau cutoff; không nội suy giữa mốc trước và sau, không backfill giá tương lai. Nếu chỉ có ngày thì loại cập nhật cùng ngày trận theo quy tắc bảo thủ, thêm tuổi định giá và tỷ lệ missing. Quy tắc này giảm rủi ro; chưa chứng minh publication time khi lịch sử bị sửa mà không lưu phiên bản.

Thiếu giá trị không bằng 0. Tổng giá trị XI phải kèm số cầu thủ có dữ liệu; không so tổng của 7 người với tổng của 11 người như cùng đại lượng. Tổng giá trị toàn CLB cần roster đúng thời điểm, nên xếp sau tổng XI.

## 5. Bộ đặc trưng đề xuất

Khởi đầu khoảng 25–40 biến cấp đội, không tăng số feature chỉ vì nguồn có nhiều cột. Các con số là phạm vi thiết kế, không phải cấu hình đã chọn qua test.

| Nhóm | Đặc trưng ưu tiên | Điều kiện/ý nghĩa |
|---|---|---|
| A bắt buộc | Elo home/away và chênh lệch | Tự cập nhật theo thời gian; home advantage học từ train |
| A bắt buộc | PPG, goals for/against trên 5 và 10 trận trước | Có số quan sát hỗ trợ, không tính trận hiện tại |
| A bắt buộc | Home-only/away-only form | Tối thiểu hóa nhiễu bằng shrinkage khi ít trận |
| A bắt buộc | Sporting points, PPG, GD và số trận đã chơi trong mùa | Không dùng bảng cuối mùa; 3W+D chưa bao gồm trừ điểm |
| A bắt buộc | Days since last PL match, lịch dày trong EPL | Không gọi là nghỉ mọi giải nếu thiếu cúp/châu Âu |
| A bắt buộc | Mới lên hạng, thiếu lịch sử, số trận hỗ trợ | Prior cho đội mới học từ train, không từ thành tích cuối mùa |
| A mở rộng | Shots/shots-on-target rolling, H2H có decay | H2H ít mẫu; kiểm tra bằng ablation |
| A mở rộng | Thứ hạng chính thức trước trận | Cần lịch sử trừ điểm và quy tắc xếp hạng đúng thời điểm |
| B1 có điều kiện | Tuổi XI trung bình, continuity so với trận trước | Ngày sinh và announced XI đủ bằng chứng |
| B1 có điều kiện | Kinh nghiệm EPL, số cầu thủ mới/ít lịch sử | Tất cả chỉ cộng dồn trước cutoff |
| B2 mở rộng | log tổng/median giá trị XI, tỷ trọng top 3, chênh lệch hai đội | Value PIT, currency nhất quán, age-of-value và coverage |
| C lõi | Phút, số lần đá chính, goals/assists lagged | Tính theo cầu thủ, aggregate trên XI hợp lệ |
| C mở rộng | xG/xA, defensive/goalkeeper stats theo vị trí | Chỉ khi cùng định nghĩa và đủ mùa |
| Mở rộng khó | Formation, injuries/suspensions, full-squad value | Chứng cứ thông tin trước trận; không phải dependency MVP |

Giữ một tập nhỏ biến home, away và chênh lệch; tránh thêm mọi biến trùng lặp. Mô hình có thể học lợi thế sân nhà qua cách mã hóa home/away và intercept, không cần một cột hằng `is_home=1` trong dataset một dòng/trận.

Với cầu thủ, ưu tiên cửa sổ **5 trận gần nhất của đội** cho mức sử dụng. Không ra sân chỉ tính 0 nếu có bằng chứng bảng trận/roster đầy đủ; dòng thiếu chưa chắc là không ra sân. Cửa sổ 5 lần ra sân của cầu thủ là biến khác và phải có thời gian từ lần ra sân gần nhất. Per90 tính từ tổng đóng góp/tổng phút trong cửa sổ, có shrinkage hoặc ngưỡng phút; không lấy trung bình các per90 rất nhiễu của người đá ít.

Không đồng nhất “không có trong XI” với chấn thương. Có thể tạo proxy số cầu thủ thường xuyên đá chính vắng XI, trong đó mức quan trọng xác định từ phút quá khứ. Không dùng số ngày còn lại đến bình phục hoặc tổng số trận đã nghỉ của cả đợt chấn thương.

## 6. Kiến trúc dataset

Ba lớp: **raw bất biến → curated có ID và thời gian → feature snapshots**. CSV/JSON cho raw, Parquet cho bảng chuẩn; pandas và DuckDB đủ cho quy mô này. Notebook phục vụ khám phá/trình bày, logic dùng lại nằm trong module Python.

| Bảng | Khóa và trường chính |
|---|---|
| `source_manifest` | source, URL, retrieval time, version/commit, hash, terms URL, access outcome |
| `teams`, `players` | ID nội bộ; tên chuẩn; ngày sinh nếu có nguồn |
| `source_id_map` | source, entity type, external ID, season scope, internal ID, match confidence |
| `player_memberships` | player, club, valid_from/to, evidence; optional khi roster được xác minh |
| `matches` | match ID, season, teams, scheduled/actual kickoff, status, source IDs |
| `match_outcomes` | match ID, goals, H/D/A, result availability; tách khỏi input hiện tại |
| `team_match_stats` | match × team, shots/cards/etc; chỉ dùng lagged |
| `lineup_snapshots` | match × team × player × snapshot, starter flag, lineup kind, publication evidence |
| `player_match_stats` | match × player × team-at-match, minutes, goals, assists, metric definition |
| `player_valuations` | player × valuation date × version, value, currency, publication evidence |
| `feature_snapshots` | match × cutoff × feature_version; bộ biến A/B/C và bằng chứng nguồn |
| `split_manifest` | match ID, split, common-cohort flag, exclusion reason |
| `predictions` | match, experiment, model version, cutoff, p_H/p_D/p_A |

Các bản ghi thay đổi theo thời gian có `event_at`, `published_at`, `available_at`, `retrieved_at`, `availability_status`, `source_url`, `source_record_id`, `raw_hash`. Nếu chưa biết thời điểm công bố thì để null/unknown, không tạo timestamp giả. Nêu rõ trạng thái verified, reconstructed_assumption hay unknown.

Feature join dùng `available_at <= prediction_cutoff`; mỗi feature giữ nguồn hoặc lineage để kiểm toán, snapshot có `source_max_available_at`. Pipeline chính loại thông tin current-lineup không rõ thời điểm. Việc tái dựng kết quả quá khứ từ archive là giả định quan sát lịch sử, không tự chứng minh feed nhà cung cấp đã phát đúng lúc.

Ghép trận bằng source ID mapping, kiểm tra team home/away, mùa và thời gian. Tên chuẩn hóa chỉ là bước tạo ứng viên, không tự fuzzy-match mọi trường hợp. Trận hoãn, timezone Europe/London và DST phải xử lý rõ. Khi nguồn thiếu giờ, dùng ngày+cặp đội+mùa để đối chiếu, không tạo độ chính xác giả.

## 7. Thiết kế thực nghiệm và so sánh công bằng

### Hai tuyến thí nghiệm

**A_full:** mọi trận hợp lệ của tập đội bóng; train 2015/16–2022/23, validation 2023/24, test 2024/25. Có thể dùng 2013/14–2014/15 làm warm-up Elo/rolling, không tính là quan sát đánh giá. Nếu không có warm-up, khởi tạo prior và đánh dấu thiếu lịch sử.

**A/B/C_common:** cùng trận ở cả train, validation và test; cùng thuật toán, ngân sách tuning, calibration và tiêu chuẩn missing. Nếu dữ liệu cầu thủ chỉ đạt từ 2018/19, cả ba cùng bắt đầu từ mùa đó. Không so A_full với C ngắn lịch sử để kết luận hiệu quả do feature.

Tách B1 = A + nhân sự XI; B2 = B1 + valuation; C = phiên bản B đủ điều kiện + performance. Nếu B2 không đủ dữ liệu, nghiên cứu B1/C vẫn có giá trị nhưng cần nói rõ đã thu hẹp giả thuyết. Không có XI thì thí nghiệm P dùng proxy cầu thủ/expected lineup là nhánh khác, không gắn nhãn kết quả cho câu hỏi XI chính thức.

Đề xuất gate chọn giai đoạn dữ liệu trước khi xem metric: ít nhất 95% trận/mùa có 22 starter hợp lệ; 100% trận được đưa vào cohort phải đạt các trường bắt buộc. 95% là ngưỡng thiết kế, không phải số đo nguồn. Báo cáo missing theo từng đội/mùa, không chỉ toàn bộ, và báo cáo selection bias của cohort bị lọc. Chỉ coverage cao không đủ thay cho bằng chứng thời gian.

### Fit, tuning và test

- Logistic Regression multinomial + regularization là mô hình chính dễ giải thích.
- Random Forest là đối chứng quan hệ phi tuyến; kiểm tra xác suất và calibration.
- Chọn một trong XGBoost/LightGBM để giữ ngân sách thí nghiệm vừa phải; giới hạn độ sâu/leaves, tăng regularization. Chưa cần cả hai hoặc Deep Learning.
- Chia expanding-window theo mùa trong train để chọn hyperparameters, ví dụ train đến 2019/20 → đánh giá 2020/21; train đến 2020/21 → đánh giá 2021/22; train đến 2021/22 → đánh giá 2022/23.
- Khóa hyperparameters qua temporal folds trong train; báo metrics 2023/24 trước calibration. Nếu fit calibrator ít tham số trên 2023/24, scores/plots sau calibration trên chính mùa đó chỉ là diagnostics, không phải đánh giá ngoài mẫu. Đánh giá calibrated model ngoài mẫu ở test cuối. Nếu cần so sánh calibration trong development, dùng temporal out-of-fold; không CV ngẫu nhiên. [Calibration](https://scikit-learn.org/stable/modules/calibration.html).
- Khóa feature, preprocessing, hyperparameters, calibrator và cohort trước khi tính test metrics. Mặc định estimator fit đến 2022/23, calibrator fit validation sau khi đã khóa cách làm; không tự refit estimator lên validation rồi giữ calibrator cũ.
- Trong 2024/25, được cập nhật rolling/Elo từ các trận trước đã hoàn tất và có dữ liệu tại cutoff; không fit lại estimator bằng test. Đây là dự đoán từng trận theo tuần tự, không dự đoán toàn mùa từ tháng 8.
- Đánh giá tất cả cấu hình đã đăng ký trong một vòng test cuối, không chỉnh model sau khi xem test. Khi phát hiện bug, ghi rõ sửa lỗi và lần chạy lại, không che giấu.

### Đánh giá xác suất

Primary: multiclass Log Loss. Secondary: Brier, Accuracy, Macro F1, Precision/Recall từng lớp, confusion matrix và reliability diagram theo lớp.

Quy ước Brier: `mean_i(sum_c((p_ic - y_ic)^2))`, miền [0,2], không trộn với biến thể chia đôi. Ép thứ tự xác suất H,D,A khi xuất; thư viện có thể sắp nhãn theo A,D,H. [Brier documentation](https://scikit-learn.org/stable/modules/generated/sklearn.metrics.brier_score_loss.html).

Baselines:

1. Luôn đoán H cho các metric phân loại.
2. Tần suất H/D/A từ train với smoothing cho metric xác suất; không gán xác suất 0 cho lớp còn lại.
3. Elo với ánh xạ ba lớp được học từ dữ liệu quá khứ. Expected score Elo không tự là xác suất thắng vì còn hòa.

So sánh chênh lệch Log Loss/Brier trên cùng trận. Đề xuất đăng ký trước 2.000 lần paired moving-block bootstrap, block hai tuần lịch liên tiếp, seed cố định, sensitivity block một và bốn tuần; các mô hình dùng cùng chỉ số lấy mẫu. Dùng ngày thực tế thay gameweek vì trận hoãn. Phương pháp vẫn chưa loại hết phụ thuộc theo đội. Một mùa test chỉ 380 trận nên không hứa kết luận mạnh từ chênh lệch Accuracy nhỏ. Báo cáo kết quả từng mùa validation để thấy độ ổn định.

Permutation importance theo nhóm feature trên validation; SHAP nếu cần cho boosting. Tránh diễn giải nhân quả: tầm quan trọng dự đoán của market value không chứng minh tăng giá trị đội hình sẽ làm đội thắng. Feature tương quan như Elo/form/value cần group ablation.

## 8. Kiểm thử cần viết khi triển khai

Các kiểm thử này bảo vệ câu hỏi nghiên cứu, không chỉ kiểm tra code chạy được:

1. Match ID duy nhất; home khác away; số trận mỗi mùa và mỗi đội hợp lệ; H/D/A khớp bàn thắng.
2. Mọi bản ghi được sử dụng có ID ánh xạ không mơ hồ; 11 starter mỗi phía, không lặp cầu thủ.
3. Thay kết quả trận hiện tại không làm đổi feature của chính trận đó.
4. Thay hoặc thêm dữ liệu tương lai không làm đổi feature quá khứ.
5. Feature tính trên prefix thời gian trùng với feature tương ứng của full history; phát hiện backfill và aggregate tương lai.
6. Đảo thứ tự các trận cùng cutoff không làm đổi dự đoán; cập nhật sau khi tạo cả batch.
7. Test riêng đầu mùa, lên hạng, chuyển CLB, đổi tên, trận hoãn, double gameweek, thiếu ngày sinh/valuation.
8. Mọi join PIT có bằng chứng/cờ giả định; valuation mới không được lan ngược.
9. Probability hữu hạn, [0,1], tổng bằng 1; thứ tự nhãn nhất quán.
10. Cùng cohort A/B/C; preprocessing train-only; file test không lọt vào tuning.

## 9. Lộ trình và sản phẩm

Ước lượng cho một người học bán thời gian; chưa có hạn nộp nên đây là kế hoạch điều chỉnh được.

| Giai đoạn | Thời lượng dự kiến | Sản phẩm | Điều kiện hoàn tất |
|---|---|---|---|
| 0. Nghiên cứu và protocol | Lần làm việc hiện tại | Báo cáo này, protocol đề xuất | Nguồn và giới hạn được ghi rõ |
| 1. Audit mẫu nguồn miễn phí | 2–3 ngày | Source manifest, schema, bảng coverage thí điểm | Quyết định nguồn A và go/no-go B/C |
| 2. Thu thập và chuẩn hóa A | 3–4 ngày | Raw cache, matches/team IDs, quality report | Không trùng, target nhất quán, lịch đúng |
| 3. Feature PIT + kiểm thử | 3–5 ngày | Feature builder, data dictionary, leakage tests | Kiểm thử thời gian đạt |
| 4. MVP mô hình A | 3–4 ngày | Baselines, 3 thuật toán, walk-forward/validation report | Chỉ đánh giá development; test tiếp tục khóa |
| 5. B1/B2/C hoặc P | 5–8 ngày | Player/XI tables, cohort chung, ablation validation | Đủ coverage/rights/PIT hoặc ghi fallback |
| 6. Khóa và test cuối | 2–3 ngày | Metrics, CI, calibration, giải thích | Không tuning bằng test |
| 7. Báo cáo và demo | 3–4 ngày | Notebook tái chạy, báo cáo, slides/Streamlit tùy chọn | Kết quả truy vết được và nêu hạn chế |

MVP kỹ thuật có thể hoàn thành khoảng 2–3 tuần; phiên bản mở rộng khoảng 4–6 tuần tùy dữ liệu và thời gian làm việc. Không coi đây là cam kết lịch khi chưa biết hạn nộp. Nếu muốn giữ test cho so sánh A/B/C cuối cùng, MVP ban đầu chỉ công bố metrics validation. Nếu phải nộp MVP sớm và đã mở test, cần ghi nhận điều đó trong nghiên cứu mở rộng.

## 10. Rủi ro và phương án xử lý

| Rủi ro | Xử lý |
|---|---|
| Không có XI trước cutoff | Không giả timestamp; loại khỏi mô hình chính hoặc chuyển expected-lineup proxy; hồi cứu XI chỉ là phụ lục có điều kiện |
| Valuation tương lai/không rõ ngày công bố | Backward as-of, không nội suy, bỏ same-day date-only, flag tuổi/missing; B1 độc lập B2 |
| Cập nhật/sửa dữ liệu quá khứ | Raw hash, version/commit, ghi provenance; không tự gán verified |
| Nguồn miễn phí đổi điều kiện hoặc chặn truy cập | Cache, không gọi lặp/vượt chặn; chọn dependency ít nguồn; loại nguồn không phù hợp |
| ID/tên cầu thủ khác nhau, chuyển CLB | Mapping có kiểm tra; dùng club-at-match và roster hiệu lực |
| Chỉ giữ trận đủ dữ liệu làm lệch mẫu | Coverage theo đội/mùa; cùng cohort và báo cáo exclusions |
| Đội mới, đầu mùa, COVID/lịch thi đấu đổi | Prior từ train, missing flags, đánh giá nhiều mùa; không dùng sự kiện chưa biết tại cutoff |
| Bảng xếp hạng sai do trừ điểm | Sporting points/PPG làm core, official rank chỉ khi có lịch sử quyết định |
| “Ngày nghỉ” thiếu trận cúp | Đặt tên đúng days_since_last_PL_match; chỉ mở rộng khi có lịch mọi giải |
| Overfit khoảng 3.000 trận, nhiều thí nghiệm | Ít feature có cơ sở, regularization, ngân sách tuning cố định, test khóa |
| Cầu thủ không cải thiện dự đoán | Kết quả hợp lệ; báo cáo độ bất định và phân tích coverage/tín hiệu trùng lặp |

## 11. MVP được đề xuất

**MVP hoàn chỉnh:** nguồn trận đấu miễn phí; A với Elo, form 5/10, home/away, sporting PPG/GD, khoảng cách giữa các trận EPL; baseline tần suất và Elo ba lớp; Logistic Regression, Random Forest, một boosting model; probabilities H/D/A; chronological validation; leakage tests; báo cáo xác suất và giải thích.

**Mở rộng ưu tiên:** B1 trước, thêm C cơ bản (phút/bàn/kiến tạo); B2 valuation sau; xG/xA, formation, injury chỉ khi nguồn đạt tiêu chuẩn. Nếu thiếu announced XI, làm nhánh P với trọng số nhân sự từ lịch sử phút hoặc expected lineup, đóng băng quy tắc trước cutoff; không dùng phút trận hiện tại để chọn người hoặc cân trọng số.

**Công việc kế tiếp cụ thể:** audit nhỏ trên mùa 2015/16, 2023/24, 2024/25 của nguồn trận đấu; kiểm tra vài trận trải đầu/giữa/cuối mùa cho nguồn XI/cầu thủ mà không xem performance mô hình. Lập `coverage_by_season` gồm số trận, tỷ lệ giờ chính xác, 22 starters, ID match rate, minutes/goals/assists coverage, valuation PIT coverage và chứng cứ quyền dùng. Chọn khoảng lịch sử chung sau audit, rồi mới triển khai thu thập toàn bộ và feature builder.

Không có metric thực nghiệm hoặc số liệu minh họa bị trình bày như kết quả thật trong tài liệu này.
