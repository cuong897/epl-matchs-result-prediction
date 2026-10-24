"""Build an offline archive demo and result-reproduction notebook, no model fit."""
import csv
import json
from pathlib import Path
import nbformat as nbf
from delivery_data import load_delivery,demo_payload,read_csv,sha

ROOT=Path(__file__).resolve().parents[1]


def main():
    out=ROOT/'reports/delivery';out.mkdir(exist_ok=True)
    matches=[r for r in read_csv(ROOT/'data/curated/matches.csv') if r['split']=='test']
    outcomes={r['match_id']:r for r in read_csv(ROOT/'data/curated/match_outcomes.csv')}
    rows=[]
    for m in sorted(matches,key=lambda r:(r['match_date'],r['match_id'])):
        outcome=outcomes[m['match_id']]
        rows.append({**{c:m[c] for c in ['match_id','match_date','home_team','away_team']},
                     **{c:outcome[c] for c in ['home_goals','away_goals','result']}})
    with (out/'match_catalog.csv').open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    data=load_delivery(ROOT);payload=demo_payload(data)
    template=(ROOT/'demo/template.html').read_text(encoding='utf-8')
    encoded=json.dumps(payload,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c').replace('&','\\u0026')
    demo_path=ROOT/'demo/index.html';demo_path.write_text(template.replace('__ARCHIVE_DATA__',encoded),encoding='utf-8')
    md=nbf.v4.new_markdown_cell;code=nbf.v4.new_code_cell
    cells=[md('# Premier League 2024–2025 — tái lập kết quả đã khóa\n\nNotebook đọc lại artifact của vòng test `final_test_v1`, tự tính lại metric và đối chiếu. **Không fit mô hình, không chọn lại calibration hoặc tune theo test.** P/F là proxy lịch sử cầu thủ; chưa có announced XI T−60 được xác minh.'),
      code("from pathlib import Path\nimport sys, json\nimport numpy as np\nimport pandas as pd\nfrom IPython.display import display, Image\nROOT = Path.cwd().resolve()\nif not (ROOT / 'research/final_lock.json').exists():\n    ROOT = ROOT.parent\nassert (ROOT / 'research/final_lock.json').exists(), 'Mở notebook từ thư mục dự án hoặc notebooks/'\nsys.path.insert(0, str(ROOT / 'scripts'))\nfrom delivery_data import load_delivery, FAMILY, ARM\ndata = load_delivery(ROOT)\nprint('Đã xác minh khóa, 380 trận và 11.400 bộ xác suất. Không huấn luyện lại.')"),
      md('## 1. Dữ liệu và phạm vi\n\nA_full train 2015–2023 với 3.040 trận; cohort common train 2019–2023 với 1.520 trận. Validation 2023–2024 và test 2024–2025 có 380 trận mỗi mùa. P/F reset đầu mùa; snapshot chỉ dùng ngày lịch trước. Availability vẫn là giả định nửa đêm kế tiếp, chưa phải publication timestamp đã chứng minh.'),
      code("pd.DataFrame([{'Nhánh':'A_full','Train':3040,'Validation':380,'Test':380,'Đặc trưng':40},\n {'Nhánh':'A_common','Train':1520,'Validation':380,'Test':380,'Đặc trưng':40},\n {'Nhánh':'A+P','Train':1520,'Validation':380,'Test':380,'Đặc trưng':52},\n {'Nhánh':'A+P+F','Train':1520,'Validation':380,'Test':380,'Đặc trưng':60}])"),
      md('## 2. Những phát hiện audit quan trọng\n\n59 placeholder của trận bị hoãn được loại có quy tắc và bằng chứng; 136 trận đầu mùa 2022–2023 có starts/xG/xA toàn 0 nên được đánh dấu không dùng được. Không đưa xG/xA hay starts vào P/F. 322 dòng Assistant Manager mùa test bị loại. Bảng sau mô tả độ phủ, không phải đánh giá mô hình.'),
      code("audit = json.loads((ROOT/'reports/player_history/audit.json').read_text(encoding='utf-8'))\npd.DataFrame([{k:s.get(k) for k in ['season','raw_rows','status','curated_rows','linked_fixtures']} for s in audit['seasons']])"),
      md('## 3. Tự tính lại metric\n\nThứ tự xác suất luôn H, D, A. Log Loss dùng xác suất của nhãn đúng; Brier là tổng sai số bình phương ba lớp rồi lấy trung bình, miền [0,2]. Precision/recall bằng 0 khi mẫu số bằng 0, phù hợp protocol.'),
      code("pred = pd.DataFrame(data['predictions'])\nlabels = ['H','D','A']\nchecks = []\nfor (model, variant), group in pred.groupby(['model','variant']):\n    p = group[['p_H','p_D','p_A']].to_numpy(float)\n    y = np.array([labels.index(v) for v in group['result']])\n    yh = p.argmax(axis=1)\n    assert len(group)==380 and group.match_id.nunique()==380\n    np.testing.assert_allclose(p.sum(axis=1),1,atol=1e-10)\n    ll = -np.log(np.clip(p[np.arange(len(y)),y],1e-15,1)).mean()\n    brier = ((p-np.eye(3)[y])**2).sum(axis=1).mean()\n    f1=[]\n    for c in range(3):\n        tp=((y==c)&(yh==c)).sum(); fp=((y!=c)&(yh==c)).sum(); fn=((y==c)&(yh!=c)).sum()\n        f1.append(2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0.)\n    metric={'accuracy':(yh==y).mean(),'macro_f1':np.mean(f1),'log_loss':ll,'brier_sum':brier}\n    expected=data['result']['metrics'][model+'::'+variant]\n    for k,v in metric.items(): np.testing.assert_allclose(v,expected[k],atol=1e-12,rtol=0)\n    checks.append({'model':model,'variant':variant,**metric})\nmetrics = pd.DataFrame(checks)\nprint(f'Tái tính đúng {len(metrics)} đầu ra xác suất trên cùng 380 trận.')\nmetrics.head()"),
      md('## 4. Kết quả tham chiếu đã chọn trước test\n\nElo A_full là tham chiếu đã chỉ định ở protocol, không chọn lại mô hình theo điểm test.'),
      code("reference = metrics[metrics.model.eq('full__elo')].copy()\nreference[['variant','accuracy','macro_f1','log_loss','brier_sum']]"),
      md('## 5. Calibration ngoài mẫu\n\nTemperature được fit trên validation 2023–2024. Điểm validation sau fit là in-sample diagnostics. Bảng dưới kiểm tra tác động lên test, giữ cả raw và temperature.'),
      code("calibration = metrics.pivot(index='model',columns='variant',values='log_loss').dropna()\ncalibration['delta_temperature_minus_raw'] = calibration['temperature']-calibration['raw']\nassert (calibration.delta_temperature_minus_raw > 0).all()\nprint('Cả 14 mô hình có Log Loss test tăng sau temperature trong thí nghiệm này.')\ncalibration"),
      md('## 6. So sánh P và F trên cùng cohort\n\nĐọc các khoảng bootstrap đã đăng ký và đã tính trong vòng test. Block chính 2 tuần; family interval 99,1667% cho sáu contrast temperature. Không resample thêm hoặc chọn block sau khi thấy test.'),
      code("contrasts = pd.DataFrame(data['result']['paired_feature_comparisons'])\nprimary = contrasts[contrasts.variant.eq('temperature') & contrasts.block_weeks.eq(2)]\nassert len(primary)==6\nassert ((primary.family_ci_low<=0)&(primary.family_ci_high>=0)).all()\nprimary[['family','model_arm','reference_arm','delta_log_loss','ci95_low','ci95_high','family_ci_low','family_ci_high']]"),
      code("display(Image(filename=str(ROOT/'reports/final_test_v1/feature_comparison.png')))"),
      md('## 7. Điểm yếu lớp hòa và reliability\n\nAccuracy không thay thế đánh giá từng lớp. Temperature dương giữ nguyên argmax, vì vậy không tự cải thiện recall lớp D.'),
      code("r=data['result']['metrics']['full__elo::raw']\ndisplay(pd.DataFrame(r['confusion_matrix_rows_true_cols_pred_HDA'],index=['Thật H','Thật D','Thật A'],columns=['Dự đoán H','Dự đoán D','Dự đoán A']))\ndisplay(pd.DataFrame(r['per_class']).T)\ndisplay(Image(filename=str(ROOT/'reports/final_test_v1/reference_reliability.png')))"),
      md('## 8. Xem một trận trong archive\n\nĐây là dự đoán lịch sử đã lưu, không phải dự báo trực tiếp. Có thể đổi chỉ số `match_index` để xem trận khác mà không fit lại.'),
      code("match_index = 0\ncatalog=pd.DataFrame(data['matches'])\nmatch=catalog.iloc[match_index]\ndisplay(match.to_frame('Giá trị'))\nchosen=pred[pred.match_id.eq(match.match_id)&pred.model.eq('full__elo')]\ndisplay(chosen[['variant','p_H','p_D','p_A','predicted_label']])"),
      md('## 9. Kết luận và tái lập\n\nElo là baseline mạnh; P/F chưa có bằng chứng cải thiện chắc chắn theo protocol; calibration fit một mùa không bảo đảm tốt hơn mùa kế tiếp. Không suy rộng thành “cầu thủ không quan trọng” hoặc “calibration luôn có hại”.\n\nNotebook này tái lập **kết quả từ artifact**, không thay cho việc chạy lại thu thập, chuẩn hóa và huấn luyện từ raw. Xem `docs/reproducibility.vi.md` để phân biệt các mức tái lập. Demo mở ở `demo/index.html`. Dữ liệu, mô hình và mã scoring đã khóa không được sửa để tìm điểm test tốt hơn.')]
    notebook=nbf.v4.new_notebook(cells=cells,metadata={'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},'language_info':{'name':'python','version':'3.13'}})
    folder=ROOT/'notebooks';folder.mkdir(exist_ok=True)
    nbf.write(notebook,folder/'results_reproduction.ipynb')
    manifest={'purpose':'read-only delivery, not a new experiment','final_lock_sha256':sha(ROOT/'research/final_lock.json'),
              'inputs':{str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'reports/final_test_v1/results.json',ROOT/'reports/final_test_v1/test_predictions_scored.csv',out/'match_catalog.csv']},
              'outputs':{'demo/index.html':sha(demo_path),'notebooks/results_reproduction.ipynb':sha(folder/'results_reproduction.ipynb')}}
    (out/'delivery_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    print('Built offline demo and unexecuted reproduction notebook from verified frozen results.')


if __name__=='__main__':main()
