# Diễn giải kết quả cuối và điều kiện kết luận

Đã hoàn thành vòng test cố định `final_test_v1` trên 380 trận Premier League 2024–2025. Khóa `7773397` được commit trước scoring; không sửa mô hình hoặc calibration sau khi thấy test. Báo cáo đầy đủ và số liệu máy đọc nằm cùng thư mục.

## Ba kết quả chính

**1. Baseline Elo vẫn là mốc mạnh.** Elo A_full đã được chỉ định trước test làm tham chiếu thực dụng. Nó đạt Accuracy 54,74%, Macro F1 0,41096, Log Loss raw 0,98141 và Brier raw 0,58654. Baseline luôn chọn chủ nhà chỉ đạt Accuracy 40,79%; tần suất lịch sử A_full có Log Loss 1,08089. Elo common có Log Loss raw 0,98025, nhưng chênh lệch rất nhỏ với Elo A_full không đủ để tự tuyên bố vượt trội chắc chắn.

**2. Calibration không cải thiện ngoài mẫu trong thí nghiệm này.** Cả 14 nhiệt độ fit trên 2023–2024 đều dưới 1, làm xác suất sắc hơn. Trên test, Log Loss và Brier của cả 14 mô hình sau temperature đều cao hơn bản raw. Riêng tham chiếu Elo A_full, Log Loss tăng 0,98141 → 0,98606, Brier tăng 0,58654 → 0,58993. Accuracy/F1 không đổi vì temperature giữ argmax. Không che bản calibrated hoặc chọn lại phương pháp sau khi biết test.

Validation có H/D/A = 175/82/123, test có 155/93/132. Tỷ lệ chủ nhà thắng giảm từ 46,05% xuống 40,79%, còn hòa tăng từ 21,58% lên 24,47%. Đây là bằng chứng mô tả phân phối hai mùa khác nhau; nó chưa chứng minh nguyên nhân calibration thất bại. Chất lượng tín hiệu, quan hệ giữa đặc trưng/nhãn và sai số fit T cũng có thể thay đổi. Một calibrator fit trên một mùa không bảo đảm tốt hơn ở mùa kế tiếp.

**3. Chưa có bằng chứng chắc chắn P/F cải thiện dự đoán.** Trong so sánh chính đã đăng ký, sau calibration P làm Log Loss tăng ở cả ba thuật toán so với A_common. F làm Log Loss giảm ở cả ba thuật toán so với A+P. Tuy nhiên, cả sáu khoảng Bonferroni-style 99,1667% tại block chính hai tuần đều chứa 0. Khoảng 95% tương ứng cũng chứa 0. Không kết luận hai mô hình tương đương và không loại trừ lợi ích nhỏ; dữ liệu một mùa chưa đủ phân biệt chắc chắn.

| Thuật toán | Delta P − A | Delta APF − AP |
|---|---:|---:|
| Logistic Regression | +0,002380 | −0,004191 |
| Random Forest | +0,001236 | −0,003716 |
| XGBoost | +0,001935 | −0,003716 |

Delta âm có lợi cho feature mới. Các khoảng, độ nhạy block một/bốn tuần và kết quả raw được công bố trong report.vi.md/results.json. Có nhiều mô hình nhưng không chọn mô hình có điểm test đẹp nhất làm bằng chứng xác nhận giả thuyết.

## Điều nghiên cứu chưa giải quyết

- Elo tham chiếu không chọn nhãn hòa lần nào; recall D bằng 0. Xác suất D vẫn tham gia scoring đầy đủ. Đây là hạn chế rõ ràng, không được giấu bằng Accuracy tổng.
- P/F dùng nhóm tham gia trong quá khứ, chưa dùng announced XI có timestamp T−60. Không có kết luận cho tác động của XI chính thức, market value hoặc tuổi đội hình.
- Availability là tái dựng theo ngày với giả định nửa đêm địa phương kế tiếp, dữ liệu có thể đã sửa hồi cứu. Không khẳng định đây là backtest với feed lịch sử point-in-time đã chứng minh đầy đủ.
- Mẫu test chỉ có 380 trận; bootstrap có giả định về phụ thuộc và độ phủ xấp xỉ. Không suy rộng thành cam kết hiệu suất cho mọi mùa.

## Cách viết kết luận đề tài

Phát biểu được dữ liệu hỗ trợ: “Trên mùa test 2024–2025 và cohort/lược đồ được định nghĩa, các proxy sử dụng và hiệu suất cầu thủ chưa tạo cải thiện Log Loss có bằng chứng chắc chắn so với thống kê đội; baseline Elo là đối chứng mạnh. Temperature scaling fit trên mùa trước làm chất lượng xác suất test giảm trong các cấu hình được đánh giá.”

Không phát biểu: “Dữ liệu cầu thủ không giúp dự đoán bóng đá”, “đội hình chính thức không quan trọng”, hoặc “calibration luôn có hại”. Các câu đó vượt quá bằng chứng thực nghiệm.

Một tên đề tài phù hợp với phần đã triển khai là: **“Dự đoán kết quả Premier League 2024–2025 từ thống kê đội bóng và các đặc trưng lịch sử cầu thủ: đánh giá theo thời gian và kiểm soát rò rỉ dữ liệu.”** Mục tiêu XI/market value ban đầu cần trình bày là hướng nghiên cứu chưa đủ điều kiện dữ liệu.

Bước tiếp theo là tổng hợp báo cáo học thuật, notebook tái lập và demo từ mô hình đã khóa; giữ nguyên kết quả test và toàn bộ lịch sử thực nghiệm.
