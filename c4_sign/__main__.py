import argparse

from c4_sign.screen import init_matrix, update_screen
from c4_sign.ScreenManager import ScreenManager
from c4_sign.tasks import TaskManager


def run_gif():
    from datetime import timedelta
    from pathlib import Path

    from PIL import Image, ImageDraw, ImageFont

    from c4_sign.lib.canvas import Canvas

    try:
        from rich.progress import track
    except ImportError:

        def track(iter, description=""):
            yield from iter

    screen_manager = ScreenManager()
    screen_manager.update_tasks()
    delta_t = timedelta(seconds=1 / 24)
    canvas = Canvas()
    tasks = screen_manager.current_tasks
    font = ImageFont.truetype("Courier", 16)
    with open("docs/screen_tasks.md", "w") as f:
        f.write("# Screen Tasks\n\n")
        for task in sorted(tasks, key=lambda x: x.__class__.__name__):
            f.write(f"## {task.__class__.__name__}\n")
            f.write(f"**Title**: {task.title}\n\n")
            f.write(f"**Artist**: {task.artist}\n\n")
            if task.__doc__:
                f.write(f"Description:\n```python\n{task.__doc__}\n```\n")
            f.write(f"![{task.__class__.__name__}](images/screen_tasks/{task.__class__.__name__}.webp)\n")
    source = Path("docs/images/screen_tasks")
    source.mkdir(parents=True, exist_ok=True)
    existing = [x.stem for x in source.glob("*.webp")]
    tasks = [task for task in tasks if task.__class__.__name__ not in existing]
    for task in track(tasks, description="Converting!"):
        print(f"Running {task.__class__.__name__}")
        duration = 0
        images = []
        task.prepare()
        while True:
            canvas.clear()
            text = task.get_lcd_text()
            result = task.draw(canvas, delta_t)
            img = Image.new("RGB", (256, 384))
            draw = ImageDraw.Draw(img)
            for y in range(32):
                for x in range(32):
                    r, g, b = canvas.get_pixel(x, y)
                    draw.rectangle((x * 8, y * 8, (x + 1) * 8, (y + 1) * 8), fill=(r, g, b))
            # add text
            draw.text((0, 320), text[16:], font=font, fill=(255, 255, 255))
            draw.text((0, 300), text[:16], font=font, fill=(255, 255, 255))
            images.append(img)
            duration += 1 / 24
            if result or duration > 30:
                break
        images[0].save(
            source / f"{task.__class__.__name__}.webp",
            save_all=True,
            append_images=images[1:],
            duration=(1 / 24) * 1000,
            loop=0,
        )

    exit(0)


def main(args=None):
    if args.purge_cache:
        from c4_sign.lib.assets import purge_cache

        purge_cache()
        print("Cache purged!")
    if args.gif:
        print("GIF mode!")
        if args.purge_cache:
            # we're also gonna clear the gif folder, just so we're forced to regenerate them
            from pathlib import Path
            from shutil import rmtree

            source = Path("docs/images/screen_tasks")
            rmtree(source, ignore_errors=True)
        return run_gif()
    init_matrix(args.simulator)
    tm = TaskManager()

    print("Finishing up startup...")

    while True:
        tm.check_and_run_tasks()
        update_screen()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--simulator", action="store_true")
    parser.add_argument("--gif", action="store_true")
    parser.add_argument("--profile", action="store_true")
    parser.add_argument("--purge-cache", action="store_true")
    args = parser.parse_args()
    if args.profile:
        try:
            from pyinstrument import Profiler
            from pyinstrument.renderers import SpeedscopeRenderer
        except ImportError:
            print("Please install pyinstrument to use the --profile flag")
            print("try pip install -e .[misc]")
            exit(1)

        with Profiler(interval=0.01) as profiler:
            try:
                main(args)
            except BaseException:
                pass
        print("Writing profile to /tmp/c4_profile/profile.speedscope.json")
        with open("/tmp/c4_profile/profile.speedscope.json", "w") as f:
            f.write(profiler.output(renderer=SpeedscopeRenderer(show_all=True)))
    else:
        main(args)
