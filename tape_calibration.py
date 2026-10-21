"""Conservative white-tape corner proposals. Operator confirmation is required."""
import math


def detect_tape_corners(frame, value_min=180, saturation_max=65, roi=None):
    """Return four normalized tape CENTERS and full-frame mask; refuse ambiguity.

    roi is an optional pixel (x,y,width,height) search box. Use four separated,
    compact white patches on dark soil. This does not identify encoded markers.
    """
    import cv2
    import numpy as np
    height, width = frame.shape[:2]
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, np.array([0, 0, value_min]), np.array([179, saturation_max, 255]))
    if roi is not None:
        x, y, w, h = roi
        keep = np.zeros_like(mask)
        keep[y:y+h, x:x+w] = 255
        mask = cv2.bitwise_and(mask, keep)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    candidates = []
    for contour in contours:
        area = cv2.contourArea(contour)
        if not max(12, width*height*.00005) <= area <= width*height*.02:
            continue
        x, y, w, h = cv2.boundingRect(contour)
        if not .4 <= w/h <= 2.5 or area/(w*h) < .35:
            continue
        # Reject patches clipped by image/search bounds: their centers are biased.
        left, top, rw, rh = roi if roi is not None else (0, 0, width, height)
        if x <= left or y <= top or x+w >= left+rw or y+h >= top+rh:
            continue
        moments = cv2.moments(contour)
        if moments["m00"]:
            candidates.append([moments["m10"]/moments["m00"]/width,
                               moments["m01"]/moments["m00"]/height])
    if len(candidates) != 4:
        return None, mask, f"Found {len(candidates)} white patches; need exactly 4. B: search box; +/-: brightness; M: mask"
    points = np.asarray(candidates)
    center = points.mean(axis=0)
    points = np.array(sorted(points, key=lambda p: math.atan2(p[1]-center[1], p[0]-center[0])))
    first = int(np.argmin(points.sum(axis=1)))
    points = np.roll(points, -first, axis=0)
    if any(np.linalg.norm(points[i]-points[j]) < .12 for i in range(4) for j in range(i)):
        return None, mask, "White patches too close together; use four tray corners"
    contour = np.float32(points * [width, height])
    if not cv2.isContourConvex(contour) or cv2.contourArea(contour, oriented=True) < width*height*.05:
        return None, mask, "White patches do not form a usable tray quadrilateral"
    return points.tolist(), mask, "Four white patches found"


class StableTape:
    def __init__(self, required=8, tolerance=.008):
        self.required, self.tolerance = required, tolerance
        self.reference = None
        self.samples = []

    def update(self, points):
        import numpy as np
        if points is None:
            self.reference, self.samples = None, []
            return None
        points = np.asarray(points, dtype=float)
        if self.reference is None or np.max(np.linalg.norm(points-self.reference, axis=1)) > self.tolerance:
            self.reference, self.samples = points, [points]
        else:
            self.samples.append(points)
        if len(self.samples) >= self.required:
            return np.mean(self.samples[-self.required:], axis=0).tolist()
        return None
