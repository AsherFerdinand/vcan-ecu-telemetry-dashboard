"""Read-only storage audit and compact run manifests. There is no cleanup action."""
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version, PackageNotFoundError
import os
from pathlib import Path, PureWindowsPath
import subprocess
from urllib.parse import urlsplit
from . import __version__


def external_data_directory():
    """Return a configurable path; do not create, download or delete anything."""
    return Path(os.environ.get('VCAN_DATA_DIR', str(Path.home() / 'VCAN-data'))).expanduser()


def checked_source_metadata(metadata):
    if metadata is None:return {}
    allowed={'dataset_id','url','revision','license','kind','compatibility_status'}
    if not isinstance(metadata,dict) or set(metadata)-allowed:
        raise ValueError('source metadata permits dataset_id, url, revision, license, kind, compatibility_status only')
    for key,value in metadata.items():
        if not isinstance(value,str) or not value.strip() or '\n' in value or '\x00' in value:
            raise ValueError('source metadata values must be nonempty single-line strings')
        if key=='url':
            url=urlsplit(value)
            if url.scheme!='https' or not url.hostname or url.username or url.password or url.query or url.fragment:
                raise ValueError('source URLs must be public HTTPS without credentials/query/fragment')
        elif Path(value).is_absolute() or PureWindowsPath(value).is_absolute():
            raise ValueError('source metadata must not contain absolute private paths')
    return dict(metadata)


def file_hash(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as stream:
        while chunk:=stream.read(1024*1024):digest.update(chunk)
    return digest.hexdigest()


def git_state(root=None):
    try:
        args=['git']+(['-C',str(root)] if root else [])
        commit=subprocess.check_output(args+['rev-parse','HEAD'],stderr=subprocess.DEVNULL,text=True).strip()
        dirty=bool(subprocess.check_output(args+['status','--porcelain'],stderr=subprocess.DEVNULL,text=True))
        return {'commit':commit,'working_tree_dirty':dirty}
    except (OSError,subprocess.CalledProcessError):
        return {'commit':None,'working_tree_dirty':None}


def generated_output(path,root):
    """Validate an explicit generated output path; no deletion or overwrite."""
    path=Path(path).absolute();root=Path(root).absolute()
    if root.is_symlink() or root.resolve()!=root or path.resolve()!=path:
        raise ValueError('generated output paths must not traverse symbolic links')
    if path==root or root not in path.parents:
        raise ValueError('output must be inside the explicitly configured generated-output root')
    if path.exists():raise ValueError('refusing to overwrite an existing artifact')
    return path


def build_manifest(investigation,output_paths,*,output_root,reproduction,validation_timestamp=None,repository_root=None):
    root=Path(output_root).resolve()
    outputs=[]
    for path in output_paths:
        path=Path(path)
        if path.is_symlink() or root not in path.resolve().parents:
            raise ValueError('manifest output outside generated-output root')
        outputs.append({'path':path.resolve().relative_to(root).as_posix(),'bytes':path.stat().st_size,
                        'sha256':file_hash(path),'retention':'reproducible_generated'})
    decoder={}
    for package in ('cantools','python-can'):
        try:decoder[package]=version(package)
        except PackageNotFoundError:decoder[package]=None
    state=git_state(repository_root)
    reproducibility='source_commit_recorded' if state['commit'] and not state['working_tree_dirty'] else 'working_tree_dirty_or_git_unavailable; hashes retained but commit alone is insufficient'
    return {'schema':'vcan-investigation-manifest-1','source':investigation.source,'dbc':investigation.dbc,
            'decoder':{'vcan':__version__,**decoder},'git':state,'reproducibility_status':reproducibility,
            'validation_timestamp_utc':validation_timestamp or datetime.now(timezone.utc).isoformat(),
            'reference_configuration':investigation.recording.metadata.get('can_references'),
            'processing_configuration':investigation.configuration,'mapping':investigation.recording.metadata['can_mapping'],
            'input_hash_policy':'Source hash covers the complete original input, even when only a bounded subset is decoded.',
            'subset_selection':'original line/frame indices, channel and timestamp window; source bytes are unchanged',
            'validation_status':investigation.validation,'physical_accuracy':'not_established',
            'outputs':outputs,'output_location':'relative to the explicitly configured generated-output root',
            'reproduction':reproduction,
            'retention_note':'Do not automatically delete originals, independent references or reviewed historical evidence. No cleanup utility is provided.'}


def audit_storage(repository_root,*,output_root=None):
    """Measure tracked source and generated output, skip symlinks, never delete."""
    root=Path(repository_root).resolve()
    names=subprocess.check_output(['git','-C',str(root),'ls-files','-z']).decode().split('\0')
    tracked=[]
    for name in names:
        if not name:continue
        path=root/name
        size=len(os.readlink(path).encode()) if path.is_symlink() else path.stat().st_size if path.is_file() else 0
        tracked.append({'path':name,'bytes':size})
    output=Path(output_root) if output_root else root/'outputs'
    generated=[];skipped=0
    if output.is_symlink():raise ValueError('audit root must not be a symlink')
    if output.exists():
        for folder,dirs,files in os.walk(output,followlinks=False):
            skipped+=sum((Path(folder)/name).is_symlink() for name in dirs)
            dirs[:]=[name for name in dirs if not (Path(folder)/name).is_symlink()]
            for name in files:
                path=Path(folder)/name
                if path.is_symlink():skipped+=1;continue
                generated.append({'path':path.relative_to(output).as_posix(),'bytes':path.stat().st_size})
    return {'tracked_file_count':len(tracked),'tracked_bytes':sum(f['bytes'] for f in tracked),
            'generated_file_count':len(generated),'generated_bytes':sum(f['bytes'] for f in generated),
            'largest_generated':sorted(generated,key=lambda f:(-f['bytes'],f['path']))[:10],
            'symlinks_skipped':skipped,'operations':'read-only; no cleanup or deletion performed'}
