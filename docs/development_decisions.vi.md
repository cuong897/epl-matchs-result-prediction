# Quyết định sau giai đoạn development

Ngày 24/10/2026. Các quyết định dưới đây được ghi khi chưa tính metric test 2024–2025.

## Phạm vi đã hoàn thành

| Nhánh | Dữ liệu | Mô hình | Trạng thái |
|---|---|---|---|
| A_full | 3.040 trận train, 40 đặc trưng cấp đội | Elo ba lớp, Logistic, RF, XGBoost và tần suất | Đã đánh giá validation |
| A_common | 1.520 trận train, cùng 40 đặc trưng A | Ba thuật toán và baseline common | Đã đánh giá validation |
| A+P | Cùng 1.520 trận, thêm 12 biến mức sử dụng/continuity cầu thủ | Logistic, RF, XGBoost | Đã đánh giá validation |
| A+P+F | Cùng 1.520 trận, thêm 8 biến bàn/kiến tạo của nhóm trận trước | Logistic, RF, XGBoost | Đã đánh giá validation |
| B/C theo XI chính thức | Thiếu chứng cứ announced XI tại T−60 và lịch sử valuation phù hợp | Chưa đủ điều kiện | Không gắn kết quả proxy với giả thuyết này |

Validation là 380 trận 2023–2024 cho mọi nhánh. Hyperparameters chọn bằng các fold trong training. Mọi lượt development và giới hạn đã được lưu, gồm cả kết quả không cải thiện.

## Kết luận hiện có

1. Elo là baseline mạnh trên validation: Log Loss A_full 0,92848, Elo common 0,93133. Chưa có lý do bỏ baseline vì mô hình cây có Accuracy tốt hơn.
2. P chưa cải thiện Log Loss rõ ràng trên cohort chung; cả chín khoảng bootstrap đều chứa 0. Không coi đó là chứng minh P không có tác dụng trong mọi điều kiện.
3. F giảm Log Loss rất ít ở RF/XGBoost so với A+P, các khoảng đều chứa 0. Logistic tăng Log Loss khoảng 0,00899; bằng chứng về mức giảm chất lượng nhạy với độ dài block.
4. Khả năng chọn nhãn hòa vẫn yếu. Thêm F chỉ giúp Logistic chọn đúng một trong 82 trận hòa. Không đổi ngưỡng hoặc class weighting sau khi nhìn validation để làm đẹp Recall.
5. Câu hỏi về XI chính thức và market value vẫn chưa được trả lời do giới hạn dữ liệu. Một đề tài thực nghiệm có thể báo cáo kết quả proxy, nhưng phải thu hẹp tên/phát biểu giả thuyết cho đúng bằng chứng.

## Dừng mở rộng thăm dò

Khóa định nghĩa A, P_usage_v1 và F_performance_v1, cùng lưới bốn ứng viên cho mỗi thuật toán. Không tăng thêm cửa sổ, shrinkage, biến, mô hình hay ensemble để tìm điểm validation cao hơn trong nghiên cứu hiện tại. Nếu phát hiện lỗi code thật sự, phải ghi rõ lỗi, phiên bản sửa và kết quả chạy lại.

Giữ toàn bộ A_common/A+P/A+P+F làm ablation, không chỉ giữ cấu hình có Accuracy cao nhất. Không dùng so sánh A_full với một nhánh cầu thủ train ngắn hơn để kết luận hiệu quả nhân quả của feature.

## Bước kế tiếp trước test

- Tổng hợp danh sách estimator và baseline sẽ đánh giá; chỉ định so sánh chính/phụ, metric chính, cách trình bày nhiều so sánh và các giới hạn suy luận.
- Chốt calibration ít tham số, có cùng quy tắc cho các nhóm feature; ghi config và kiểm thử trước khi fit. Chưa fit calibrator ở thời điểm viết tài liệu này.
- Nếu fit calibrator bằng dự đoán/nhãn 2023–2024 thì số liệu sau calibration trên chính mùa đó chỉ là diagnostic in-sample. Giữ estimator gốc fit đến 2022–2023; không refit lên validation rồi tái sử dụng calibrator cũ.
- Tạo P/F cho test bằng trạng thái cuốn chiếu theo ngày với cùng giả định availability; không fit lại estimator bằng kết quả test. Kiểm thử prefix và invariance phải đạt trước scoring.
- Lưu manifest khóa phiên bản feature, estimator, calibrator và danh sách so sánh trước khi tạo dự đoán/tính metric test. Báo cả raw và calibrated theo kế hoạch cố định; không chọn phiên bản thắng sau khi xem test rồi che phiên bản còn lại.
- Thực hiện một vòng test cuối cho danh sách đã khóa, sau đó viết báo cáo kết quả, uncertainty, giải thích và giới hạn. Không sửa mô hình dựa trên test.

Đây là quyết định kết thúc exploration và chuyển giai đoạn, chưa phải manifest khóa test cuối. Các giả định publication time và lịch hồi cứu vẫn giữ trạng thái reconstructed_assumption.
