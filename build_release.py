#!/usr/bin/env python3
"""Build a release zip of QLC+ Show Creator for Windows."""

import argparse
import os
import shutil
import subprocess
import sys
import zipfile


def read_version():
    """Read __version__ from _version.py."""
    version_vars = {}
    with open(os.path.join(os.path.dirname(__file__), '_version.py')) as f:
        exec(f.read(), version_vars)
    return version_vars['__version__']


def run(cmd, description, check=True):
    """Run a subprocess command, printing status."""
    print(f"\n{'='*60}")
    print(f"  {description}")
    print(f"{'='*60}")
    print(f"  > {' '.join(cmd)}\n")
    result = subprocess.run(cmd, check=check)
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description='Build QLC+ Show Creator release')
    parser.add_argument('--skip-tests', action='store_true', help='Skip running pytest')
    args = parser.parse_args()

    project_root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_root)

    version = read_version()
    print(f"\nBuilding QLC+ Show Creator v{version}")

    # Step 1: Run tests
    if not args.skip_tests:
        success = run(
            [sys.executable, '-m', 'pytest', '-m', 'not integration and not visual', '-q'],
            'Running tests',
            check=False,
        )
        if not success:
            print("\nTests failed. Fix them or use --skip-tests to skip.")
            sys.exit(1)
    else:
        print("\nSkipping tests (--skip-tests)")

    # Step 2: Run PyInstaller
    run(
        [sys.executable, '-m', 'PyInstaller', 'qlcshowcreator.spec', '--noconfirm'],
        'Building with PyInstaller',
    )

    dist_dir = os.path.join(project_root, 'dist', 'QLCShowCreator')
    if not os.path.isdir(dist_dir):
        print(f"\nERROR: Expected output directory not found: {dist_dir}")
        sys.exit(1)

    # Step 3: Smoke test
    exe_path = os.path.join(dist_dir, 'QLCShowCreator.exe')
    if not os.path.isfile(exe_path):
        print(f"\nERROR: Executable not found: {exe_path}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"  Smoke test: --version")
    print(f"{'='*60}")
    result = subprocess.run([exe_path, '--version'], capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        print(f"  Smoke test failed (exit code {result.returncode})")
        print(f"  stdout: {result.stdout}")
        print(f"  stderr: {result.stderr}")
        sys.exit(1)
    print(f"  {result.stdout.strip()}")

    # Step 4: Create zip
    release_dir = os.path.join(project_root, 'release')
    os.makedirs(release_dir, exist_ok=True)

    zip_name = f"QLCShowCreator-v{version}-windows.zip"
    zip_path = os.path.join(release_dir, zip_name)

    if os.path.exists(zip_path):
        os.remove(zip_path)

    print(f"\n{'='*60}")
    print(f"  Creating {zip_name}")
    print(f"{'='*60}")

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(dist_dir):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.join('QLCShowCreator', os.path.relpath(file_path, dist_dir))
                zf.write(file_path, arcname)

    # Step 5: Summary
    zip_size = os.path.getsize(zip_path) / (1024 * 1024)
    exe_size = os.path.getsize(exe_path) / (1024 * 1024)

    dist_total = sum(
        os.path.getsize(os.path.join(r, f))
        for r, _, files in os.walk(dist_dir)
        for f in files
    ) / (1024 * 1024)

    print(f"\n{'='*60}")
    print(f"  Build complete!")
    print(f"{'='*60}")
    print(f"  Version:       v{version}")
    print(f"  Executable:    {exe_size:.1f} MB")
    print(f"  Dist folder:   {dist_total:.1f} MB")
    print(f"  Zip file:      {zip_size:.1f} MB")
    print(f"  Output:        {zip_path}")
    print()


if __name__ == '__main__':
    main()
