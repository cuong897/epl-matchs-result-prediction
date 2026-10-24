# Kết quả vòng test đã khóa: Premier League 2024–2025

**Phạm vi:** backtest hồi cứu theo ngày, dùng dữ liệu miễn phí. Thời điểm nguồn công bố và announced XI tại T−60 chưa được chứng minh. P/F là proxy lịch sử nhân sự, không phải thí nghiệm XI chính thức hoặc market value.

Đã đánh giá đủ **380 trận**, với 14 estimator cố định và hai baseline tần suất; tổng 30 đầu ra xác suất raw/temperature. Phân phối test H/D/A: 155/93/132.

## Kết quả tham chiếu đã chọn trước test

Elo A_full được chọn làm tham chiếu thực dụng trước test vì có Log Loss validation gốc tốt nhất. Trên test, Accuracy **54.74%**, Macro F1 **0.41096**; Log Loss raw **0.98141**, temperature **0.98606**; Brier raw **0.58654**, temperature **0.58993**.

Báo cả hai phiên bản theo kế hoạch, không chọn raw hay calibrated dựa trên test. Temperature dương giữ nguyên argmax; Accuracy/F1/confusion matrix raw và calibrated của cùng estimator không đổi.

## Toàn bộ kết quả xác suất

| Cohort train | Thuật toán/nhánh | Accuracy | Macro F1 | Log Loss raw ↓ | Temperature ↓ | Brier raw ↓ | Temperature ↓ |
|---|---|---:|---:|---:|---:|---:|---:|
| full | Elo / A_full | 54.74% | 0.41096 | 0.98141 | 0.98606 | 0.58654 | 0.58993 |
| full | Logistic / A_full | 52.11% | 0.39624 | 0.99114 | 0.99403 | 0.59254 | 0.59442 |
| full | Random Forest / A_full | 51.32% | 0.38028 | 1.00598 | 1.01080 | 0.60136 | 0.60410 |
| full | XGBoost / A_full | 51.84% | 0.38712 | 1.00575 | 1.01215 | 0.60029 | 0.60365 |
| full | Tần suất / A_full | 40.79% | 0.19315 | 1.08089 | — | 0.65559 | — |
| common | Elo / A_common | 54.47% | 0.41123 | 0.98025 | 0.98470 | 0.58538 | 0.58887 |
| common | Tần suất / A_common | 40.79% | 0.19315 | 1.07920 | — | 0.65424 | — |
| common | Logistic / A_common | 53.16% | 0.40430 | 0.99430 | 0.99869 | 0.59368 | 0.59630 |
| common | Logistic / A_plus_P | 51.05% | 0.37926 | 0.99688 | 1.00107 | 0.59626 | 0.59883 |
| common | Logistic / A_plus_P_plus_F | 52.63% | 0.39960 | 0.99557 | 0.99688 | 0.59407 | 0.59478 |
| common | Random Forest / A_common | 53.68% | 0.40532 | 0.99978 | 1.00475 | 0.59625 | 0.59877 |
| common | Random Forest / A_plus_P | 53.68% | 0.40508 | 1.00118 | 1.00599 | 0.59748 | 0.60007 |
| common | Random Forest / A_plus_P_plus_F | 53.42% | 0.40333 | 0.99871 | 1.00227 | 0.59543 | 0.59730 |
| common | XGBoost / A_common | 52.37% | 0.39495 | 1.00105 | 1.00683 | 0.59735 | 0.60053 |
| common | XGBoost / A_plus_P | 52.89% | 0.39813 | 1.00247 | 1.00876 | 0.59852 | 0.60204 |
| common | XGBoost / A_plus_P_plus_F | 53.68% | 0.40595 | 1.00012 | 1.00505 | 0.59707 | 0.59983 |

Luôn chọn H: Accuracy 40.79%, Macro F1 0.19315; không gán xác suất 0 để tính Log Loss. Brier là mean(sum_c((p_c−y_c)^2)), miền [0,2]. Full train 3.040 trận, common train 1.520 trận; các ablation P/F chỉ so sánh trong common.

## So sánh chính: đóng góp P và F

Trong sáu contrast temperature đã đăng ký, 3/6 có Delta Log Loss âm. Với khoảng percentile có độ phủ điều chỉnh Bonferroni-style 99,1667% và block chính hai tuần, 0/6 nằm hoàn toàn dưới 0, 0/6 nằm hoàn toàn trên 0. Các kết luận vẫn chịu giới hạn độ phủ bootstrap trên một mùa phụ thuộc theo thời gian.

![So sánh feature](feature_comparison.png)

Delta = Log Loss mô hình thêm feature trừ nhánh tham chiếu; âm có lợi. 2.000 resample moving-block theo tuần lịch, seed 42. Cùng chỉ số lấy mẫu cho hai mô hình. Độ phủ điều chỉnh tương ứng 1−0,05/6 cho sáu contrast chính; percentile bootstrap chỉ xấp xỉ, và 2.000 lần có ít mẫu ở đuôi rộng. Không coi khoảng chứa 0 là chứng minh tương đương.

| Thuật toán | So sánh | Block tuần | Delta | CI 95% | CI 99,1667% |
|---|---|---:|---:|---|---|
| Logistic | P − A | 1 | 0.002380 | [-0.005495; 0.009946] | [-0.007919; 0.012132] |
| Logistic | P − A | 2 | 0.002380 | [-0.005542; 0.010632] | [-0.008593; 0.012916] |
| Logistic | P − A | 4 | 0.002380 | [-0.006877; 0.009266] | [-0.010430; 0.011174] |
| Random Forest | P − A | 1 | 0.001236 | [-0.004294; 0.006606] | [-0.005867; 0.008096] |
| Random Forest | P − A | 2 | 0.001236 | [-0.004388; 0.006273] | [-0.006951; 0.007763] |
| Random Forest | P − A | 4 | 0.001236 | [-0.005854; 0.005951] | [-0.008307; 0.007125] |
| XGBoost | P − A | 1 | 0.001935 | [-0.003095; 0.006963] | [-0.004565; 0.008901] |
| XGBoost | P − A | 2 | 0.001935 | [-0.002191; 0.006491] | [-0.003619; 0.008098] |
| XGBoost | P − A | 4 | 0.001935 | [-0.001980; 0.005853] | [-0.003150; 0.007086] |
| Logistic | APF − AP | 1 | -0.004191 | [-0.012842; 0.004285] | [-0.015749; 0.008193] |
| Logistic | APF − AP | 2 | -0.004191 | [-0.013147; 0.003810] | [-0.016532; 0.006862] |
| Logistic | APF − AP | 4 | -0.004191 | [-0.012437; 0.004989] | [-0.015723; 0.007631] |
| Random Forest | APF − AP | 1 | -0.003716 | [-0.009493; 0.001656] | [-0.011668; 0.003414] |
| Random Forest | APF − AP | 2 | -0.003716 | [-0.008607; 0.000992] | [-0.010004; 0.002388] |
| Random Forest | APF − AP | 4 | -0.003716 | [-0.008328; 0.000734] | [-0.009985; 0.001802] |
| XGBoost | APF − AP | 1 | -0.003716 | [-0.010591; 0.003036] | [-0.013023; 0.004752] |
| XGBoost | APF − AP | 2 | -0.003716 | [-0.009766; 0.002610] | [-0.011693; 0.005211] |
| XGBoost | APF − AP | 4 | -0.003716 | [-0.008787; 0.002131] | [-0.011011; 0.003720] |

So sánh raw là phân tích phụ, lưu đầy đủ trong results.json. Không chọn độ dài block cho kết luận thuận lợi: hai tuần là chính, một/bốn tuần là sensitivity. Không có uncertainty do fit lại mô hình trong resampling, nên các khoảng không bao phủ mọi nguồn bất định.

## Phân loại hòa, calibration và giải thích

| Thuật toán/nhánh | D được chọn | Đúng D | Precision D | Recall D |
|---|---:|---:|---:|---:|
| Elo / full / A_full | 0 | 0 | 0.00% | 0.00% |
| Logistic / full / A_full | 1 | 1 | 100.00% | 1.08% |
| Random Forest / full / A_full | 0 | 0 | 0.00% | 0.00% |
| XGBoost / full / A_full | 0 | 0 | 0.00% | 0.00% |
| Tần suất / full / A_full | 0 | 0 | 0.00% | 0.00% |
| Elo / common / A_common | 0 | 0 | 0.00% | 0.00% |
| Tần suất / common / A_common | 0 | 0 | 0.00% | 0.00% |
| Logistic / common / A_common | 3 | 1 | 33.33% | 1.08% |
| Logistic / common / A_plus_P | 2 | 0 | 0.00% | 0.00% |
| Logistic / common / A_plus_P_plus_F | 4 | 1 | 25.00% | 1.08% |
| Random Forest / common / A_common | 0 | 0 | 0.00% | 0.00% |
| Random Forest / common / A_plus_P | 0 | 0 | 0.00% | 0.00% |
| Random Forest / common / A_plus_P_plus_F | 0 | 0 | 0.00% | 0.00% |
| XGBoost / common / A_common | 1 | 0 | 0.00% | 0.00% |
| XGBoost / common / A_plus_P | 0 | 0 | 0.00% | 0.00% |
| XGBoost / common / A_plus_P_plus_F | 0 | 0 | 0.00% | 0.00% |

Temperature không sửa ranh giới quyết định, do đó không tự khắc phục recall hòa. Calibration fit trên 380 trận 2023–2024; điểm validation sau fit là in-sample diagnostics. Chỉ bảng test ở đây là đánh giá ngoài mẫu của calibrator.

![Reliability tham chiếu](reference_reliability.png)

Reliability chia tối đa năm nhóm phân vị mỗi lớp; quan sát trong bin có phụ thuộc nên Wilson intervals ở CSV chỉ là mô tả, không dùng như kiểm định calibration độc lập. Feature importance đã thực hiện trên validation; không chỉnh đặc trưng từ lỗi test.

## Tính toàn vẹn và giới hạn nghiên cứu

- Cấu hình, 14 mô hình, hai baseline, 14 nhiệt độ, dữ liệu test và mã chấm điểm được khóa bằng SHA-256 trước scoring. Tất cả xác suất test được lưu trước khi runner ghép nhãn để tính metric.
- Estimator fit đến 2022–2023; calibrator fit validation 2023–2024. Không refit hoặc chọn tham số bằng test. Có cập nhật trạng thái Elo/rolling/P/F từ các trận test trước ngày dự đoán theo quy tắc đã khóa; đây là dự đoán tuần tự, không dự đoán toàn mùa từ tháng Tám.
- Cùng 380 trận cho mọi mô hình; giữ các trận đầu mùa thiếu lịch sử P/F. Player IDs reset đầu mùa. Loại 322 dòng Assistant Manager khỏi dữ liệu test trước khi tạo feature.
- Bảng đội và tỷ số được đối chiếu; A tái dựng khớp snapshot. P/F đạt prefix/invariance/lineage checks. Artifact verification nạp lại mô hình và tái tạo đủ 11.400 xác suất, các metric và confusion matrices mà không fit lại.
- Một mùa test có 380 trận, nhiều mô hình và phân phối mùa có thể đổi. Các khoảng bootstrap phụ thuộc giả định; không hứa độ chính xác cho mọi mùa hoặc ứng dụng cá cược.
- Không có dữ liệu announced XI, tuổi/market value lịch sử đủ bằng chứng. Nghiên cứu chứng minh quy trình và kết quả với proxy đã định nghĩa, chưa giải quyết đầy đủ giả thuyết ban đầu về XI.
- Không tiếp tục sửa mô hình dựa trên test. Bước tiếp theo là tổng hợp báo cáo học thuật, notebook tái lập và demo xác suất từ mô hình đã khóa.

## Tái lập

```powershell
python -m unittest discover -s tests -q
python scripts/report_final_test.py
```

run_final_test.py từ chối ghi đè vòng test đã có. report_final_test.py chỉ kiểm chứng và dựng lại báo cáo/biểu đồ từ cùng artifact đã khóa. Dữ liệu raw/curated và model artifacts giữ cục bộ; hướng dẫn thu thập và các checksum nằm trong repo.

Nguồn phương pháp: [scikit-learn: temperature calibration](https://scikit-learn.org/stable/modules/calibration.html). Khóa thí nghiệm: research/final_evaluation_config.json, research/final_model_registry.json, research/final_lock.json.
