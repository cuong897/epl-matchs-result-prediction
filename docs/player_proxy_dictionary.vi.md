# Đặc trưng P: lịch sử sử dụng cầu thủ

Phiên bản `P_usage_v1_day_batched` có 12 cột: sáu đại lượng bên dưới cho mỗi đội, prefix home_/away_. Đây là proxy sử dụng nhân sự từ các trận đã diễn ra, không phải announced XI, dự đoán roster hiện tại hay chất lượng từng cầu thủ.

| Tên gốc | Định nghĩa trên tối đa 5 trận trước của đội trong cùng mùa |
|---|---|
| p_history_n5 | Số trận hỗ trợ, từ 0 đến 5 |
| p_participants_n5 | Số player-season ID khác nhau có phút dương được ghi nhận |
| p_minutes_hhi5 | Tổng bình phương tỷ trọng phút của từng cầu thủ trong toàn cửa sổ; lớn hơn thể hiện phút tập trung vào ít người hơn |
| p_top11_minutes_share5 | Tổng tỷ trọng phút của 11 cầu thủ có tổng phút lớn nhất trong cửa sổ; nếu ít hơn 11 người thì lấy tất cả |
| p_last_returning_minutes_share5 | Trong trận trước gần nhất, tỷ trọng phút thuộc về người đã có phút dương ở ít nhất một trận sớm hơn trong cửa sổ |
| p_mean_minutes_overlap5 | Với từng cặp trận liền nhau trong cửa sổ: cộng min(tỷ trọng phút trận trước, tỷ trọng phút trận sau) của từng người; lấy trung bình các cặp |

Không có lịch sử: history_n5=0, các đại lượng khác missing. Chỉ một trận lịch sử: hai biến continuity cuối missing. Missing được xử lý trong pipeline chỉ fit trên training, không lấp bằng trận tương lai.

Snapshot lúc 00:00 Europe/London của ngày trận đấu chỉ dùng các ngày trước. Cập nhật trạng thái sau khi xuất snapshot cho toàn bộ các trận cùng ngày. Availability của dữ liệu nguồn được giả định là nửa đêm địa phương ngày tiếp theo; chưa chứng minh publication time thực tế. Không dùng phút, goals, assists, starts, xG/xA, giá FPL hay đội hình trận hiện tại.

Player ID có season scope; reset mọi cửa sổ cầu thủ đầu mùa. Nhóm người được ghi nhận ở đội nào trong trận quá khứ thuộc về lịch sử đội đó, kể cả sau này chuyển CLB. Không suy ra họ vẫn còn trong roster hiện tại. Dòng minutes=0 không tạo người tham gia trong cửa sổ; không suy diễn nguyên nhân không ra sân.

Lineage lưu match ID của các trận nguồn, ngày trận nguồn mới nhất, available_at giả định lớn nhất và asof. Bảng feature chỉ chứa match_id và allowlist 12 cột số; không có nhãn, player ID hay đội hiện tại để estimator học trực tiếp.

**Giới hạn:** số người được sử dụng có thể phản ánh thay đổi luật thay người, mùa COVID hoặc cách ghi phút, ngoài ý nghĩa ổn định nhân sự. Không diễn giải importance là quan hệ nhân quả. P hiện chưa kiểm tra giả thuyết phong độ ghi bàn/kiến tạo hoặc XI chính thức.

Phạm vi so sánh: A_common và A+P có cùng 1.520 trận training 2019–2023, 380 trận validation 2023–2024. Cùng snapshot 40 đặc trưng A ở cả hai nhánh; A+P có thêm 12 đặc trưng P. Mỗi thuật toán/nhánh thử bốn cấu hình giống nhau trên ba fold expanding-window; fit lại preprocessing và estimator cho từng fold. Chưa tạo P cho mùa test.

Kiểm chứng: 12 unit tests mới gồm tính tay các thống kê, giới hạn cửa sổ, thay đổi trận hiện tại/tương lai, reset mùa, input ordering, cột bị cấm và dữ liệu sai. Bốn kiểm tra trên dữ liệu thật gồm prefix invariance, thay phút validation không ảnh hưởng training, đảo thứ tự dòng và lineage không vượt cutoff. Tổng bộ test hiện tại: 61 tests đạt.
