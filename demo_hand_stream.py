"""Camera-free hand sender. Run beside garden.py --hand-stream.

Move mouse as the cursor. Hold Space/F for a click; release keys for neutral.
Q exits. --legacy uses F=fist and P=palm for the old two-gesture receiver.
This tests transport and interaction, not actual hand detection/calibration.
"""
import argparse
import json
import socket
import time
import uuid


def main():
    import pygame as pg
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--rows", type=int, default=2)
    parser.add_argument("--cols", type=int, default=3)
    parser.add_argument("--legacy", action="store_true")
    args = parser.parse_args()
    pg.init()
    screen = pg.display.set_mode((720, 480))
    pg.display.set_caption("SIMULATED hands: mouse cursor; Space/F click; release to rearm; Q quits")
    font, clock = pg.font.Font(None, 30), pg.time.Clock()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    session, seq = uuid.uuid4().hex, 0
    running = True
    try:
        while running:
            for event in pg.event.get():
                if event.type == pg.QUIT or (event.type == pg.KEYDOWN and event.key in (pg.K_q, pg.K_ESCAPE)):
                    running = False
            keys = pg.key.get_pressed()
            focused = pg.key.get_focused()
            if args.legacy:
                gesture = "closed_fist" if focused and keys[pg.K_f] else "open_palm" if focused and keys[pg.K_p] else "unknown"
            else:
                gesture = "click" if focused and (keys[pg.K_f] or keys[pg.K_SPACE]) else "unknown"
            x, y = pg.mouse.get_pos()
            seq += 1
            data = {"version": 1, "session": session, "calibration": "simulation", "seq": seq,
                    "sent_at": time.time(), "rows": args.rows, "cols": args.cols,
                    "state": "ok" if focused else "ambiguous", "x": x/720 if focused else None,
                    "y": y/480 if focused else None, "gesture": gesture, "score": 1.}
            sock.sendto(json.dumps(data).encode(), (args.host, args.port))
            screen.fill((210, 225, 175))
            for row in range(args.rows):
                for col in range(args.cols):
                    rect = pg.Rect(col*720/args.cols, row*480/args.rows, 720/args.cols, 480/args.rows)
                    pg.draw.rect(screen, (40, 60, 20), rect, 2)
                    screen.blit(font.render(str(row*args.cols+col+1), True, (20, 30, 10)), rect.move(10, 10))
            pg.draw.circle(screen, (230, 100, 50), (x, y), 15)
            screen.blit(font.render("SIMULATED: " + gesture, True, (20, 30, 10)), (10, 445))
            pg.display.flip()
            clock.tick(30)
    finally:
        sock.close()
        pg.quit()


if __name__ == "__main__":
    main()
