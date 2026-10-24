# F: phong độ đóng góp của nhóm cầu thủ trận trước

Phiên bản `F_performance_v1_day_batched` bổ sung tám cột, bốn cột mỗi đội, vào A+P (52 → 60 đặc trưng). F là proxy dựa trên quá khứ. Chưa có roster hiện tại hoặc announced XI ở T−60 đã được xác minh, nên không gọi đây là Model C theo đội hình chính thức.

Ký hiệu trong tối đa năm trận trước của đội, cùng mùa: M_i là tổng phút cầu thủ i, G_i là tổng bàn ghi được và A_i là tổng kiến tạo FPL. Nhóm L gồm người có phút dương trong trận trước gần nhất của đội. Trọng số w_i bằng phút của i trong trận trước gần nhất chia tổng phút của đội trong trận đó. Tất cả được tính trước ngày trận đang dự đoán.

| Tên gốc, thêm prefix home_/away_ | Công thức |
|---|---|
| f_recent_group_goal90_s180_5 | Tổng trên i thuộc L của w_i × 90 × G_i / (M_i + 180) |
| f_recent_group_assist90_s180_5 | Tổng trên i thuộc L của w_i × 90 × A_i / (M_i + 180) |
| f_contribution_hhi5 | Tổng bình phương tỷ trọng (G_i+A_i) của từng người trong toàn cửa sổ |
| f_recent_group_contribution_share5 | Tổng (G_i+A_i) trong cửa sổ của những người thuộc L chia tổng (G_i+A_i) toàn cửa sổ |

180 phút là tham số thiết kế cố định, đăng ký trước khi đo metric F. Công thức kéo rate của người ít phút về prior 0, tránh per90 cực lớn từ vài phút. Đây không phải rate ghi bàn kỳ vọng của cả đội hoặc prior đã học từ dữ liệu. Không dùng trung bình các per90 chưa regularize. Hai biến rate có thể bằng 0 hợp lệ; hai tỷ trọng missing nếu tổng đóng góp bằng 0. Không có lịch sử thì cả bốn missing; imputer chỉ fit trên training.

F dùng contribution trong lịch sử của chính đội, không nối identity xuyên mùa hoặc tự mang phong độ cầu thủ từ CLB khác. Người chuyển đi vẫn có thể nằm trong lịch sử, vì chưa biết roster hiệu lực tại cutoff. Không suy diễn họ còn có thể thi đấu trận tới. Nhóm L không phải đội hình dự đoán hoặc injury report. Assists là thống kê FPL; không mặc định cùng định nghĩa với nguồn khác.

Snapshot/lineage tái sử dụng logic P: chỉ dùng ngày lịch trước, Europe/London; cập nhật sau batch cả ngày; reset đầu mùa. Availability vẫn là giả định nửa đêm địa phương kế tiếp sau ngày trận, chưa phải thời điểm xuất bản đã chứng minh. Không dùng current-match stats, starts, xG/xA không đủ lịch sử, giá FPL, tuổi hoặc market value.

## Phạm vi thí nghiệm đã chốt trước scoring

- Cùng 1.520 trận train 2019–2023 và 380 trận validation 2023–2024, không tạo F cho test.
- Ba thuật toán Logistic/RF/XGBoost, bốn ứng viên mỗi thuật toán, cùng ba fold 380/760/1.140 → 380; 36 lượt fit CV mới.
- Đối chứng A_common và A+P của AP_dev_v1 được giữ nguyên, kiểm tra checksum đầu vào/code, ID, nhãn và metric. Không chọn lại đối chứng sau khi nhìn F.
- So sánh chính là A+P+F trừ A+P, để đo lợi ích bổ sung performance. So sánh với A_common là phụ.
- Paired moving-block bootstrap 2.000 lần, block chính hai tuần, độ nhạy một/bốn tuần. Hoán vị chung tám cột F trong từng tháng validation, 10 lần.
- Đây là thử nghiệm giới hạn sau khi đã quan sát validation A/P. Sau phiên bản này dừng mở rộng feature thăm dò để chuẩn bị calibration và khóa vòng test cuối; giữ cả kết quả không cải thiện.

F có thể trùng tín hiệu với goals/form cấp đội. Thử nghiệm không thể chứng minh tác động nhân quả của cầu thủ, và một mùa validation nhỏ có thể không đủ phân biệt chênh lệch nhỏ. Thành tích ghi bàn của nhóm trận trước không cho biết ai sẽ ra sân trận tới.
