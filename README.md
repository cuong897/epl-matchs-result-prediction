# Premier League — dự đoán xác suất H/D/A

Trạng thái ngày 24/10/2026: **đã hoàn thành vòng test cuối Premier League 2024–2025**, sau khi khóa mô hình, calibration, feature và mã scoring bằng checksum. Đã đánh giá đủ 380 trận, 30 đầu ra xác suất từ 14 estimator và hai baseline tần suất; không refit hoặc tune bằng test.

Kết quả tham chiếu Elo A_full đã chọn trước test: Accuracy 54,74%; Log Loss raw 0,98141, temperature 0,98606; Brier raw 0,58654, temperature 0,58993. Temperature làm Log Loss test tăng ở cả 14 mô hình. Chưa có bằng chứng chắc chắn P/F cải thiện trong các contrast chính; xem diễn giải và giới hạn bên dưới. Bước tiếp theo là báo cáo học thuật, notebook tái lập và demo, không chỉnh mô hình từ test.

- Ngân sách dữ liệu: chỉ nguồn miễn phí.
- Mục tiêu: dự đoán từng trận tại khoảng 60 phút trước giờ bóng lăn.
- [Báo cáo khả thi, nguồn dữ liệu, thiết kế và lộ trình](docs/feasibility-plan.vi.md).
- [Protocol dự kiến để khóa trước thực nghiệm](research/protocol.json).
- [Kết quả audit mẫu và các quyết định dữ liệu](reports/pilot_audit.vi.md).
- [Số liệu kiểm tra máy đọc được](reports/pilot_audit.json).
- [Nguồn, thời điểm tải và SHA-256](research/download_manifest.json).
- [Kết quả xây bộ dữ liệu cấp đội](reports/team_dataset_build.vi.md).
- [Từ điển 40 đặc trưng và giả định thời gian](docs/team_feature_dictionary.vi.md).
- [Kết quả Model A, độ bất định và phân tích lỗi](reports/model_A_development/report.vi.md).
- [Cấu hình thực nghiệm đăng ký trước lần chạy đầu](research/model_A_development_config.json).
- [Kiểm chứng mô hình đã lưu](reports/model_A_development/artifact_verification.json).
- [So sánh Random Forest/XGBoost và phân tích lỗi](reports/A_trees_v1/report.vi.md).
- [Log tiến trình lượt cây đã chạy](reports/A_trees_v1/console_excerpt.txt).
- [Cấu hình, thời điểm bắt đầu và hash lượt cây](reports/A_trees_v1/run_manifest.json).
- [Audit lịch sử cầu thủ và phạm vi A/P](reports/player_history/report.vi.md).
- [Định nghĩa và giới hạn 12 đặc trưng P](docs/player_proxy_dictionary.vi.md).
- [Kết quả so sánh A_common với A+P](reports/AP_dev_v1/report.vi.md).
- [Log huấn luyện A/P](reports/AP_dev_v1/progress.log).
- [Định nghĩa tám biến performance F](docs/player_performance_dictionary.vi.md).
- [Kết quả A+P+F và đối chứng giữ nguyên](reports/APF_dev_v1/report.vi.md).
- [Log huấn luyện A+P+F](reports/APF_dev_v1/progress.log).
- [Quyết định kết thúc exploration và bước trước test](docs/development_decisions.vi.md).
- [Protocol vòng cuối, ghi trước test](docs/final_evaluation_protocol.vi.md).
- [Kết quả test đầy đủ](reports/final_test_v1/report.vi.md).
- [Diễn giải kết quả và giới hạn kết luận](reports/final_test_v1/findings.vi.md).
- [Log vòng test đã khóa](reports/final_test_v1/progress.log).
- [Kiểm chứng artifact vòng cuối](reports/final_test_v1/artifact_verification.json).

Đã audit dữ liệu cầu thủ 2016–2024 và chuẩn hóa 128.543 dòng/1.900 trận từ 2019–2024. Phát hiện và loại 59 placeholder trận hoãn; đánh dấu starts/xG/xA không dùng được ở 136 trận đầu mùa 2022–2023. Đã tạo P và fit lại A_common/A+P trên cùng 1.520 trận training, cùng 380 trận validation. B/C vẫn có điều kiện; FPL starts chưa phải announced XI tại T−60.

Thêm P chưa cải thiện Log Loss rõ ràng: Logistic +0,002024; RF +0,001476; XGBoost −0,000579 (A+P trừ A_common). Cả chín khoảng bootstrap 95% theo block 1/2/4 tuần đều chứa 0. XGBoost tăng Accuracy từ 56,58% lên 58,16%, nhưng chưa đủ kết luận P cải thiện xác suất.

Trên validation, nhánh performance F cũng chưa cải thiện rõ: so với A+P, Logistic +0,008985; RF −0,000744; XGBoost −0,000146 Log Loss. Mức cải thiện của hai mô hình cây nhỏ và mọi khoảng chứa 0; Logistic kém hơn trên ước lượng điểm, mức chắc chắn nhạy với block bootstrap. Sau mốc này đã dừng exploration, fit 14 temperature trên validation và thực hiện vòng test theo cấu hình khóa trước scoring.

Validation A_full: Elo có Log Loss 0,9285; Random Forest 0,9299; XGBoost 0,9388; Logistic A 0,9417; tần suất lịch sử 1,0541. RF/XGBoost đạt Accuracy 57,89% nhưng chưa vượt Elo về Log Loss; recall lớp hòa vẫn bằng 0. Đây là kết quả development trên phạm vi training khác với A_common, chưa phải kết luận cuối của đề tài.

## Chạy lại kiểm tra (không cần mạng khi đã có raw cache)

```powershell
Set-Location 'D:\premier-league-ml'
python -m unittest discover -s tests -v
python scripts/audit_pilot.py
python scripts/build_team_dataset.py
python scripts/verify_team_dataset.py
```

Nếu dùng môi trường mới, cài các phiên bản đã kiểm tra trong requirements-audit.txt. Runtime hiện tại: Python 3.13.5.

## Kiểm chứng và dựng lại báo cáo test

```powershell
python -m unittest discover -s tests -q
python scripts/report_final_test.py
```

81 unit tests đã đạt. Report kiểm tra checksum, nạp lại mô hình và tái tạo 11.400 xác suất, metric và confusion matrices; không fit lại. run_final_test.py từ chối ghi đè vòng đã có. final_lock.json được commit trước scoring. Các lệnh xây dữ liệu/huấn luyện bên dưới mô tả các giai đoạn trước: không thay đổi artifact đã khóa rồi gọi đó là cùng run cuối.

## Chạy lại development mô hình

```powershell
python -m pip install -r requirements-modeling.txt
python scripts/train_model_A.py
python scripts/report_model_A.py
```

Runner chỉ fit trên training và đánh giá validation; không nạp features_A_test.csv. Lệnh training ghi lại run A_dev_v1, vì vậy cần lưu run cũ trước khi đổi cấu hình. Lệnh report không huấn luyện lại: kiểm tra hash, nạp mô hình đã lưu, đối chiếu dự đoán/metric rồi tạo báo cáo và biểu đồ.

Lượt cây dùng CPU local, n_jobs=2, XGBoost 3.4.1. Đã thử bốn cấu hình cho mỗi thuật toán trên ba fold training. Không sử dụng GPU.

```powershell
python -u scripts/train_model_A_trees.py 2>&1 | Tee-Object -FilePath training-trees.log
python scripts/report_model_A_trees.py
```

Runner cây từ chối ghi đè thư mục run đã tồn tại. Muốn chạy thí nghiệm mới cần đăng ký run ID mới và cập nhật đường dẫn báo cáo; không xóa run cũ. Script report hiện trỏ tới A_trees_v1 và có thể chạy lại độc lập.

Git lưu mã, cấu hình và báo cáo; loại trừ raw, curated, models và .deps. Commit theo mốc hoàn thành, không thêm Co-authored-by. Giữ nguyên byte xuống dòng bằng .gitattributes để checksum audit ổn định giữa các lần checkout.

## Chạy nhánh A/P

```powershell
python scripts/audit_player_history.py
python scripts/verify_player_history.py
python scripts/build_player_proxy.py
python -u scripts/train_AP.py
python scripts/report_AP.py
```

Nhánh A/P chỉ nạp feature training/validation, không tạo P cho test. Runner từ chối ghi đè AP_dev_v1 đã tồn tại. Báo cáo có thể dựng lại bằng report_AP.py mà không fit lại; log tiến trình được lưu trong thư mục run. Cả hai nhánh có cùng ba fold, bốn ứng viên mỗi thuật toán, tổng 72 lượt fit CV; chọn tham số riêng cho mỗi nhánh bằng training CV.

## Chạy nhánh performance F

```powershell
python scripts/build_player_performance.py
python -u scripts/train_APF.py
python scripts/report_APF.py
```

Runner chỉ fit nhánh A+P+F, với 36 lượt CV và ba fit cuối; tái sử dụng đối chứng đã khóa từ AP_dev_v1 sau khi kiểm tra checksum/cohort/nhãn/metric. Không ghi đè run có sẵn. F có năm kiểm tra thời gian trên dữ liệu thật; bundle, estimator riêng và XGBoost native đều tái tạo đúng dự đoán. Dùng CPU local, không dùng GPU.

## Tải mẫu

```powershell
Set-Location 'D:\premier-league-ml'
python scripts/download_pilot.py
python scripts/download_pilot.py --catalog team_sources --provider football_data_co_uk
```

Downloader đọc catalog cố định (pilot_sources, team_sources hoặc player_sources), bỏ qua tệp có checksum đúng, không ghi đè raw, không tự thử lại khi nguồn lỗi/chặn. Đường dẫn player tùy chọn trả 404 được ghi nhớ; 403 vẫn dừng nhà cung cấp. Không xóa cache để tải lại thường xuyên. Raw được loại khỏi Git; không có giấy phép dự án nào mặc nhiên tái cấp phép dữ liệu bên thứ ba.

## Logic kiểm tra

- `download_pilot.py`: tải một lần, kiểm tra CSV sơ bộ, lưu metadata và SHA-256.
- `audit_pilot.py`: đọc cache đã xác minh hash; kiểm tra mùa, trận, bàn thắng/nhãn; tách AM khỏi cầu thủ; ánh xạ đội bằng bảng rõ ràng; ghép một-một theo ngày và cặp đội; giữ cả hai giờ khi không khớp.
- `test_audit.py`: 9 kiểm thử dùng dữ liệu giả chỉ trong tests, không trộn vào dữ liệu nghiên cứu.
- `team_features.py`: tạo snapshot trước khi cập nhật kết quả cả ngày; Elo, rolling và H2H chỉ dùng quá khứ.
- `build_team_dataset.py`: audit 12 mùa, chỉ bỏ dòng hoàn toàn trống, tách outcomes, xuất 4 split và lineage.
- `test_team_features.py`: 14 kiểm thử feature và thời gian.
- `test_modeling.py`: 12 kiểm thử về thứ tự nhãn, metric, preprocessing, chronological folds và bootstrap.
- `test_tree_modeling.py`: 4 kiểm thử mapping nhãn, float32, preprocessing và tính đầy đủ các fold; tổng 39 unit tests đã đạt.
- `test_player_history.py` và `test_download_optional.py`: thêm 10 kiểm thử lịch sử cầu thủ và phản hồi nguồn; tổng hiện tại 49 unit tests đã đạt.
- `audit_player_history.py` và `verify_player_history.py`: xử lý placeholder có tài liệu, phát hiện fixture-wide zeros, chuẩn hóa đội tại trận và kiểm chứng lịch sử development; không đọc thống kê cầu thủ test.
- `test_player_proxy.py`: thêm 12 kiểm thử tính tay và thời gian; tổng hiện tại 61 unit tests đã đạt.
- `player_proxy_features.py` và `build_player_proxy.py`: snapshot theo ngày, reset đầu mùa, lineage và bốn kiểm tra invariance trên dữ liệu thật.
- `train_AP.py` và `report_AP.py`: so sánh cùng cohort, lưu manifest trước fit, kiểm chứng mô hình nạp lại và báo cáo cả kết quả không cải thiện.
- `test_player_performance.py` và `test_apf_comparators.py`: thêm 12 kiểm thử performance và đối chứng cố định; tổng hiện tại 73 unit tests đã đạt.
- `player_performance_features.py`, `build_player_performance.py`, `train_APF.py`, `report_APF.py`: nhánh performance F, năm kiểm tra dữ liệu thật, so sánh A+P+F với A+P/A_common và kiểm chứng artifact.
- `temperature_calibration.py`, `final_models.py` và các script final: temperature validation-only, danh sách cố định, kiểm tra test covariates, khóa checksum trước scoring, một vòng test rồi kiểm chứng độc lập.
- `test_temperature.py` và `test_final_bootstrap.py`: thêm tám test calibration/split/argmax và khoảng bootstrap; tổng 81 unit tests đã đạt.
- `train_model_A_trees.py`: lưu manifest trước fit, chọn cấu hình bằng CV training, đánh giá validation và permutation importance.
- `report_model_A_trees.py`: xác minh mô hình đã lưu và XGBoost native, so sánh cùng cohort, dựng báo cáo và biểu đồ.
- `modeling.py` và `train_model_A.py`: baseline xác suất và Logistic Regression; chọn C qua ba fold trong training, fit preprocessing riêng từng fold.
- `report_model_A.py`: bốn nhóm kiểm chứng artifact, báo cáo tiếng Việt, confusion matrix và reliability plot.
- `verify_team_dataset.py`: 4 kiểm tra tích hợp trên dữ liệu thật, gồm prefix và thay đổi tương lai; không sửa raw.
- Audit 2024–2025 ban đầu chỉ kiểm tra cấu trúc. Metric và phân phối nhãn test chỉ được công bố ở final_test_v1 sau khi commit khóa; các artifact audit/development cũ giữ nguyên.
