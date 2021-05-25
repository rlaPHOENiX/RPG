import sys
import subprocess
from pathlib import Path
from pymediainfo import MediaInfo


GLOBAL_TAGS_NET = "https://raw.githubusercontent.com/rlaphoenix/RPG/master/global_tags.xml"
CHANNEL_LAYOUT_MAP = {"LFE": 0.1}
MEDIA_INFO_SETTINGS = {"Language": "raw"}


def get_tracks(mediainfo, types):
    return [t for t in mediainfo.tracks if t.track_type in types]


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
        mediainfo = MediaInfo.parse(file, mediainfo_options=MEDIA_INFO_SETTINGS)
        video_tracks = get_tracks(mediainfo, ["Video"])
        if not video_tracks:
            exit("no video tracks? the fuck?")
        audio_tracks = get_tracks(mediainfo, ["Audio"])
        if not video_tracks:
            exit("no audio tracks? the fuck?")
        sub_tracks = get_tracks(mediainfo, ["Text"])

        args = [
            "mkvpropedit",
            # tags
            "-t", f"global:{global_tags}",
            # general
            "-e", "info",
            "-s", f"title={file.stem}"
        ]
        for track in video_tracks:
            args.extend([
                "-e", f"track:{track.track_id}",
                "-s", "flag-enabled=1",
                "-s", f"flag-default={'1' if int(track.stream_identifier) == 0 else '0'}",
                "-s", "flag-forced=0",
                "-s", "name="
            ])
            language = next((x.language for x in audio_tracks if x.language), None)
            if language:
                args.extend(["-s", f"language={language}"])
        for track in audio_tracks:
            channels = sum(CHANNEL_LAYOUT_MAP.get(x, 1) for x in track.channel_layout.split(" "))
            title = f"{track.format} {float(channels)}"
            if not audio_tracks[0].language == track.language:
                title += ", different lang, is this wanted?"
            if int(track.stream_identifier) > 0:
                title += ", not first audio, is this commentary?"
            args.extend([
                "-e", f"track:{track.track_id}",
                "-s", "flag-enabled=1",
                "-s", f"flag-default={'1' if int(track.stream_identifier) == 0 else '0'}",
                "-s", "flag-forced=0",
                "-s", f"name={title}",
            ])
        for track in sub_tracks:
            if track.language:
                title = track.other_language[0]
                if not sub_tracks[0].language == track.language:
                    title += ", different lang, is this wanted?"
                if len([x for x in sub_tracks if x.language == track.language and x.codec_id == track.codec_id]) > 1:
                    title += " (Dialect? Forced?)"
            else:
                title = "Undefined???"
            title += f" ({'CC' if track.codec_id == 'S_TEXT/UTF8' else 'type'}?)"
            args.extend([
                "-e", f"track:{track.track_id}",
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
