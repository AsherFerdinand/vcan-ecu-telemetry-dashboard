"""Decode every final GIF frame, verify manifest facts, optionally extract review PNGs."""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image


def verify(directory,extract=None):
    manifest=json.loads((directory/'manifest.json').read_text())
    total=0
    if extract:
        extract=extract.resolve()
        root=Path(__file__).resolve().parents[1]
        if extract==root or root in extract.parents:raise ValueError('Review frames must remain outside the checkout')
        extract.mkdir(parents=True,exist_ok=True)
    for asset in manifest['assets']:
        path=directory/asset['asset'];data=path.read_bytes()
        assert len(data)==asset['bytes'] and hashlib.sha256(data).hexdigest()==asset['sha256']
        with Image.open(path) as image:
            assert image.format=='GIF' and (image.width,image.height)==(asset['width'],asset['height'])
            assert image.n_frames==asset['frames'] and image.info.get('loop')==0
            elapsed=0;targets=iter([0,.25,.5,.7,.85,.99]);fraction=next(targets,None);sample=0
            for index in range(image.n_frames):
                image.seek(index);image.load()
                delay=image.info.get('duration',0)
                assert delay>0,'Zero-duration frame is not acceptable for this portfolio'
                while extract and fraction is not None and (elapsed+delay)/1000>=asset['duration_s']*fraction:
                    image.convert('RGB').save(extract/(path.stem+f'-{sample}.png'))
                    sample+=1;fraction=next(targets,None)
                elapsed+=delay
            assert abs(elapsed/1000-asset['duration_s'])<.001
        total+=len(data)
        print(f"{path.name}: {asset['width']}×{asset['height']}, {asset['frames']} frames, {elapsed/1000:.2f} s, {len(data)/1_000_000:.2f} MB")
    print(f'Total GIF size: {total/1_000_000:.2f} MB; every frame decoded; hashes and timing verified.')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',type=Path,default=Path('docs/media'))
    parser.add_argument('--extract-dir',type=Path)
    args=parser.parse_args();verify(args.directory,args.extract_dir)
