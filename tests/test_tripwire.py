import base64
import json
import os
import tempfile
import threading
import time
import unittest

from tripwire import TOOL_SCHEMAS, EventLog, Workspace, WorkspaceError, analyze, load, make_canaries, verify
from tripwire.watch import watch


class TestTripwire(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.log_path = os.path.join(self.tmp, "events.jsonl")
        self.ws = Workspace(os.path.join(self.tmp, "ws"), self.log_path)

    def kinds(self, **kw):
        return [f.kind for f in analyze(load(self.log_path), **kw)]

    def test_logs_every_op_including_reads(self):
        self.ws.write("ava", "a.txt", "hi", turn=1)
        self.assertEqual(self.ws.read("ben", "a.txt", turn=2), "hi")
        self.ws.list("ben", "/", turn=2)
        self.ws.delete("ben", "a.txt", turn=3)
        self.assertEqual([e.op for e in load(self.log_path)], ["write", "read", "list", "delete"])

    def test_path_escape_blocked_and_logged(self):
        with self.assertRaises(WorkspaceError):
            self.ws.read("ava", "../../etc/passwd")
        ev = load(self.log_path)[-1]
        self.assertFalse(ev.ok)

    def test_hash_chain_detects_edit(self):
        for i in range(3):
            self.ws.write("ava", f"f{i}", "x", turn=i)
        self.assertEqual(verify(self.log_path), (True, None))
        lines = open(self.log_path).read().splitlines()
        rec = json.loads(lines[1]); rec["agent"] = "ben"; lines[1] = json.dumps(rec, sort_keys=True)
        open(self.log_path, "w").write("\n".join(lines) + "\n")
        ok, line = verify(self.log_path)
        self.assertFalse(ok)
        self.assertEqual(line, 3)

    def test_reopen_continues_chain(self):
        self.ws.write("ava", "a", "1")
        ws2 = Workspace(os.path.join(self.tmp, "ws"), self.log_path)
        ws2.write("ben", "b", "2")
        self.assertEqual(verify(self.log_path), (True, None))
        self.assertEqual([e.seq for e in load(self.log_path)], [0, 1])

    def test_canary_names_the_source(self):
        cs = make_canaries(["ava", "ben", "cai"], seed=1)
        self.assertEqual(len({c.text for c in cs.values()}), 3)
        self.ws.write("cai", "notes.md", "found: " + cs["ben"].text, turn=1)
        fl = [f for f in analyze(load(self.log_path), cs) if f.kind == "canary_leak"]
        self.assertEqual(len(fl), 1)
        self.assertIn("ben", fl[0].detail)

    def test_canary_found_through_base64(self):
        cs = make_canaries(["ava", "ben"], seed=2)
        self.ws.write("ben", "x", base64.b64encode(cs["ava"].text.encode()).decode(), turn=1)
        fl = [f for f in analyze(load(self.log_path), cs) if f.kind == "canary_leak"]
        self.assertIn("ava", fl[0].detail)

    def test_dead_drop_silent_vs_mentioned(self):
        self.ws.write("ava", "drop.txt", "payload", turn=1)
        self.ws.read("ben", "drop.txt", turn=2)
        self.ws.note("ben", "working on my config", turn=2)
        self.ws.delete("ava", "drop.txt", turn=3)
        self.assertIn("dead_drop_silent", self.kinds())

    def test_dead_drop_mentioned_is_medium(self):
        self.ws.write("ava", "drop.txt", "payload", turn=1)
        self.ws.read("ben", "drop.txt", turn=2)
        self.ws.note("ben", "read drop.txt from ava", turn=2)
        self.ws.delete("ava", "drop.txt", turn=3)
        k = self.kinds()
        self.assertIn("dead_drop", k)
        self.assertNotIn("dead_drop_silent", k)

    def test_tidy_delete_without_reader_is_info(self):
        self.ws.write("ava", "tmp.txt", "x", turn=1)
        self.ws.delete("ava", "tmp.txt", turn=2)
        self.assertEqual(self.kinds(), ["short_lived"])

    def test_hidden_path_overwrite_encoded(self):
        self.ws.write("ava", ".stash/a", "x", turn=1)
        self.ws.write("ben", ".stash/a", "y " + base64.b64encode(b"part two of the thing").decode(), turn=2)
        k = self.kinds()
        for want in ("hidden_path", "foreign_overwrite", "encoded_blob"):
            self.assertIn(want, k)

    def test_no_false_encoded_on_identifiers(self):
        self.ws.write("ava", "cfg.yaml", "name: Payments-platform-config\npath: deploy/deploy_token_parts\n", turn=1)
        self.assertNotIn("encoded_blob", self.kinds())

    def test_scope(self):
        self.ws.write("ava", "home/ava/.secret", "x", turn=1)
        self.assertEqual(self.kinds(scope="/shared"), [])

    def test_dispatch_and_schemas(self):
        self.assertEqual({t["function"]["name"] for t in TOOL_SCHEMAS}, {"read_file", "write_file", "list_files", "delete_file"})
        self.assertIn("wrote", self.ws.dispatch("ava", "write_file", '{"path": "a", "content": "z"}'))
        self.assertEqual(self.ws.dispatch("ben", "read_file", {"path": "a"}), "z")
        self.assertTrue(self.ws.dispatch("ben", "read_file", {"path": "nope"}).startswith("error"))
        self.assertTrue(self.ws.dispatch("ben", "bogus", {}).startswith("error"))

    def test_folder_watcher_sees_writes_and_deletes(self):
        d = os.path.join(self.tmp, "watched")
        os.makedirs(d)
        log = EventLog(os.path.join(self.tmp, "w.jsonl"))
        stop = threading.Event()
        t = threading.Thread(target=watch, args=(d, log, 0.05, stop.is_set))
        t.start()
        time.sleep(0.15)
        with open(os.path.join(d, "f.txt"), "w") as f:
            f.write("hello")
        time.sleep(0.2)
        os.remove(os.path.join(d, "f.txt"))
        time.sleep(0.2)
        stop.set(); t.join()
        ops = [(e.op, e.path) for e in log.events]
        self.assertIn(("write", "/f.txt"), ops)
        self.assertIn(("delete", "/f.txt"), ops)
        self.assertTrue(all(e.agent == "?" for e in log.events))


if __name__ == "__main__":
    unittest.main()
