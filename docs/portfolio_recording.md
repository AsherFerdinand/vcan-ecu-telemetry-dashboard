# Portfolio capture and asset verification — v0.4.8

The README demonstrations are recordings of the running **v0.4.7 application**.
This documentation milestone does not change its calculations, signal definitions,
UI source or application version. The capture manifest pins the application Git
commit and `src` tree object; compare that tree with the final portfolio revision
to establish that the demonstrated application is unchanged.

## Method

`tools/record_portfolio.py` uses optional, already-installed Playwright/Chromium
and FFmpeg. It opens the native theme picker, selects Dark, applies appearance,
then records three fresh browser contexts. Official `?embed=true` hides the app
hosting toolbar, not its engineering controls. Each sequence starts at Overview,
opens the module and scrolls the real viewport to its engineering content.
No DOM calculation values, screenshots, caption overlays or simulation events are
injected. The network clip uses actual timed playback and SVG wire-path animation.

Native Playwright records WebM at **1120×960**. Setup preceding the marked sequence
is trimmed; source time within the retained sequence is preserved. FFmpeg samples
at **12 FPS**, coalesces near-identical frames with `mpdecimate`, builds a
**96-colour full-clip palette**, disables dithering and optimizes unchanged
rectangles/transparency. Variable GIF delays preserve source presentation
timestamps, including the final actual hold. GIF delays have centisecond
precision; static scenes therefore use fewer stored frames than motion. These
are screen-playback timings, never physical CAN propagation or bitrate evidence.
No interpolation or invented intermediate UI state is used. The resulting GIFs loop without JavaScript and are referenced through relative
GitHub Markdown image paths.

The automation asserts the actual raw integers and 3.04/3.12 km/h results, waits
for the real arbitration loss/winner states, and rejects JavaScript/Streamlit
exceptions. It does not alter or replace the decoder, arbitration or event model.
Paused sensor inspection demonstrates a local connection to passive ABS/ESC.
Receiver flashes still represent the same broadcast frame; they are not extra
transmissions or independent hardware reception evidence.

## Reproduce

Application dependencies are unchanged. Recording is an **optional documentation
tool**, not an application or CI prerequisite. Use a machine with Playwright,
Chromium, FFmpeg and Pillow available; Pillow is already in the application's
locked UI environment. Playwright also expects its small FFmpeg recorder utility.
No browser or recording package was added to runtime requirements in this task.

From the repository root, in one terminal:

```bash
.venv/bin/python -m streamlit run src/can_lab/dashboard.py --server.headless true --server.port 8518
```

In an environment with the recording tools installed:

```bash
python tools/record_portfolio.py --url http://localhost:8518 --browser /usr/bin/chromium --raw-dir /tmp/vcan-portfolio-raw --output-dir /tmp/vcan-portfolio-review
```

Use fresh output paths: the script refuses existing final assets. Raw captures
must remain **outside the checkout**. It never automatically removes recordings
or historical evidence. The only publishable outputs are the three reviewed GIFs
and compact manifest. Copy reviewed final outputs to `docs/media/` deliberately;
never copy raw videos, browser profiles or intermediate palettes into Git.

This execution reused system Chromium and FFmpeg. Playwright's expected recorder
binary was absent, so a temporary `PLAYWRIGHT_BROWSERS_PATH` under `/tmp` pointed
its `ffmpeg-1011/ffmpeg-linux` entry to the installed `/usr/bin/ffmpeg`. No package
or binary download was required. This is a capture-tool compatibility arrangement,
not an application dependency. A standard Playwright installation can instead
provide its recorder via `python -m playwright install ffmpeg`.

**Windows recording workflow:** run the existing Streamlit command with
`.venv\Scripts\python.exe`; use a separate recording environment with Playwright
and FFmpeg installed, provide `--browser` pointing at installed Chromium/Chrome,
and use an external raw folder, for example `$env:TEMP\vcan-portfolio-raw`.
FFmpeg must be on PATH (or supplied with `--ffmpeg`). Use fresh external final-review
paths and inspect assets before copying them into `docs/media`. Native Windows
recording has not been executed here; the Python/Chromium workflow is provided
for reproduction, not a tested Windows platform claim.

## Inspect before publication

The manifest records the actual image dimensions, frame count, summed GIF duration,
file size, SHA-256, capture trims, application revision/tree and tool versions.
Exact byte counts remain in machine metadata; human-facing tables use decimal units.

Verification includes decoding every GIF frame, checking frame timing/dimensions
and representative first/middle/final frames, and opening the animations in Chromium
from a static page. Check readable IDs/payloads, 538→539 and speed changes, real
path-following pulses, sensor context, both arbitration losses, winner and reset.
Successful encoding alone is insufficient. No dataset or credential is entered;
all recordings use the bundled teaching definitions and synthetic traffic.

See [the workbench sequences](workbench.md#portfolio-recording-sequences) for the
engineering narrative and [validation record](validation.md) for actual results.
The original historical screenshots remain available. No GIF establishes hardware
CAN performance, sensor calibration, production diagnostics or physical accuracy.


## Published asset inventory

| Actual recording | Dimensions | Stored frames | Duration | Size |
| --- | --- | --- | --- | --- |
| CAN Frame Laboratory | 1120×960 | 31 | 10.67 s | 1.80 MB |
| Virtual CAN Network | 1120×960 | 97 | 12.48 s | 2.47 MB |
| CAN Arbitration | 1120×960 | 30 | 13.62 s | 2.42 MB |

Total optimized GIF content: **6.69 MB**. Motion is sampled at 12 FPS; unchanged
UI holds are represented by longer GIF frame delays, so frame count divided by
whole-clip duration is not the active-motion sampling rate. The frame clip is below
the suggested 2.00 MB lower target because it compresses well; it was not padded.
All clips are below 5.00 MB and the 8.00 MB review threshold.

The first encode totalled about 18.95 MB. Removing near-identical compression shimmer
and dithering reduced the final total while preserving readable IDs/values and actual
motion. A second genuine capture improved framing: sensor details and the arbitration
winner are scrolled into view. Unpublished takes and raw WebM remain external;
only three final GIFs and their manifest are retained in Git.

Run the asset verifier, optionally extracting representative review frames outside
the checkout:

```bash
python tools/verify_portfolio.py --directory docs/media --extract-dir /tmp/vcan-gif-review
```

It decodes every frame, checks dimensions/looping/timing and validates exact hashes.
Representative frames were also visually inspected for 539 / 3.12 km/h, reset to
538 / 3.04 km/h, real cyan bus pulses, paused FL wheel-sensor context, both losing
contenders and the displayed 0x120 winner. A static browser preview checks native
GIF rendering without requiring application JavaScript.
