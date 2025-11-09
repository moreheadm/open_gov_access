#!/usr/bin/env python3
"""
Parse meeting narrative XML from board-mayor-topics-summary-xml command
and convert to JSON for downstream consumption.

Updated to handle person-based organization (not topic-based).
"""

import xml.etree.ElementTree as ET
import json
import sys
from typing import Dict, List, Any


def parse_meeting_narrative(xml_str: str) -> Dict[str, Any]:
    """
    Parse meetingNarrative XML and return as a Python dict.
    
    Args:
        xml_str: XML string from board-mayor-topics-summary-xml command
        
    Returns:
        Dict with meeting path and list of people with their moments
    """
    root = ET.fromstring(xml_str)
    
    people = []
    for person in root.findall("person"):
        person_name = person.get("name")
        person_role = person.get("role")
        
        moments = []
        for moment in person.findall("moment"):
            moment_id = moment.get("id")
            headline = (moment.findtext("headline") or "").strip()
            summary = (moment.findtext("summary") or "").strip()
            timestamps_str = (moment.findtext("timestamps") or "").strip()
            
            # Parse timestamps into a list
            timestamps = [ts.strip() for ts in timestamps_str.split(",") if ts.strip()]
            
            moments.append({
                "id": moment_id,
                "headline": headline,
                "summary": summary,
                "timestamps": timestamps,
            })
        
        people.append({
            "name": person_name,
            "role": person_role,
            "moments": moments,
        })
    
    return {
        "meeting": root.get("meeting"),
        "people": people,
    }


def parse_public_comments(xml_str: str) -> Dict[str, Any]:
    """Parse publicComments XML to dict."""
    root = ET.fromstring(xml_str)
    items = []
    for item in root.findall("item"):
        totals = item.find("totals").attrib if item.find("totals") is not None else {}
        comments = []
        for comment in (item.find("comments") or []).findall("comment"):
            comments.append({
                "index": comment.get("index"),
                "speaker": comment.get("speaker"),
                "position": comment.get("position"),
                "timestamp": comment.get("timestamp"),
                "text": "".join(comment.itertext()).strip(),
            })
        items.append({
            "id": item.get("id"),
            "description": (item.findtext("description") or "").strip(),
            "totals": totals,
            "comments": comments,
        })
    return {"meeting": root.get("meeting"), "items": items}


if __name__ == "__main__":
    # Read XML from stdin or file argument
    if len(sys.argv) > 1:
        with open(sys.argv[1], "r") as f:
            xml_input = f.read()
    else:
        xml_input = sys.stdin.read()
    
    # Parse and output as JSON
    parsed = parse_meeting_narrative(xml_input)
    print(json.dumps(parsed, indent=2))

