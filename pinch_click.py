"""Optional pinch click rule over existing MediaPipe landmarks, not a new model."""


def with_pinch_click(observation, landmarks, world_landmarks=None, aspect=.75):
    """Add a second click source; never change anchor/mapped/point/state.

    Thumb/index distance is normalized by palm size. A small index reach rejects
    a collapsed/folded fist. Score is a rule margin, not model confidence.
    """
    import numpy as np
    result = dict(observation)
    result["click_source"] = "model"
    result["model_pose"] = observation["raw_pose"]
    if observation["state"] not in ("ok", "outside") or len(landmarks) != 21:
        return result
    if world_landmarks is not None and len(world_landmarks) == 21:
        points = np.array([[p.x,p.y,p.z] for p in world_landmarks],dtype=float)
    else:
        points = np.array([[p.x,p.y*aspect,getattr(p,"z",0.)] for p in landmarks],dtype=float)
    if not np.isfinite(points).all():
        return result
    scale = max(np.linalg.norm(points[5]-points[17]),np.linalg.norm(points[0]-points[9]))
    if scale < 1e-6:
        return result
    gap = float(np.linalg.norm(points[4]-points[8])/scale)
    reach = float(np.linalg.norm(points[8]-points[5])/scale)
    result["pinch_ratio"] = round(gap,3)
    if gap <= .28 and reach >= .35:
        result.update(gesture="click",raw_pose="Pinch",score=.7+.3*max(0.,min(1.,(.28-gap)/.28)),
                      click_source="pinch_rule")
        if result["state"] == "ok":
            result["reason"] = "ready_pose"
    elif gap >= .45 and reach >= .35 and result["gesture"] != "click":
        # Explicitly opened pinch rearms even if the model names no gesture.
        result.update(gesture="unknown", score=1., click_source="pinch_release")
    return result
