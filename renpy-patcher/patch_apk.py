"""Build a separately signed, local Ren'Py APK with an in-game keyboard."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile

HERE = Path(__file__).resolve().parent
ASSET = "assets/x-game/x-keyquest_overlay.rpyc"


def executable(directory, name):
    directory = Path(directory).expanduser().resolve(strict=True)
    for suffix in ("", ".exe", ".bat", ".cmd", ".sh"):
        candidate = directory / (name + suffix)
        if candidate.is_file():
            return str(candidate)
    raise ValueError(f"{name} was not found in {directory}")


def run(args, **kw):
    subprocess.run([str(arg) for arg in args], check=True, **kw)


def pull_installed(package, destination):
    import re
    if not re.fullmatch(r"[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)+", package):
        raise ValueError("Enter a valid Android package name.")
    adb = shutil.which("adb")
    if not adb:
        raise ValueError("Install Android Platform Tools and add adb to PATH.")
    result = subprocess.check_output([adb, "-d", "shell", "pm", "path", package], text=True)
    paths = [line.removeprefix("package:") for line in result.splitlines() if line.startswith("package:")]
    if len(paths) != 1 or not paths[0].endswith(".apk"):
        raise ValueError("Select a single installed APK. Split packages cannot be patched.")
    run([adb, "-d", "pull", paths[0], destination])


def patch(source, destination, sdk, build_tools, keystore):
    destination = Path(destination).expanduser().resolve()
    if destination.exists() or destination.suffix.lower() != ".apk":
        raise ValueError("Choose a new output filename ending in .apk.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="keyquest-", dir=destination.parent) as temp:
        work = Path(temp)
        with zipfile.ZipFile(source) as original:
            names = original.namelist()
            if ("AndroidManifest.xml" not in names or "assets/private.mp3" not in names
                    or not any(n.startswith("assets/x-game/") and n.endswith((".rpyc", ".rpa")) for n in names)):
                raise ValueError("This APK does not have the supported Ren’Py universal APK layout.")
            if len(names) != len(set(names)) or ASSET in names:
                raise ValueError("The APK has duplicate entries or already contains this keyboard.")

            game = work / "compile" / "game"
            game.mkdir(parents=True)
            shutil.copyfile(HERE / "keyquest_overlay.rpy", game / "keyquest_overlay.rpy")
            (game / "script.rpy").write_text("label start:\n    return\n", encoding="utf-8")
            command = executable(sdk, "renpy.exe" if os.name == "nt" else "renpy.sh")
            run([command, game.parent, "compile"])
            compiled = game / "keyquest_overlay.rpyc"
            if not compiled.is_file():
                raise ValueError("The selected Ren’Py SDK did not compile the keyboard.")

            unsigned = work / "unsigned.apk"
            with zipfile.ZipFile(unsigned, "w", allowZip64=True) as rebuilt:
                for entry in original.infolist():
                    name = entry.filename.upper()
                    if name.startswith("META-INF/") and name.rsplit("/", 1)[-1].endswith(
                            (".SF", ".RSA", ".DSA", ".EC", "MANIFEST.MF")):
                        continue
                    with original.open(entry) as reader, rebuilt.open(
                            entry, "w", force_zip64=entry.file_size >= zipfile.ZIP64_LIMIT) as writer:
                        shutil.copyfileobj(reader, writer, length=1024 * 1024)
                rebuilt.write(compiled, ASSET, compress_type=zipfile.ZIP_STORED)

        keystore = Path(keystore).expanduser().resolve()
        if not keystore.exists():
            keytool = shutil.which("keytool")
            if not keytool:
                raise ValueError("Install a Java JDK and add keytool to PATH.")
            keystore.parent.mkdir(parents=True, exist_ok=True)
            run([keytool, "-genkeypair", "-noprompt", "-keystore", keystore, "-storepass", "android",
                 "-keypass", "android", "-alias", "keyquest", "-dname", "CN=Keyquest Sideload",
                 "-keyalg", "RSA", "-keysize", "2048", "-validity", "10000"])

        aligned, signed = work / "aligned.apk", work / "signed.apk"
        zipalign = executable(build_tools, "zipalign")
        apksigner = executable(build_tools, "apksigner")
        run([zipalign, "-P", "16", "4", unsigned, aligned])
        run([apksigner, "sign", "--ks", keystore, "--ks-key-alias", "keyquest", "--ks-pass",
             "pass:android", "--v4-signing-enabled", "false", "--out", signed, aligned])
        run([apksigner, "verify", signed])
        run([zipalign, "-c", "-P", "16", "4", signed])
        with signed.open("rb") as reader, destination.open("xb") as writer:
            try:
                shutil.copyfileobj(reader, writer, length=1024 * 1024)
            except BaseException:
                writer.close()
                destination.unlink()
                raise
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    origin = parser.add_mutually_exclusive_group(required=True)
    origin.add_argument("--apk", type=Path)
    origin.add_argument("--installed", help="Android package to pull over authorized USB ADB")
    parser.add_argument("--sdk", required=True, help="Ren’Py SDK matching the game version")
    parser.add_argument("--build-tools", required=True, help="Android SDK build-tools 35+ directory")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--keystore", type=Path, help="Existing Keyquest test key or path to create it")
    args = parser.parse_args()
    keystore = args.keystore or args.output.parent / "keyquest-sideload.p12"
    try:
        with tempfile.TemporaryDirectory(prefix="keyquest-input-") as temp:
            source = args.apk
            if args.installed:
                source = Path(temp) / "original.apk"
                pull_installed(args.installed, source)
            print(patch(source, args.output, args.sdk, args.build_tools, keystore))
    except (OSError, ValueError, zipfile.BadZipFile, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Keyquest: {error}\n")


if __name__ == "__main__":
    main()
