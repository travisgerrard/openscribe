#!/usr/bin/env python3
import sys
sys.path.append('.')
from text_processor import text_processor
from settings_manager import settings_manager

print('=== Testing Filler Word Filtering ===')

# Test cases
test_cases = [
    "Um, the patient is, uh, doing well.",
    "Uh, I think, um, we should proceed with, ah, the treatment.",
    "The, uh, diagnosis is, um, clear and, er, straightforward.",
    "Hello um this is a test uh without punctuation",
    "Um um um multiple consecutive filler words uh uh",
    "Normal sentence without any filler words.",
    "",  # Empty string
    "Um",  # Only filler word
]

print('Current settings:')
print(f'  Filter enabled: {text_processor.is_filter_enabled()}')
print(f'  Filler words: {text_processor.get_filler_words()}')
print()

print('Testing with filtering ENABLED:')
text_processor.set_filter_enabled(True)
for i, test_text in enumerate(test_cases, 1):
    result = text_processor.clean_text(test_text)
    print(f'{i}. Original: "{test_text}"')
    print(f'   Filtered: "{result}"')
    print()

print('Testing with filtering DISABLED:')
text_processor.set_filter_enabled(False)
for i, test_text in enumerate(test_cases[:3], 1):  # Just test first 3
    result = text_processor.clean_text(test_text)
    print(f'{i}. Original: "{test_text}"')
    print(f'   No filter: "{result}"')
    print()

# Test custom filler words
print('Testing custom filler words:')
text_processor.set_filter_enabled(True)
text_processor.set_filler_words(["well", "actually", "like"])
test_text = "Well, actually, I think we should, like, proceed."
result = text_processor.clean_text(test_text)
print(f'Custom filler words: {text_processor.get_filler_words()}')
print(f'Original: "{test_text}"')
print(f'Filtered: "{result}"')

# Restore defaults
text_processor.set_filler_words(["um", "uh", "ah", "er", "hmm", "mm", "mhm"])
text_processor.set_filter_enabled(True)
print(f'\nRestored default settings')
print(f'Filter enabled: {text_processor.is_filter_enabled()}')
print(f'Filler words: {text_processor.get_filler_words()}') 