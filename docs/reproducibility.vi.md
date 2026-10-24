# Tái lập và sử dụng bộ bàn giao

## Mức 1 Xem demo mà không cài thư viện

Mở `demo/index.html` bằng trình duyệt. Tệp chứa sẵn dự đoán đã khóa cho 380 trận, hoạt động khi không có mạng. Chọn đội, ngày, trận và mô hình; xem cả xác suất raw và temperature. Kết quả thực tế mặc định ẩn, có thể bật để đối chiếu.

Demo không fit, không nhận live fixtures và không dự báo trận tương lai. Chỉ số Accuracy/Log Loss trên giao diện là của toàn mùa test, không phải của tập trận sau lọc. P/F dùng lịch sử nhân sự, chưa có announced XI T−60 được xác minh.

## Mức 2 Tái tính kết quả từ artifact đã lưu

Các CSV/JSON kết quả và match_catalog.csv nằm trong Git; không cần raw hoặc model joblib để chạy notebook. Với Python 3.13.5 và các phiên bản đã kiểm tra:

```powershell
python -m pip install -r requirements-notebook.txt
python scripts/execute_results_notebook.py
```

Mở `notebooks/results_reproduction.ipynb` trong môi trường đọc notebook để xem các bảng và hình. Notebook đã có output sau một lượt chạy toàn bộ thành công. Khi chạy lại, nó kiểm tra khóa, đối chiếu 11.400 bộ xác suất và tự tính lại Accuracy, Macro F1, Log Loss và Brier cho 30 đầu ra. Nó không fit mô hình, không bootstrap thêm hoặc chọn lại contrast theo test.

Đây là **tái lập kết quả từ artifact**, không đồng nghĩa đã chạy lại thu thập, huấn luyện và tạo dự đoán từ đầu. Hash khóa được kiểm tra nhưng notebook không yêu cầu hay xác minh từng file raw/joblib bị loại khỏi Git.

## Mức 3 Kiểm chứng từ mô hình và đặc trưng đã khóa

Trên workspace gốc có đủ `data/curated`, raw cache và `models`, chạy:

```powershell
python -m pip install -r requirements-modeling.txt
python scripts/report_final_test.py
```

Script kiểm tra checksum dữ liệu, model, nhiệt độ và code; nạp lại model, tái tạo 30 đầu ra trên cùng 380 trận, đối chiếu metric/confusion matrices. Không fit lại, không chọn lại raw/calibrated. Không chạy lại run_final_test.py để ghi đè: runner từ chối thư mục vòng test đã tồn tại.

Model joblib chỉ được nạp từ nguồn tin cậy của chính dự án. Bản raw/curated và model artifacts không có trong Git do kích thước và quyền dữ liệu upstream; clone repo đơn thuần chưa đủ cho mức này.

## Mức 4 Thực hiện lại quy trình từ dữ liệu đầu vào

Thực hiện trong bản sao riêng, giữ nguyên workspace và vòng test gốc. Thứ tự nguồn → audit → features → training → calibration → final lock/scoring được mô tả trong README và các protocol. Dùng đúng catalog, bảng sửa lỗi, alias, split, seed và phiên bản thư viện đã ghi trong manifest.

Một bản tải mới từ URL `master` hoặc website có thể khác snapshot nghiên cứu. Phải đối chiếu với download_manifest.json đã commit và raw SHA-256 gốc; không chấp nhận khác checksum rồi gọi là cùng bộ dữ liệu. Khi snapshot gốc không còn lấy được công khai, cần bản cache gốc có quyền chia sẻ phù hợp hoặc ghi rõ không thể tái lập toàn bộ từ nguồn hiện tại. Không tự phân phối lại raw dưới giấy phép mã nguồn dự án.

Ngay cả với cùng seed, phiên bản hệ điều hành/thư viện/phép tính có thể ảnh hưởng byte của joblib hoặc sai số số học. Tách kiểm tra số học tương đương với kiểm tra artifact nguyên byte; không thay đổi manifest vòng test gốc để khiến bản tái chạy được coi là bản gốc.

## Xây lại phần trình bày

`build_delivery.py` cần bảng curated gốc để tạo match catalog; script tạo lại demo và notebook chưa thực thi. Sau đó chạy execute_results_notebook.py và cập nhật checksum bàn giao qua verify_delivery.py. Không dùng script bàn giao để tái tính mô hình hoặc thay đổi test.

Builder báo cáo Word chạy với runtime Documents đã dùng khi tạo artifact; mã builder dùng python-docx. Thiết kế báo cáo và số liệu được lưu trong script, nguồn số liệu là các JSON/CSV đã khóa. Máy khác cần môi trường xuất/kiểm tra bố cục Word tương ứng; file Word và bản Markdown đã tạo có thể đọc độc lập.

## Cấu trúc bàn giao

- Báo cáo học thuật: `reports/delivery/academic_report.vi.docx` và bản nguồn đọc được `academic_report.vi.md`.
- Notebook thực thi: `notebooks/results_reproduction.ipynb`.
- Demo offline: `demo/index.html`.
- Kết quả đầy đủ và chẩn đoán: `reports/final_test_v1/`.
- Protocol, registry và checksum khóa: `research/`.
- Báo cáo kiểm chứng bàn giao: `reports/delivery/delivery_verification.json`.

Giữ nguyên lịch sử Git và các kết quả không cải thiện. Mọi nghiên cứu mới sau khi đã nhìn test phải được gắn nhãn nghiên cứu mới; không trình bày test cũ như một tập chưa từng quan sát.
