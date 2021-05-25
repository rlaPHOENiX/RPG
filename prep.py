import sys
import subprocess
from pathlib import Path
from pymediainfo import MediaInfo


GLOBAL_TAGS_NET = "https://raw.githubusercontent.com/rlaphoenix/RPG/master/global_tags.xml"
CHANNEL_LAYOUT_MAP = {"LFE": 0.1}


def main():
    if len(sys.argv) <= 1:
        exit("Usage: prep.py [DIRECTORY]")
    if len(sys.argv) > 2:
        exit("Error: You provided too much arguments %s, expecting only one." % sys.argv[1:])

    folder = Path(sys.argv[1])

    if not folder.exists():
        exit("Error: The directory you provided (%s) does not exist." % folder)

    print(
        "Ok, setting up what I can automatically.\n"
        "You still need to follow the handbook. This script cannot cover every single thing.\n"
        "There's various stuff a script simply cannot do automatically."
    )

    global_tags = folder / "global_tags.xml"

    if not global_tags.exists():
        exit(
            f"No global_tags.xml in provided directory ({global_tags}). This is required. "
            f"An example file is available on the GitHub page: {GLOBAL_TAGS_NET}"
        )

    for file in folder.glob("**/*.mkv"):
        mediainfo = MediaInfo.parse(file)

        if not mediainfo.video_tracks:
            exit("Error: No video tracks? hmm?")
        if not mediainfo.audio_tracks:
            exit("Error: No audio tracks? hmm?")
        if not mediainfo.text_tracks:
            print("Warning: No subtitle tracks?")

        args = [
            "mkvpropedit",
            # tags
            "-t", f"global:{global_tags}",
            # general
            "-e", "info",
            "-s", f"title={file.stem}"
        ]

        for video in mediainfo.video_tracks:
            language = next(
                (x.language for x in mediainfo.audio_tracks if x.language and x.language[0].islower()),
                None
            )
            memo = "More than one video track? " if int(video.stream_identifier) > 0 else ""
            if not language:
                memo += "Correct Lang tag? "

            args.extend([
                "-e", f"track:{video.track_id}",
                "-s", "flag-enabled=1",
                "-s", f"flag-default={'1' if int(video.stream_identifier) == 0 else '0'}",
                "-s", "flag-forced=0",
                "-s", f"name={memo.strip()}"
            ])
            if language:
                args.extend(["-s", f"language={language}"])

        for audio in mediainfo.audio_tracks:
            channels = sum(CHANNEL_LAYOUT_MAP.get(x, 1) for x in audio.channel_layout.split(" "))
            title = f"{audio.format} {float(channels)}"
            if not audio.language or audio.language[0].isupper():
                title += ", Und lang tag?"
            if mediainfo.audio_tracks[0].language != audio.language:
                title += ", different lang, is this wanted?"
            if int(audio.stream_identifier) > 0:
                title += ", not first audio, is this commentary?"
            args.extend([
                "-e", f"track:{audio.track_id}",
                "-s", "flag-enabled=1",
                "-s", f"flag-default={'1' if int(audio.stream_identifier) == 0 else '0'}",
                "-s", "flag-forced=0",
                "-s", f"name={title}",
            ])

        for sub in mediainfo.text_tracks:
            if sub.language and sub.language[0].islower():
                title = sub.language
                if mediainfo.text_tracks[0].language != sub.language:
                    title += ", different lang, is this wanted?"
                if sum(x.language == sub.language and x.codec_id == sub.codec_id for x in mediainfo.text_tracks) > 1:
                    title += " (Dialect? Forced?)"
            else:
                title = "Und lang tag?"
            title += f" (CC?{' its SRT so probably' if sub.codec_id == 'S_TEXT/UTF8' else ''} SDH?)"
            if sub.muxing_mode == "zlib":
                title += ", Disable zlib/track compression!"
            args.extend([
                "-e", f"track:{sub.track_id}",
                "-s", "flag-enabled=1",
                "-s", "flag-default=0",
                "-s", "flag-forced=0",
                "-s", f"name={title}"
            ])
        args.extend([file])

        mkvpropedit = subprocess.run(args, capture_output=True)
        if (mkvpropedit.returncode != 0):
            exit(f"Failed to mkvpropedit: {file}\nWhy? Not sure, here's the log:\n\n{mkvpropedit.stdout.decode()}")
        print(f"✓ : {file.name}")

    print("✓✓✓ done all files")


if __name__ == "__main__":
    main()
