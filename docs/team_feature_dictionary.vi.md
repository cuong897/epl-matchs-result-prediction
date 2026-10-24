# Từ điển 40 đặc trưng Model A — phiên bản v1

Phiên bản: `team_A_v1_day_batched`. Chỉ danh sách trong [feature_columns_A.json](../research/feature_columns_A.json) được phép đưa vào estimator. `match_id`, season, split, hash nguồn, cutoff và mọi cột kết quả đều là metadata/target, không phải input.

## Quy tắc thời gian

Với trận ngày D theo Europe/London, tạo snapshot lúc 00:00 ngày D và chỉ dùng kết quả các ngày < D. Không dùng kết quả trận sớm hơn trong cùng ngày, kể cả khi đã có giờ cụ thể. Các mùa thiếu giờ vẫn giữ cutoff T−60 là unknown; không tự gán giờ.

Giả định tái dựng: kết quả trận ngày D có thể dùng từ 00:00 ngày D+1. Đây là giả định khả dụng, không phải timestamp nguồn đã được chứng minh. `source_max_available_at_assumed_utc` phải không sau `feature_asof_utc`. Tính midnight theo lịch địa phương rồi đổi UTC để xử lý DST, không cộng cố định 24 giờ UTC.

Với trận có giờ archive, `prediction_cutoff_assumed_utc` = giờ Football-Data (giả định Europe/London) − 60 phút. Snapshot ngày phải không sau cutoff này. `kickoff_publication_status` vẫn unknown. Không thay bằng giờ FPL cập nhật sát/sau trận.

## 18 đặc trưng cho mỗi phía: home_ và away_

| Hậu tố | Ý nghĩa/công thức | Khi thiếu lịch sử |
|---|---|---|
| `form5_ppg` | Trung bình điểm trong tối đa 5 trận EPL trước đó, mọi sân | NaN |
| `form5_gf` | Bàn ghi trung bình trong cửa sổ trên | NaN |
| `form5_ga` | Bàn thua trung bình trong cửa sổ trên | NaN |
| `form10_ppg` | Trung bình điểm trong tối đa 10 trận EPL trước đó | NaN |
| `form10_gf` | Bàn ghi trung bình trong cửa sổ 10 | NaN |
| `form10_ga` | Bàn thua trung bình trong cửa sổ 10 | NaN |
| `history_n10` | Số trận hỗ trợ cửa sổ 10, từ 0 đến 10 | 0 |
| `venue5_ppg` | Điểm/trận trong tối đa 5 trận sân nhà (home) hoặc sân khách (away) trước đó | NaN |
| `venue_n5` | Số trận hỗ trợ venue5, từ 0 đến 5 | 0 |
| `season_matches` | Số trận đã hoàn thành trong mùa, tính đến trước ngày D | 0 ở đầu mùa |
| `season_points` | Tổng điểm thi đấu: 3 thắng + 1 hòa; không tính án trừ điểm | 0 ở đầu mùa |
| `season_ppg` | season_points / season_matches | NaN nếu chưa đá |
| `season_gd_per_game` | Hiệu số bàn thắng mùa hiện tại / số trận đã đá | NaN nếu chưa đá |
| `days_since_last_pl` | Số ngày lịch từ lần gần nhất xuất hiện trong EPL đã quan sát | NaN nếu chưa từng thấy |
| `newly_promoted` | 1 nếu không thuộc tập đội đã quan sát ở mùa EPL liền trước | NaN khi không có mùa trước |
| `prior_season_membership_known` | Có quan sát mùa EPL liền trước hay chưa | 0 nếu chưa có |
| `elo` | Rating tại snapshot, trước khi cập nhật kết quả ngày D | Prior được quy định bên dưới |
| `missing_history` | 1 khi chưa có trận hỗ trợ rolling trong trạng thái hiện tại | 1 |

Điểm cho một trận là 3/1/0. Khi có n<5/10 trận, dùng trung bình n trận đó và cung cấp số quan sát, không điền thêm trận giả. Không suy NaN thành 0 và chưa fit imputer ở giai đoạn này.

Rolling được mang qua các mùa liên tiếp ở EPL. Khi đội không có ở mùa EPL liền trước, reset rolling/venue để không coi phong độ từ vài năm trước là phong độ gần đây. `days_since_last_pl` vẫn giữ ngày EPL cuối cùng nếu đã biết, kể cả sau một khoảng vắng mặt; trường này không phải ngày nghỉ thực tế vì chưa có lịch cúp/Championship/châu Âu.

Trong dữ liệu thật, tất cả mùa trước trong giai đoạn train đều đã audit đủ; cờ promoted chỉ là suy luận từ membership EPL quá khứ, không lấy thứ hạng cuối mùa hiện tại. Không cần đọc danh sách đội cuối mùa tương lai để khởi tạo feature.

## Bốn đặc trưng chung

| Tên | Ý nghĩa |
|---|---|
| `elo_diff` | home_elo − away_elo |
| `rest_days_diff` | home_days_since_last_pl − away_days_since_last_pl; NaN nếu một phía chưa biết |
| `h2h_home_ppg5` | Điểm/trận của đội đang là home trong tối đa 5 lần hai đội gặp nhau trước ngày D, bất kể sân |
| `h2h_n5` | Số trận hỗ trợ H2H; 0 khi chưa có, còn ppg để NaN |

H2H chỉ từ các mùa EPL đã tải, có thể xa về thời gian; chưa decay theo tuổi dữ liệu. Đây là nhánh cần ablation trên development, không mặc định hữu ích. Elo và Elo difference có tương quan tuyến tính; regularization và ablation cần được thực hiện khi huấn luyện, không lựa chọn theo test.

## Elo: tham số mặc định đã ghi trước khi huấn luyện

- Khởi tạo đầu kho lịch sử: 1500.
- Đội không thuộc mùa EPL liền trước: 1400.
- K = 20; home advantage = 65 điểm.
- Đầu mùa: `1500 + 0.75 × (rating − 1500)` cho đội đã biết; sau đó entrant được gán prior riêng.
- Expected score chủ nhà: `1 / (1 + 10 ** ((R_away − R_home − 65) / 400))`.
- Actual score: thắng 1, hòa 0.5, thua 0.
- Sau snapshot: `delta = 20 × (actual − expected)`; cộng delta cho home, trừ delta cho away.

Đây là **lựa chọn thiết kế chưa tối ưu**, không phải tham số đã chứng minh phù hợp EPL. Nếu điều chỉnh, chỉ dùng temporal folds trong train, lưu phiên bản config mới và xây lại features. Expected score Elo không được dùng trực tiếp như xác suất H/D/A.

## Thứ tự cập nhật và ranh giới mùa

Sắp theo ngày thực tế; các trận cùng ngày tạo features trên cùng trạng thái. Chỉ sau khi tạo toàn bộ snapshot ngày đó mới cập nhật outcomes. Đổi thứ tự dòng không thay đổi kết quả. Reset season counters theo nhãn mùa của nguồn, không dựa vào tháng: mùa 2019–2020 có trận tháng 7/2020.

Hai mùa 2013–2014 và 2014–2015 chỉ khởi tạo state; không được đưa vào tập train đã đăng ký 2015–2023. Khi xử lý validation/test, state có thể cập nhật từ các trận trước đã kết thúc theo chính sách ngày; không có estimator nào được fit trong quá trình này.

## Các giới hạn được giữ rõ

Chưa có shots/SOT rolling, official rank, chấn thương, đội hình cầu thủ hoặc odds trong v1. Chưa có trọng số theo độ mới của H2H, shrinkage rolling hay hiệu chỉnh COVID/home advantage theo thời kỳ. Không có scaler, imputer, feature selection hoặc mô hình dự đoán được fit. Các bước đó thuộc development sau này và phải fit trong train fold.
