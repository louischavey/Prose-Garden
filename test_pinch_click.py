import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch
import numpy as np
from camera_stream import hand_observation, main
from hand_input import ClickGate
from pinch_click import with_pinch_click
from test_hand_input import packet


def landmarks(gap=0., reach=.7):
    points=np.zeros((21,3))
    points[0]=(0,0,0)
    points[9]=(0,1,0)
    points[5]=(-.5,.5,0)
    points[17]=(.5,.5,0)
    points[8]=(-.5,.5+reach,0)
    points[4]=points[8]+(gap,0,0)
    world=[SimpleNamespace(x=p[0],y=p[1],z=p[2]) for p in points]
    image=[SimpleNamespace(x=.5+p[0]*.1,y=.5+p[1]*.1,z=p[2]*.1) for p in points]
    return image,world


def result(image,world,label="None"):
    return SimpleNamespace(hand_landmarks=[image],hand_world_landmarks=[world],
                           gestures=[[SimpleNamespace(category_name=label,score=.9)]])


class PinchTests(unittest.TestCase):
    def test_pinch_adds_click_without_changing_position(self):
        image,world=landmarks()
        original=hand_observation(result(image,world),np.eye(3))
        pinch=with_pinch_click(original,image,world)
        self.assertEqual(pinch["gesture"],"click")
        self.assertEqual(pinch["click_source"],"pinch_rule")
        self.assertEqual(original["raw_pose"],"None")
        for name in ("anchor","mapped","point","state"):
            np.testing.assert_array_equal(pinch[name],original[name])

    def test_open_fingers_preserve_model_click_and_folded_fist_rejects_pinch(self):
        for gap,reach in ((.8,.7),(0.,.1)):
            image,world=landmarks(gap,reach)
            observation=hand_observation(result(image,world,"Thumb_Up"),np.eye(3))
            observation["gesture"]="click"
            chosen=with_pinch_click(observation,image,world)
            self.assertEqual(chosen["raw_pose"],"Thumb_Up")
            self.assertEqual(chosen["gesture"],"click")
            self.assertEqual(chosen["click_source"],"model")

    def test_open_pinch_rearms_without_model_label_and_preserves_position(self):
        image,world=landmarks(.8,.7)
        original=hand_observation(result(image,world),np.eye(3))
        original.update(gesture="unknown",score=.1)
        opened=with_pinch_click(original,image,world)
        self.assertEqual(opened["click_source"],"pinch_release")
        self.assertEqual(opened["score"],1.)
        self.assertEqual(opened["gesture"],"unknown")
        for name in ("anchor","mapped","point","state"):
            np.testing.assert_array_equal(opened[name],original[name])

    def test_invalid_and_suppressed_tracking_do_not_create_pinch(self):
        image,world=landmarks()
        observation=hand_observation(result(image,world),np.eye(3),elapsed=.6)
        self.assertNotEqual(with_pinch_click(observation,image,world)["raw_pose"],"Pinch")
        observation=hand_observation(result(image,world),np.eye(3))
        world[4].x=float('nan')
        self.assertNotEqual(with_pinch_click(observation,image,world)["raw_pose"],"Pinch")

    def test_switching_thumb_and_pinch_is_still_one_click_until_release(self):
        gate=ClickGate(hold=.6)
        gate.update(packet(state="outside"),0)
        gate.update(packet(state="outside"),.31)
        events=[]
        for index,tick in enumerate((.4,.7,1.01,1.2,1.5,1.8)):
            observation=packet(gesture="click",raw_pose="Pinch" if index%2 else "Thumb_Up")
            event=gate.update(observation,tick,target_id="same-root")
            if event: events.append(event)
        self.assertEqual(len(events),1)

    def test_production_sender_accepts_both_option_and_emits_pinch_click(self):
        image,world=landmarks()
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"profile.json"
            text=json.dumps(dict(version=1,id="test",camera=0,width=640,height=480,rows=2,cols=3,
                                 corners=[[.1,.1],[.9,.1],[.9,.9],[.1,.9]]))
            path.write_text(text)
            camera=MagicMock()
            camera.isOpened.return_value=True
            camera.read.return_value=(True,np.zeros((480,640,3),dtype=np.uint8))
            model=MagicMock()
            model.recognize_for_video.return_value=result(image,world)
            context=MagicMock()
            context.__enter__.return_value=model
            with patch("sys.argv",["camera_stream.py","--confirm-setup","--enable-pinch","--profile",str(path)]), \
                 patch("cv2.VideoCapture",return_value=camera),patch("cv2.imshow"),patch("cv2.destroyAllWindows"), \
                 patch("cv2.waitKey",return_value=ord('q')),patch("socket.socket") as socket_factory, \
                 patch("mediapipe.tasks.python.vision.GestureRecognizer.create_from_options",return_value=context):
                main()
            sent=json.loads(socket_factory.return_value.sendto.call_args_list[0].args[0])
            self.assertEqual(sent["gesture"],"click")
            self.assertEqual(sent["raw_pose"],"Pinch")
            self.assertEqual(sent["click_source"],"pinch_rule")
            self.assertEqual(path.read_text(),text)


if __name__ == '__main__': unittest.main()
