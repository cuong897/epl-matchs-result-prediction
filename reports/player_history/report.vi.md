# Audit dữ liệu cầu thủ lịch sử và quyết định phạm vi P

**Ngày:** 24/10/2026. Chỉ dùng nguồn miễn phí. Bước này không huấn luyện mô hình và không đọc thống kê cầu thủ mùa test để phân tích kết quả dự đoán.

Đã tải thêm 16 CSV lịch sử; 5 đường dẫn tùy chọn trả 404. API GitHub trả giới hạn truy cập, nên chưa lấy được commit nguồn: các URL raw dùng `master`, còn nội dung tải thực tế được cố định bằng SHA-256 trong download_manifest.json. 404 chỉ chứng minh đường dẫn đã kiểm tra không tồn tại, không chứng minh không có dữ liệu ở nơi khác.

## Độ phủ đo được

| Mùa | Dòng cầu thủ raw | Fixture ID trong bảng cầu thủ | Chuẩn hóa/ghép với dữ liệu đội | Starts và xG/xA |
|---|---:|---:|---|---|
| 2016–2017 | 23.679 | 380 | Chưa: thiếu fixtures.csv và teams.csv ở đường dẫn kiểm tra | Không có cột |
| 2017–2018 | 22.467 | 380 | Chưa: thiếu fixtures.csv và teams.csv ở đường dẫn kiểm tra | Không có cột |
| 2018–2019 | 21.790 | 380 | Chưa: thiếu teams.csv ở đường dẫn kiểm tra | Không có cột |
| 2019–2020 | 22.560 | 380 | Đủ 380 trận; còn 22.501 dòng sau loại placeholder | Không có cột |
| 2020–2021 | 24.365 | 380 | Đủ 380 trận | Không có cột |
| 2021–2022 | 25.447 | 380 | Đủ 380 trận | Không có cột |
| 2022–2023 | 26.505 | 380 | Đủ 380 trận | Có cột nhưng 136 trận không dùng được |
| 2023–2024 | 29.725 | 380 | Đủ 380 trận, tái sử dụng cache đã tải | Không thiếu ô; đủ 22 recorded starts mỗi trận |

Tổng bảng chuẩn hóa development: **128.543 dòng cầu thủ–trận, 1.900 trận**, gồm 1.520 trận training 2019–2020 đến 2022–2023 và 380 trận validation 2023–2024. Cả 100 tổ hợp đội–mùa có 38 trận. Mỗi phía trận có ít nhất 11 người được ghi nhận phút thi đấu; kiểm tra này hỗ trợ phát hiện thiếu nghiêm trọng, không chứng minh mọi dòng roster dự bị đều đầy đủ.

Ba mùa 2016–2019 cần fallback Latin-1 khi đọc; chưa khẳng định đây là encoding gốc. Không dùng tên cầu thủ để ghép ID. Có thể nghiên cứu thêm mapping để mở rộng sau, nhưng chưa coi các mùa này đủ điều kiện cho P trong phạm vi hiện tại. Mùa 2015–2016 không nằm trong bộ lịch sử cầu thủ đang kiểm tra.

## Các lỗi quan trọng đã xử lý

**1. Trận hoãn bị ghi hai lần dưới cùng fixture ID.** Mùa 2019–2020 có 59 khóa player–fixture lặp tại fixture 275. Bản ngày 11/03/2020 có minutes=0 và cả hai tỷ số trống; bản trận diễn ra ngày 17/06/2020 có dữ liệu thực tế. Premier League xác nhận [hoãn trận ngày 11/03](https://www.premierleague.com/en/news/1643922) và [lịch đấu lại ngày 17/06](https://www.premierleague.com/en/news/1676717).

Chỉ loại 59 placeholder khi khớp đầy đủ quy tắc có tài liệu: đúng fixture/ngày, không có phút hoặc tỷ số, và từng cầu thủ có bản thay thế ở trận diễn ra. Không dùng `drop_duplicates(keep='last')` tùy tiện. Raw được giữ nguyên; dòng nguồn bị loại được ghi trong audit.json. Việc chuẩn hóa lịch hồi cứu không có nghĩa lịch mới đã biết tại thời điểm lịch cũ.

**2. Có cột không có nghĩa có dữ liệu.** Trong 136 trận đầu mùa 2022–2023, tổng starts, xG và xA của toàn bộ cầu thủ đều bằng 0. Chỉ 244/380 trận có đủ 22 recorded starts; trận đầu tiên trong nhóm này diễn ra ngày 12/11/2022. Bộ ba giá trị toàn trận bằng 0 được đánh dấu `fixture_wide_zero_starts_xg_xa_unusable` và chuyển thành missing ở bảng chuẩn hóa, giữ nguyên raw. Giá trị 0 hợp lệ của một cầu thủ trong trận có dữ liệu vẫn được giữ. Do lịch sử không đồng nhất, P phiên bản đầu loại starts/xG/xA khỏi allowlist.

**3. Giờ giữa các bảng không luôn trùng.** Mùa 2021–2022 có 78 dòng ở fixture 263 ghi 15:00 UTC trong bảng cầu thủ và 15:30 UTC trong bảng fixture cùng ngày 26/02/2022. Giữ cả hai giờ, gắn cờ lệch cùng ngày; không tự biến giờ hồi cứu thành giờ đã công bố trước trận. Các khác biệt với Football-Data cũng nằm trong fixture_links.csv. Quy tắc dùng lịch sử trước ngày hiện tại không bị ảnh hưởng bởi chênh lệch trong cùng ngày.

## Những gì có thể và chưa thể dùng

- **Dùng được có điều kiện:** minutes, goals_scored, assists lịch sử từ 2019–2020, ID cầu thủ trong phạm vi mùa, đội tại trận được suy ra từ fixture và was_home. Không lấy đội cuối mùa của cầu thủ làm đội ở quá khứ.
- **Assists là thống kê FPL**, không mặc định cùng định nghĩa với kiến tạo của mọi nhà cung cấp khác.
- **ID cầu thủ chỉ có hiệu lực trong mùa.** Chưa giải quyết identity xuyên mùa; trạng thái cầu thủ phải reset đầu mùa trong phiên bản đầu.
- **Không có market value hoặc ngày sinh** trong các bảng đã tải. Cột value là giá FPL, không phải định giá chuyển nhượng; không đưa vào nghiên cứu market value.
- **Chưa xác minh announced XI ở T−60**. Starts là thông tin tham gia trận đã diễn ra, không chứng minh đội hình đã được công bố trước cutoff. Không dùng current-match starts/minutes để chọn người.
- Không có injury/suspension history có bằng chứng thời gian trong nguồn này. Không suy diễn “không ra sân” thành chấn thương.
- Dữ liệu lưu hiện nay có thể đã được sửa hồi cứu. `available_at_assumed_utc` là giả định nửa đêm Europe/London kế tiếp sau ngày trận; trạng thái luôn `reconstructed_assumption`, không phải timestamp nguồn đã xác minh.
- [Kho tác giả](https://github.com/vaastav/Fantasy-Premier-League) và [LICENSE](https://github.com/vaastav/Fantasy-Premier-League/blob/master/LICENSE) không được diễn giải thành quyền tái phân phối vô điều kiện dữ liệu upstream. Chỉ lưu raw cục bộ, không đưa raw/curated vào Git; không công bố lại dataset tại bước này.

## Phạm vi thực nghiệm đề xuất sau audit

Chọn **P — đặc trưng sử dụng cầu thủ từ quá khứ** làm nhánh mở rộng khả thi. P chưa trả lời được giả thuyết về đội hình xuất phát chính thức hoặc market value; B/C theo định nghĩa ban đầu vẫn chưa đủ bằng chứng để triển khai.

| Thành phần | Phạm vi |
|---|---|
| A_full đã chạy | Training 2015–2023; giữ làm tham chiếu riêng |
| A_common và A+P | Cùng 1.520 trận training 2019–2023; cùng 380 trận validation 2023–2024 |
| Fold chọn tham số | Train 2019–2020 → 2020–2021; mở rộng đến 2020–2021 → 2021–2022; đến 2021–2022 → 2022–2023 |
| Số trận train mỗi fold | 380, 760, 1.140; mỗi fold đánh giá 380 trận |
| Đặc trưng A | Cùng 40 cột và cùng giá trị snapshot giữa hai nhánh; lịch sử cấp đội trước 2019 được giữ giống nhau |
| Đầu mùa P | Reset player-season ID, thiếu lịch sử được giữ missing và có cờ; không lấp từ tương lai |
| Test | Chưa tạo feature P hoặc mở metric test; chỉ thực hiện sau khi khóa thiết kế và các kiểm thử |

Phải **fit lại A_common** trên đúng cohort. Không so A_full được train 3.040 trận với A+P train 1.520 trận rồi quy chênh lệch hoàn toàn cho dữ liệu cầu thủ.

Nhóm P đầu tiên ưu tiên khoảng 8–12 đại lượng cấp đội: số người có phút được ghi nhận trong năm trận trước, mức tập trung phút thi đấu, tỷ trọng phút của 11 người được sử dụng nhiều nhất, sự liên tục của nhóm tham gia giữa các trận và giữa hai cửa sổ; các cờ số trận hỗ trợ. Chọn nhóm bằng dữ liệu trước cutoff, gọi đúng là nhóm được sử dụng nhiều, không gọi là starting XI dự đoán vì chưa áp quy tắc vị trí/roster.

Phong độ bàn/kiến tạo của từng người có thể là P mở rộng sau đó, nhưng cần kiểm tra mức trùng lặp với thống kê bàn cấp đội đã có. Không tăng số biến chỉ vì có sẵn. Thuật toán, cửa sổ, cách xử lý chuyển CLB và missing sẽ được ghi trong cấu hình trước khi tạo feature và đo metric P.

## Kiểm thử và sản phẩm

49 unit tests đã đạt, gồm 8 test mới về placeholder/ID/thời gian/missing và 2 test downloader mô phỏng 404/403, không gọi mạng. Downloader nhớ 404 của đường dẫn tùy chọn; 403 vẫn dừng nhà cung cấp, không retry để vượt chặn.

Kiểm tra trên dữ liệu thật xác nhận checksum bảng chuẩn hóa, tính duy nhất player–match, không có mùa test, đủ 38 trận cho mỗi đội–mùa, các trường performance bắt buộc không thiếu và 136 trận có advanced stats không dùng được đã được chuyển đúng sang missing.

```powershell
python scripts/download_pilot.py --catalog player_sources
python scripts/audit_player_history.py
python scripts/verify_player_history.py
python -m unittest discover -s tests -q
```

Các đầu ra: audit.json, coverage_by_team_season.csv, fixture_links.csv, artifact_verification.json. Bảng player_match_stats_P_development.csv nằm trong data/curated và được loại khỏi Git.
