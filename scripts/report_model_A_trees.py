"""Reload and verify tree artifacts, then render the development comparison."""
import hashlib
import json
from pathlib import Path

import joblib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from modeling import LABELS, evaluate, load_development, ordered_probabilities
from tree_modeling import XGBClassifier, normalized_float_probabilities

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'reports/A_trees_v1'
NAMES = {'frequency':'Tần suất lịch sử','elo_threeway':'Elo','logistic_A':'Logistic A',
         'random_forest':'Random Forest','xgboost':'XGBoost','always_home':'Luôn chọn H'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest = json.loads((OUT/'run_manifest.json').read_text())
    result = json.loads((OUT/'results.json').read_text())
    config = manifest['config']
    assert sha(ROOT/'research/model_A_tree_config.json') == manifest['config_sha256']
    for path,expected in manifest['input_sha256'].items():assert sha(ROOT/path)==expected,path
    for name,expected in manifest['code_sha256'].items():assert sha(ROOT/'scripts'/name)==expected,name
    assert sha(ROOT/config['previous_run'])==manifest['previous_results_sha256']
    assert sha(ROOT/'reports/model_A_development/validation_predictions.csv')==manifest['previous_predictions_sha256']
    model_dir = ROOT/'models'/config['run_id']
    bundle = joblib.load(model_dir/'bundle.joblib')
    assert bundle['label_order'] == LABELS
    frame = load_development(ROOT,bundle['feature_columns'])
    valid = frame[frame['split'].eq('validation')]
    saved = pd.read_csv(OUT/'validation_predictions.csv')
    assert set(saved.model)==set(NAMES)-{'always_home'}
    assert set(saved.season)=={'2023-24'} and len(saved)==1900
    assert not saved.duplicated(['model','match_id']).any()
    for flag in ['test_feature_matrix_loaded','test_predictions_generated','test_metrics_computed','posthoc_calibration_fitted']:
        assert result[flag] is False
    p_by_model = {}
    reload_errors = {}
    for name in NAMES:
        if name=='always_home':continue
        part = saved[saved.model.eq(name)].set_index('match_id').loc[valid.match_id]
        assert part.result.tolist()==valid.result.tolist()
        p = part[['p_H','p_D','p_A']].to_numpy()
        m = evaluate(valid.result.to_numpy(),p)
        for key in ['accuracy','macro_f1','log_loss','brier_sum']:
            np.testing.assert_allclose(m[key],result['validation_metrics'][name][key],atol=1e-12,rtol=0)
        assert m['confusion_matrix_rows_true_cols_pred_HDA']==result['validation_metrics'][name]['confusion_matrix_rows_true_cols_pred_HDA']
        assert m['per_class']==result['validation_metrics'][name]['per_class']
        p_by_model[name]=p
        if name in bundle['models']:
            for model in [bundle['models'][name],joblib.load(model_dir/f'{name}.joblib')]:
                actual = ordered_probabilities(model,valid[bundle['feature_columns']])
                np.testing.assert_allclose(actual,p,atol=1e-12,rtol=0)
            reload_errors[name]=float(np.max(np.abs(actual-p)))
    # Native XGBoost persistence must agree after applying the saved imputer.
    native = XGBClassifier()
    native.load_model(model_dir/'xgboost_native.ubj')
    transformed = bundle['models']['xgboost'].named_steps['imputer'].transform(valid[bundle['feature_columns']])
    native_p = normalized_float_probabilities(native.predict_proba(transformed))
    np.testing.assert_allclose(native_p,p_by_model['xgboost'],atol=1e-12,rtol=0)
    verification = {'config_input_and_code_hashes_match':True,
                    'prior_baseline_results_unchanged':True,
                    'same_380_validation_matches_all_models':True,
                    'reloaded_bundle_and_estimators_match_saved_predictions':True,
                    'native_xgboost_matches_pipeline':True,
                    'all_exported_metrics_and_confusion_matrices_reproduced':True,
                    'maximum_reload_errors':reload_errors,
                    'test_predictions_generated':False,
                    'artifact_sha256':{str(p.relative_to(ROOT)):sha(p) for p in model_dir.iterdir() if p.is_file()}}
    (OUT/'artifact_verification.json').write_text(json.dumps(verification,indent=2)+'\n',encoding='utf-8')
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10})
    fig,axes = plt.subplots(1,3,figsize=(15,4.5),layout='constrained',gridspec_kw={'width_ratios':[1.25,1,1]})
    names = list(p_by_model)
    losses = [result['validation_metrics'][n]['log_loss'] for n in names]
    bars = axes[0].barh([NAMES[n] for n in names],losses,color=['#94a3b8','#0891b2','#2563eb','#16a34a','#d97706'])
    axes[0].bar_label(bars,fmt='%.4f',padding=3,fontsize=9)
    axes[0].invert_yaxis()
    axes[0].set(xlim=(0,1.2),xlabel='Log Loss — thấp hơn tốt hơn',title='Xác suất H/D/A')
    for ax,name in zip(axes[1:],['random_forest','xgboost']):
        cm = np.array(result['validation_metrics'][name]['confusion_matrix_rows_true_cols_pred_HDA'])
        ax.imshow(cm,cmap='Blues',vmin=0,vmax=150)
        for i in range(3):
            for j in range(3):ax.text(j,i,str(cm[i,j]),ha='center',va='center',color='white' if cm[i,j]>90 else '#172554',fontsize=14)
        ax.set(xticks=range(3),xticklabels=LABELS,yticks=range(3),yticklabels=LABELS,
               xlabel='Nhãn dự đoán',ylabel='Nhãn thực tế',title=NAMES[name])
    fig.suptitle('Validation 2023–2024 · cùng 380 trận · chưa calibration',fontsize=14)
    fig.savefig(OUT/'validation_comparison.png',dpi=180)
    plt.close(fig)
    bins = pd.read_csv(OUT/'reliability_bins.csv')
    fig,axes = plt.subplots(1,3,figsize=(12,4.3),layout='constrained')
    for ax,label in zip(axes,LABELS):
        ax.plot([0,1],[0,1],'--',color='#94a3b8')
        for name,color in [('elo_threeway','#0891b2'),('random_forest','#16a34a'),('xgboost','#d97706')]:
            d = bins[bins.model.eq(name)&bins['class'].eq(label)]
            ax.plot(d.mean_predicted,d.observed_fraction,'o-',color=color,label=NAMES[name])
        ax.set(xlim=(0,1),ylim=(0,1),xlabel='Xác suất trung bình',ylabel='Tần suất thực tế',title=label)
        ax.grid(alpha=.15)
    axes[0].legend(fontsize=9)
    fig.suptitle('Reliability theo lớp · 5 nhóm phân vị · chẩn đoán validation',fontsize=13)
    fig.savefig(OUT/'validation_reliability.png',dpi=180)
    plt.close(fig)

    rows = ['# So sánh Random Forest và XGBoost với baseline Model A','',
      '**Run A_trees_v1: chỉ development, chưa dự đoán hoặc tính metric test 2024–2025.**','',
      '## Kết quả chính','',
      'Random Forest và XGBoost đều đạt Accuracy 57,89%, nhưng Elo vẫn có Log Loss thấp nhất trên validation. '
      'Random Forest có Brier thấp nhất với chênh lệch nhỏ. Cả hai mô hình cây không chọn nhãn hòa lần nào; chưa giải quyết được hạn chế lớp D.','',
      '| Mô hình | Accuracy | Macro F1 | Log Loss ↓ | Brier ↓ |','|---|---:|---:|---:|---:|']
    for name,m in result['validation_metrics'].items():
        ll = f"{m['log_loss']:.5f}" if 'log_loss' in m else '—'
        brier = f"{m['brier_sum']:.5f}" if 'brier_sum' in m else '—'
        rows.append(f"| {NAMES[name]} | {m['accuracy']:.2%} | {m['macro_f1']:.5f} | {ll} | {brier} |")
    rows += ['', '![So sánh validation](validation_comparison.png)','',
      'Brier sử dụng tổng bình phương sai số ba lớp rồi lấy trung bình, miền [0,2]. Tất cả so sánh trên cùng 380 trận và cùng nhãn. '
      'Kết quả baseline được nạp từ run trước, kiểm tra ID, nhãn, metric và hash; không huấn luyện lại để chọn baseline thuận lợi hơn.','',
      '## Thiết kế đã ghi trước lượt chạy','',
      '- Huấn luyện cuối trên 3.040 trận 2015–2016 đến 2022–2023, đánh giá 380 trận 2023–2024. Hai mùa warm-up chỉ phục vụ tạo đặc trưng.',
      '- Mỗi thuật toán thử bốn cấu hình trên ba fold walk-forward trong training: 2020–2021, 2021–2022, 2022–2023. Tổng cộng 24 lượt fit CV và hai lượt fit cuối. Logistic Regression trước đó cũng có bốn cấu hình; số ứng viên bằng nhau không có nghĩa chi phí tính toán hay độ rộng tìm kiếm tương đương.',
      '- Chọn cấu hình theo Log Loss trung bình ba fold, không dùng điểm validation cuối để chọn tham số. Không early stopping, không đổi ngưỡng argmax, không cân bằng lớp, chưa calibration.',
      '- Cùng 40 đặc trưng đầu vào. Median imputation và missing indicators fit riêng trong training từng fold. Mô hình cây không cần StandardScaler.',
      '- Cấu hình này được ghi sau khi đã thấy kết quả Logistic/Elo, nhưng trước khi chạy RF/XGBoost. Đây là development tuần tự, không phải toàn bộ kế hoạch đã đăng ký trước khi xem bất kỳ validation nào.',
      '- Thiết bị: CPU local, XGBoost device=cpu và tree_method=hist; n_jobs=2 ở cả hai mô hình. GPU không được dùng.',
      f"- Thời gian đo trong runner: {result['elapsed_seconds']:.2f} giây, gồm CV, fit cuối và diagnostics; không gồm cài thư viện hay dựng báo cáo. XGBoost {manifest['runtime']['xgboost']}; seed 42.",
      '- Snapshot đặc trưng chỉ dùng các ngày lịch trước theo Europe/London. Thời điểm dữ liệu nguồn thực sự công bố chưa được chứng minh; giữ giới hạn tái dựng point-in-time như báo cáo trước.',
      '- Shared outcomes được đọc để lọc ID development; ma trận đặc trưng test không được nạp, nhãn test không dùng cho fit/scoring.', '',
      '## Lựa chọn siêu tham số','',
      '| Thuật toán | Ứng viên | Tham số thay đổi | Log Loss CV trung bình | SD giữa 3 mùa |',
      '|---|---:|---|---:|---:|']
    for name,ranking in result['candidate_rankings'].items():
        for r in ranking:
            params = config[f'{name}_candidates'][r['candidate']]
            rows.append(f"| {NAMES[name]} | {r['candidate']} | {json.dumps(params)} | {r['mean_log_loss']:.6f} | {r['std_log_loss']:.6f} |")
    rows += ['', 'Cấu hình được chọn: RF có 300 cây, max_depth=4, min_samples_leaf=30, max_features=0,7; '
      'XGBoost có max_depth=2, n_estimators=100, learning_rate=0,03, min_child_weight=10, reg_lambda=5, reg_alpha=0,1, subsample=colsample_bytree=0,8. '
      'Các tham số cố định khác nằm trong run_manifest.json. Điểm CV đã dùng chọn cấu hình không phải kết quả test độc lập.','',
      '## Độ bất định','',
      'Paired moving-block bootstrap theo tuần lịch, 2.000 lần, seed 42. Delta = Log Loss mô hình cây trừ mô hình tham chiếu; âm có lợi cho mô hình cây. '
      'Block chính là hai tuần; một và bốn tuần dùng phân tích độ nhạy.','',
      '| Mô hình | Tham chiếu | Block tuần | Delta | Khoảng percentile 95% |','|---|---|---:|---:|---|']
    for u in result['paired_uncertainty_validation']:
        rows.append(f"| {NAMES[u['model']]} | {NAMES[u['reference']]} | {u['block_weeks']} | {u['delta_log_loss_model_minus_reference']:.5f} | [{u['ci95_low']:.5f}; {u['ci95_high']:.5f}] |")
    rows += ['', 'Tất cả bốn so sánh có khoảng chính hai tuần chứa 0; chưa có bằng chứng vững chắc rằng mô hình cây tốt hơn Elo hoặc Logistic A. '
      'XGBoost so với Elo có khoảng một tuần không chứa 0 theo hướng XGBoost kém hơn, nhưng kết luận này không bền qua các độ dài block. '
      'Đây là khoảng mô tả chưa điều chỉnh cho nhiều so sánh, chỉ resample một mùa với mô hình cố định, không phản ánh đầy đủ bất định do huấn luyện hoặc thay đổi giữa các mùa.','',
      '## Phân tích nhãn hòa và xác suất','',
      'Có 82 trận hòa thực tế. RF và XGBoost đều có recall D=0 vì không chọn D bằng argmax. Không sửa ngưỡng trên validation để làm đẹp kết quả. '
      'Xác suất D vẫn được dự đoán và tham gia đầy đủ vào Log Loss/Brier.','',
      '| Mô hình | Số dự đoán D | Recall D | Xác suất D trung bình | Tỷ lệ D thực tế |',
      '|---|---:|---:|---:|---:|']
    for name,p in p_by_model.items():
        m = result['validation_metrics'][name]
        rows.append(f"| {NAMES[name]} | {m['predicted_label_counts']['D']} | {m['per_class']['D']['recall']:.2%} | {p[:,1].mean():.2%} | {valid.result.eq('D').mean():.2%} |")
    rows += ['', '![Reliability](validation_reliability.png)','',
      'Đường reliability là chẩn đoán validation, chưa phải xác suất đã hiệu chỉnh. Tỷ lệ trung bình gần tỷ lệ thực tế chưa đảm bảo calibration từng trận. '
      'Wilson intervals trong CSV giả định độc lập, không dùng làm kiểm định chính thức cho chuỗi trận có phụ thuộc. '
      'Precision/recall/F1 đầy đủ từng lớp và confusion matrices nằm trong results.json.','',
      '## Vai trò các nhóm đặc trưng','',
      'Hoán vị đồng thời các cột trong từng nhóm, trong cùng tháng validation, 10 lần; không fit lại hoặc chọn lại tham số. '
      'SD dưới đây là độ biến thiên giữa các lần hoán vị, không phải khoảng tin cậy của tác động.','',
      '| Mô hình | Nhóm | Tăng Log Loss | SD hoán vị |','|---|---|---:|---:|']
    for row in result['permutation_groups_validation']:
        rows.append(f"| {NAMES[row['model']]} | {row['group']} | {row['mean_increase_log_loss']:.5f} | {row['repeat_std']:.5f} |")
    rows += ['', 'Nhóm Elo có tác động lớn nhất trong cả hai mô hình. Không suy ra quan hệ nhân quả hoặc lập tức bỏ nhóm có importance nhỏ/âm: '
      'các đặc trưng tương quan có thể thay thế nhau, và hoán vị tạo tổ hợp kém thực tế.','',
      '## Kiểm thử, lưu mô hình và bước kế tiếp','',
      '- 39 unit tests đạt, gồm bốn test mới cho mapping H/D/A, sai số float32, đủ fold cho mọi ứng viên và preprocessing chỉ fit trên training.',
      '- Kiểm chứng artifact: hash cấu hình/đầu vào/code khớp; baseline cũ không đổi; cùng cohort 380 trận; nạp lại bundle và estimator riêng tái tạo xác suất; file XGBoost native UBJSON khớp pipeline; metric và confusion matrix tái tính khớp.',
      '- XGBoost mã hóa H=0, D=1, A=2. Chuẩn hóa lại sai số softmax float32 nhỏ hơn 1e-6 trước scoring; xác suất sai lớn hơn bị từ chối. Không đổi định nghĩa metric hoặc thứ tự nhãn.',
      '- Giữ Elo làm mốc so sánh mạnh. Chưa chọn mô hình cuối hoặc tuyên bố cây vượt baseline chỉ dựa trên Accuracy.',
      '- Mốc tiếp theo nên tập trung audit lịch sử cầu thủ trong các mùa training để thiết kế so sánh A/P trên cùng cohort. Nếu không xác minh được announced XI ở T−60, chỉ dùng player/expected-lineup proxy từ quá khứ và không gọi đó là Model B/C đội hình chính thức.',
      '- Sau khi chốt các nhóm đặc trưng và mô hình sẽ quyết định calibration, khóa cấu hình rồi mới chạy test cuối. Validation hiện đã được quan sát, không còn là tập kiểm tra độc lập chưa từng xem.', '',
      '## Chạy và xem log','',
      '```powershell','python -m pip install -r requirements-modeling.txt',
      'python -m unittest discover -s tests -v',
      'python -u scripts/train_model_A_trees.py 2>&1 | Tee-Object -FilePath training-trees.log',
      'python scripts/report_model_A_trees.py','```','',
      'Runner từ chối ghi đè nếu thư mục run đã tồn tại. Để chạy thí nghiệm mới, tạo cấu hình/run ID mới và điều chỉnh đường dẫn report tương ứng; '
      'không xóa kết quả cũ. Script report hiện trỏ tới A_trees_v1, chỉ xác minh và dựng lại báo cáo. Chỉ nạp joblib do dự án tạo từ nguồn tin cậy.','',
      'Tham khảo API: [XGBoost Python API](https://xgboost.readthedocs.io/en/stable/python/python_api.html), '
      '[RandomForestClassifier](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestClassifier.html). '
      'Phiên bản thực thi được ghi trong run_manifest.json; tài liệu stable có thể mới hơn bản đã cài.','']
    (OUT/'report.vi.md').write_text('\n'.join(rows),encoding='utf-8')
    print(json.dumps(verification,indent=2))


if __name__=='__main__':main()
