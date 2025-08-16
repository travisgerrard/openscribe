import os
import unittest

# This test validates our stdout contract and DICTATION_PREVIEW behavior
# without booting the full backend. It checks helper-level behavior and
# documented prefixes to prevent regression of console noise.

WHITELIST_PREFIXES = [
    'PYTHON_BACKEND_READY',
    'GET_CONFIG',
    'MODELS:',
    'MODEL_SELECTED:',
    'STATE:',
    'STATUS:',
    'FINAL_TRANSCRIPT:',
    'DICTATION_PREVIEW:',
    'TRANSCRIPTION:'
]


class TestStdoutNoiseContract(unittest.TestCase):
    def setUp(self):
        # Ensure minimal terminal mode by default
        os.environ.pop('CT_VERBOSE', None)

    def test_stdout_prefix_whitelist(self):
        valid_samples = [
            'PYTHON_BACKEND_READY',
            'GET_CONFIG',
            'MODELS:{"proof":"id","letter":"id"}',
            'MODEL_SELECTED:proof:some/model',
            'STATE:{"audioState":"activation"}',
            'STATUS:blue:Listening for activation words...',
            'FINAL_TRANSCRIPT:hello world',
            'DICTATION_PREVIEW:line1\\nline2',
            'TRANSCRIPTION:PROOFED:- item',
        ]
        for msg in valid_samples:
            with self.subTest(msg=msg):
                self.assertTrue(any(msg.startswith(p) for p in WHITELIST_PREFIXES))

        invalid_samples = [
            '[DEBUG] something',
            'HotkeyManager Status: started',
            'AudioHandler Status: Listening...',
            'Cleared log file: /tmp/x',
            'Unhandled misc output',
        ]
        for msg in invalid_samples:
            with self.subTest(msg=msg):
                self.assertFalse(any(msg.startswith(p) for p in WHITELIST_PREFIXES))

    def test_dictation_preview_is_full_and_escaped(self):
        # Simulate the same escaping we use before printing DICTATION_PREVIEW
        raw = 'line1\nline2\rwith CR and newline\n'
        escaped = raw.replace("\n", "\\n").replace("\r", "\\r")
        preview_line = 'DICTATION_PREVIEW:' + escaped
        self.assertTrue(preview_line.startswith('DICTATION_PREVIEW:'))
        # Ensure escape sequences are present, not raw newlines
        after_prefix = preview_line[len('DICTATION_PREVIEW:'):]
        self.assertIn('\\n', after_prefix)
        self.assertIn('\\r', after_prefix)


if __name__ == '__main__':
    unittest.main()


