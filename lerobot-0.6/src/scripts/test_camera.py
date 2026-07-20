"""Test SO-101 camera configuration matching the reference project.

Reference:
    https://github.com/JereoZero/so101-real/blob/main/踩坑记录/06-camera.md

Camera layout:
    front (gripper view): index=2, fourcc=YUYV, 640x480@30
    top   (third-person): index=0, fourcc=MJPG, 640x480@30
"""

import argparse
import sys

import cv2


def list_cameras(max_idx: int = 10):
    """List indices that OpenCV can open."""
    print("Scanning OpenCV camera indices...")
    found = []
    for i in range(max_idx):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            print(f"  /dev/video{i}: {w}x{h} @ {fps:.1f}fps")
            found.append(i)
        cap.release()
    if not found:
        print("  No cameras found.")
    return found


def test_camera(index: int, fourcc: str | None, width: int, height: int, fps: int):
    """Open camera with given settings and print actual values."""
    print(f"\nTesting /dev/video{index} (requested {width}x{height}@{fps}, fourcc={fourcc})")
    cap = cv2.VideoCapture(index)
    if not cap.isOpened():
        print("  FAILED to open")
        return False

    if fourcc:
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*fourcc))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    cap.set(cv2.CAP_PROP_FPS, fps)

    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    actual_fps = cap.get(cv2.CAP_PROP_FPS)
    actual_fourcc = int(cap.get(cv2.CAP_PROP_FOURCC))
    actual_fourcc_str = "".join(chr((actual_fourcc >> 8 * i) & 0xFF) for i in range(4))

    print(f"  Actual: {actual_w}x{actual_h} @ {actual_fps:.1f}fps, fourcc={actual_fourcc_str}")

    ok, frame = cap.read()
    if not ok:
        print("  FAILED to read frame")
        cap.release()
        return False

    print(f"  Frame shape: {frame.shape}, dtype: {frame.dtype}")
    cap.release()
    return True


def main():
    parser = argparse.ArgumentParser(description="Test SO-101 cameras")
    parser.add_argument("--scan", action="store_true", help="Scan all camera indices")
    parser.add_argument(
        "--cameras",
        nargs="+",
        default=["front", "top"],
        choices=["front", "top"],
        help="Which configured cameras to test",
    )
    args = parser.parse_args()

    configured = {
        "front": {"index": 2, "fourcc": "YUYV", "width": 640, "height": 480, "fps": 30},
        "top": {"index": 0, "fourcc": "MJPG", "width": 640, "height": 480, "fps": 30},
    }

    if args.scan:
        list_cameras()
        return

    all_ok = True
    for name in args.cameras:
        cfg = configured[name]
        ok = test_camera(cfg["index"], cfg["fourcc"], cfg["width"], cfg["height"], cfg["fps"])
        all_ok = all_ok and ok

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
