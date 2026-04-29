# src/hunter_sprite.py
import pygame


class HunterSprite:
    DIRECTIONS = {
        "down":  0,
        "left":  1,
        "right": 2,
        "up":    3,
    }
    FRAME_COUNT = 3

    def __init__(self, sheet_path: str, frame_w: int, frame_h: int, scale: float = 1.0):
        sheet = pygame.image.load(sheet_path).convert_alpha()
        self.frames: dict = {}
        sheet_rect = sheet.get_rect()
        expected_rect = pygame.Rect(
            (self.FRAME_COUNT - 1) * frame_w,
            (len(self.DIRECTIONS) - 1) * frame_h,
            frame_w,
            frame_h,
        )

        if not sheet_rect.contains(expected_rect):
            detected_x = self._find_nontransparent_ranges(sheet, axis="x")
            detected_y = self._find_nontransparent_ranges(sheet, axis="y")
            if len(detected_x) == self.FRAME_COUNT and len(detected_y) == len(self.DIRECTIONS):
                for direction, row in self.DIRECTIONS.items():
                    row_frames = []
                    y0, y1 = detected_y[row]
                    for col in range(self.FRAME_COUNT):
                        x0, x1 = detected_x[col]
                        rect = pygame.Rect(x0, y0, x1 - x0 + 1, y1 - y0 + 1)
                        frame = sheet.subsurface(rect).copy()
                        if scale != 1.0:
                            new_size = (int(frame.get_width() * scale), int(frame.get_height() * scale))
                            frame = pygame.transform.smoothscale(frame, new_size)
                        row_frames.append(frame)
                    self.frames[direction] = row_frames
                self.frame_w = int((detected_x[0][1] - detected_x[0][0] + 1) * scale)
                self.frame_h = int((detected_y[0][1] - detected_y[0][0] + 1) * scale)
                return

            # Fallback: treat the entire image as a single frame if the sheet layout is wrong.
            frame = sheet.copy()
            if scale != 1.0:
                new_size = (int(frame.get_width() * scale), int(frame.get_height() * scale))
                frame = pygame.transform.smoothscale(frame, new_size)
            for direction in self.DIRECTIONS:
                self.frames[direction] = [frame]
            self.frame_w = frame.get_width()
            self.frame_h = frame.get_height()
            self.FRAME_COUNT = 1
            return

        for direction, row in self.DIRECTIONS.items():
            row_frames = []
            for col in range(self.FRAME_COUNT):
                rect  = pygame.Rect(col * frame_w, row * frame_h, frame_w, frame_h)
                frame = sheet.subsurface(rect).copy()
                if scale != 1.0:
                    new_size = (int(frame_w * scale), int(frame_h * scale))
                    frame = pygame.transform.smoothscale(frame, new_size)
                row_frames.append(frame)
            self.frames[direction] = row_frames

        self.frame_w = int(frame_w * scale)
        self.frame_h = int(frame_h * scale)

    @staticmethod
    def _find_nontransparent_ranges(sheet: pygame.Surface, axis: str, min_span: int = 8):
        if axis == "x":
            length = sheet.get_width()
            other = sheet.get_height()
            is_blank = lambda pos: all(sheet.get_at((pos, y)).a == 0 for y in range(other))
        else:
            length = sheet.get_height()
            other = sheet.get_width()
            is_blank = lambda pos: all(sheet.get_at((x, pos)).a == 0 for x in range(other))

        spans = []
        start = None
        for pos in range(length):
            blank = is_blank(pos)
            if blank and start is not None:
                spans.append((start, pos - 1))
                start = None
            elif not blank and start is None:
                start = pos
        if start is not None:
            spans.append((start, length - 1))

        return [span for span in spans if span[1] - span[0] + 1 >= min_span]

    def get_frame(self, direction: str, tick: int, anim_speed: int = 8) -> pygame.Surface:
        direction = direction if direction in self.frames else "down"
        idx = (tick // anim_speed) % self.FRAME_COUNT
        return self.frames[direction][idx]