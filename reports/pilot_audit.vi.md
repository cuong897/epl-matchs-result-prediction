# Kết quả kiểm tra dữ liệu thí điểm

Ngày: **24/10/2026, Asia/Saigon**. Đây là kết quả đo trên các tệp thật đã tải. Không phải dữ liệu minh họa, không phải kết quả mô hình.

## 1. Phạm vi và khả năng tái lập

Đã tải **9 tệp**: ba CSV trận đấu Football-Data.co.uk; hai CSV cầu thủ FPL; hai bảng fixtures và hai bảng teams FPL. Mỗi tệp có URL, thời gian tải UTC, số byte và SHA-256 trong [manifest](../research/download_manifest.json). Raw giữ nguyên, không phát hành lại tự động; download chạy lại sẽ dùng cache.

Các mùa kiểm tra chỉ gồm 2015–2016, 2023–2024, 2024–2025 ở cấp trận, và hai mùa sau ở cấp cầu thủ. Chưa suy rộng kết quả sang các mùa train còn lại. Nguồn FPL là kho cộng đồng [vaastav/Fantasy-Premier-League](https://github.com/vaastav/Fantasy-Premier-League); điều kiện dữ liệu upstream vẫn cần được phân biệt với giấy phép phần mềm.

Máy chạy: Python 3.13.5, pandas 3.0.5. Lệnh tái lập và giải thích các bước trong [README](../README.md). Mã kiểm tra chạy offline sau khi có cache. Các số liệu gốc ở [pilot_audit.json](pilot_audit.json); bảng ghép ID không chứa kết quả ở [pilot_match_links.csv](pilot_match_links.csv).

## 2. Dữ liệu trận đấu

| Mùa | Trận | Đội | Cột | Trận có giờ hợp lệ | Thiếu trường cốt lõi | Trùng khóa trận |
|---|---:|---:|---:|---:|---:|---:|
| 2015–2016 | 380 | 20 | 65 | 0 | 0 | 0 |
| 2023–2024 | 380 | 20 | 106 | 380 | 0 | 0 |
| 2024–2025 | 380 | 20 | 120 | 380 | 0 | 0 |

Ở cả ba mùa: mỗi đội có 38 trận, 19 sân nhà và 19 sân khách; không có cặp home-away lặp; H/D/A nhất quán với bàn thắng; không có bàn thắng âm/phân số, ngày không hợp lệ, đội tự đấu hoặc dòng thuộc giải khác. Các trường shots, shots on target, corners và cards được kiểm tra đều không thiếu.

Đây là **đạt kiểm tra cấu trúc**, chưa phải xác minh mọi con số thống kê với biên bản độc lập. Các cột thống kê chính trận đang dự đoán không được dùng làm input. Số cột khác nhau giữa mùa chủ yếu phản ánh schema rộng hơn; pipeline cần chọn cột rõ ràng, không sử dụng tự động toàn bộ cột số.

Mùa 2015–2016 không có `Time`: giữ thời gian chính xác là unknown. Không tự gán 15:00 hoặc biến ngày thành midnight rồi coi đó là kickoff. Feature theo ngày có thể dùng quy tắc loại thông tin cùng ngày; nghiên cứu T−60 chính xác cần nguồn bổ sung.

## 3. Dữ liệu cầu thủ FPL

| Chỉ tiêu | 2023–2024 | 2024–2025 |
|---|---:|---:|
| Dòng raw | 29.725 | 27.605 |
| Dòng AM loại khỏi bảng cầu thủ | 0 | 322 |
| Dòng cầu thủ còn lại | 29.725 | 27.283 |
| Player ID riêng trong mùa | 865 | 784 |
| Fixture có dữ liệu cầu thủ | 380 | 380 |
| Fixture có đúng 11 `starts=1` mỗi phía | 380 | 380 |
| Trùng khóa `(element, fixture)` | 0 | 0 |
| Dòng có minutes=0 | 18.341 | 15.717 |

Các dòng minutes=0 cho thấy đây là bảng player–fixture chứa cả người không thi đấu, không phải danh sách appearances thuần túy. ID cầu thủ riêng trong mùa cũng không bằng số cầu thủ thực sự đã ra sân. Không được lấy tất cả người có dòng trong một fixture làm Starting XI.

`AM` là nhóm Assistant Manager. Premier League đã đưa cơ chế này vào FPL 2024–2025. [Giới thiệu chính thức](https://www.premierleague.com/en/news/4230266). Pipeline chỉ giữ GK/DEF/MID/FWD; vị trí không nhận diện được sẽ gây lỗi thay vì bị âm thầm bỏ qua.

Sau khi bỏ AM, các trường element, fixture, minutes, goals_scored, assists, starts, expected_goals, expected_assists và value không có giá trị null trong hai tệp này. Các thống kê số đã kiểm tra không âm, starts chỉ là 0/1. Điều này chứng minh có trường và không thiếu ở hai mùa được tải; không chứng minh xG/xA có cùng độ phủ ở các mùa cũ hoặc mọi giá trị là ground truth độc lập.

Không có ngày sinh hoặc market value trong hai tệp player–fixture này. `value` là giá FPL, không được đổi tên thành giá trị thị trường. `xP`, total_points, bonus, bps, các điểm số cùng trận và các trường modified không được tự coi là thông tin trước trận. Hỗ trợ xG/xA ở hai mùa này là phát hiện mới so với nghiên cứu chỉ dựa trên tài liệu.

**Starting XI:** đủ 22 người được đánh dấu đá chính trong mỗi trận, nhưng `starts` được ghi nhận sau trận. Chưa có chứng cứ timestamp hoặc snapshot của đội hình đã công bố tại cutoff. Vì vậy chưa đạt yêu cầu announced XI T−60. Có thể dùng các starts của trận cũ sau khi có dữ liệu để tính continuity trong quá khứ; không dùng starts của trận mục tiêu để chọn XI trong mô hình T−60 chính.

## 4. Kết hợp hai nguồn

Đã ghép **380/380 trận cho từng mùa**, tổng 760 trận, bằng ngày theo Europe/London và tên đội chuẩn hóa. Không có trận thừa ở một phía; tỷ số cuối trận giữa Football-Data và FPL fixtures khớp ở toàn bộ các cặp, chỉ dùng việc này để kiểm tra chất lượng, không tính hiệu năng dự đoán.

Mapping rõ ràng: Man Utd → Man United; Spurs → Tottenham; Sheffield Utd → Sheffield United. Không fuzzy-match tự động. Kiểm tra nguồn cầu thủ với fixture: không lệch opponent ID, tên CLB hoặc kickoff nội bộ FPL; không có fixture ID thiếu.

ID đội/cầu thủ phải gắn mùa; không dùng một external ID cho toàn bộ lịch sử. CLB của cầu thủ được suy từ fixture và was_home, rồi đối chiếu tên; không lấy CLB hiện tại của cầu thủ để khôi phục quá khứ. Chưa xây cross-season player identity map trong đợt này.

## 5. Hai chênh lệch giờ có ý nghĩa phương pháp

| Trận | Ngày | Football-Data (giờ Anh) | FPL (đổi về giờ Anh) |
|---|---|---|---|
| Arsenal – Nottingham Forest | 12/08/2023 | 12:30 | 13:00 |
| Ipswich – Everton | 19/10/2024 | 15:00 | 15:15 |

Thông tin trận đầu bị lùi 30 phút được xác nhận trong [bài của Premier League](https://www.premierleague.com/es/news/3627475). Ipswich công bố trận thứ hai chuyển sang 15:15 trong [thông báo CLB](https://www.itfc.co.uk/news/2024/october/19/everton-kick-off-delayed/).

**Diễn giải:** FPL đang phản ánh giờ cập nhật muộn hơn trong hai trường hợp này. Nếu lấy FPL kickoff rồi trừ 60 phút, cutoff sẽ trễ hơn 30 hoặc 15 phút so với lịch ban đầu. Đây là rủi ro đưa thông tin phát sinh sát trận vào dự đoán quá khứ.

**Quyết định:** giữ cả `fd_kickoff_utc_assuming_London`, `fpl_recorded_kickoff_utc` và `time_conflict`. Không tự sửa một nguồn bằng nguồn kia. Chưa gán verified cho lịch được biết tại thời điểm dự đoán; thông báo xác minh việc lùi giờ chưa đủ cung cấp lịch sử đầy đủ mọi phiên bản. Phép đổi giờ Football-Data theo Europe/London khớp 379/380 trận mỗi mùa, là bằng chứng nhất quán thực nghiệm, không phải bằng chứng riêng về thời điểm công bố.

## 6. Quyết định go/no-go

| Hạng mục | Quyết định sau audit |
|---|---|
| A với form/Elo/thống kê lịch sử | GO triển khai dữ liệu; ba mùa thí điểm đạt kiểm tra cấu trúc |
| Ghép FPL với Football-Data | GO cho hai mùa đã audit; chưa suy rộng toàn bộ lịch sử |
| C với phút/goals/assists lagged | Khả thi kỹ thuật; cần audit mùa train, mapping xuyên mùa và availability policy |
| C thêm xG/xA | Có dữ liệu hai mùa; chưa đủ cơ sở chọn khoảng train |
| B/C dùng announced XI T−60 | NO-GO vào mô hình chính lúc này: thiếu timestamp/snapshot |
| Tuổi XI và market value | Chưa đủ dữ liệu trong mẫu; không giả lập hoặc thay bằng giá FPL |
| Dữ liệu chấn thương/treo giò | Chưa được thu thập hoặc kiểm chứng |

GO ở đây là quyết định kỹ thuật trên dữ liệu thí điểm, không phải tuyên bố mọi quyền tái sử dụng/tái phân phối đã được giải quyết. Các nguồn miễn phí và raw vẫn giữ provenance, không được đóng gói phát hành như dữ liệu tự sở hữu.

Không tải bulk Transfermarkt trong đợt này: nguồn FPL đã trả lời được câu hỏi kỹ thuật về khả năng ghép trận, stats và actual starters; điều kiện sử dụng và PIT của Transfermarkt vẫn chưa được giải quyết. Không coi công việc đó là đã hoàn thành.

## 7. Kiểm thử và bảo vệ test

Đã chạy **9/9 kiểm thử đạt**: định dạng ngày; lịch round-robin; mâu thuẫn kết quả/bàn thắng; trùng trận; lọc manager và không nhầm actual XI với announced XI; trùng player-fixture; vị trí lạ; alias và lệch kickoff; join trận mơ hồ.

Tests dùng dữ liệu tổng hợp có ghi chú riêng, không đưa vào tập nghiên cứu. Raw thật được xác minh SHA-256 mỗi lần audit. Đây là kiểm thử cho giai đoạn audit, chưa phải bộ leakage tests của feature builder.

Đã đọc nhãn test 2024–2025 chỉ để kiểm tra hợp lệ và đối chiếu kết quả giữa hai nguồn. Chưa thống kê phân phối H/D/A, chưa đo baseline, chưa huấn luyện, chưa tuning và chưa tính model metrics trên test. Không gọi đây là test chưa từng được đọc; cách mô tả chính xác là test chưa được sử dụng để phát triển hoặc đánh giá mô hình.

## 8. Bước triển khai tiếp theo

1. Mở rộng Football-Data cho các mùa train còn thiếu và warm-up, theo lịch tải nhẹ; giữ cache.
2. Chuẩn hóa matches/outcomes, source ID và hai loại timestamp, giữ unknown nơi chưa có chứng cứ.
3. Xây feature builder A: form 5/10, Elo, home/away form, sporting PPG và days_since_last_PL_match.
4. Viết leakage tests thay đổi tương lai/hiện tại, prefix invariance và batch cùng thời điểm.
5. Trước B/C, audit FPL các mùa train và nguồn announced XI riêng. Nếu không đạt, dùng nhánh player-history proxy, không tự đổi nghĩa đề tài.

Chưa bắt đầu huấn luyện mô hình trong giai đoạn này.
