import subprocess
import unittest
from unittest.mock import patch

from editor.encoding import check_gpu, encoding_options


class EncodingTests(unittest.TestCase):
    output = dict(width=1920, height=1080, fps=30, preset='medium', crf=18)

    def test_gpu_does_not_use_software_encoder_options(self):
        device, options = encoding_options(self.output, True, '/dev/dri/renderD129')
        self.assertEqual(device, ['-vaapi_device', '/dev/dri/renderD129'])
        self.assertIn('h264_vaapi', options)
        self.assertIn('hwupload', options[1])
        self.assertNotIn('-crf', options)
        self.assertNotIn('-preset', options)
        self.assertNotIn('-pix_fmt', options)

    def test_cpu_preserves_quality_settings(self):
        device, options = encoding_options(self.output)
        self.assertEqual(device, [])
        self.assertIn('libx264', options)
        self.assertEqual(options[options.index('-crf')+1], '18')

    @patch('editor.encoding.Path.exists', return_value=False)
    @patch('editor.encoding.subprocess.run')
    def test_missing_device_stops_before_encoding(self, run, exists):
        with self.assertRaisesRegex(RuntimeError, '--gpu false'):
            check_gpu(self.output, '/dev/dri/renderD128')
        run.assert_not_called()

    @patch('editor.encoding.Path.exists', return_value=True)
    @patch('editor.encoding.subprocess.run')
    def test_driver_failure_is_actionable(self, run, exists):
        run.return_value = subprocess.CompletedProcess([], 1, '', 'unsupported profile')
        with self.assertRaisesRegex(RuntimeError, 'unsupported profile'):
            check_gpu(self.output, '/dev/dri/renderD128')
        command = run.call_args.args[0]
        self.assertIn('color=black:s=1920x1080:r=30,format=rgb24', command)


if __name__ == '__main__':
    unittest.main()
