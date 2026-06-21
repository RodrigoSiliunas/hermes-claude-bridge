"""Tests for hermes_claude_bridge.parser."""

from hermes_claude_bridge.parser import OutputParser
from hermes_claude_bridge.schemas import ClaudeResult


def test_parse_file_edit():
    output = """
I'll edit the file for you.

● Read(0) ● Edit(1) ● Bash(2)

✓ Edited src/main.py

```diff
--- a/src/main.py
+++ b/src/main.py
@@ -1,3 +1,3 @@
 def hello():
-    return "world"
+    return "universe"
```

Done!
"""
    parser = OutputParser()
    edits = parser.extract_edits(output)
    assert len(edits) == 1
    assert edits[0].path == "src/main.py"
    assert "universe" in edits[0].diff


def test_parse_file_create():
    output = """
✓ Created src/new_file.py
"""
    parser = OutputParser()
    edits = parser.extract_edits(output)
    assert len(edits) == 1
    assert edits[0].path == "src/new_file.py"
    assert edits[0].operation == "create"


def test_parse_bash_commands():
    output = """
$ python -m pytest tests/ -v
==================
PASSED

$ ls -la
"""
    parser = OutputParser()
    cmds = parser.extract_bash_commands(output)
    assert len(cmds) == 2
    assert "pytest" in cmds[0].command
    assert "ls -la" in cmds[1].command


def test_enrich_result():
    result = ClaudeResult(
        task_id="abc",
        success=True,
        raw_output="\u2713 Edited src/main.py\n\n```diff\n- old\n+ new\n```",
    )
    parser = OutputParser()
    enriched = parser.enrich_result(result)
    assert len(enriched.file_edits) == 1
    assert enriched.file_edits[0].path == "src/main.py"
