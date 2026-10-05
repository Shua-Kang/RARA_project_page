"""Turn the raw rollout videos in videos/ (not published) into web videos in static/videos/.

Real robot: the 1280x720 global view is cropped to a 720x720 square (left cables and right empty table
removed), the 640x480 gripper view to a 480x480 square, and the gripper view is inset at the bottom right.
RoboTwin: the 23-px burned-in label bar at the top is cropped; labels are shown on the page instead.

Run from the repository root:  python tools/process_videos.py
"""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'videos'
OUT = ROOT / 'static' / 'videos'
ENC = ['-c:v', 'libx264', '-preset', 'slow', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', '-an']

# (raw stem relative to videos/real, output name). Episodes are paired by their initial scene.
REAL = [
    ('BlindVLA/pick_3_toys_20', 'toys_blindvla_1'),          # table with cloth
    ('RARA/pick_3_toys_19', 'toys_rara_1'),
    ('BlindVLA/pick_3_toys_21_failure', 'toys_blindvla_2'),  # lion in front
    ('RARA/pick_3_toys_20_success', 'toys_rara_2'),
    ('BlindVLA/pick_3_toys_26_failure', 'toys_blindvla_3'),  # zebra and monkey
    ('RARA/pick_3_toys_25_success', 'toys_rara_3'),
    ('BlindVLA/toaster_04', 'toaster_blindvla_1'),
    ('RARA/toaster_05', 'toaster_rara_1'),
]

ROBOTWIN_TASKS = {'env200005_e300': 'click_alarm_clock', 'env300008_e300': 'move_pill_bottle'}
ROBOTWIN_METHODS = {'1_FT_fail': 'ft', '2_CoFT_fail': 'coft', '3_BlindVLA_fail': 'blindvla',
                    '4_STRAP-FT_fail': 'strap', '5_RARA-anchor_success': 'rara'}


ROBOCASA_TASKS = {'OpenBlenderLid': 'open_blender_lid', 'OpenCabinet': 'open_cabinet',
                  'PickPlaceCounterToDrawer': 'pick_place_drawer', 'TurnOnToaster': 'turn_on_toaster'}
ROBOCASA_METHODS = {'1_FT': 'ft', '2_BlindVLA': 'blindvla', '3_RARA': 'rara'}
ROBOCASA_EPISODES = 3  # first episodes (by seed) of each task and split


def run(args):
    subprocess.run(['ffmpeg', '-v', 'error', '-y'] + args, check=True)


def real():
    (OUT / 'real').mkdir(parents=True, exist_ok=True)
    graph = ('[0:v]crop=720:720:220:0,scale=540:540[g];'
             '[1:v]crop=480:480:80:0,scale=164:164,pad=170:170:3:3:white[r];'
             '[g][r]overlay=W-w-12:H-h-12:shortest=1')
    for stem, name in REAL:
        dst = OUT / 'real' / f'{name}.mp4'
        missing = [k for k in ('global', 'gripper') if not (RAW / 'real' / f'{stem}_{k}.mp4').exists()]
        if missing:
            print('SKIP', stem, '- missing', ', '.join(missing))
            continue
        run(['-i', str(RAW / 'real' / f'{stem}_global.mp4'), '-i', str(RAW / 'real' / f'{stem}_gripper.mp4'),
             '-filter_complex', graph, '-r', '30', '-crf', '26'] + ENC + [str(dst)])
        print(dst.relative_to(ROOT), dst.stat().st_size // 1024, 'KB')


def robotwin():
    (OUT / 'robotwin').mkdir(parents=True, exist_ok=True)
    for env, task in ROBOTWIN_TASKS.items():
        for raw, method in ROBOTWIN_METHODS.items():
            dst = OUT / 'robotwin' / f'{task}_{method}.mp4'
            run(['-i', str(RAW / 'RoboTwin' / env / f'{raw}.mp4'),
                 '-vf', 'crop=640:456:0:24,scale=480:-2', '-crf', '28'] + ENC + [str(dst)])
            print(dst.relative_to(ROOT), dst.stat().st_size // 1024, 'KB')


def robocasa():
    (OUT / 'robocasa').mkdir(parents=True, exist_ok=True)
    for raw_task, task in ROBOCASA_TASKS.items():
        for split in ('ID', 'OOD'):
            episodes = sorted((RAW / 'robocasa' / raw_task / split).iterdir())[:ROBOCASA_EPISODES]
            for ep, folder in enumerate(episodes, start=1):
                for raw_prefix, method in ROBOCASA_METHODS.items():
                    src = next(folder.glob(f'{raw_prefix}_*.mp4'))
                    dst = OUT / 'robocasa' / f'{task}_{split.lower()}_{ep}_{method}.mp4'
                    run(['-i', str(src), '-vf', 'scale=384:384', '-crf', '28'] + ENC + [str(dst)])
                print(task, split, ep, folder.name)


if __name__ == '__main__':
    real()
    robotwin()
    robocasa()
