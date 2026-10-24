# Hướng dẫn trình bày và bảo vệ bài tập lớn

## Mạch trình bày khoảng 7 phút

**Phút 0–1 — Câu hỏi và phạm vi.** Nêu dự đoán xác suất H/D/A, không chỉ nhãn. Giải thích dữ liệu đội hình chính thức và market value chưa đủ bằng chứng tại T−60; thực nghiệm khả thi dùng A, P và F từ lịch sử. Không gọi proxy là XI chính thức.

**Phút 1–2 — Dữ liệu đáng tin cậy đến đâu.** Nêu Football-Data, archive FPL, checksum và audit. Hai ví dụ đáng trình bày là 59 placeholder trận hoãn và 136 trận có starts/xG/xA toàn 0. Có cột và không thiếu ô chưa có nghĩa dữ liệu đầy đủ. Giới thiệu ngắn giả định next-local-midnight và giới hạn publication time.

**Phút 2–3 — Chống rò rỉ.** Minh họa “snapshot trước, cập nhật sau cả ngày”. Đổi thống kê trận hiện tại không đổi feature của chính trận đó; đổi tương lai không đổi quá khứ. Imputer/scaler fit riêng trên training fold. Tách validation và test theo mùa, không random split.

**Phút 3–4 — So sánh công bằng.** A_full có 3.040 trận training, còn A_common/A+P/A+P+F có cùng 1.520 trận. Chỉ so tác dụng feature trong common. Ba thuật toán, bốn ứng viên mỗi nhánh, chọn bằng Log Loss walk-forward. P là usage/continuity; F là đóng góp lịch sử nhóm trận trước.

**Phút 4–5 — Kết quả.** Elo tham chiếu chọn trước test đạt Accuracy 54,74%, Log Loss raw 0,98141. Temperature fit mùa trước làm Log Loss test tăng ở cả 14 mô hình. Các contrast P/F chưa có bằng chứng cải thiện chắc chắn. Nói rõ recall hòa của Elo bằng 0; không chỉ đọc Accuracy.

**Phút 5–6 — Demo.** Mở demo/index.html, chọn một trận rồi đọc ba xác suất. Đổi mô hình để thấy bảng thay đổi; giải thích chỉ số bên dưới là cho cả 380 trận. Bật kết quả thực tế để đối chiếu, nhắc đây là replay archive đã khóa. Không demo train lại để cố đạt số đẹp hơn.

**Phút 6–7 — Kết luận và giới hạn.** Kết quả âm vẫn có giá trị nếu thiết kế kiểm soát tốt. Không suy ra “cầu thủ không quan trọng” hoặc “calibration luôn có hại”. Hướng tiếp theo cần dữ liệu timestamp/identity/roster tốt hơn và giai đoạn đánh giá mới.

## Những câu hỏi cần trả lời được

**Vì sao dùng xác suất thay vì nhãn?** Hai dự đoán cùng nhãn có thể có mức tự tin khác nhau. Log Loss/Brier đánh giá chất lượng xác suất; Accuracy chỉ nhìn argmax.

**Vì sao mô hình không chọn hòa nhưng p(D) vẫn khác 0?** Hòa có thể không phải xác suất lớn nhất trong trận nào dù tổng xác suất hòa hợp lý. Argmax và probability scoring là hai góc đánh giá khác nhau. Recall D bằng 0 vẫn là hạn chế cần công bố.

**Tại sao thêm cầu thủ chưa tốt hơn?** Proxy có sai số về roster, cửa sổ ngắn và tín hiệu có thể trùng form đội; một mùa test nhỏ không đủ phân biệt lợi ích nhỏ. Thực nghiệm chưa có XI chính thức, nên không kết luận cho mọi dữ liệu cầu thủ.

**Tại sao calibration lại kém hơn?** T được fit theo mùa trước và mọi T dưới 1 làm xác suất sắc hơn. Test có phân phối khác; đây là giải thích khả dĩ chứ chưa chứng minh nguyên nhân. Fit loss giảm trên validation không bảo đảm ngoài mẫu tốt hơn.

**Test có bị dùng để tạo feature không?** Trạng thái dự đoán từng trận được cập nhật bằng kết quả các trận test ở ngày trước, theo policy đã khóa. Không dùng nhãn/thống kê trận hiện tại hoặc tương lai, không refit estimator/calibrator trong test. Đây là sequential backtest, không dự đoán toàn mùa từ tháng Tám.

**T−60 đã được chứng minh chưa?** Chưa. Quy tắc chỉ dùng ngày trước là cách tái dựng bảo thủ, không chứng minh thời điểm nguồn công bố hoặc lịch trận được biết trong lịch sử. Báo cáo nêu giới hạn này rõ ràng.

**Notebook tái lập được gì?** Tái tính metric từ artifact đã khóa, không mặc định đã thu thập và train lại từ raw. Các mức tái lập được tách trong reproducibility.vi.md.

**Có được chỉnh lại mô hình sau test không?** Có thể mở một nghiên cứu mới, nhưng test cũ không còn là tập chưa quan sát. Trong dự án hiện tại giữ nguyên code/model/feature đã khóa và không dùng test để tune.

## Kiểm tra trước buổi trình bày

- Mở trước báo cáo Word, notebook có output và demo offline.
- Đọc được H/D/A theo đúng thứ tự; không nhầm giá FPL với market value.
- Dùng đúng bảng test, phân biệt với validation; phân biệt full với common.
- Không tuyên bố có ý nghĩa thống kê chỉ vì điểm Accuracy tăng vài trận.
- Chuẩn bị trả lời vì sao phạm vi đề tài đã thu hẹp theo dữ liệu thực tế.
