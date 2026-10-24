"""Execute the read-only notebook with bounded kernel startup and cell timeouts."""
from pathlib import Path
import nbformat
from nbclient import NotebookClient

ROOT=Path(__file__).resolve().parents[1]


def main():
    path=ROOT/'notebooks/results_reproduction.ipynb'
    notebook=nbformat.read(path,as_version=4)
    client=NotebookClient(notebook,timeout=60,startup_timeout=30,kernel_name='python3',
                          resources={'metadata':{'path':str(ROOT)}})
    client.execute()
    nbformat.validate(notebook)
    nbformat.write(notebook,path)
    print(f'Notebook executed successfully: {sum(c.cell_type=="code" for c in notebook.cells)} code cells.',flush=True)


if __name__=='__main__':main()
