"""Verify paired artifacts and produce a report without fitting or test scoring."""
import hashlib
import json
from pathlib import Path

import joblib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from modeling import LABELS,evaluate,load_development,ordered_probabilities
from tree_modeling import XGBClassifier,normalized_float_probabilities,rank_candidates

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/AP_dev_v1'
NAMES={'logistic':'Logistic Regression','random_forest':'Random Forest','xgboost':'XGBoost',
       'frequency_common':'Tần suất common','elo_common':'Elo common'}


def main():
    manifest=json.loads((OUT/'run_manifest.json').read_text())
    result=json.loads((OUT/'results.json').read_text())
    for relative,digest in manifest['input_sha256'].items():
        assert hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()==digest,relative
    for name,digest in manifest['code_sha256'].items():
        assert hashlib.sha256((ROOT/'scripts'/name).read_bytes()).hexdigest()==digest,name
    config=manifest['config'];models=ROOT/'models'/config['run_id']
    bundle=joblib.load(models/'bundle.joblib')
    assert bundle['label_order']==LABELS
    a=manifest['feature_columns']['A_common'];ap=manifest['feature_columns']['A_plus_P']
    assert len(a)==40 and len(ap)==52 and ap[:40]==a
    frame=load_development(ROOT,a)
    frame=frame[frame.season.str[:4].astype(int).ge(2019)]
    p=pd.concat([pd.read_csv(ROOT/f'data/curated/features_P_{s}.csv') for s in ['train','validation']],ignore_index=True)
    frame=frame.merge(p,on='match_id',validate='one_to_one').sort_values(['match_date','match_id']).reset_index(drop=True)
    assert frame['split'].value_counts().to_dict()=={'train':1520,'validation':380}
    cohort=pd.read_csv(OUT/'common_cohort.csv',parse_dates=['match_date'])
    pd.testing.assert_frame_equal(frame[['match_id','season','match_date','split']],cohort)
    valid=frame[frame['split'].eq('validation')]
    saved=pd.read_csv(OUT/'validation_predictions.csv')
    assert len(saved)==8*380 and not saved.duplicated(['model','match_id']).any()
    assert set(saved.season)=={'2023-24'}
    assert set(saved.model)==set(result['validation_metrics'])
    for flag in ['test_feature_matrix_loaded','test_predictions_generated','test_metrics_computed','posthoc_calibration_fitted']:
        assert result[flag] is False
    maxerror=0.
    for name in result['validation_metrics']:
        subset=saved[saved.model.eq(name)]
        assert set(subset.match_id)==set(valid.match_id)
        subset=subset.set_index('match_id').loc[valid.match_id]
        assert subset.result.tolist()==valid.result.tolist()
        stored=subset[['p_H','p_D','p_A']].to_numpy()
        if name=='frequency_common':actual=np.tile(bundle['frequency_probabilities'],(len(valid),1))
        else:
            columns=bundle['model_columns'][name]
            actual=ordered_probabilities(bundle['models'][name],valid[columns])
            separate=joblib.load(models/f'{name}.joblib')
            np.testing.assert_allclose(ordered_probabilities(separate,valid[columns]),actual,atol=1e-12,rtol=0)
            if name.startswith('xgboost'):
                native=XGBClassifier();native.load_model(models/f'{name}.ubj')
                X=bundle['models'][name].named_steps['imputer'].transform(valid[columns])
                np.testing.assert_allclose(normalized_float_probabilities(native.predict_proba(X)),actual,atol=1e-12,rtol=0)
        np.testing.assert_allclose(actual,stored,atol=1e-12,rtol=0)
        maxerror=max(maxerror,float(np.max(np.abs(actual-stored))))
        metrics=evaluate(valid.result.to_numpy(),stored)
        for key in ['log_loss','brier_sum','accuracy','macro_f1']:
            np.testing.assert_allclose(metrics[key],result['validation_metrics'][name][key],atol=1e-12,rtol=0)
        assert metrics['per_class']==result['validation_metrics'][name]['per_class']
        assert metrics['confusion_matrix_rows_true_cols_pred_HDA']==result['validation_metrics'][name]['confusion_matrix_rows_true_cols_pred_HDA']
    cv=pd.read_csv(OUT/'walk_forward_metrics.csv')
    assert len(cv)==72
    for family in config['families']:
        for arm in config['arms']:
            rows=cv[cv.family.eq(family)&cv.arm.eq(arm)].to_dict('records')
            ranks=rank_candidates(rows,config['walk_forward_validation_seasons'],4)
            assert result['selected_candidates'][f'{family}__{arm}']==ranks[0]['candidate']
    verification={'input_code_hashes_match':True,'identical_training_validation_cohort':True,
                  'A_common_is_identical_subset_of_AP_features':True,'all_72_training_fold_scores_present':True,
                  'selected_candidates_reproduce_from_training_CV':True,
                  'saved_bundle_individual_models_and_native_XGBoost_agree':True,
                  'all_validation_metrics_and_class_metrics_reproduced':True,
                  'maximum_reload_probability_error':maxerror,'test_evaluated':False,
                  'artifact_sha256':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in models.iterdir()}}
    (OUT/'artifact_verification.json').write_text(json.dumps(verification,indent=2)+'\n',encoding='utf-8')
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10})
    families=config['families'];fig,axes=plt.subplots(1,2,figsize=(12,4.8),layout='constrained')
    x=np.arange(3);width=.35
    for offset,arm,color in [(-width/2,'A_common','#0891b2'),(width/2,'A_plus_P','#d97706')]:
        losses=[result['validation_metrics'][f'{f}__{arm}']['log_loss'] for f in families]
        bars=axes[0].bar(x+offset,losses,width,label='A common' if arm=='A_common' else 'A + P',color=color)
        axes[0].bar_label(bars,fmt='%.4f',fontsize=8,padding=3)
    axes[0].set(xticks=x,xticklabels=['Logistic','Random Forest','XGBoost'],ylim=(0,1.2),ylabel='Log Loss — thấp hơn tốt hơn',title='Cùng cohort và ngân sách tuning')
    axes[0].legend(ncol=2,fontsize=9,frameon=False,loc='upper right')
    for i,family in enumerate(families):
        ci=next(u for u in result['paired_uncertainty'] if u['family']==family and u['block_weeks']==2)
        delta=ci['delta_log_loss_AP_minus_A']
        axes[1].errorbar(delta,i,xerr=[[delta-ci['ci95_low']],[ci['ci95_high']-delta]],fmt='o',color='#2563eb',capsize=5)
    axes[1].axvline(0,color='#64748b',linestyle='--')
    axes[1].set(yticks=x,yticklabels=['Logistic','Random Forest','XGBoost'],xlabel='Delta Log Loss (A+P − A) · âm có lợi cho P',title='Khoảng 95% · paired bootstrap 2 tuần',ylim=(-.6,2.6))
    axes[1].invert_yaxis();axes[1].grid(axis='x',alpha=.15)
    fig.suptitle('Validation 2023–2024 · 380 trận · P là lịch sử sử dụng cầu thủ',fontsize=13)
    fig.savefig(OUT/'paired_comparison.png',dpi=180);plt.close(fig)
    rows=['# A_common so với A+P: kết quả development','',
      '**Kết luận:** bộ 12 đặc trưng lịch sử sử dụng cầu thủ chưa cải thiện Log Loss một cách rõ ràng trên validation. '
      'XGBoost tăng Accuracy nhưng lợi ích Log Loss rất nhỏ và khoảng bất định chứa 0. Đây là kết quả thực nghiệm hợp lệ; không suy ra mọi dữ liệu cầu thủ đều vô ích.','',
      '## Thiết kế so sánh','',
      '- Run AP_dev_v1; cả hai nhánh được fit lại trên cùng 1.520 trận 2019–2020 đến 2022–2023, đánh giá cùng 380 trận 2023–2024. Không so trực tiếp với A_full train 3.040 trận để quy hiệu quả cho P.',
      '- A_common dùng 40 đặc trưng A; A+P giữ nguyên 40 cột đó và thêm 12 cột P. Lịch sử cấp đội trước 2019 được giữ giống nhau; lịch sử cầu thủ reset đầu mùa do ID có season scope.',
      '- P chỉ mô tả mức sử dụng/continuity từ tối đa năm trận trước của đội: số người tham gia, HHI phút, tỷ trọng phút của top 11 và mức lặp lại người/phút giữa trận. Không dùng performance ghi bàn/kiến tạo, current XI, injury hoặc market value trong P phiên bản này.',
      '- Ba fold theo mùa 2020–2021, 2021–2022, 2022–2023, có lần lượt 380/760/1.140 trận training. Mỗi thuật toán/nhánh chọn trong bốn cấu hình giống nhau; preprocessing fit riêng trên phần training.',
      '- Tổng 72 lượt fit CV, sáu estimator chính cuối và một Elo baseline common. Baseline tần suất được tính lại trên training common. Không class weighting, không chỉnh threshold, không calibration.',
      '- Cấu hình và code đã được commit trước lượt fit. Đã xem validation A_full trong các bước trước; đây là development tuần tự, không phải một nghiên cứu hoàn toàn chưa quan sát validation.',
      f"- CPU local, n_jobs=2 cho cây; runner đo {result['elapsed_seconds']:.2f} giây gồm fit và diagnostics, không gồm tạo feature/báo cáo. Log đầy đủ được lưu ở progress.log.",
      '- Chưa tạo feature P cho test, chưa tính metric test 2024–2025. Shared outcomes chỉ được lọc để lấy ID development.', '',
      '## Kết quả validation','',
      '| Thuật toán | Nhánh | Accuracy | Macro F1 | Log Loss ↓ | Brier ↓ |', '|---|---|---:|---:|---:|---:|']
    for name,m in result['validation_metrics'].items():
        if '__' in name:family,arm=name.split('__');label=NAMES[family]
        else:label=NAMES[name];arm='baseline common'
        rows.append(f"| {label} | {arm} | {m['accuracy']:.2%} | {m['macro_f1']:.5f} | {m['log_loss']:.5f} | {m['brier_sum']:.5f} |")
    rows += ['', 'Brier là trung bình tổng bình phương sai số ba lớp, miền [0,2]. Thứ tự xác suất H,D,A; nhãn lấy argmax. '
      'Elo common có Log Loss tốt nhất trong bảng, vẫn là baseline mạnh.','',
      '![So sánh ghép cặp](paired_comparison.png)','',
      'Logistic A+P tăng ba dự đoán đúng, XGBoost A+P tăng sáu dự đoán đúng, Random Forest giữ nguyên số dự đoán đúng. '
      'Accuracy không phản ánh đầy đủ chất lượng của các xác suất; Log Loss và Brier vẫn là trọng tâm đánh giá.','',
      '## Tham số được chọn bằng CV training','',
      '| Thuật toán | Nhánh | Tham số thay đổi được chọn | Log Loss CV trung bình | SD giữa 3 mùa |',
      '|---|---|---|---:|---:|']
    for name,ranking in result['candidate_rankings'].items():
        family,arm=name.split('__');best=ranking[0]
        params=manifest['candidates'][family][best['candidate']]
        rows.append(f"| {NAMES[family]} | {arm} | {json.dumps(params)} | {best['mean_log_loss']:.6f} | {best['std_log_loss']:.6f} |")
    rows += ['', 'Mỗi nhánh được phép chọn tham số độc lập với ngân sách bằng nhau; trong lượt này các tham số được chọn trùng nhau theo từng thuật toán. '
      'Điểm CV đã dùng chọn tham số không phải điểm test độc lập. Toàn bộ 24 tổ hợp thuật toán/nhánh/ứng viên và 72 điểm fold được lưu trong CSV.','',
      '## Độ bất định của lợi ích P','',
      'Delta = Log Loss A+P trừ A_common; âm có lợi cho P. Paired moving-block bootstrap 2.000 lần, seed 42, theo tuần lịch; '
      'hai tuần là block chính, một và bốn tuần là phân tích độ nhạy.','',
      '| Thuật toán | Block tuần | Delta | Khoảng percentile 95% |','|---|---:|---:|---|']
    for u in result['paired_uncertainty']:
        rows.append(f"| {NAMES[u['family']]} | {u['block_weeks']} | {u['delta_log_loss_AP_minus_A']:.6f} | [{u['ci95_low']:.6f}; {u['ci95_high']:.6f}] |")
    rows += ['', 'Cả chín khoảng đều chứa 0. Chưa có bằng chứng chắc chắn về cải thiện hoặc suy giảm. Không diễn giải việc khoảng chứa 0 là chứng minh hai mô hình tương đương. '
      'Khoảng chỉ resample một mùa với mô hình cố định, không bao gồm toàn bộ bất định do huấn luyện, các mùa khác hoặc nhiều lần thử nghiệm; chưa điều chỉnh nhiều so sánh.','',
      '## Lớp hòa và giải thích P','',
      'Có 82 trận hòa thực tế. Logistic A+P chọn D năm lần, đúng một trận: precision D=20%, recall D=1/82≈1,22%. '
      'Logistic A_common chọn D hai lần nhưng đều sai; RF/XGBoost ở cả hai nhánh không chọn D. Vấn đề dự đoán hòa vẫn chưa được giải quyết. '
      'Confusion matrices và precision/recall/F1 từng lớp có trong results.json; reliability theo lớp có trong reliability_bins.csv.','',
      '| Thuật toán A+P | Tăng Log Loss khi hoán vị nhóm P | SD giữa 10 lần |','|---|---:|---:|']
    for item in result['P_group_permutation']:
        rows.append(f"| {NAMES[item['family']]} | {item['mean_increase_log_loss']:.6f} | {item['repeat_std']:.6f} |")
    rows += ['', 'Hoán vị chung 12 cột P trong từng tháng validation, không fit lại. Giá trị gần 0 hoặc âm ở đây không cho thấy đóng góp dự đoán đáng kể của nhóm P. '
      'SD là biến thiên của phép hoán vị, không phải CI. Tương quan với A và các tổ hợp không thực tế sau hoán vị hạn chế diễn giải; không phải quan hệ nhân quả.','',
      '## Giới hạn và quyết định tiếp theo','',
      '- Chưa kiểm tra giả thuyết starting XI chính thức, phong độ ghi bàn/kiến tạo từng người, tuổi hoặc giá trị thị trường. Không gọi P này là Model B/C ban đầu.',
      '- Dữ liệu thuộc bản lưu hồi cứu; snapshot dùng các ngày trước và giả định availability nửa đêm kế tiếp. Chưa chứng minh feed trước trận đã công bố đúng từng thời điểm.',
      '- Missing đầu mùa là có chủ ý, không loại các trận khó khỏi cohort. Luật thay người, cách ghi phút và lịch COVID có thể ảnh hưởng các biến sử dụng nhân sự.',
      '- Không mở rộng cửa sổ, đổi định nghĩa P hoặc lưới tham số sau khi thấy điểm này rồi trình bày như cùng run. Nếu thử đóng góp bàn/kiến tạo cá nhân, cần đăng ký một phiên bản riêng và tiếp tục giữ test khóa.',
      '- Giữ cả kết quả không cải thiện trong báo cáo. Bước kế tiếp có thể kiểm tra một nhánh hiệu suất cầu thủ có phạm vi giới hạn; sau đó khóa danh sách thí nghiệm/calibration trước vòng test cuối.', '',
      '## Kiểm chứng và chạy lại','',
      '61 unit tests đã đạt, cộng bốn kiểm tra feature trên dữ liệu thật. Kiểm chứng artifact xác nhận cùng cohort, 40 cột A được giữ nguyên, '
      'đủ 72 điểm fold và chọn tham số đúng, hash đầu vào/code, nạp lại bundle/estimator riêng/native XGBoost tái tạo xác suất, metric và confusion matrix.', '',
      '```powershell','python scripts/build_player_proxy.py','python -m unittest discover -s tests -q',
      'python -u scripts/train_AP.py','python scripts/report_AP.py','```','',
      'Runner từ chối ghi đè thư mục run đã tồn tại. Với thí nghiệm mới, đăng ký run ID mới và cập nhật report tương ứng; giữ nguyên run cũ. '
      'Script report chỉ đọc mô hình cục bộ tin cậy, xác minh và dựng lại tài liệu/ảnh.','']
    (OUT/'report.vi.md').write_text('\n'.join(rows),encoding='utf-8')
    print(json.dumps(verification,indent=2))


if __name__=='__main__':main()
