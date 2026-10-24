"""Verify saved development artifacts and render a report without fitting models."""
from pathlib import Path
import hashlib
import json

import joblib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from modeling import LABELS, evaluate, load_development, ordered_probabilities

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'reports/model_A_development'
NAMES = {'frequency': 'Tần suất lịch sử', 'elo_threeway': 'Elo → xác suất H/D/A',
         'logistic_A': 'Logistic Regression A', 'always_home': 'Luôn chọn chủ nhà'}


def main():
    result = json.loads((OUT / 'results.json').read_text(encoding='utf-8'))
    for relative, expected in result['input_sha256'].items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected, relative
    for name, expected in result['code_sha256'].items():
        assert hashlib.sha256((ROOT / 'scripts' / name).read_bytes()).hexdigest() == expected, name
    # Only load trusted artifacts produced locally by train_model_A.py.
    bundle = joblib.load(ROOT / 'models/A_dev_v1/bundle.joblib')
    assert bundle['label_order'] == LABELS
    frame = load_development(ROOT, bundle['feature_columns'])
    valid = frame[frame['split'].eq('validation')].copy()
    predictions = pd.read_csv(OUT / 'validation_predictions.csv')
    assert len(predictions) == 3 * len(valid)
    assert set(predictions.season) == {'2023-24'}
    probabilities = {}
    largest_error = 0.
    for name in ['frequency', 'elo_threeway', 'logistic_A']:
        if name == 'frequency':
            p = np.tile(bundle['frequency_probabilities'], (len(valid), 1))
        else:
            columns = ['elo_diff'] if name == 'elo_threeway' else bundle['feature_columns']
            p = ordered_probabilities(bundle['models'][name], valid[columns])
            separate = joblib.load(ROOT / 'models/A_dev_v1' / f'{name}.joblib')
            np.testing.assert_allclose(p, ordered_probabilities(separate, valid[columns]), atol=1e-12, rtol=0)
        saved = predictions[predictions.model.eq(name)].set_index('match_id').loc[valid.match_id]
        assert saved.result.tolist() == valid.result.tolist()
        np.testing.assert_allclose(p, saved[['p_H', 'p_D', 'p_A']].to_numpy(), atol=1e-12, rtol=0)
        largest_error = max(largest_error, float(np.max(np.abs(p-saved[['p_H','p_D','p_A']].to_numpy()))))
        metrics = evaluate(valid.result.to_numpy(), p)
        for key in ['accuracy', 'macro_f1', 'log_loss', 'brier_sum']:
            np.testing.assert_allclose(metrics[key], result['validation_metrics'][name][key], atol=1e-12, rtol=0)
        assert metrics['confusion_matrix_rows_true_cols_pred_HDA'] == result['validation_metrics'][name]['confusion_matrix_rows_true_cols_pred_HDA']
        probabilities[name] = p
    verification = {'input_and_training_code_hashes_match': True,
                    'saved_models_reproduce_validation_probabilities': True,
                    'saved_probabilities_reproduce_metrics_and_confusion_matrices': True,
                    'only_validation_season_in_prediction_export': True,
                    'maximum_probability_reload_difference': largest_error,
                    'test_predictions_or_metrics_generated': False}
    (OUT / 'artifact_verification.json').write_text(json.dumps(verification, indent=2)+'\n', encoding='utf-8')

    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10})
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), layout='constrained')
    names = list(probabilities)
    scores = [result['validation_metrics'][n]['log_loss'] for n in names]
    bars = axes[0].barh([NAMES[n] for n in names], scores, color=['#94a3b8','#0891b2','#2563eb'])
    axes[0].bar_label(bars, fmt='%.4f', padding=4)
    axes[0].set(xlim=(0, 1.2), xlabel='Multiclass Log Loss — thấp hơn tốt hơn', title='So sánh xác suất')
    axes[0].invert_yaxis()
    cm = np.array(result['validation_metrics']['logistic_A']['confusion_matrix_rows_true_cols_pred_HDA'])
    axes[1].imshow(cm, cmap='Blues', vmin=0)
    for i in range(3):
        for j in range(3):
            axes[1].text(j, i, str(cm[i,j]), ha='center', va='center', color='white' if cm[i,j]>90 else '#172554', fontsize=15)
    axes[1].set(xticks=range(3), xticklabels=LABELS, yticks=range(3), yticklabels=LABELS,
                xlabel='Nhãn dự đoán', ylabel='Nhãn thực tế', title='Logistic A: Confusion Matrix')
    fig.suptitle('Validation 2023–2024 · 380 trận · chưa hiệu chỉnh xác suất', fontsize=14)
    fig.savefig(OUT/'validation_overview.png', dpi=180)
    plt.close(fig)

    bins = pd.read_csv(OUT/'reliability_bins.csv')
    fig, axes = plt.subplots(1,3,figsize=(12,4.4),layout='constrained')
    for ax,label in zip(axes,LABELS):
        ax.plot([0,1],[0,1],color='#94a3b8',linestyle='--',label='Hiệu chỉnh hoàn hảo')
        for name,color in [('elo_threeway','#0891b2'),('logistic_A','#2563eb')]:
            data = bins[bins.model.eq(name)&bins['class'].eq(label)]
            ax.plot(data.mean_predicted,data.observed_fraction,'o-',color=color,label=NAMES[name])
        ax.set(xlim=(0,1),ylim=(0,1),xlabel='Xác suất dự đoán trung bình',ylabel='Tần suất thực tế',title=label)
        ax.grid(alpha=.15)
    axes[0].legend(fontsize=8)
    fig.suptitle('Reliability theo lớp · 5 nhóm phân vị · mô tả trên validation',fontsize=13)
    fig.savefig(OUT/'validation_reliability.png',dpi=180)
    plt.close(fig)

    lines = [
        '# Model A: baseline và Logistic Regression — kết quả development',
        '',
        'Run `A_dev_v1`; dữ liệu miễn phí; kết quả thực nghiệm trên 380 trận validation 2023–2024. '
        '**Chưa tính metric hay tạo dự đoán test 2024–2025.**',
        '',
        '## Thiết kế và khả năng tái lập',
        '',
        '- Training cuối: 3.040 trận, 2015–2016 đến 2022–2023. Hai mùa warm-up chỉ khởi tạo trạng thái đặc trưng.',
        '- Chọn C bằng Log Loss trung bình của ba fold walk-forward trong training: 2020–2021, 2021–2022, 2022–2023; lần lượt có 1.900, 2.280 và 2.660 trận huấn luyện. Mỗi fold kiểm tra 380 trận.',
        '- Median imputation, missing indicators và StandardScaler được fit riêng trên training của từng fold. Logistic Regression đa lớp dùng L2, không class weighting; không có cảnh báo hội tụ.',
        '- Elo baseline học ánh xạ ba lớp từ riêng elo_diff; không coi expected score của Elo là xác suất thắng. Baseline tần suất dùng Laplace smoothing alpha=1. Luôn chọn H chỉ có metric phân loại.',
        '- Cấu hình được ghi trước lần chạy đầu. Không dùng validation 2023–2024 để chọn C, không hiệu chỉnh xác suất hậu nghiệm trong run này.',
        '- Đặc trưng chỉ dùng trận đã kết thúc ở các ngày lịch trước theo Europe/London. Đây là tái dựng với giả định dữ liệu có vào nửa đêm tiếp theo, chưa xác minh thời điểm nguồn công bố; không khẳng định là feed point-in-time đã chứng minh đầy đủ tại T−60.',
        '- File outcomes chung được đọc để lọc ID development; nhãn test không được giữ lại cho fit/scoring. Không tải ma trận đặc trưng test vào mô hình.',
        '',
        '| C | Log Loss trung bình walk-forward | Độ lệch chuẩn giữa 3 mùa |',
        '|---:|---:|---:|',
    ]
    for row in result['C_ranking_training_folds']:
        lines.append(f"| {row['C']:g} | {row['mean_log_loss']:.6f} | {row['std_log_loss']:.6f} |")
    lines += ['', '**Chọn C=0,01.** Điểm CV đã dùng chọn siêu tham số nên không phải ước lượng test độc lập. '
              'C tốt nhất nằm ở biên dưới lưới; chưa mở rộng lưới sau khi nhìn validation.', '',
              '## Kết quả validation', '',
              '| Mô hình | Accuracy | Macro F1 | Log Loss ↓ | Brier ↓ |',
              '|---|---:|---:|---:|---:|']
    for name,m in result['validation_metrics'].items():
        ll = f"{m['log_loss']:.4f}" if 'log_loss' in m else '—'
        bs = f"{m['brier_sum']:.4f}" if 'brier_sum' in m else '—'
        lines.append(f"| {NAMES[name]} | {m['accuracy']:.2%} | {m['macro_f1']:.4f} | {ll} | {bs} |")
    lines += ['', 'Brier = trung bình tổng bình phương sai số của ba xác suất, miền [0,2]. '
              'Thứ tự xác suất và confusion matrix luôn H, D, A. Nhãn dự đoán là argmax.', '',
              '![Tổng quan](validation_overview.png)', '',
              'Elo đạt Log Loss tốt nhất trong các mô hình đã chạy. Bổ sung cả 40 đặc trưng vào Logistic Regression '
              'chưa cải thiện so với Elo trên mùa này; không đủ cơ sở để kết luận các đặc trưng đó vô dụng cho mọi thuật toán hay mùa giải.', '',
              '### Độ bất định của chênh lệch', '',
              'Paired moving-block bootstrap theo tuần lịch, 2.000 lần, seed 42. Delta = Log Loss Logistic A trừ baseline; âm có lợi cho Logistic A.', '',
              '| Baseline | Độ dài block (tuần) | Delta | Khoảng percentile 95% |',
              '|---|---:|---:|---|']
    for u in result['paired_uncertainty_validation']:
        lines.append(f"| {NAMES[u['comparator']]} | {u['block_weeks']} | {u['delta_log_loss_LR_minus_baseline']:.5f} | [{u['ci95_low']:.5f}; {u['ci95_high']:.5f}] |")
    lines += ['', 'So với tần suất lịch sử, Logistic A cải thiện trong cả ba lựa chọn block. '
              'So với Elo, chênh lệch điểm là +0,01318; khoảng chính với block 2 tuần chứa 0, còn block 1 và 4 tuần không chứa 0. '
              'Kết luận về độ chắc chắn nhạy với cách resample; không tuyên bố khác biệt có ý nghĩa thống kê vững chắc. '
              'Các khoảng chỉ phản ánh resampling một mùa với mô hình cố định, không bao gồm bất định do huấn luyện hoặc thay đổi giữa các mùa.', '',
              '## Lỗi dự đoán hòa và chất lượng xác suất', '',
              'Validation có H=175, D=82, A=123. Elo không chọn nhãn D lần nào. Logistic A chọn D bốn lần và đều sai; recall lớp D bằng 0 ở cả hai. '
              'Điều này là hạn chế nghiêm trọng của phân loại ba nhãn, dù các mô hình vẫn xuất xác suất hòa khác 0.', '',
              '| Mô hình | Xác suất D trung bình | Tỷ lệ hòa thực tế |', '|---|---:|---:|']
    for name,p in probabilities.items():
        lines.append(f"| {NAMES[name]} | {p[:,1].mean():.2%} | {valid.result.eq('D').mean():.2%} |")
    lines += ['', 'Xác suất trung bình gần tỷ lệ thực tế chưa chứng minh hiệu chỉnh tốt cho từng trận. '
              'Biểu đồ reliability dưới đây là chẩn đoán trên validation, không phải kết quả sau calibration.', '',
              '![Reliability](validation_reliability.png)', '',
              'File reliability_bins.csv có Wilson intervals mô tả theo bin; các khoảng này giả định quan sát độc lập, '
              'không xử lý đầy đủ phụ thuộc giữa trận đấu, vì vậy không dùng làm kiểm định hiệu chỉnh chính thức.', '',
              '## Giải thích mô hình', '',
              'Permutation importance hoán vị đồng thời các cột cùng nhóm trong từng tháng validation, 10 lần; không fit lại hay chọn lại mô hình. '
              'Giá trị dương là Log Loss tăng khi phá thông tin nhóm đó.', '',
              '| Nhóm | Tăng Log Loss trung bình | Độ lệch chuẩn 10 lần |', '|---|---:|---:|']
    for row in sorted(result['permutation_groups_validation'],key=lambda x:-x['mean_increase_log_loss']):
        lines.append(f"| {row['group']} | {row['mean_increase_log_loss']:.5f} | {row['repeat_std']:.5f} |")
    lines += ['', 'Elo là nhóm có tác động lớn nhất trong mô hình đã fit. Các nhóm còn lại có tác động nhỏ; H2H và venue có trung bình âm. '
              'Đây là chẩn đoán phụ thuộc mô hình và cách hoán vị, không phải quan hệ nhân quả hay bằng chứng chắc chắn nên bỏ nhóm. '
              'Tương quan giữa các nhóm có thể tạo tổ hợp đặc trưng ít thực tế khi hoán vị. Hệ số đã chuẩn hóa được xuất riêng, không diễn giải là tác động nhân quả.', '',
              '## Kiểm chứng và bước kế tiếp', '',
              '- 35 unit tests đã chạy thành công: 9 audit, 14 feature, 12 modeling. Bốn kiểm tra tích hợp feature trên dữ liệu thật đã đạt ở giai đoạn trước.',
              '- Kiểm chứng artifact: hash đầu vào/code khớp; nạp lại cả bundle và estimator riêng tái tạo xác suất trong sai số 1e-12; xác suất đã xuất tái tạo metric và confusion matrix; prediction export chỉ chứa validation.',
              '- Kết quả trên chưa phải kết quả cuối của đề tài. Validation hiện là dữ liệu development đã được quan sát; các quyết định tiếp theo phải ghi rõ, không gọi nó là tập kiểm tra độc lập chưa từng xem.',
              '- Bước tiếp theo: đăng ký ngân sách thử nghiệm Random Forest và một thuật toán boosting, chọn siêu tham số bằng các fold training hiện có. Giữ Log Loss làm tiêu chí chính, kiểm tra lỗi D; không tùy tiện đổi threshold hoặc class weight chỉ để tăng recall D trên validation.',
              '- Chỉ chọn cách calibration sau khi thống nhất mô hình; nếu fit calibrator trên 2023–2024, điểm sau calibration trên chính mùa này chỉ là chẩn đoán in-sample. Khóa cấu hình trước vòng test cuối.',
              '- Mở rộng B/C còn phụ thuộc kiểm chứng lịch sử cầu thủ và thời điểm announced XI; không coi FPL starts sau trận là thông tin chắc chắn có ở T−60.', '',
              '## Chạy lại', '',
              '```powershell', 'python -m pip install -r requirements-modeling.txt',
              'python -m unittest discover -s tests -v', 'python scripts/train_model_A.py',
              'python scripts/report_model_A.py', '```', '',
              'Lệnh training ghi lại thư mục A_dev_v1; cần lưu bản cũ và tăng run_id khi thay đổi cấu hình. '
              'Lệnh report chỉ đọc mô hình, xác minh và tạo lại báo cáo/ảnh. Chỉ nạp joblib do chính dự án tạo từ nguồn tin cậy.', '',
              'Các đầu ra: results.json, validation_predictions.csv, walk_forward_metrics.csv, validation_metrics.csv, '
              'reliability_bins.csv, group_permutation_importance.csv, standardized_coefficients.csv, artifact_verification.json.', '']
    (OUT/'report.vi.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps(verification,indent=2))


if __name__ == '__main__':
    main()
