from django.test import SimpleTestCase

from sablier.services import format_duration, parse_duration


class DurationTests(SimpleTestCase):
    def test_supported_formats(self):
        self.assertEqual(parse_duration("1.5"), 90)
        self.assertEqual(parse_duration("05:30"), 330)
        self.assertEqual(parse_duration("01:02:03"), 3723)
        self.assertEqual(parse_duration("0:01"), 1)
        self.assertEqual(parse_duration("24:00:00"), 86400)

    def test_out_of_bounds_and_malformed_values(self):
        for value in ("0", "24:00:01", "1:60", "1:2:60", "abc", "1:2:3:4"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_duration(value)

    def test_format(self):
        self.assertEqual(format_duration(149.1), "02:30")
        self.assertEqual(format_duration(3723), "01:02:03")
