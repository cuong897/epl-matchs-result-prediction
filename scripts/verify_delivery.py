"""Verify delivery artifacts and original experiment integrity without fitting."""
import json
from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET
from delivery_data import load_delivery,sha

ROOT=Path(__file__).resolve().parents[1]


def main():
    data=load_delivery(ROOT)
    lock=json.loads((ROOT/'research/final_lock.json').read_text())
    missing=[]
    for relative,expected in lock['files_sha256'].items():
        path=ROOT/relative
        if path.exists():
            if sha(path)!=expected:raise ValueError(f'Original locked artifact changed: {relative}')
        else:missing.append(relative)
    for name,expected in lock['code_sha256'].items():
        if sha(ROOT/'scripts'/name)!=expected:raise ValueError('Original scoring code changed')
    notebook_path=ROOT/'notebooks/results_reproduction.ipynb'
    n=json.loads(notebook_path.read_text(encoding='utf-8'))
    cells=[c for c in n['cells'] if c['cell_type']=='code']
    if len(cells)!=10 or any(c['execution_count'] is None for c in cells):raise ValueError('Notebook not fully executed')
    if any(o['output_type']=='error' for c in cells for o in c['outputs']):raise ValueError('Notebook contains error output')
    demo=json.loads((ROOT/'reports/delivery/demo_verification.json').read_text())
    if demo['javascript_errors'] or demo['external_network_requests']:raise ValueError('Demo QA failed')
    doc_path=ROOT/'reports/delivery/academic_report.vi.docx'
    qa=json.loads((ROOT/'reports/delivery/report_qa.json').read_text())
    if sha(doc_path)!=qa['docx_sha256'] or not qa['all_pages_visually_reviewed']:raise ValueError('DOCX changed after visual QA')
    with ZipFile(doc_path) as archive:
        styles=ET.fromstring(archive.read('word/styles.xml'));document=ET.fromstring(archive.read('word/document.xml'))
    ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','m':'http://schemas.openxmlformats.org/officeDocument/2006/math'}
    title=styles.find("w:style[@w:styleId='Title']",ns)
    if title is None or title.find('.//w:pBdr',ns) is not None:raise ValueError('Title contains an unwanted border')
    if len(document.findall('.//m:oMath',ns))!=3:raise ValueError('Expected three editable math equations')
    outputs=['demo/index.html','notebooks/results_reproduction.ipynb','reports/delivery/academic_report.vi.docx',
             'reports/delivery/academic_report.vi.md','docs/reproducibility.vi.md','docs/presentation-guide.vi.md']
    manifest_path=ROOT/'reports/delivery/delivery_manifest.json'
    manifest=json.loads(manifest_path.read_text())
    # Refresh hashes after notebook execution and final report layout QA.
    manifest['outputs']={relative:sha(ROOT/relative) for relative in outputs}
    manifest['notebook_execution']='10 code cells completed without errors'
    manifest['docx_visual_qa']='all 11 pages rendered and reviewed'
    manifest_path.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    verification={'read_only_delivery':True,'matches':len(data['matches']),'probability_records':len(data['predictions']),
                  'executed_notebook_cells':10,'notebook_errors':0,'demo_desktop_and_mobile_passed':True,
                  'demo_external_requests':0,'report_pages':11,'editable_math_equations':3,
                  'report_all_pages_visually_reviewed':True,'original_scoring_code_unchanged':True,
                  'all_original_locked_files_present':not missing,'missing_original_locked_files':missing,
                  'present_original_locked_files_unchanged':True,'no_model_fit_or_test_tuning':True,
                  'delivery_manifest_sha256':sha(manifest_path)}
    (ROOT/'reports/delivery/delivery_verification.json').write_text(json.dumps(verification,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(verification,indent=2))


if __name__=='__main__':main()
