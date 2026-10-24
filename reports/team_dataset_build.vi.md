# Hoàn thành dữ liệu cấp đội và feature builder A

Ngày: **24/10/2026, Asia/Saigon**. Chưa huấn luyện mô hình; các số sau là kiểm tra dữ liệu và phần mềm.

## Dữ liệu đã hoàn tất

Đã tải đủ 12 mùa EPL từ 2013–2014 đến 2024–2025. Tái sử dụng ba tệp thí điểm, chỉ tải chín tệp còn thiếu một lần. Raw có SHA-256, URL và thời điểm tải trong [manifest](../research/download_manifest.json).

| Phần | Mùa | Số trận sau kiểm tra |
|---|---|---:|
| Warm-up | 2013–2014 → 2014–2015 | 760 |
| Train | 2015–2016 → 2022–2023 | 3.040 |
| Validation | 2023–2024 | 380 |
| Test | 2024–2025 | 380 |
| Tổng | 12 mùa | 4.560 |

Tất cả mùa sau xử lý có 380 trận, 20 đội, mỗi đội 19 sân nhà/19 sân khách, không trùng khóa trận và nhãn nhất quán bàn thắng. Đây là structural QA; không tuyên bố đã đối chiếu từng thống kê với biên bản trận chính thức.

## Hai phát hiện và quyết định xử lý

1. **2014–2015:** CSV được đọc thành 381 dòng do một dòng hoàn toàn rỗng. Chỉ loại dòng mà toàn bộ cột trống, giữ nguyên raw; không drop mọi dòng thiếu một trường. Không có trận thật bị loại.
2. **2019–2020:** 66 trận nằm sau 30/6/2020. Quy tắc ngày kết thúc mùa cũ sai với mùa bị gián đoạn COVID. Đã thêm ngoại lệ lịch có nguồn, chấp nhận đến 26/7/2020; không đổi nhãn mùa theo tháng và không bỏ các trận tháng 7. [Lịch xác nhận của Premier League](https://www.premierleague.com/en/news/1702418).

Các mùa 2013–2014 đến 2018–2019 không có giờ thi đấu; từ 2019–2020 đến 2024–2025 có đủ trường giờ. Tổng 2.280 trận có giờ archive và 2.280 trận chỉ có ngày, gồm cả warm-up. Tình trạng giờ được lưu riêng, không giả định giờ thiếu.

## Đầu ra và logic feature

Đã tạo **40 đặc trưng**: 18 cho mỗi phía và 4 biến chung. Bao gồm form 5/10 trận, Elo, phong độ sân nhà/sân khách, sporting points/PPG/GD trước trận, số trận hỗ trợ, khoảng cách giữa các trận EPL, cờ đội mới/thiếu lịch sử và H2H. [Từ điển chi tiết](../docs/team_feature_dictionary.vi.md), [config](../research/team_feature_config.json).

Phiên bản đầu dùng **toàn bộ lịch sử trước ngày thi đấu**, không dùng kết quả cùng ngày. Snapshot ở 00:00 Europe/London, đổi sang UTC đúng DST. Không lấy giờ trận sau cập nhật của FPL để dịch cutoff. Lựa chọn này làm đồng nhất các mùa thiếu giờ và hạn chế leakage, nhưng bỏ bớt thông tin hợp lệ từ các trận sớm trong cùng ngày.

Availability của kết quả vẫn là giả định tái dựng: ngày D được dùng từ midnight ngày D+1. Các kiểm thử chứng minh code tuân thủ chính sách này, không chứng minh nhà cung cấp đã công bố mọi số liệu đúng thời điểm lịch sử. Vẫn chưa đạt xác minh feed T−60 nghiêm ngặt.

Elo initial=1500, promoted prior=1400, K=20, home advantage=65, retention đầu mùa=0.75 là tham số đặt trước, chưa tuning. Không hứa đây là lựa chọn tối ưu. Rolling của đội mới lên hạng được reset; historical PL last-date vẫn giữ nếu đã biết. Season counters reset theo season label.

## Dữ liệu đã lưu

Tại `D:\premier-league-ml\data\curated`:

- `matches.csv`: định danh, mùa, đội, ngày, các timestamp và provenance; không chứa bàn thắng/nhãn.
- `match_outcomes.csv`: bàn thắng, H/D/A và assumed availability; tách khỏi input.
- `split_manifest.csv`: match ID và tập đã đăng ký.
- `feature_lineage_A.csv`: thời điểm snapshot, cận trên thời gian nguồn, phiên bản feature và trạng thái giả định.
- `features_A_train.csv`, `features_A_validation.csv`, `features_A_test.csv`, `features_A_warmup.csv`: match ID và đúng 40 biến trong allowlist.

CSV được chọn cho quy mô nhỏ và khả năng kiểm tra trực tiếp; chưa yêu cầu thêm Parquet dependency. Không đưa file raw/curated vào Git. Kết quả audit từng mùa, missing và code/config hash ở [team_dataset_build.json](team_dataset_build.json).

Missing có ý nghĩa được giữ nguyên. Ví dụ trong train: home_form5_ppg thiếu 16 dòng và away_form5_ppg thiếu 8 dòng do khởi tạo đội mới; H2H PPG thiếu 218 trận vì chưa có đối đầu trong kho lịch sử. Không điền bằng dữ liệu tương lai hoặc lấy mean từ toàn bộ dataset. Preprocessing sẽ fit riêng trong từng train fold.

## Bằng chứng kiểm thử

**23/23 unit tests đạt**, gồm 9 tests audit có sẵn và 14 tests feature mới: tính tay rolling/Elo, current/future outcome invariance, prefix invariance, hoán vị đầu vào, batch cùng ngày, H2H theo đúng phía, đầu mùa/đội trở lại, DST, metadata/allowlist, cleanup và ngoại lệ lịch 2019–2020.

**4 kiểm tra tích hợp trên dữ liệu thật đạt:**

1. Xây riêng warm-up + train cho cùng feature với phần tương ứng khi chạy toàn bộ 12 mùa.
2. Thay toàn bộ bàn thắng mùa test bằng giá trị kiểm thử trong bộ nhớ không làm thay đổi feature warm-up/train/validation.
3. Feature được xuất ra tệp trùng với xây lại bằng phiên bản code hiện tại, trong sai số số thực quy định.
4. Đúng 4.560 dòng, đúng split và allowlist 40 biến; không lẫn nhãn vào ma trận feature.

Không sửa raw khi kiểm tra can thiệp. Các con số can thiệp là dữ liệu test trong bộ nhớ, không phải kết quả bóng đá. Hash các output và trạng thái kiểm tra lưu trong [team_dataset_verification.json](team_dataset_verification.json).

## Bước kế tiếp

Model A đã có dữ liệu và bộ feature tái lập được để bắt đầu development. Bước tiếp theo: baseline tần suất/Elo ba lớp, Logistic Regression với preprocessing train-only, expanding-window validation; sau đó Random Forest và một boosting model. Chưa tính metric mô hình trên test.

B/C không được xem là hoàn tất: audit FPL hiện chỉ có hai mùa cuối; chưa có mapping cầu thủ xuyên mùa, tuổi, market value hoặc announced XI tại cutoff.
