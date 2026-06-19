#!/usr/bin/env python3
"""
Fix all single-choice questions missing options.
Replace broken questions (3+ missing options) with KB equivalents that have full options.
"""

import json
import sys
sys.path.insert(0, __import__('os').path.dirname(__import__('os').path.abspath('.')))
import sc_knowledge_base as skb

DATA_FILE = 'data.js'

def main():
    # Load data.js
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    start = content.find('{')
    end = content.rfind('}') + 1
    data = json.loads(content[start:end])

    sc = data.get('single_choice', [])

    # Build KB lookup: stem -> (stem, opts, answer, explanation)
    kb_lookup = {}
    for ch_name, items in skb.SC_KB.items():
        for stem, opts, ans, expl in items:
            kb_lookup[stem] = (stem, opts, ans, expl)

    # Find broken questions and replace them
    fixed_count = 0
    kept_count = 0

    for i, q in enumerate(sc):
        opts = [q.get('option_a',''), q.get('option_b',''), q.get('option_c',''), q.get('option_d',''), q.get('option_e','')]
        empty_count = sum(1 for o in opts if not o or len(str(o).strip()) < 2)

        if empty_count >= 3:
            stem = q.get('stem', '')
            if stem in kb_lookup:
                kb_stem, kb_opts, kb_ans, kb_expl = kb_lookup[stem]
                sc[i] = {
                    'chapter': q.get('chapter', ''),
                    'number': q.get('number', 0),
                    'stem': kb_stem,
                    'option_a': kb_opts.get('A', ''),
                    'option_b': kb_opts.get('B', ''),
                    'option_c': kb_opts.get('C', ''),
                    'option_d': kb_opts.get('D', ''),
                    'option_e': kb_opts.get('E', ''),
                    'answer': kb_ans,
                    'explanation': kb_expl,
                }
                fixed_count += 1
            else:
                print(f"WARNING: No KB match for broken question #{i}: {stem[:60]}")
        else:
            kept_count += 1

    data['single_choice'] = sc

    # Save back
    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    wrapper = "QUESTION_DATA = \n\n" + json_str + "\n"
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        f.write(wrapper)

    print(f"Fixed {fixed_count} questions with missing options")
    print(f"Kept {kept_count} questions with sufficient options")
    print(f"Total SC: {len(sc)}")

    # Verify
    remaining_missing = 0
    for q in sc:
        opts = [q.get('option_a',''), q.get('option_b',''), q.get('option_c',''), q.get('option_d',''), q.get('option_e','')]
        empty_count = sum(1 for o in opts if not o or len(str(o).strip()) < 2)
        if empty_count >= 3:
            remaining_missing += 1
    print(f"Remaining questions with 3+ missing options: {remaining_missing}")

if __name__ == '__main__':
    main()
