"""Source-capture font evidence must use resolved layout font and DPI."""
import unittest
from types import SimpleNamespace
from marble_source_capture import capture_label_font


class CaptureFontTest(unittest.TestCase):
    def test_resolved_family_and_point_to_pixel_conversion(self):
        calls = []
        font = SimpleNamespace(name="Actual fallback", size=14, dpi=96,
                               weight="normal", ascent=16, descent=-5,
                               get_glyphs=lambda text: ([SimpleNamespace(advance=8)
                                                      for _ in text], []))
        def get_font(position, dpi):
            calls.append((position, dpi))
            return font
        label = SimpleNamespace(document=SimpleNamespace(get_font=get_font),
            dpi=96, text="Test", font_name=["Unavailable", "Actual fallback"],
            content_width=120, content_height=21, anchor_x="center",
            anchor_y="top", x=400, y=545)
        result = capture_label_font(label)
        self.assertEqual(calls, [(0, 96)])
        self.assertEqual(result["resolvedFamily"], "Actual fallback")
        self.assertAlmostEqual(result["pixelSize"], 14 * 4 / 3)
        self.assertEqual(result["descent"], -5)
        self.assertEqual(result["requestedFamilies"], label.font_name)
        self.assertEqual(result["text"], "Test")
        self.assertEqual(result["glyphAdvances"], [8,8,8,8])


if __name__ == "__main__":
    unittest.main()
