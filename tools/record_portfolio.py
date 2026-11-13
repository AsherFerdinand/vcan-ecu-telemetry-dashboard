"""Record actual Streamlit browser interactions, then optimize three GIFs.

Optional documentation tooling only: installed Playwright/Chromium and FFmpeg.
Raw WebM captures remain in an explicit external directory. No application code,
DOM values or calculated results are replaced. Existing final assets are refused.
"""
import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import time

WIDTH,HEIGHT,FPS=1120,960,12


def git(*args):
    return subprocess.check_output(['git',*args],text=True).strip()


async def ready(page,text):
    await page.get_by_text(text,exact=True).first.wait_for()


async def frame_sequence(page):
    await page.get_by_role('button',name='Open Frame Laboratory',exact=True).click()
    await ready(page,'3.04')
    await page.get_by_role('heading',name='CAN Frame Laboratory',exact=True).evaluate('(e)=>e.scrollIntoView({block:"start"})')
    await asyncio.sleep(2)
    await page.get_by_role('textbox',name=re.compile('^Arbitration ID')).click()
    await asyncio.sleep(.8)
    payload=page.get_by_role('textbox',name=re.compile('^Payload bytes'))
    await payload.fill('38 BD 21 03 0E 00 00 00');await payload.press('Enter')
    await ready(page,'3.12');await ready(page,'539')
    await asyncio.sleep(2.5)
    await page.get_by_role('button',name='Reset verified example',exact=True).click()
    await ready(page,'3.04');await ready(page,'538')
    await asyncio.sleep(2)


async def network_sequence(page):
    await page.get_by_role('button',name='Open Virtual CAN Network',exact=True).click()
    await ready(page,'Position 1 / 33 · Paused')
    await page.get_by_role('heading',name='Vehicle CAN network',exact=True).evaluate('(e)=>e.scrollIntoView({block:"start"})')
    slider=page.get_by_role('slider');await slider.focus();await slider.press('Home')
    await asyncio.sleep(1)
    await page.get_by_role('button',name='Start',exact=True).click()
    component=page.frame_locator('iframe').first
    await component.locator('animateMotion').first.wait_for(state='attached')
    await asyncio.sleep(6.5)
    await page.get_by_role('button',name='Pause',exact=True).click()
    await page.get_by_text(re.compile(r'Position \d+ / 33.*Paused')).wait_for()
    await asyncio.sleep(.5)
    await component.locator('[data-node="FL"]').focus()
    await component.locator('[data-node="FL"]').press('Enter')
    await component.locator('#info').filter(has_text='ABS/ESC').wait_for()
    await component.locator('#info').scroll_into_view_if_needed()
    await asyncio.sleep(2.5)


async def arbitration_sequence(page):
    await page.get_by_role('button',name='Open Virtual CAN Network',exact=True).click()
    await ready(page,'Position 1 / 33 · Paused')
    await page.get_by_text('Arbitration',exact=True).click()
    title=page.get_by_text('Bitwise arbitration · standard 11-bit data frames',exact=True)
    await title.wait_for();await title.evaluate('(e)=>e.scrollIntoView({block:"start"})')
    await ready(page,'Position 1 / 11 · Paused');await asyncio.sleep(1.5)
    await page.get_by_role('button',name='Step',exact=True).click()
    await ready(page,'Position 2 / 11 · Paused')
    await page.get_by_text('Lost here',exact=True).wait_for();await asyncio.sleep(1.5)
    for index in range(2,9):
        await page.get_by_role('button',name='Step',exact=True).click()
        await ready(page,f'Position {index+1} / 11 · Paused')
        await asyncio.sleep(.25)
    await page.get_by_text(re.compile('Identifier winner: 0x120')).wait_for()
    await page.get_by_text(re.compile('Identifier winner: 0x120')).scroll_into_view_if_needed()
    await asyncio.sleep(2.5)
    await page.get_by_role('button',name='Reset',exact=True).click()
    await ready(page,'Position 1 / 11 · Paused');await asyncio.sleep(1.5)


async def record(args):
    from playwright.async_api import async_playwright
    raw=args.raw_dir.resolve();out=args.output_dir.resolve()
    repository=Path(__file__).resolve().parents[1]
    if raw==repository or repository in raw.parents:raise ValueError('Raw captures must be outside the repository checkout')
    raw.mkdir(parents=True,exist_ok=True);out.mkdir(parents=True,exist_ok=True)
    names=('frame-laboratory','vehicle-network','can-arbitration')
    if any((out/(name+'.gif')).exists() for name in names) or (out/'manifest.json').exists():
        raise ValueError('Refusing to overwrite existing final portfolio assets; choose a fresh output directory')
    results=[]
    async with async_playwright() as p:
        options={'headless':True,'args':['--no-sandbox']}
        if args.browser:options['executable_path']=args.browser
        browser=await p.chromium.launch(**options)
        # Use actual native controls to establish dark appearance, outside footage.
        warm=await browser.new_context(viewport={'width':WIDTH,'height':HEIGHT})
        page=await warm.new_page();await page.goto(args.url,wait_until='networkidle')
        await ready(page,'Explore the measurement. Follow the evidence.')
        await page.locator('[data-testid="stMainMenu"]').click()
        await page.get_by_role('menuitemradio',name='Dark',exact=True).click()
        await page.get_by_role('button',name=re.compile('^Appearance')).click()
        await page.get_by_role('button',name='Apply appearance',exact=True).click()
        await page.keyboard.press('Escape')
        storage=await warm.storage_state();await warm.close()
        for name,sequence in zip(names,(frame_sequence,network_sequence,arbitration_sequence)):
            context=await browser.new_context(viewport={'width':WIDTH,'height':HEIGHT},device_scale_factor=1,
                storage_state=storage,record_video_dir=str(raw/name),record_video_size={'width':WIDTH,'height':HEIGHT})
            page=await context.new_page();origin=time.monotonic();errors=[]
            page.on('pageerror',lambda error:errors.append(str(error)))
            # Official embed mode removes Streamlit's toolbar, not engineering UI.
            await page.goto(args.url.rstrip('/')+'/?embed=true',wait_until='networkidle')
            await ready(page,'Explore the measurement. Follow the evidence.')
            await page.get_by_role('button',name=re.compile('^Appearance')).click()
            await page.get_by_role('button',name='Apply appearance',exact=True).click()
            await page.keyboard.press('Escape');await asyncio.sleep(.5)
            start=time.monotonic()-origin
            await asyncio.sleep(.6);await sequence(page)
            end=time.monotonic()-origin
            if errors or await page.locator('[data-testid="stException"]').count():raise RuntimeError(str(errors))
            video=page.video;await context.close();source=Path(await video.path())
            final=out/(name+'.gif')
            # Coalesce visually unchanged source frames while preserving their PTS.
            # This removes video-compression shimmer from static UI holds, not UI states.
            prefix=[args.ffmpeg,'-hide_banner','-loglevel','info','-ss',f'{start:.3f}','-t',f'{end-start:.3f}','-i',str(source)]
            analysis=subprocess.run(prefix+['-vf',f'fps={FPS},mpdecimate,showinfo','-f','null','-'],capture_output=True,text=True,check=True)
            timestamps=[float(value) for value in re.findall(r'pts_time:([0-9.]+)',analysis.stderr)]
            if not timestamps:raise RuntimeError('No recorded source frames survived conversion')
            final_delay=max(8,round((end-start-timestamps[-1])*100))
            command=prefix+['-loglevel','error','-filter_complex_threads','1','-filter_complex',
                f'fps={FPS},mpdecimate,split[a][b];[a]palettegen=max_colors=96:stats_mode=full[p];[b][p]paletteuse=dither=none:diff_mode=rectangle',
                '-fps_mode','vfr','-final_delay',str(final_delay),'-loop','0',str(final)]
            subprocess.run(command,check=True)
            if final.stat().st_size>8_000_000:raise ValueError('GIF exceeds 8.00 MB; review/optimize before publication')
            # Pillow is an existing environment tool, not an application dependency.
            from PIL import Image
            with Image.open(final) as image:
                durations=[]
                for index in range(image.n_frames):image.seek(index);durations.append(image.info.get('duration',0))
                results.append({'asset':final.name,'width':image.width,'height':image.height,'frames':image.n_frames,
                    'duration_s':sum(durations)/1000,'sampling_fps':FPS,'timing':'Variable GIF delays preserve source PTS after near-identical-frame suppression','bytes':final.stat().st_size,
                    'sha256':hashlib.sha256(final.read_bytes()).hexdigest(),'loop':0,
                    'raw_clip_start_s':round(start,3),'raw_clip_duration_s':round(end-start,3),
                    'raw_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'raw_bytes':source.stat().st_size})
            print(name,results[-1]['duration_s'],'s',f'{final.stat().st_size/1_000_000:.2f} MB',flush=True)
        version=browser.version;await browser.close()
    manifest={'schema':'vcan-portfolio-assets-1','application_git_commit':git('rev-parse','HEAD'),
        'application_source_tree':git('rev-parse','HEAD:src'),'browser':'Chromium '+version,
        'ffmpeg':subprocess.check_output([args.ffmpeg,'-version'],text=True).splitlines()[0],
        'method':'Native Playwright WebM recording; actual UI actions/assertions; setup trimmed; FFmpeg 12 FPS sampling, near-identical-frame coalescing with source timestamps, 96-color palette, no dithering. No synthetic UI frames, caption overlays or injected calculation values.',
        'engineering_scope':'Same v0.4.7 application; schematic network motion, DBC interpretation only, no hardware/physical validation.',
        'assets':results}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url',default='http://localhost:8518')
    parser.add_argument('--browser',default=shutil.which('chromium'))
    parser.add_argument('--ffmpeg',default=shutil.which('ffmpeg') or 'ffmpeg')
    parser.add_argument('--raw-dir',type=Path,required=True)
    parser.add_argument('--output-dir',type=Path,default=Path('docs/media'))
    asyncio.run(record(parser.parse_args()))
