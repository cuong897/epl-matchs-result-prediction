# Premier League — dự đoán xác suất H/D/A

Trạng thái ngày 24/10/2026: **đã hoàn thành baseline và Logistic Regression cho Model A**, sau khi chuẩn hóa 12 mùa và tạo 40 đặc trưng theo thời gian. Đã đánh giá validation 2023–2024; chưa dự đoán hoặc tính metric test 2024–2025.

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

Bước kế tiếp: so sánh Random Forest và một thuật toán boosting bằng cùng chronological validation; giữ model metrics test cho vòng cuối. B/C vẫn có điều kiện; FPL starts là nhãn đá chính sau trận, chưa phải announced XI tại T−60.

Validation hiện tại: Elo có Log Loss 0,9285; Logistic A 0,9417; tần suất lịch sử 1,0541. Logistic A chưa vượt Elo và recall lớp hòa bằng 0. Đây là kết quả development, chưa phải kết luận cuối của đề tài.

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
- `test_modeling.py`: 12 kiểm thử về thứ tự nhãn, metric, preprocessing, chronological folds và bootstrap; tổng 35 unit tests đã đạt.
- `modeling.py` và `train_model_A.py`: baseline xác suất và Logistic Regression; chọn C qua ba fold trong training, fit preprocessing riêng từng fold.
- `report_model_A.py`: bốn nhóm kiểm chứng artifact, báo cáo tiếng Việt, confusion matrix và reliability plot.
- `verify_team_dataset.py`: 4 kiểm tra tích hợp trên dữ liệu thật, gồm prefix và thay đổi tương lai; không sửa raw.
- Audit 2024–2025 chỉ kiểm tra cấu trúc và tính nhất quán, không tính phân phối nhãn, baseline scores hoặc metric mô hình.
