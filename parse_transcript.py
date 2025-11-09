import json
import re
from pathlib import Path
from collections import defaultdict

# Read inputs
transcript_path = "/var/folders/m6/x5htrd9s1fx7910ykkwkhyq40000gp/T/tmp_dp8ekpy.txt"
output_path = "/var/folders/m6/x5htrd9s1fx7910ykkwkhyq40000gp/T/tmpezyqkdcp.xml"
officials_json_path = "/var/folders/m6/x5htrd9s1fx7910ykkwkhyq40000gp/T/tmpke6fmyis.json"

with open(transcript_path, 'r') as f:
    transcript = f.read()

with open(officials_json_path, 'r') as f:
    officials = json.load(f)

supervisors = set(officials.get('supervisors', []))
mayor = officials.get('mayor', '')

# Normalize timestamps
text_with_ts = re.sub(r'\[\^(\d{2})-(\d{2})-(\d{2})\]', r' [\1:\2:\3]', transcript)

# Split by >> which marks speaker transitions
segments = text_with_ts.split('>>')

# Parse segments to identify speakers and content
person_moments = defaultdict(list)

for i, segment in enumerate(segments):
    segment = segment.strip()
    if not segment:
        continue

    # Extract timestamps from this segment
    timestamps = re.findall(r'\[(\d{2}:\d{2}:\d{2})\]', segment)
    timestamps = sorted(set(timestamps))

    # Clean text
    clean_text = re.sub(r'\[\d{2}:\d{2}:\d{2}\]', '', segment).strip()
    clean_text = ' '.join(clean_text.split())

    # Identify speaker
    speaker = None

    # Check for Jackie Fielder
    if 'FIELDER' in clean_text or 'FILTER' in clean_text:
        if 'CHAIR' in clean_text or 'SUPERVISOR' in clean_text:
            speaker = 'Jackie Fielder'

    # Check for Bilal Mahmood
    if 'MAHMUD' in clean_text or 'MAHMOOD' in clean_text:
        if 'SUPERVISOR' in clean_text or 'CHAIR' in clean_text:
            speaker = 'Bilal Mahmood'

    # Check for other supervisors
    if not speaker:
        for name in supervisors:
            if name.upper() in clean_text.upper():
                speaker = name
                break

    # Filter for substantive content
    if speaker and len(clean_text) > 100:
        exclude_kw = ['ROLL CALL', 'SAME HOUSE SAME CALL', 'MOTION PASSES', 'EXCUSE', 'ADJOURNED', 'ANNOUNCEMENTS']
        include_kw = ['HEARING', 'CONCERN', 'ABUSE', 'VIOLATION', 'QUESTION', 'MOTION', 'POLICY', 'FACILITY', 'OVERSIGHT', 'ACCOUNTABILITY', 'DEBATE', 'AMENDMENT', 'POSITION', 'COMMEND', 'REQUEST', 'THANK', 'APPRECIATE', 'IMPORTANT', 'CRITICAL', 'VITAL', 'ISSUE', 'PROBLEM', 'FAILURE', 'CHALLENGE', 'SUPPORT', 'OPPOSE']

        if not any(kw in clean_text for kw in exclude_kw) and any(kw in clean_text for kw in include_kw):
            person_moments[speaker].append({'text': clean_text, 'timestamps': timestamps})

# Build XML
xml_lines = ['<?xml version="1.0" encoding="UTF-8"?>']
xml_lines.append(f'<meetingNarrative meeting="{transcript_path}">')

moment_id = 1
for person in sorted(person_moments.keys()):
    role = 'mayor' if person == mayor else 'supervisor'
    xml_lines.append(f'  <person name="{person}" role="{role}">')

    for moment in person_moments[person][:5]:
        text = moment['text']
        timestamps_str = ', '.join(moment['timestamps']) if moment['timestamps'] else '00:00:00'
        headline = text.split('.')[0][:100].strip()
        if len(text) > 100:
            headline += "..."

        xml_lines.append(f'    <moment id="{moment_id}">')
        xml_lines.append(f'      <headline>{headline}</headline>')
        xml_lines.append(f'      <summary>')
        xml_lines.append(f'        <![CDATA[')
        xml_lines.append(f'        {text[:1000]}')
        xml_lines.append(f'        ]]>')
        xml_lines.append(f'      </summary>')
        xml_lines.append(f'      <timestamps>{timestamps_str}</timestamps>')
        xml_lines.append(f'    </moment>')
        moment_id += 1

    xml_lines.append(f'  </person>')

xml_lines.append('</meetingNarrative>')

# Write output
output_dir = Path(output_path).parent
output_dir.mkdir(parents=True, exist_ok=True)

with open(output_path, 'w') as f:
    f.write('\n'.join(xml_lines))

print(f"Saved to {output_path}")

