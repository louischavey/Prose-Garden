"""Camera -> calibrated normalized locations + gestures -> Python UDP receiver.

Run --calibrate once for each physical setup. No video leaves this process.
"""
import argparse
import hashlib
import json
from pathlib import Path
import socket
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parent
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/gesture_recognizer/gesture_recognizer/float16/1/gesture_recognizer.task"


def download_model(path):
    import urllib.request
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".download")
    try:
        urllib.request.urlretrieve(MODEL_URL, temp)
        if temp.stat().st_size < 1_000_000:
            raise ValueError("Incomplete model download")
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


def transform_from_corners(corners, width, height):
    import cv2
    import numpy as np
    pts = np.asarray(corners, dtype=np.float32)
    if pts.shape != (4, 2) or not np.isfinite(pts).all():
        raise ValueError("Four finite calibration corners required")
    if (pts < 0).any() or (pts > 1).any():
        raise ValueError("Corners must be within the image")
    pixels = pts * [width, height]
    # Click clockwise: TL, TR, BR, BL; reject crossed/tiny/degenerate shapes.
    contour = pixels.astype(np.float32)
    if not cv2.isContourConvex(contour) or cv2.contourArea(contour, oriented=True) <= width*height*.02:
        raise ValueError("Corners must form a clockwise convex tray covering >2% of the image")
    return cv2.getPerspectiveTransform(pts, np.float32([[0, 0], [1, 0], [1, 1], [0, 1]]))


def map_point(matrix, x, y):
    import numpy as np
    mapped = matrix @ np.array([x, y, 1.])
    if abs(mapped[2]) < 1e-8:
        return None
    return float(mapped[0]/mapped[2]), float(mapped[1]/mapped[2])


def hand_observation(result, matrix, elapsed=0., plant_pose="Closed_Fist", cultivate_pose="Open_Palm"):
    """Keep valid position independent of pose confidence; intent gate checks pose."""
    import numpy as np
    observation = dict(state="no_hand", gesture="unknown", score=0., point=None,
                       anchor=None, mapped=None, reason="no_hand", raw_pose="None")
    if len(result.hand_landmarks) > 1:
        observation.update(state="ambiguous", reason="multiple_hands")
    elif len(result.hand_landmarks) == 1:
        landmarks = result.hand_landmarks[0]
        anchor = np.mean([[landmarks[i].x, landmarks[i].y] for i in (0, 5, 9, 13, 17)], axis=0)
        mapped = map_point(matrix, *anchor)
        category = result.gestures[0][0] if result.gestures and result.gestures[0] else None
        score = float(category.score) if category else 0.
        raw_pose = category.category_name if category else "None"
        gesture = {plant_pose: "closed_fist", cultivate_pose: "open_palm"}.get(raw_pose, "unknown")
        inside = mapped is not None and all(0 <= value <= 1 for value in mapped)
        reason = "palm_outside" if not inside else "gesture_uncertain" if score < .7 else "gesture_not_command" if gesture == "unknown" else "ready_pose"
        observation.update(state="ok" if inside else "outside", gesture=gesture, score=score,
                           point=mapped if inside else None, anchor=anchor, mapped=mapped, reason=reason, raw_pose=raw_pose)
    if elapsed > .5:
        observation.update(state="ambiguous", point=None, reason="processing_slow")
    return observation


def calibrate(cap, args):
    import cv2
    import numpy as np
    from tape_calibration import detect_tape_corners, StableTape
    points = []
    title = "Poetree calibration - A: white tape / click TL TR BR BL"
    cv2.namedWindow(title, cv2.WINDOW_AUTOSIZE)
    size = [1, 1]
    mode = "manual"
    def click(event, x, y, flags, param):
        nonlocal mode
        if event == cv2.EVENT_LBUTTONDOWN and len(points) < 4:
            mode = "manual"
            points.append([x/size[0], y/size[1]])
    cv2.setMouseCallback(title, click)
    error = ""
    auto = False
    stable = StableTape()
    value_min = 180
    roi = None
    show_mask = False
    mask_title = "Tape mask - white pixels are candidates"
    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                raise RuntimeError("Camera stopped during calibration")
            height, width = frame.shape[:2]
            size[:] = [width, height]
            raw = frame.copy()
            if auto:
                proposed, mask, auto_status = detect_tape_corners(raw, value_min=value_min, roi=roi)
                accepted = stable.update(proposed)
                error = auto_status + f" | stable {len(stable.samples)}/8 | V>={value_min}"
                if accepted is not None:
                    points[:] = accepted
                    mode, auto = "white_tape_centers", False
            elif show_mask:
                _, mask, _ = detect_tape_corners(raw, value_min=value_min, roi=roi)
            if show_mask:
                cv2.imshow(mask_title, mask)
            if roi is not None:
                x, y, w, h = roi
                cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 180, 0), 1)
            for i, point in enumerate(points):
                xy = tuple(int(v) for v in np.array(point)*[width, height])
                cv2.circle(frame, xy, 6, (0, 255, 255), -1)
                cv2.putText(frame, str(i+1), xy, 0, .7, (0, 0, 255), 2)
            if len(points) == 4:
                try:
                    matrix = transform_from_corners(points, width, height)
                    inverse = np.linalg.inv(matrix)
                    for row in range(args.rows):
                        for col in range(args.cols):
                            poly = [[col/args.cols, row/args.rows], [(col+1)/args.cols, row/args.rows],
                                    [(col+1)/args.cols, (row+1)/args.rows], [col/args.cols, (row+1)/args.rows]]
                            image_poly = np.int32([np.array(map_point(inverse, *p))*[width, height] for p in poly])
                            cv2.polylines(frame, [image_poly], True, (100, 255, 100), 2)
                            center = map_point(inverse, (col+.5)/args.cols, (row+.5)/args.rows)
                            cv2.putText(frame, str(row*args.cols+col+1), tuple(np.int32(np.array(center)*[width, height])), 0, .8, (0, 255, 0), 2)
                    error = "Check tape CENTERS/grid. ENTER saves; A redetects; R manual; Q quits"
                except ValueError as exc:
                    error = str(exc) + " - R resets"
            elif not auto:
                error = "A: detect 4 white tape patches OR click TL, TR, BR, BL. R resets; Q quits"
            # Dark panels keep instructions legible over both white tape and soil.
            cv2.rectangle(frame, (0, 0), (width, 54), (20, 20, 20), -1)
            cv2.putText(frame, error[:100], (8, 20), 0, .36, (255, 255, 255), 1)
            cv2.putText(frame, "B: limit search area | +/-: tape brightness | M: mask | Enter: accept", (8, 43), 0, .4, (255, 255, 255), 1)
            cv2.imshow(title, frame)
            key = cv2.waitKey(20) & 255
            if key in (ord('q'), 27):
                raise RuntimeError("Calibration cancelled")
            if key == ord('r'):
                points.clear()
                mode, auto, stable = "manual", False, StableTape()
            if key == ord('a'):
                points.clear()
                auto, stable = True, StableTape()
            if key in (ord('+'), ord('='), ord('-')):
                value_min = max(80, min(250, value_min + (10 if key in (ord('+'), ord('=')) else -10)))
                points.clear()
                auto, stable = True, StableTape()
            if key == ord('b'):
                box = cv2.selectROI("Choose tray search area - ENTER accepts", raw, showCrosshair=True, fromCenter=False)
                cv2.destroyWindow("Choose tray search area - ENTER accepts")
                roi = tuple(map(int, box)) if box[2] and box[3] else None
                points.clear()
                auto, stable = True, StableTape()
            if key == ord('m'):
                show_mask = not show_mask
                if not show_mask:
                    cv2.destroyWindow(mask_title)
            if key in (10, 13) and len(points) == 4 and not auto:
                try:
                    transform_from_corners(points, width, height)
                except ValueError:
                    continue
                profile = {"version": 1, "id": uuid.uuid4().hex, "camera": args.camera,
                           "width": width, "height": height, "rows": args.rows, "cols": args.cols,
                           "corners": points, "method": mode,
                           "tape_value_min": value_min, "tape_search_roi": roi}
                args.profile.parent.mkdir(parents=True, exist_ok=True)
                args.profile.write_text(json.dumps(profile, indent=2), encoding="utf-8")
                print(f"Saved {args.profile}. Recalibrate after any camera/tray movement.")
                return profile
    finally:
        cv2.destroyWindow(title)
        if show_mask:
            cv2.destroyWindow(mask_title)


def main():
    from gesture_trials import POSES, GestureTrials, default_report
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--camera", type=int, default=0, help="Camera index; use 1/2 for a USB webcam")
    parser.add_argument("--host", default="127.0.0.1", help="Garden receiver host; localhost by default")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--rows", type=int, default=2)
    parser.add_argument("--cols", type=int, default=3)
    parser.add_argument("--calibrate", action="store_true")
    parser.add_argument("--profile", type=Path, default=ROOT/"camera-profile.json")
    parser.add_argument("--model", type=Path, default=ROOT/"models/gesture_recognizer.task")
    parser.add_argument("--download-model", action="store_true", help="Download official version-1 model then exit")
    parser.add_argument("--confirm-setup", action="store_true", help="Confirm saved calibration still matches camera/tray placement")
    parser.add_argument("--no-preview", action="store_true")
    parser.add_argument("--gesture-test", action="store_true", help="Timed comparison of candidate poses; sends NO garden packets")
    parser.add_argument("--plant-pose", choices=POSES, default="Closed_Fist")
    parser.add_argument("--cultivate-pose", choices=POSES, default="Open_Palm")
    args = parser.parse_args()
    if args.download_model:
        download_model(args.model)
        print(f"Model saved: {args.model}")
        return
    if args.plant_pose == args.cultivate_pose:
        parser.error("Plant and cultivate poses must differ")
    if args.gesture_test and (args.no_preview or args.calibrate):
        parser.error("Gesture test uses the existing profile: --confirm-setup --gesture-test, with preview enabled")
    from hand_input import IntentGate
    IntentGate(args.rows, args.cols)
    if not args.model.exists():
        parser.error("Model missing. Run camera_stream.py --download-model first.")
    if not args.calibrate and not args.confirm_setup:
        parser.error("Use --calibrate or --confirm-setup after checking the unchanged physical setup")
    import cv2
    import mediapipe as mp
    import numpy as np
    cap = cv2.VideoCapture(args.camera)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    session, seq = uuid.uuid4().hex, 0
    def send(state, gesture="unknown", score=0., point=None, reason="", raw_pose="None"):
        nonlocal seq
        seq += 1
        message = {"version": 1, "session": session, "seq": seq, "sent_at": time.time(),
                   "calibration": profile["id"], "rows": args.rows, "cols": args.cols,
                   "state": state, "x": point[0] if point else None, "y": point[1] if point else None,
                   "gesture": gesture, "score": float(score), "reason": reason, "raw_pose": raw_pose}
        sock.sendto(json.dumps(message, allow_nan=False).encode(), (args.host, args.port))
        return message
    try:
        if not cap.isOpened():
            raise RuntimeError("Camera unavailable; check OS permissions and --camera index")
        profile = calibrate(cap, args) if args.calibrate else json.loads(args.profile.read_text(encoding="utf-8"))
        if profile.get("version") != 1 or profile.get("camera") != args.camera or (profile.get("rows"), profile.get("cols")) != (args.rows, args.cols):
            raise ValueError("Camera/layout differs from saved profile; use --calibrate")
        matrix = transform_from_corners(profile["corners"], profile["width"], profile["height"])
        trials = GestureTrials(default_report(ROOT), dict(camera=args.camera, calibration=profile["id"])) if args.gesture_test else None
        options = mp.tasks.vision.GestureRecognizerOptions(
            base_options=mp.tasks.BaseOptions(model_asset_path=str(args.model)),
            running_mode=mp.tasks.vision.RunningMode.VIDEO, num_hands=2)
        if trials:
            print(f"GESTURE TEST: no garden actions sent. Press 1-5 for trials; report: {trials.path}")
        else:
            print(f"Streaming to {args.host}:{args.port}. Plant={args.plant_pose}; cultivate={args.cultivate_pose}. Exit tray to arm; Q quits.")
        previous_ms = -1
        with mp.tasks.vision.GestureRecognizer.create_from_options(options) as recognizer:
            while True:
                start = time.monotonic()
                ok, frame = cap.read()
                if not ok:
                    if not trials:
                        send("no_hand")
                    raise RuntimeError("Camera disconnected; restart and verify calibration")
                height, width = frame.shape[:2]
                if (width, height) != (profile["width"], profile["height"]):
                    if not trials:
                        send("uncalibrated")
                    raise ValueError("Frame dimensions changed; recalibrate")
                stamp = max(previous_ms+1, int(time.monotonic()*1000))
                previous_ms = stamp
                result = recognizer.recognize_for_video(mp.Image(image_format=mp.ImageFormat.SRGB,
                    data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)), stamp)
                observation = hand_observation(result, matrix, time.monotonic()-start, args.plant_pose, args.cultivate_pose)
                state, gesture, score, point = (observation[k] for k in ("state", "gesture", "score", "point"))
                for landmarks in result.hand_landmarks:
                    for lm in landmarks:
                        cv2.circle(frame, (int(lm.x*width), int(lm.y*height)), 3, (100, 255, 100), -1)
                if trials:
                    trials.update(observation, time.monotonic())
                else:
                    send(state, gesture, score, point, observation["reason"], observation["raw_pose"])
                if not args.no_preview:
                    inverse = np.linalg.inv(matrix)
                    for r in range(args.rows):
                        for c in range(args.cols):
                            corners = [(c/args.cols, r/args.rows), ((c+1)/args.cols, r/args.rows),
                                       ((c+1)/args.cols, (r+1)/args.rows), (c/args.cols, (r+1)/args.rows)]
                            polygon = np.int32([np.array(map_point(inverse, *corner))*[width, height] for corner in corners])
                            cv2.polylines(frame, [polygon], True, (0, 220, 220), 1)
                            center = map_point(inverse, (c+.5)/args.cols, (r+.5)/args.rows)
                            xy = tuple(np.int32(np.array(center)*[width, height]))
                            cv2.putText(frame, str(r*args.cols+c+1), xy, 0, .8, (0, 255, 255), 2)
                    if observation["anchor"] is not None:
                        xy = tuple(np.int32(observation["anchor"]*[width, height]))
                        cv2.circle(frame, xy, 10, (0, 255, 255) if state == "ok" else (0, 0, 255), 3)
                    mapped = observation["mapped"]
                    position = f" x={mapped[0]:.2f} y={mapped[1]:.2f}" if mapped else ""
                    label = f"POSITION {state}{position} | {observation['raw_pose']} {score:.2f}"
                    help_text = {"palm_outside": "Palm-center ring is outside tray. Move lower/inside; check calibration.",
                                 "multiple_hands": "Two hands visible: remove the other hand from camera view.",
                                 "gesture_uncertain": "Position tracked; pose unclear. Commands still require score >=0.70.",
                                 "gesture_not_command": "Position tracked. Neutral pose can rearm; fist plants, palm cultivates.",
                                 "processing_slow": "Frame processing >0.5s: commands paused.",
                                 "no_hand": "No hand detected.",
                                 "ready_pose": "Position and pose detected. Exit tray to arm, then hold pose inside."}[observation["reason"]]
                    if not trials and observation["reason"] == "ready_pose":
                        help_text = "Plant="+args.plant_pose+" | Cultivate="+args.cultivate_pose+" | Exit tray to arm; hold inside."
                    cv2.rectangle(frame, (0, 0), (width, 54), (20, 20, 20), -1)
                    cv2.putText(frame, label, (8, 20), 0, .44, (255, 255, 255), 1)
                    cv2.putText(frame, help_text, (8, 43), 0, .38, (255, 255, 255), 1)
                    if trials:
                        frame = cv2.copyMakeBorder(frame, 0, 65, 0, 0, cv2.BORDER_CONSTANT, value=(20,20,20))
                        cv2.putText(frame, "TEST ONLY: 1 Fist | 2 Palm | 3 V sign | 4 Index | 5 Thumbs-up", (8, height+20), 0, .43, (255,255,255), 1)
                        cv2.putText(frame, trials.status(time.monotonic()), (8, height+44), 0, .43, (255,255,255), 1)
                    cv2.imshow("Poetree hand stream (unmirrored) - Q quits", frame)
                    key = cv2.waitKey(1) & 255
                    if trials and ord('1') <= key <= ord('5'):
                        trials.start(key-ord('1'), time.monotonic())
                    if key in (ord('q'), 27):
                        break
                time.sleep(max(0, 1/30-(time.monotonic()-start)))
        if not trials:
            send("no_hand")
    finally:
        cap.release()
        sock.close()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, ImportError) as exc:
        print(f"Camera: {exc}", file=sys.stderr)
        raise SystemExit(1)
