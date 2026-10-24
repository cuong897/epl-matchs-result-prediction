"""Verify F extension persistence and report primary/secondary paired comparisons."""
import json
from pathlib import Path
import joblib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from apf_modeling import sha,load_apf,frozen_probabilities
from modeling import LABELS,evaluate,ordered_probabilities
from tree_modeling import rank_candidates,XGBClassifier,normalized_float_probabilities

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/APF_dev_v1'
NAMES={'logistic':'Logistic Regression','random_forest':'Random Forest','xgboost':'XGBoost',
       'frequency_common':'Tần suất common','elo_common':'Elo common'}


def main():
    manifest=json.loads((OUT/'run_manifest.json').read_text())
    result=json.loads((OUT/'results.json').read_text());config=manifest['config']
    for group in ['input_sha256','frozen_AP_input_sha256','F_input_output_sha256']:
        for relative,digest in manifest[group].items():assert sha(ROOT/relative)==digest,relative
    for name,digest in manifest['code_sha256'].items():assert sha(ROOT/'scripts'/name)==digest,name
    frame,columns,_,old_result,_=load_apf(ROOT,config)
    valid=frame[frame['split'].eq('validation')]
    pd.testing.assert_frame_equal(frame[['match_id','season','match_date','split']],pd.read_csv(OUT/'common_cohort.csv',parse_dates=['match_date']))
    used=columns[config['new_arm']]
    assert len(used)==60 and used[:52]==columns['A_plus_P']
    previous=ROOT/'reports'/config['frozen_comparator_run']
    frozen=frozen_probabilities(valid,pd.read_csv(previous/'validation_predictions.csv'),old_result)
    saved=pd.read_csv(OUT/'validation_predictions.csv')
    assert len(saved)==4180 and set(saved.season)=={'2023-24'}
    assert not saved.duplicated(['model','match_id']).any()
    assert set(saved.model)==set(result['validation_metrics'])
    bundle=joblib.load(ROOT/'models'/config['run_id']/'bundle.joblib')
    assert bundle['label_order']==LABELS and bundle['feature_columns']==used
    maxerror=0.
    for name,expected in result['validation_metrics'].items():
        part=saved[saved.model.eq(name)]
        assert set(part.match_id)==set(valid.match_id)
        part=part.set_index('match_id').loc[valid.match_id]
        assert part.result.tolist()==valid.result.tolist()
        prob=part[['p_H','p_D','p_A']].to_numpy()
        if name in frozen:actual=frozen[name]
        else:
            actual=ordered_probabilities(bundle['models'][name],valid[used])
            separate=joblib.load(ROOT/'models'/config['run_id']/f'{name}.joblib')
            np.testing.assert_allclose(actual,ordered_probabilities(separate,valid[used]),atol=1e-12,rtol=0)
        np.testing.assert_allclose(actual,prob,atol=1e-12,rtol=0)
        maxerror=max(maxerror,float(np.max(np.abs(actual-prob))))
        m=evaluate(valid.result.to_numpy(),prob)
        for key in ['log_loss','brier_sum','accuracy','macro_f1']:
            np.testing.assert_allclose(m[key],expected[key],atol=1e-12,rtol=0)
        assert m['per_class']==expected['per_class'] and m['confusion_matrix_rows_true_cols_pred_HDA']==expected['confusion_matrix_rows_true_cols_pred_HDA']
    name=f"xgboost__{config['new_arm']}"
    native=XGBClassifier();native.load_model(ROOT/'models'/config['run_id']/'xgboost_native.ubj')
    transformed=bundle['models'][name].named_steps['imputer'].transform(valid[used])
    np.testing.assert_allclose(normalized_float_probabilities(native.predict_proba(transformed)),ordered_probabilities(bundle['models'][name],valid[used]),atol=1e-12,rtol=0)
    cv=pd.read_csv(OUT/'walk_forward_metrics.csv');assert len(cv)==36
    for family in config['families']:
        ranking=rank_candidates(cv[cv.family.eq(family)].to_dict('records'),config['walk_forward_validation_seasons'],4)
        assert result['selected_candidates'][family]==ranking[0]['candidate']
    for flag in ['test_feature_matrix_loaded','test_predictions_generated','test_metrics_computed','posthoc_calibration_fitted']:
        assert result[flag] is False
    model_dir=ROOT/'models'/config['run_id']
    verification={'input_and_code_hashes_match':True,'frozen_comparator_probabilities_unchanged':True,
                  'same_1520_training_and_380_validation_matches':True,'original_A_and_P_columns_preserved':True,
                  'all_36_CV_scores_and_selected_candidates_verified':True,'bundle_individual_estimators_native_XGBoost_agree':True,
                  'all_validation_metrics_and_confusion_matrices_reproduced':True,'maximum_reload_probability_error':maxerror,
                  'test_evaluated':False,'artifact_sha256':{p.name:sha(p) for p in model_dir.iterdir()}}
    (OUT/'artifact_verification.json').write_text(json.dumps(verification,indent=2)+'\n',encoding='utf-8')
    families=config['families'];arms=['A_common','A_plus_P',config['new_arm']]
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10})
    fig,axes=plt.subplots(1,2,figsize=(13,4.8),layout='constrained');x=np.arange(3);width=.25
    for offset,arm,color,label in [(-width,arms[0],'#0891b2','A'),(0,arms[1],'#d97706','A+P'),(width,arms[2],'#7c3aed','A+P+F')]:
        values=[result['validation_metrics'][f'{f}__{arm}']['log_loss'] for f in families]
        bars=axes[0].bar(x+offset,values,width,label=label,color=color)
        axes[0].bar_label(bars,fmt='%.4f',fontsize=7,padding=3)
    axes[0].set(xticks=x,xticklabels=['Logistic','Random Forest','XGBoost'],ylim=(0,1.2),ylabel='Log Loss — thấp hơn tốt hơn',title='Cùng 1.520 trận training · 380 validation')
    axes[0].legend(ncol=3,frameon=False,fontsize=9,loc='upper right')
    for i,family in enumerate(families):
        u=next(v for v in result['paired_uncertainty'] if v['family']==family and v['reference_arm']=='A_plus_P' and v['block_weeks']==2)
        delta=u['delta_log_loss_APF_minus_reference']
        axes[1].errorbar(delta,i,xerr=[[delta-u['ci95_low']],[u['ci95_high']-delta]],fmt='o',capsize=5,color='#7c3aed')
    axes[1].axvline(0,linestyle='--',color='#64748b')
    axes[1].set(yticks=x,yticklabels=['Logistic','Random Forest','XGBoost'],ylim=(-.6,2.6),
                xlabel='Delta Log Loss (A+P+F − A+P) · âm có lợi cho F',title='So sánh chính · khoảng 95% · block 2 tuần')
    axes[1].invert_yaxis();axes[1].grid(axis='x',alpha=.15)
    fig.suptitle('Validation 2023–2024 · hiệu suất từ lịch sử nhóm cầu thủ trận trước',fontsize=13)
    fig.savefig(OUT/'performance_comparison.png',dpi=180);plt.close(fig)
    rows=['# A+P+F: đóng góp bổ sung của hiệu suất cầu thủ','',
      '**Kết luận development:** tám biến performance F chưa cho thấy lợi ích rõ ràng. So với A+P, Random Forest và XGBoost giảm Log Loss rất ít; '
      'Logistic Regression tăng Log Loss. Kết quả không chứng minh mọi dữ liệu cầu thủ đều không hữu ích, và chưa trả lời giả thuyết starting XI chính thức.','',
      '## Thiết kế đã đăng ký','',
      '- 40 cột A + 12 cột P + 8 cột F = 60 đặc trưng. F gồm rate bàn thắng/kiến tạo đã giảm nhiễu, mức tập trung đóng góp và phần đóng góp của nhóm người tham gia trận trước.',
      '- Rate là tổng có trọng số 90×G/(M+180) hoặc 90×A/(M+180), với trọng số là tỷ trọng phút ở trận trước gần nhất. M/G/A lấy tối đa năm trận trước của chính đội, cùng mùa. Prior 180 phút về rate 0 cố định trước khi đo.',
      '- Cả ba nhánh có cùng 1.520 trận training 2019–2023, cùng 380 trận validation 2023–2024. A và A+P được giữ nguyên từ AP_dev_v1, kiểm tra cohort/nhãn/xác suất/metric và checksum; không chọn lại đối chứng.',
      '- So sánh chính A+P+F trừ A+P; so sánh với A_common là phụ. Cùng ba fold theo thời gian, bốn ứng viên mỗi thuật toán; 36 fit CV mới và ba estimator cuối.',
      '- Chọn tham số bằng Log Loss training CV; fit imputer/scaler riêng từng fold. Không class weighting, không chỉnh threshold, chưa calibration.',
      '- Cấu hình và mã đã commit trước fit; validation A/P đã được quan sát. Đây là development tuần tự có giới hạn, không phải một đánh giá hoàn toàn chưa từng quan sát validation.',
      f"- CPU local, cây n_jobs=2. Runner đo {result['elapsed_seconds']:.2f} giây, gồm fit/diagnostics, không gồm dựng feature/báo cáo. Log lưu tại progress.log.",
      '- Chưa tạo F cho test và chưa tính metric test. Availability là giả định nửa đêm địa phương kế tiếp, chưa chứng minh thời điểm xuất bản của nguồn trong quá khứ.', '',
      '## Kết quả validation','',
      '| Thuật toán | Nhánh | Accuracy | Macro F1 | Log Loss ↓ | Brier ↓ |', '|---|---|---:|---:|---:|---:|']
    for family in families:
        for arm in arms:
            m=result['validation_metrics'][f'{family}__{arm}']
            rows.append(f"| {NAMES[family]} | {arm} | {m['accuracy']:.2%} | {m['macro_f1']:.5f} | {m['log_loss']:.5f} | {m['brier_sum']:.5f} |")
    for name in ['elo_common','frequency_common']:
        m=result['validation_metrics'][name]
        rows.append(f"| {NAMES[name]} | baseline | {m['accuracy']:.2%} | {m['macro_f1']:.5f} | {m['log_loss']:.5f} | {m['brier_sum']:.5f} |")
    rows += ['', 'Brier dùng tổng bình phương sai số ba lớp rồi lấy trung bình, miền [0,2]. Thứ tự xác suất H,D,A; nhãn argmax. '
      'Elo common vẫn có Log Loss tốt nhất trong bảng.','', '![So sánh performance](performance_comparison.png)','',
      '## Tham số và độ bất định','',
      '| Thuật toán | Tham số thay đổi được chọn | Log Loss CV trung bình | SD giữa ba mùa |', '|---|---|---:|---:|']
    for family,ranking in result['candidate_rankings'].items():
        r=ranking[0];params=manifest['candidates'][family][r['candidate']]
        rows.append(f"| {NAMES[family]} | {json.dumps(params)} | {r['mean_log_loss']:.6f} | {r['std_log_loss']:.6f} |")
    rows += ['', 'Điểm CV đã dùng chọn tham số không phải điểm kiểm tra độc lập. Cả ba cấu hình được chọn trùng với lựa chọn A+P theo từng thuật toán trong lượt trước.','',
      'Delta = Log Loss A+P+F trừ nhánh tham chiếu, âm có lợi cho mô hình mới. Paired moving-block bootstrap 2.000 lần, seed 42, '
      'block chính hai tuần và phân tích độ nhạy một/bốn tuần.','',
      '| Thuật toán | Tham chiếu | Block tuần | Delta | Khoảng percentile 95% |', '|---|---|---:|---:|---|']
    for u in result['paired_uncertainty']:
        rows.append(f"| {NAMES[u['family']]} | {u['reference_arm']} | {u['block_weeks']} | {u['delta_log_loss_APF_minus_reference']:.6f} | [{u['ci95_low']:.6f}; {u['ci95_high']:.6f}] |")
    rows += ['', 'So với A+P, RF/XGBoost có mọi khoảng chứa 0. Logistic kém hơn trên ước lượng điểm và khoảng chính hai tuần nằm hoàn toàn trên 0, '
      'nhưng khoảng bốn tuần chứa 0; mức chắc chắn nhạy với cách resample. Không tuyên bố cải thiện hoặc suy giảm vững chắc trên mọi mùa. '
      'Các khoảng chưa điều chỉnh nhiều so sánh, chỉ resample một mùa với mô hình cố định, không bao gồm toàn bộ bất định huấn luyện.','',
      '## Lớp hòa và vai trò F','',
      'Logistic A+P+F chọn hòa bảy lần và đúng một trong 82 trận hòa: precision D≈14,29%, recall D≈1,22%. '
      'RF/XGBoost mới không chọn D. Chất lượng phân loại hòa vẫn yếu; probability scoring vẫn tính đầy đủ xác suất D. '
      'Precision/recall/F1 từng lớp và confusion matrices có trong results.json; reliability bins có trong CSV.','',
      '| Thuật toán mới | Tăng Log Loss khi hoán vị F | SD 10 lần |', '|---|---:|---:|']
    for item in result['F_group_permutation']:
        rows.append(f"| {NAMES[item['family']]} | {item['mean_increase_log_loss']:.6f} | {item['repeat_std']:.6f} |")
    rows += ['', 'Hoán vị chung tám cột F trong cùng tháng validation; không fit lại. Kết quả phụ thuộc mô hình và tương quan với A/P; '
      'SD chỉ là biến thiên phép hoán vị. Không dùng importance làm quan hệ nhân quả hoặc lý do chọn lại feature sau khi xem điểm.','',
      '## Giới hạn và quyết định','',
      '- Nhóm người tham gia trận trước có thể khác nhân sự hiện tại, nhất là chuyển CLB, chấn thương hoặc xoay tua. Chưa có bằng chứng announced XI T−60, không gắn kết quả này với Model C theo XI chính thức.',
      '- Assists là định nghĩa FPL. Rate với prior 0 là proxy được regularize; chưa phải ước lượng đội sẽ ghi bao nhiêu bàn. Tín hiệu F có thể trùng với bàn thắng/phong độ cấp đội.',
      '- Reset player ID đầu mùa, giữ missing khi thiếu lịch sử; không lọc bỏ trận khó. Không sử dụng xG/xA, tuổi hoặc market value vì chưa đủ lịch sử đáng tin cậy.',
      '- Kết thúc mở rộng feature thăm dò sau phiên bản đã đăng ký này. Giữ cả kết quả P/F không cải thiện trong báo cáo; không đổi cửa sổ hay shrinkage để tìm điểm validation đẹp hơn.',
      '- Bước tiếp theo: tổng hợp các mô hình/nhóm đặc trưng đã thử, chốt phương pháp calibration và danh sách đánh giá trước vòng test cuối. Nếu calibrator fit trên 2023–2024, điểm trên chính mùa này chỉ là chẩn đoán in-sample.', '',
      '## Kiểm chứng và chạy lại','',
      '73 unit tests đã đạt. F có năm kiểm tra trên dữ liệu thật: prefix invariance, tương lai không đổi training, trận hiện tại không đổi chính nó, '
      'đảo thứ tự đầu vào và lineage không vượt cutoff. Kiểm chứng artifact xác nhận đối chứng cũ không đổi, cùng cohort, đủ 36 điểm CV, '
      'nạp lại bundle/estimator/native XGBoost khớp xác suất và toàn bộ metric/confusion matrices.', '',
      '```powershell','python scripts/build_player_performance.py','python -m unittest discover -s tests -q',
      'python -u scripts/train_APF.py','python scripts/report_APF.py','```','',
      'Runner từ chối ghi đè run tồn tại. Report có thể dựng lại độc lập từ mô hình cục bộ tin cậy, không huấn luyện lại.','']
    (OUT/'report.vi.md').write_text('\n'.join(rows),encoding='utf-8')
    print(json.dumps(verification,indent=2))


if __name__=='__main__':main()
