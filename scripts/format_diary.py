"""Sort yearly diaries newest first and normalize their YAML without changing records."""
import argparse
import io
import sys
from pathlib import Path

import yaml as pyyaml
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedSeq
from diary import ROOT, diary_files, read_document, date_text

FIELD_ORDER = ('url', 'name', 'date', 'seasons', 'tags', 'rewatch', 'status', 'notes')


def clean_whitespace(text, nodes):
    """Normalize whitespace outside multiline scalar values such as personal notes."""
    protected = set()

    def protect(node):
        if isinstance(node, pyyaml.ScalarNode):
            if node.end_mark.line > node.start_mark.line:
                protected.update(range(node.start_mark.line, node.end_mark.line + 1))
        elif isinstance(node, pyyaml.MappingNode):
            for key, value in node.value:
                protect(key)
                protect(value)
        elif isinstance(node, pyyaml.SequenceNode):
            for child in node.value:
                protect(child)

    for node in nodes:
        protect(node)
    lines = []
    for number, line in enumerate(text.splitlines()):
        if number in protected:
            lines.append((line, True))
            continue
        line = line.rstrip(' \t')
        if not line:
            if lines and lines[-1][0]:
                lines.append(('', False))
            continue
        if line.startswith('- ') and lines and lines[-1][0] and not lines[-1][0].lstrip().startswith('#'):
            lines.append(('', False))
        lines.append((line, False))
    while lines and not lines[-1][0] and not lines[-1][1]:
        lines.pop()
    return '\n'.join(line for line, _ in lines) + '\n'


def formatted_document(path):
    original, rows = read_document(path)
    yaml = YAML(typ='rt')
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=2, offset=0)
    yaml.width = 4096
    data = yaml.load(original)
    if data is None:
        return original.rstrip() + ('\n\n' if original.strip() else '') + '[]\n'
    if not data:
        return original.rstrip() + '\n'
    positions = {id(entry): index for index, entry in enumerate(data)}
    # ruamel includes the original index as a secondary sort key. Make our keys
    # unique so reverse sorting still preserves the order of equal-date records.
    data.sort(key=lambda entry: (date_text(entry['date'], path.stem), -positions[id(entry)]), reverse=True)
    by_position = {node.start_mark.line: row for _, row, node in rows}
    for entry in data:
        for key in FIELD_ORDER:
            if key in entry:
                entry.move_to_end(key)
        if 'rewatch' in entry:
            entry['rewatch'] = by_position[entry.lc.line].get('rewatch', False)
        for key in ('seasons', 'tags'):
            value = entry.get(key)
            if isinstance(value, CommentedSeq) and not value.ca.items and not value.ca.comment:
                value.fa.set_flow_style()
    output = io.StringIO()
    yaml.dump(data, output)
    candidate = output.getvalue()
    candidate_rows = read_document(path, text=candidate)[1]
    candidate = clean_whitespace(candidate, [node for _, _, node in candidate_rows])
    expected = sorted((row for _, row, _ in rows), key=lambda row: row['date'], reverse=True)
    actual = [row for _, row, _ in read_document(path, text=candidate)[1]]
    if actual != expected:
        raise ValueError(f'{path.name}: formatting would change viewing data; no changes written')
    return candidate


def format_diaries(root=ROOT, check=False):
    updates = []
    for path in diary_files(root):
        result = formatted_document(path)
        if result != path.read_text():
            updates.append((path, result))
    if check:
        for path, _ in updates:
            print(f'Needs formatting: {path.name}')
    else:
        # Validate every candidate before writing any file.
        for path, result in updates:
            path.write_text(result)
            print(f'Formatted {path.name}')
    return len(updates)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Report formatting changes without writing files')
    args = parser.parse_args()
    try:
        changed = format_diaries(check=args.check)
    except (ValueError, OSError) as error:
        print(f'Formatting failed: {error}', file=sys.stderr)
        return 1
    return 1 if args.check and changed else 0


if __name__ == '__main__':
    raise SystemExit(main())
