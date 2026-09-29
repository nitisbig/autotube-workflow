import json
import copy
import unittest
from pathlib import Path
from editor.renderer import Renderer
from editor.modes import available_box, placement_phases

ROOT = Path(__file__).resolve().parents[1]

class LayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = json.loads((ROOT/'config.json').read_text())
        cls.config['output'].update(width=640, height=360)
        cls.config['hand']['enabled'] = False
        cls.config['jackdaw']['enabled'] = False
        cls.renderer = Renderer(cls.config, ROOT)

    def test_free_space_does_not_cover_completed_art(self):
        r=self.renderer
        for cell in range(6):
            a=available_box(r,cell)
            for b in r.cells[:cell]:
                self.assertTrue(a[2]<=b[0] or b[2]<=a[0] or a[3]<=b[1] or b[3]<=a[1])

    def test_phases_and_settled_frame_on_every_scene(self):
        r=self.renderer
        for i,b in enumerate(r.beats):
            end,move,settled=placement_phases(b,r.c['animation'])
            self.assertGreater(end,b['draw_start'])
            self.assertAlmostEqual(move-end,.5)
            self.assertAlmostEqual(settled-move,.6)
            self.assertEqual(r.drawing_frame(settled).tobytes(),r.board(i//6,i%6+1).tobytes())

    def test_hold_is_still_and_movement_finishes_continuously(self):
        r=self.renderer
        for i in range(6):
            end,move,settled=placement_phases(r.beats[i],r.c['animation'])
            self.assertEqual(r.drawing_frame(end+.01).tobytes(),r.drawing_frame(move-.01).tobytes())
            self.assertEqual(r.drawing_frame(settled-1e-8).tobytes(),r.drawing_frame(settled).tobytes())

    def test_swipe_only_appears_during_placement_in_all_six_cells(self):
        r = self.renderer
        for i in range(6):
            end, move, settled = placement_phases(r.beats[i], r.c['animation'])
            for t, visible in ((end+.1, False), ((move+settled)/2, True), (settled, False)):
                with_hand = r.drawing_frame(t).tobytes()
                original = r.paste_swipe_hand
                try:
                    r.paste_swipe_hand = lambda *args: None
                    without_hand = r.drawing_frame(t).tobytes()
                finally:
                    r.paste_swipe_hand = original
                self.assertEqual(with_hand != without_hand, visible)

    def test_swipe_validation_reports_missing_asset_and_invalid_anchor(self):
        from editor.validation import validate
        for key, value, message in (('path', 'missing-swipe.png', 'Missing swipe_hand.path'),
                                    ('tip', [float('nan'), .1], 'swipe_hand.tip'),
                                    ('height_fraction', 0, 'swipe_hand.height_fraction')):
            config = copy.deepcopy(self.config)
            config['swipe_hand'][key] = value
            with self.assertRaisesRegex(ValueError, message):
                validate(config, ROOT)

if __name__=='__main__': unittest.main()
