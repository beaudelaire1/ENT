from django.test import SimpleTestCase

from core.formatting import human_mb


class HumanSizeTests(SimpleTestCase):
    def test_megabytes_stay_megabytes(self):
        self.assertEqual(human_mb(25), "25 Mo")
        self.assertEqual(human_mb(10.5), "10.5 Mo")
        self.assertEqual(human_mb(0), "0 Mo")

    def test_a_gigabyte_and_beyond_is_written_as_such(self):
        self.assertEqual(human_mb(1024), "1 Go")
        self.assertEqual(human_mb(10240), "10 Go")
        self.assertEqual(human_mb(1536), "1.5 Go")
