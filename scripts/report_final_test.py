"""Reproduce locked test artifacts and render the report without model changes."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from final_models import sha,feature_frame,predict_registered
from temperature_calibration import transform_temperature
from modeling import LABELS,evaluate

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'reports/final_test_v1'
FAMILIES=['logistic','random_forest','xgboost']
NAMES={'logistic':'Logistic','random_forest':'Random Forest','xgboost':'XGBoost','elo':'Elo','frequency':'Tần suất'}


def main():
    lock=json.loads((ROOT/'research/final_lock.json').read_text())
    result=json.loads((OUT/'results.json').read_text())
    config=json.loads((ROOT/'research/final_evaluation_config.json').read_text())
    registry=json.loads((ROOT/'research/final_model_registry.json').read_text())
    temps=json.loads((ROOT/'reports/final_calibration/temperatures.json').read_text())
    assert sha(ROOT/'research/final_lock.json')==result['lock_sha256']
    for relative,digest in lock['files_sha256'].items():assert sha(ROOT/relative)==digest,relative
    for name,digest in lock['code_sha256'].items():assert sha(ROOT/'scripts'/name)==digest,name
    frame=feature_frame(ROOT,'test');saved=pd.read_csv(OUT/'test_probabilities_before_labels.csv')
    truth=pd.read_csv(ROOT/'data/curated/match_outcomes.csv',usecols=['match_id','result'])
    truth=frame[['match_id']].merge(truth,on='match_id',validate='one_to_one');y=truth.result.to_numpy()
    assert len(saved)==11400 and len(frame)==380
    assert not saved.duplicated(['model','variant','match_id']).any()
    assert sha(OUT/'test_probabilities_before_labels.csv')==result['prediction_export_sha256']
    maxerror=0.;probs={}
    for entry in registry:
        raw=predict_registered(ROOT,entry,frame);variants={'raw':raw}
        if entry['calibrate']:variants['temperature']=transform_temperature(raw,temps[entry['id']]['temperature'])
        for variant,p in variants.items():
            key=entry['id']+'::'+variant
            part=saved[saved.model.eq(entry['id'])&saved.variant.eq(variant)]
            assert len(part)==380 and set(part.match_id)==set(frame.match_id)
            part=part.set_index('match_id').loc[frame.match_id]
            stored=part[['p_H','p_D','p_A']].to_numpy()
            np.testing.assert_allclose(p,stored,atol=1e-12,rtol=0)
            maxerror=max(maxerror,float(np.abs(p-stored).max()))
            actual=evaluate(y,stored);expected=result['metrics'][key]
            for metric in ['log_loss','brier_sum','accuracy','macro_f1']:
                np.testing.assert_allclose(actual[metric],expected[metric],atol=1e-12,rtol=0)
            assert actual['confusion_matrix_rows_true_cols_pred_HDA']==expected['confusion_matrix_rows_true_cols_pred_HDA']
            assert actual['per_class']==expected['per_class'];probs[key]=p
    assert len(probs)==30 and not result['base_estimator_fit_in_test'] and not result['calibrator_fit_in_test']
    verification={'lock_models_calibrators_features_and_code_unchanged':True,'all_30_outputs_have_same_380_matches':True,
                  'all_saved_probabilities_reproduced':True,'all_metrics_class_metrics_confusion_matrices_reproduced':True,
                  'maximum_probability_reload_error':maxerror,'estimator_or_calibrator_refit':False}
    (OUT/'artifact_verification.json').write_text(json.dumps(verification,indent=2)+'\n',encoding='utf-8')
    # Scientific figures: report all feature arms; never select a post-test winner.
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10})
    arms=['A_common','A_plus_P','A_plus_P_plus_F']
    fig,axes=plt.subplots(1,2,figsize=(14,5.8),layout='constrained');x=np.arange(3);width=.25
    for offset,arm,color,label in [(-width,arms[0],'#0891b2','A'),(0,arms[1],'#d97706','A+P'),(width,arms[2],'#7c3aed','A+P+F')]:
        values=[result['metrics'][f'common__{f}__{arm}::temperature']['log_loss'] for f in FAMILIES]
        bars=axes[0].bar(x+offset,values,width,label=label,color=color);axes[0].bar_label(bars,fmt='%.4f',fontsize=7,padding=3)
    axes[0].set(xticks=x,xticklabels=['Logistic','Random Forest','XGBoost'],ylabel='Log Loss — thấp hơn tốt hơn',title='Sau calibration đã khóa trên validation')
    axes[0].set_ylim(0,max(v['log_loss'] for k,v in result['metrics'].items() if k.startswith('common__'))*1.25)
    axes[0].legend(ncol=3,frameon=False,fontsize=9,loc='upper right')
    primary=[u for u in result['paired_feature_comparisons'] if u['variant']=='temperature' and u['block_weeks']==2]
    labels=[]
    for i,u in enumerate(primary):
        delta=u['delta_log_loss'];kind='P − A' if u['model_arm']=='A_plus_P' else 'F thêm vào P'
        labels.append(NAMES[u['family']]+' · '+kind)
        axes[1].errorbar(delta,i,xerr=[[delta-u['family_ci_low']],[u['family_ci_high']-delta]],fmt='none',ecolor='#94a3b8',capsize=4)
        axes[1].errorbar(delta,i,xerr=[[delta-u['ci95_low']],[u['ci95_high']-delta]],fmt='o',color='#2563eb',capsize=3)
    axes[1].axvline(0,linestyle='--',color='#64748b');axes[1].set(yticks=range(6),yticklabels=labels,
        xlabel='Delta Log Loss · âm có lợi cho feature mới',title='Block 2 tuần · xanh 95% · xám 99,17%')
    axes[1].invert_yaxis();axes[1].grid(axis='x',alpha=.15)
    fig.suptitle('Test Premier League 2024–2025 · 380 trận · không refit bằng test',fontsize=14)
    fig.savefig(OUT/'feature_comparison.png',dpi=180);plt.close(fig)
    bins=pd.read_csv(OUT/'reliability_bins.csv');reference=config['primary_practical_reference_chosen_before_test']
    fig,axes=plt.subplots(1,3,figsize=(12,4.3),layout='constrained')
    for ax,label in zip(axes,LABELS):
        ax.plot([0,1],[0,1],'--',color='#94a3b8')
        for variant,color in [('raw','#0891b2'),('temperature','#7c3aed')]:
            d=bins[bins.key.eq(reference+'::'+variant)&bins['class'].eq(label)]
            ax.plot(d.mean_predicted,d.observed_fraction,'o-',color=color,label=variant)
        ax.set(xlim=(0,1),ylim=(0,1),xlabel='Xác suất dự đoán trung bình',ylabel='Tần suất thực tế',title=label);ax.grid(alpha=.15)
    axes[0].legend(fontsize=9);fig.suptitle('Elo A_full · tham chiếu thực dụng đã chọn trước test · reliability',fontsize=13)
    fig.savefig(OUT/'reference_reliability.png',dpi=180);plt.close(fig)
    refraw=result['metrics'][reference+'::raw'];refcal=result['metrics'][reference+'::temperature']
    improve=sum(u['delta_log_loss']<0 for u in primary)
    supported=sum(u['family_ci_high']<0 for u in primary)
    worsened=sum(u['family_ci_low']>0 for u in primary)
    rows=['# Kết quả vòng test đã khóa: Premier League 2024–2025','',
      '**Phạm vi:** backtest hồi cứu theo ngày, dùng dữ liệu miễn phí. Thời điểm nguồn công bố và announced XI tại T−60 chưa được chứng minh. '
      'P/F là proxy lịch sử nhân sự, không phải thí nghiệm XI chính thức hoặc market value.','',
      f"Đã đánh giá đủ **380 trận**, với 14 estimator cố định và hai baseline tần suất; tổng 30 đầu ra xác suất raw/temperature. "
      f"Phân phối test H/D/A: {result['test_class_counts']['H']}/{result['test_class_counts']['D']}/{result['test_class_counts']['A']}.", '',
      '## Kết quả tham chiếu đã chọn trước test','',
      f"Elo A_full được chọn làm tham chiếu thực dụng trước test vì có Log Loss validation gốc tốt nhất. "
      f"Trên test, Accuracy **{refraw['accuracy']:.2%}**, Macro F1 **{refraw['macro_f1']:.5f}**; "
      f"Log Loss raw **{refraw['log_loss']:.5f}**, temperature **{refcal['log_loss']:.5f}**; "
      f"Brier raw **{refraw['brier_sum']:.5f}**, temperature **{refcal['brier_sum']:.5f}**.", '',
      'Báo cả hai phiên bản theo kế hoạch, không chọn raw hay calibrated dựa trên test. Temperature dương giữ nguyên argmax; '
      'Accuracy/F1/confusion matrix raw và calibrated của cùng estimator không đổi.', '',
      '## Toàn bộ kết quả xác suất','',
      '| Cohort train | Thuật toán/nhánh | Accuracy | Macro F1 | Log Loss raw ↓ | Temperature ↓ | Brier raw ↓ | Temperature ↓ |',
      '|---|---|---:|---:|---:|---:|---:|---:|']
    for e in registry:
        raw=result['metrics'][e['id']+'::raw'];cal=result['metrics'].get(e['id']+'::temperature')
        cl=f"{cal['log_loss']:.5f}" if cal else '—';cb=f"{cal['brier_sum']:.5f}" if cal else '—'
        label=NAMES[e['family']]+' / '+e['arm']
        rows.append(f"| {e['cohort']} | {label} | {raw['accuracy']:.2%} | {raw['macro_f1']:.5f} | {raw['log_loss']:.5f} | {cl} | {raw['brier_sum']:.5f} | {cb} |")
    always=result['always_home_classification_only']
    rows += ['',f"Luôn chọn H: Accuracy {always['accuracy']:.2%}, Macro F1 {always['macro_f1']:.5f}; không gán xác suất 0 để tính Log Loss. "
      'Brier là mean(sum_c((p_c−y_c)^2)), miền [0,2]. Full train 3.040 trận, common train 1.520 trận; các ablation P/F chỉ so sánh trong common.', '',
      '## So sánh chính: đóng góp P và F','',
      f"Trong sáu contrast temperature đã đăng ký, {improve}/6 có Delta Log Loss âm. Với khoảng percentile có độ phủ điều chỉnh "
      f"Bonferroni-style 99,1667% và block chính hai tuần, {supported}/6 nằm hoàn toàn dưới 0, {worsened}/6 nằm hoàn toàn trên 0. "
      'Các kết luận vẫn chịu giới hạn độ phủ bootstrap trên một mùa phụ thuộc theo thời gian.', '',
      '![So sánh feature](feature_comparison.png)','',
      'Delta = Log Loss mô hình thêm feature trừ nhánh tham chiếu; âm có lợi. 2.000 resample moving-block theo tuần lịch, seed 42. '
      'Cùng chỉ số lấy mẫu cho hai mô hình. Độ phủ điều chỉnh tương ứng 1−0,05/6 cho sáu contrast chính; percentile bootstrap chỉ xấp xỉ, '
      'và 2.000 lần có ít mẫu ở đuôi rộng. Không coi khoảng chứa 0 là chứng minh tương đương.', '',
      '| Thuật toán | So sánh | Block tuần | Delta | CI 95% | CI 99,1667% |', '|---|---|---:|---:|---|---|']
    for u in result['paired_feature_comparisons']:
        if u['variant']!='temperature':continue
        comparison='P − A' if u['model_arm']=='A_plus_P' else 'APF − AP'
        rows.append(f"| {NAMES[u['family']]} | {comparison} | {u['block_weeks']} | {u['delta_log_loss']:.6f} | [{u['ci95_low']:.6f}; {u['ci95_high']:.6f}] | [{u['family_ci_low']:.6f}; {u['family_ci_high']:.6f}] |")
    rows += ['', 'So sánh raw là phân tích phụ, lưu đầy đủ trong results.json. Không chọn độ dài block cho kết luận thuận lợi: '
      'hai tuần là chính, một/bốn tuần là sensitivity. Không có uncertainty do fit lại mô hình trong resampling, nên các khoảng không bao phủ mọi nguồn bất định.', '',
      '## Phân loại hòa, calibration và giải thích','',
      '| Thuật toán/nhánh | D được chọn | Đúng D | Precision D | Recall D |', '|---|---:|---:|---:|---:|']
    for e in registry:
        m=result['metrics'][e['id']+'::raw'];d=m['per_class']['D'];correct=m['confusion_matrix_rows_true_cols_pred_HDA'][1][1]
        rows.append(f"| {NAMES[e['family']]} / {e['cohort']} / {e['arm']} | {m['predicted_label_counts']['D']} | {correct} | {d['precision']:.2%} | {d['recall']:.2%} |")
    rows += ['', 'Temperature không sửa ranh giới quyết định, do đó không tự khắc phục recall hòa. Calibration fit trên 380 trận 2023–2024; '
      'điểm validation sau fit là in-sample diagnostics. Chỉ bảng test ở đây là đánh giá ngoài mẫu của calibrator.', '',
      '![Reliability tham chiếu](reference_reliability.png)','',
      'Reliability chia tối đa năm nhóm phân vị mỗi lớp; quan sát trong bin có phụ thuộc nên Wilson intervals ở CSV chỉ là mô tả, '
      'không dùng như kiểm định calibration độc lập. Feature importance đã thực hiện trên validation; không chỉnh đặc trưng từ lỗi test.', '',
      '## Tính toàn vẹn và giới hạn nghiên cứu','',
      '- Cấu hình, 14 mô hình, hai baseline, 14 nhiệt độ, dữ liệu test và mã chấm điểm được khóa bằng SHA-256 trước scoring. '
      'Tất cả xác suất test được lưu trước khi runner ghép nhãn để tính metric.',
      '- Estimator fit đến 2022–2023; calibrator fit validation 2023–2024. Không refit hoặc chọn tham số bằng test. '
      'Có cập nhật trạng thái Elo/rolling/P/F từ các trận test trước ngày dự đoán theo quy tắc đã khóa; đây là dự đoán tuần tự, không dự đoán toàn mùa từ tháng Tám.',
      '- Cùng 380 trận cho mọi mô hình; giữ các trận đầu mùa thiếu lịch sử P/F. Player IDs reset đầu mùa. Loại 322 dòng Assistant Manager khỏi dữ liệu test trước khi tạo feature.',
      '- Bảng đội và tỷ số được đối chiếu; A tái dựng khớp snapshot. P/F đạt prefix/invariance/lineage checks. '
      'Artifact verification nạp lại mô hình và tái tạo đủ 11.400 xác suất, các metric và confusion matrices mà không fit lại.',
      '- Một mùa test có 380 trận, nhiều mô hình và phân phối mùa có thể đổi. Các khoảng bootstrap phụ thuộc giả định; không hứa độ chính xác cho mọi mùa hoặc ứng dụng cá cược.',
      '- Không có dữ liệu announced XI, tuổi/market value lịch sử đủ bằng chứng. Nghiên cứu chứng minh quy trình và kết quả với proxy đã định nghĩa, chưa giải quyết đầy đủ giả thuyết ban đầu về XI.',
      '- Không tiếp tục sửa mô hình dựa trên test. Bước tiếp theo là tổng hợp báo cáo học thuật, notebook tái lập và demo xác suất từ mô hình đã khóa.', '',
      '## Tái lập','',
      '```powershell','python -m unittest discover -s tests -q','python scripts/report_final_test.py','```','',
      'run_final_test.py từ chối ghi đè vòng test đã có. report_final_test.py chỉ kiểm chứng và dựng lại báo cáo/biểu đồ từ cùng artifact đã khóa. '
      'Dữ liệu raw/curated và model artifacts giữ cục bộ; hướng dẫn thu thập và các checksum nằm trong repo.', '',
      'Nguồn phương pháp: [scikit-learn: temperature calibration](https://scikit-learn.org/stable/modules/calibration.html). '
      'Khóa thí nghiệm: research/final_evaluation_config.json, research/final_model_registry.json, research/final_lock.json.', '']
    (OUT/'report.vi.md').write_text('\n'.join(rows),encoding='utf-8')
    print(json.dumps(verification,indent=2))


if __name__=='__main__':main()
