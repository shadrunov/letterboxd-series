"""Validate yearly YAML diaries and metadata; never requires network access."""
from build import load_diary

diary = load_diary()
print(f'Validated {len(diary["entries"])} viewings and {len(diary["years"])} YAML files.')
