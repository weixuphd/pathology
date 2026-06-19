#!/usr/bin/env python3
"""
Final Pathology Question Bank Generator
Merges existing data.js with new questions from sc_knowledge_base.py
and generates CSV, updates data.js, creates HTML pages.
"""

import re
import json
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sc_knowledge_base as skb

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data.js')
CHAPTER_NAMES = skb.CHAPTER_NAMES
TARGET_SC = 80
TARGET_TC = 10
TARGET_SA = 10


def load_existing_data():
    """Load existing questions from data.js."""
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    start = content.find('{')
    end = content.rfind('}') + 1
    data = json.loads(content[start:end])
    return data


def get_existing_counts(data):
    """Get question counts per chapter."""
    counts = {'single_choice': {}, 'terminology': {}, 'short_answer': {}}
    for qtype in counts:
        for item in data.get(qtype, []):
            ch = item.get('chapter', '')
            counts[qtype][ch] = counts[qtype].get(ch, 0) + 1
    return counts


def generate_new_questions(existing_data, existing_counts):
    """Generate new questions to fill gaps per chapter."""
    # Track existing stems to avoid duplicates
    existing_stems = set()
    for q in existing_data.get('single_choice', []):
        existing_stems.add(q.get('stem', ''))

    existing_terms = set()
    for t in existing_data.get('terminology', []):
        existing_terms.add(t.get('term', ''))

    existing_sa = set()
    for s in existing_data.get('short_answer', []):
        existing_sa.add(s.get('question', ''))

    sc_kb = skb.SC_KB
    tc_kb = skb.TC_KB
    sa_kb = skb.SA_KB

    new_sc = []
    new_tc = []
    new_sa = []

    for ch_idx, ch_name in enumerate(CHAPTER_NAMES):
        # --- Single Choice ---
        existing_sc_count = existing_counts['single_choice'].get(ch_name, 0)
        sc_needed = max(0, TARGET_SC - existing_sc_count)

        if ch_name in sc_kb:
            kb_items = sc_kb[ch_name]
            available = [(q, opts, ans, expl) for q, opts, ans, expl in kb_items
                        if q not in existing_stems]
            for i, (stem, opts, answer, explanation) in enumerate(available[:sc_needed]):
                new_sc.append({
                    'chapter': ch_name,
                    'number': existing_sc_count + i + 1,
                    'stem': stem,
                    **{f'option_{chr(65+j)}': v for j, (_, v) in enumerate(opts.items()) if v},
                    'answer': answer,
                    'explanation': explanation
                })

        # --- Terminology ---
        existing_tc_count = existing_counts['terminology'].get(ch_name, 0)
        tc_needed = max(0, TARGET_TC - existing_tc_count)

        if ch_name in tc_kb:
            kb_items = tc_kb[ch_name]
            available = [(term, defn) for term, defn in kb_items
                        if term not in existing_terms]
            for i, (term, definition) in enumerate(available[:tc_needed]):
                new_tc.append({
                    'chapter': ch_name,
                    'number': existing_tc_count + i + 1,
                    'term': term,
                    'english': '',
                    'type': '名词解释',
                    'definition': definition,
                    '_orig_index': len(new_tc)
                })

        # --- Short Answer ---
        existing_sa_count = existing_counts['short_answer'].get(ch_name, 0)
        sa_needed = max(0, TARGET_SA - existing_sa_count)

        if ch_name in sa_kb:
            kb_items = sa_kb[ch_name]
            available = [(q, a) for q, a in kb_items
                        if q not in existing_sa]
            for i, (question, answer) in enumerate(available[:sa_needed]):
                new_sa.append({
                    'chapter': ch_name,
                    'number': existing_sa_count + i + 1,
                    'question': question,
                    'type': '简答题',
                    'answer': answer
                })

    return new_sc, new_tc, new_sa


def save_to_csv(sc, tc, sa, filepath):
    """Save all questions to CSV."""
    with open(filepath, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)

        # Single choice
        writer.writerow(['---单选题---'])
        writer.writerow(['chapter', 'number', 'stem', 'option_a', 'option_b', 'option_c',
                         'option_d', 'option_e', 'answer', 'explanation'])
        for q in sc:
            writer.writerow([q['chapter'], q['number'], q['stem'],
                           q.get('option_a', ''), q.get('option_b', ''),
                           q.get('option_c', ''), q.get('option_d', ''),
                           q.get('option_e', ''), q['answer'], q['explanation']])

        # Terminology
        writer.writerow(['---名词解释---'])
        writer.writerow(['chapter', 'number', 'term', 'english', 'definition'])
        for q in tc:
            writer.writerow([q['chapter'], q['number'], q['term'],
                           q.get('english', ''), q['definition']])

        # Short answer
        writer.writerow(['---简答题---'])
        writer.writerow(['chapter', 'number', 'question', 'answer'])
        for q in sa:
            writer.writerow([q['chapter'], q['number'], q['question'], q['answer']])


def update_data_js(existing_data, new_sc, new_tc, new_sa):
    """Merge new questions into existing data and save as data.js."""
    combined_sc = existing_data.get('single_choice', []) + new_sc
    combined_tc = existing_data.get('terminology', []) + new_tc
    combined_sa = existing_data.get('short_answer', []) + new_sa

    # Renumber per chapter
    for qtype, items in [('single_choice', combined_sc), ('terminology', combined_tc), ('short_answer', combined_sa)]:
        chapter_nums = {}
        for item in items:
            ch = item['chapter']
            chapter_nums[ch] = chapter_nums.get(ch, 0) + 1
            item['number'] = chapter_nums[ch]

    new_data = {
        'single_choice': combined_sc,
        'terminology': combined_tc,
        'short_answer': combined_sa
    }

    json_str = json.dumps(new_data, ensure_ascii=False, indent=2)
    wrapper = "QUESTION_DATA = \n\n" + json_str + "\n"

    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        f.write(wrapper)

    return new_data


def create_html_pages(new_data, output_dir):
    """Create per-chapter HTML pages."""
    os.makedirs(output_dir, exist_ok=True)

    for ch_name in CHAPTER_NAMES:
        sc_items = [q for q in new_data['single_choice'] if q['chapter'] == ch_name]
        tc_items = [q for q in new_data['terminology'] if q['chapter'] == ch_name]
        sa_items = [q for q in new_data['short_answer'] if q['chapter'] == ch_name]

        ch_num = ch_name.split('章')[0].replace('第', '')
        filename = f"chapter_{ch_num.zfill(2)}.html"
        filepath = os.path.join(output_dir, filename)

        # Escape HTML
        def esc(s):
            return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(ch_name)} - 病理学题库</title>
<style>
:root {{
    --primary: #1a5276; --primary-light: #2980b9;
    --accent: #16a085; --danger: #e74c3c; --warning: #f39c12;
    --bg: #f0f2f5; --card: #fff; --text: #2c3e50; --text-light: #7f8c8d;
    --border: #e1e8ed; --shadow: 0 2px 12px rgba(0,0,0,.08); --radius: 12px;
}}
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{
    font-family: -apple-system, BlinkMacSystemFont, "PingFang SC", "Microsoft YaHei", sans-serif;
    background: var(--bg); color: var(--text); padding-bottom: 40px;
}}
.top-nav {{ position:sticky; top:0; z-index:100; background:var(--primary); color:#fff; padding:12px 16px; display:flex; align-items:center; gap:10px; }}
.top-nav h1 {{ font-size:1.1em; flex:1; }}
.top-nav button {{ background:rgba(255,255,255,.15); border:none; color:#fff; padding:7px 12px; border-radius:18px; font-size:.8em; cursor:pointer; }}
.card {{ background:var(--card); border-radius:var(--radius); padding:20px; margin-bottom:12px; box-shadow:var(--shadow); }}
.card-header {{ display:flex; align-items:center; gap:8px; margin-bottom:12px; flex-wrap:wrap; }}
.badge {{ font-size:.72em; padding:3px 9px; border-radius:10px; font-weight:600; }}
.b-num {{ background:#e8f0fe; color:var(--primary-light); }} .b-type {{ background:#e8f8f5; color:var(--accent); }}
.stem {{ font-size:1.05em; line-height:1.8; margin-bottom:14px; }}
.options {{ list-style:none; display:flex; flex-direction:column; gap:7px; }}
.opt {{ padding:11px 12px; border:2px solid var(--border); border-radius:8px; display:flex; align-items:flex-start; gap:9px; font-size:.93em; line-height:1.5; }}
.ol {{ width:26px; height:26px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-weight:700; font-size:.8em; flex-shrink:0; }}
.oa .ol {{ background:#ebf5fb; color:#3498db; }} .ob .ol {{ background:#fdf2e9; color:#e67e22; }}
.oc .ol {{ background:#eafaf1; color:#27ae60; }} .od .ol {{ background:#f4ecf7; color:#8e44ad; }}
.oe .ol {{ background:#fdedec; color:#e74c3c; }}
.ans-box {{ display:none; margin-top:12px; padding:14px; border-radius:8px; font-size:.9em; line-height:1.7; }}
.ans-box.show {{ display:block; }}
.ans-choice {{ background:#eafaf1; border-left:4px solid var(--accent); }}
.ans-term {{ background:#f8f9fa; }}
.ans-sa {{ background:#fef9e7; border-left:4px solid var(--warning); }}
.ans-label {{ font-weight:700; color:var(--accent); margin-bottom:4px; }}
.term-name {{ font-size:1.1em; font-weight:600; color:var(--primary); margin-bottom:2px; }}
.term-en {{ font-size:.82em; color:var(--text-light); font-style:italic; margin-bottom:10px; }}
.sa-q {{ font-size:1.05em; line-height:1.7; margin-bottom:10px; }}
.btn {{ padding:7px 14px; border-radius:18px; border:1px solid var(--border); background:#fff; font-size:.82em; cursor:pointer; display:inline-flex; align-items:center; gap:4px; transition:.2s; }}
.btn-a {{ background:var(--accent); color:#fff; border-color:var(--accent); }}
.section-title {{ font-size:1.2em; color:var(--primary); margin:24px 0 12px; padding-bottom:8px; border-bottom:2px solid var(--primary); }}
.nav-links {{ margin:20px 0; display:flex; gap:8px; flex-wrap:wrap; }}
.nav-links a {{ text-decoration:none; color:var(--primary); padding:4px 8px; border:1px solid var(--primary); border-radius:4px; font-size:.8em; }}
.nav-links a:hover {{ background:var(--primary); color:#fff; }}
</style>
</head>
<body>
<div class="top-nav">
    <h1>{esc(ch_name)}</h1>
    <a href="index.html" style="color:#fff;text-decoration:none;">🏠 目录</a>
</div>

<div style="padding:12px;max-width:800px;margin:0 auto;">
    <div class="nav-links">
"""
        # Navigation links
        for i, ch in enumerate(CHAPTER_NAMES):
            ch_n = ch.split('章')[0].replace('第', '')
            html += f'        <a href="chapter_{ch_n.zfill(2)}.html">{esc(ch)}</a>\n'

        html += """    </div>

"""

        # Single choice questions
        if sc_items:
            html += f'    <h2 class="section-title">📝 单选题 ({len(sc_items)}题)</h2>\n'
            for q in sc_items:
                opts = [{'l':'A','t':str(q.get('option_a',''))},{'l':'B','t':str(q.get('option_b',''))},
                       {'l':'C','t':str(q.get('option_c',''))},{'l':'D','t':str(q.get('option_d',''))},
                       {'l':'E','t':str(q.get('option_e',''))}]
                opts = [o for o in opts if o['t'].strip()]

                html += f'    <div class="card">\n'
                html += f'        <div class="card-header">\n'
                html += f'            <span class="badge b-num">第{q["number"]}题</span>\n'
                html += f'            <span class="badge b-type">单选题</span>\n'
                html += f'        </div>\n'
                html += f'        <div class="stem">{esc(q["stem"])}</div>\n'
                html += f'        <ul class="options">\n'
                for o in opts:
                    html += f'            <li class="opt o{o["l"].lower()}"><span class="ol">{o["l"]}</span><span>{esc(o["t"])}</span></li>\n'
                html += f'        </ul>\n'
                html += f'        <div class="act-bar" style="margin-top:14px;padding-top:12px;border-top:1px solid var(--border);">\n'
                html += f'            <button class="btn btn-a" onclick="toggleAns(this)">💡 显示答案</button>\n'
                html += f'        </div>\n'
                html += f'        <div class="ans-box ans-choice" id="ansBox">\n'
                html += f'            <div class="ans-label">✅ 正确答案：<strong>{esc(q["answer"])}</strong></div>\n'
                html += f'            <div style="margin-top:8px;color:#555">{esc(q["explanation"])}</div>\n'
                html += f'        </div>\n'
                html += f'    </div>\n'

        # Terminology
        if tc_items:
            html += f'    <h2 class="section-title">📖 名词解释 ({len(tc_items)}题)</h2>\n'
            for q in tc_items:
                html += f'    <div class="card">\n'
                html += f'        <div class="card-header">\n'
                html += f'            <span class="badge b-num">第{q["number"]}题</span>\n'
                html += f'            <span class="badge b-type">名词解释</span>\n'
                html += f'        </div>\n'
                html += f'        <div class="term-name">{esc(q["term"])}</div>\n'
                html += f'        <div class="term-en">{esc(q.get("english",""))}</div>\n'
                html += f'        <div class="act-bar" style="margin-top:14px;padding-top:12px;border-top:1px solid var(--border);">\n'
                html += f'            <button class="btn btn-a" onclick="toggleAns(this)">💡 显示释义</button>\n'
                html += f'        </div>\n'
                html += f'        <div class="ans-box ans-term" id="ansBox">{esc(q["definition"])}</div>\n'
                html += f'    </div>\n'

        # Short answer
        if sa_items:
            html += f'    <h2 class="section-title">✍️ 简答题 ({len(sa_items)}题)</h2>\n'
            for q in sa_items:
                html += f'    <div class="card">\n'
                html += f'        <div class="card-header">\n'
                html += f'            <span class="badge b-num">第{q["number"]}题</span>\n'
                html += f'            <span class="badge b-type">简答题</span>\n'
                html += f'        </div>\n'
                html += f'        <div class="sa-q">{esc(q["question"])}</div>\n'
                html += f'        <div class="act-bar" style="margin-top:14px;padding-top:12px;border-top:1px solid var(--border);">\n'
                html += f'            <button class="btn btn-a" onclick="toggleAns(this)">💡 显示参考答案</button>\n'
                html += f'        </div>\n'
                html += f'        <div class="ans-box ans-sa" id="ansBox">{esc(q["answer"])}</div>\n'
                html += f'    </div>\n'

        html += """
</div>

<script>
function toggleAns(btn) {
    const box = btn.parentElement.nextElementSibling;
    if (box.classList.contains('show')) {
        box.classList.remove('show');
        btn.textContent = '💡 显示答案';
    } else {
        box.classList.add('show');
        btn.textContent = '🔄 隐藏';
    }
}
</script>
</body>
</html>"""

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)


def main():
    print("=" * 70)
    print("PATHOLOGY QUESTION BANK - FINAL GENERATOR")
    print("=" * 70)

    # Load existing data
    print("\nLoading existing data.js...")
    existing_data = load_existing_data()
    print(f"  Loaded {len(existing_data['single_choice'])} single_choice")
    print(f"  Loaded {len(existing_data['terminology'])} terminology")
    print(f"  Loaded {len(existing_data['short_answer'])} short_answer")

    # Get existing counts
    existing_counts = get_existing_counts(existing_data)

    # Generate new questions
    print("\nGenerating new questions...")
    new_sc, new_tc, new_sa = generate_new_questions(existing_data, existing_counts)
    print(f"  Generated {len(new_sc)} new single_choice")
    print(f"  Generated {len(new_tc)} new terminology")
    print(f"  Generated {len(new_sa)} new short_answer")

    # Save to CSV
    csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'questions.csv')
    print(f"\nSaving to {csv_path}...")
    save_to_csv(new_sc, new_tc, new_sa, csv_path)

    # Update data.js
    print("\nUpdating data.js...")
    new_data = update_data_js(existing_data, new_sc, new_tc, new_sa)

    # Print summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    for ch_name in CHAPTER_NAMES:
        sc_count = sum(1 for q in new_data['single_choice'] if q['chapter'] == ch_name)
        tc_count = sum(1 for q in new_data['terminology'] if q['chapter'] == ch_name)
        sa_count = sum(1 for q in new_data['short_answer'] if q['chapter'] == ch_name)
        total = sc_count + tc_count + sa_count
        print(f"{ch_name}: SC={sc_count} TC={tc_count} SA={sa_count} (Total={total})")

    print(f"\nTotal: SC={len(new_data['single_choice'])} TC={len(new_data['terminology'])} SA={len(new_data['short_answer'])}")
    print(f"Grand Total: {len(new_data['single_choice']) + len(new_data['terminology']) + len(new_data['short_answer'])}")

    # Create HTML pages
    print("\nCreating HTML pages...")
    pages_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pages')
    create_html_pages(new_data, pages_dir)
    print(f"  Created {len(CHAPTER_NAMES)} HTML pages in {pages_dir}")

    print("\nDone!")


if __name__ == '__main__':
    main()
