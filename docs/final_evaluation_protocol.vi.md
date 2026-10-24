# Protocol calibration và vòng test cuối

Ghi ngày 24/10/2026, sau khi kết thúc development và trước khi tính metric test.

## Danh sách và phương pháp khóa

- 14 estimator: A_full gồm Elo/Logistic/RF/XGBoost; common gồm Elo và ba thuật toán trên A, A+P, A+P+F. Hai baseline tần suất theo hai phạm vi training. Luôn chọn H chỉ đánh giá metric phân loại.
- Mỗi estimator có bản raw và temperature; baseline tần suất giữ raw. Tổng cộng 30 đầu ra xác suất, cùng 380 trận test 2024–2025.
- Mô hình tham chiếu thực dụng đã chọn là Elo A_full, vì Log Loss validation gốc tốt nhất trong development. Đây là lựa chọn bằng development, không phải kết luận từ test.
- Báo mọi phiên bản theo danh sách, không chọn raw/calibrated sau khi thấy test, không tune theo test. Base estimators giữ nguyên từ các run development.

## Calibration

Temperature scaling dùng softmax(log(p)/T), một T dương cho mỗi estimator. Fit bằng dự đoán và nhãn validation 2023–2024, giới hạn T trong [0,5;5], gồm phương án identity T=1 và hai biên. Tối ưu Log Loss trên inverse temperature; probability floor 1e-15.

Lựa chọn này giảm số tham số so với calibrator riêng từng lớp trên chỉ 380 trận. T giữ nguyên argmax, nên Accuracy/F1/recall hòa không đổi. Không coi calibration là cách sửa lỗi nhãn hòa. [Tài liệu scikit-learn](https://scikit-learn.org/stable/modules/calibration.html).

Điểm validation sau fit chỉ là **chẩn đoán in-sample**. Không chọn phương pháp calibration theo điểm test. Không refit estimator lên validation rồi dùng lại calibrator cũ.

## So sánh feature và độ bất định

Sáu so sánh chính dùng temperature: P trừ A và APF trừ AP, mỗi loại trên Logistic/RF/XGBoost. So sánh raw tương ứng là phân tích phụ. Tất cả trong common training 1.520 trận; không lấy A_full training 3.040 trận để quy chênh lệch cho feature.

Moving-block bootstrap ghép cặp theo tuần lịch, 2.000 lần, seed 42. Block chính hai tuần, độ nhạy một/bốn tuần. Báo CI percentile 95% và khoảng Bonferroni-style 1−0,05/6≈99,1667% cho sáu contrast chính. Độ phủ bootstrap là xấp xỉ; số mẫu đuôi hữu hạn và phụ thuộc theo đội/mùa vẫn hạn chế suy luận. Không chọn block thuận lợi sau khi đọc kết quả.

Log Loss là metric chính; Brier dùng mean(sum_c squared errors), miền [0,2]. Báo Accuracy, Macro F1, precision/recall từng lớp, confusion matrix và reliability bins. Không diễn giải interval chứa 0 là chứng minh tương đương.

## Dữ liệu test và provenance

A dùng trạng thái lịch sử trước ngày hiện tại; P/F reset đầu mùa vì ID có season scope, sau đó cập nhật từ các trận đã diễn ra ở ngày trước. Không fit lại estimator/calibrator trong test. Đây là dự đoán từng trận theo thời gian, không dự đoán toàn mùa từ tháng Tám.

Chỉ có giả định nguồn có dữ liệu vào nửa đêm Europe/London kế tiếp. Lịch archive chưa phải lịch đã biết tại thời điểm dự đoán; actual XI chưa phải announced XI có timestamp. Không tuyên bố dữ liệu đầu vào đã chứng minh đầy đủ cutoff T−60. P/F chỉ là proxy từ lịch sử, không bao gồm market value hay tuổi.

Test có cùng 380 trận cho mọi mô hình, không lọc theo hiệu năng. Missing đầu mùa giữ lại, xử lý bởi preprocessing đã fit training. Assistant Manager không phải cầu thủ, bị loại theo position trước chuẩn hóa.

## Thứ tự thực thi

1. Commit cấu hình/danh sách và mã calibration, chạy kiểm thử trước fit T.
2. Fit 14 T trên validation; tạo P/F test, kiểm tra prefix/future/lineage và A rebuild. Chưa scoring test.
3. Commit mã scoring/report và các kiểm tra. Tạo final_lock.json chứa checksum code, dữ liệu, model và T, ghi source commit; commit khóa trước scoring.
4. Runner tạo và lưu toàn bộ xác suất test trước khi ghép nhãn để tính metric. Một vòng test cố định, từ chối ghi đè thư mục run.
5. Report nạp lại artifact để kiểm chứng cùng xác suất/metric, không fit hoặc thay đổi mô hình. Báo kết quả và giới hạn, giữ nguyên cả kết quả không cải thiện.

Các file điều khiển: final_evaluation_config.json, final_model_registry.json và final_lock.json. Các checksum model giữ trong registry; model/raw/curated nằm cục bộ ngoài Git. Không dùng Git co-author trailer trong các commit dự án.
