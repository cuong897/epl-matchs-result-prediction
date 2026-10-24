# Premier League — dự đoán xác suất H/D/A

Trạng thái ngày 24/10/2026: **đã so sánh baseline, Logistic Regression, Random Forest và XGBoost cho Model A**, sau khi chuẩn hóa 12 mùa và tạo 40 đặc trưng theo thời gian. Đã đánh giá validation 2023–2024; chưa dự đoán hoặc tính metric test 2024–2025.

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

Bước kế tiếp: audit lịch sử cầu thủ trong các mùa training để xác định cohort A/P và đặc trưng proxy từ quá khứ; giữ model metrics test cho vòng cuối. B/C vẫn có điều kiện; FPL starts là nhãn đá chính sau trận, chưa phải announced XI tại T−60.

Validation hiện tại: Elo có Log Loss 0,9285; Random Forest 0,9299; XGBoost 0,9388; Logistic A 0,9417; tần suất lịch sử 1,0541. RF/XGBoost đạt Accuracy 57,89% nhưng chưa vượt Elo về Log Loss; recall lớp hòa vẫn bằng 0. Đây là kết quả development, chưa phải kết luận cuối của đề tài.

## Chạy lại kiểm tra (không cần mạng khi đã có raw cache)

```powershell
Set-Location 'D:\premier-league-ml'
python -m unittest discover -s tests -v
python scripts/audit_pilot.py
python scripts/build_team_dataset.py
python scripts/verify_team_dataset.py
```

Nếu dùng môi trường mới, cài các phiên bản đã kiểm tra trong requirements-audit.txt. Runtime hiện tại: Python 3.13.5.

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

## Tải mẫu

```powershell
Set-Location 'D:\premier-league-ml'
python scripts/download_pilot.py
python scripts/download_pilot.py --catalog team_sources --provider football_data_co_uk
```

Downloader đọc catalog cố định (pilot_sources hoặc team_sources), bỏ qua tệp có checksum đúng, không ghi đè raw, không tự thử lại khi nguồn lỗi/chặn. Không xóa cache để tải lại thường xuyên. Raw được loại khỏi Git; không có giấy phép dự án nào mặc nhiên tái cấp phép dữ liệu bên thứ ba.

## Logic kiểm tra

- `download_pilot.py`: tải một lần, kiểm tra CSV sơ bộ, lưu metadata và SHA-256.
- `audit_pilot.py`: đọc cache đã xác minh hash; kiểm tra mùa, trận, bàn thắng/nhãn; tách AM khỏi cầu thủ; ánh xạ đội bằng bảng rõ ràng; ghép một-một theo ngày và cặp đội; giữ cả hai giờ khi không khớp.
- `test_audit.py`: 9 kiểm thử dùng dữ liệu giả chỉ trong tests, không trộn vào dữ liệu nghiên cứu.
- `team_features.py`: tạo snapshot trước khi cập nhật kết quả cả ngày; Elo, rolling và H2H chỉ dùng quá khứ.
- `build_team_dataset.py`: audit 12 mùa, chỉ bỏ dòng hoàn toàn trống, tách outcomes, xuất 4 split và lineage.
- `test_team_features.py`: 14 kiểm thử feature và thời gian.
- `test_modeling.py`: 12 kiểm thử về thứ tự nhãn, metric, preprocessing, chronological folds và bootstrap.
- `test_tree_modeling.py`: 4 kiểm thử mapping nhãn, float32, preprocessing và tính đầy đủ các fold; tổng 39 unit tests đã đạt.
- `train_model_A_trees.py`: lưu manifest trước fit, chọn cấu hình bằng CV training, đánh giá validation và permutation importance.
- `report_model_A_trees.py`: xác minh mô hình đã lưu và XGBoost native, so sánh cùng cohort, dựng báo cáo và biểu đồ.
- `modeling.py` và `train_model_A.py`: baseline xác suất và Logistic Regression; chọn C qua ba fold trong training, fit preprocessing riêng từng fold.
- `report_model_A.py`: bốn nhóm kiểm chứng artifact, báo cáo tiếng Việt, confusion matrix và reliability plot.
- `verify_team_dataset.py`: 4 kiểm tra tích hợp trên dữ liệu thật, gồm prefix và thay đổi tương lai; không sửa raw.
- Audit 2024–2025 chỉ kiểm tra cấu trúc và tính nhất quán, không tính phân phối nhãn, baseline scores hoặc metric mô hình.
